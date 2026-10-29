"""The Celery task that checks Hertz and sends one Pushover notification per new group of matching cars."""

import warnings
from datetime import UTC, date, datetime
from unittest import mock

import pytest
from django.core.cache import cache

from scheduler import hertz
from scheduler.models import NotifiedRide, SavedSearch
from scheduler.tasks import check_hertz

pytestmark = pytest.mark.django_db


def route(id, pickup='Stockholm Arlanda Flygplats / Self Service Kiosk', ret='Göteborg Centralstation'):
    return {
        'id': id,
        'transportOfferId': id,
        'pickupLocation': {'name': pickup, 'kiosk': True, 'geoLat': 59.65, 'geoLon': 17.93},
        'returnLocation': {'name': ret, 'kiosk': True, 'geoLat': 57.71, 'geoLon': 11.97},
        'availableAt': '2025-08-12T07:00:00',
        'latestReturn': '2025-08-14T19:00:00',
        'carModel': 'VOLVO V60 T6 AUT AWD NE PLUS D',
        'distance': 520.0,
        'travelTime': 300,
    }


@pytest.fixture
def api(monkeypatch):
    payload = [
        {'pickupLocationName': 'x', 'returnLocationName': 'y', 'routes': [route(101), route(102, ret='Kalmar Airport')]}
    ]
    monkeypatch.setattr('scheduler.hertz.fetch_routes', lambda: payload)
    return payload


@pytest.fixture
def pushover(monkeypatch):
    """A configured Pushover that accepts every message (set return_value/side_effect to change that)."""
    monkeypatch.setenv('PUSHOVER_USER', 'test-user')
    monkeypatch.setenv('PUSHOVER_TOKEN', 'test-token')
    sender = mock.Mock(return_value=True)
    monkeypatch.setattr('scheduler.pushover.send', sender)
    monkeypatch.setattr('scheduler.routemap.render', lambda origin, destination: b'map-jpeg')
    return sender


@pytest.fixture
def owner(django_user_model):
    return django_user_model.objects.create_user('henrik', password='secret-pass-123')


def make_search(owner, **fields):
    defaults = {'origin': '*', 'destination': 'Göteborg*', 'date_from': date(2025, 8, 1), 'date_to': date(2025, 8, 31)}
    return SavedSearch.objects.create(owner=owner, **{**defaults, **fields})


def test_notifies_a_matching_ride_once(api, pushover, owner):
    make_search(owner)
    check_hertz()
    check_hertz()
    assert pushover.call_count == 1
    message = pushover.call_args.args[0]
    assert 'Göteborg Centralstation' in message
    ride = NotifiedRide.objects.get()
    assert (ride.ride_id, ride.car_type, ride.distance) == ('101', 'VOLVO V60 T6 AUT AWD NE PLUS D', 520.0)


def test_the_notification_follows_the_chosen_design(api, pushover, owner, settings):
    settings.SITE_URL = 'https://hertz.example.com'
    make_search(owner)
    check_hertz()
    kwargs = pushover.call_args.kwargs
    assert pushover.call_args.args[0].split('\n') == [
        '<font color="#e8890c"><b>A</b></font> <b>Stockholm Arlanda Flygplats</b>',
        'from 2025-08-12 07:00 (now)',
        '<font color="#e0453a"><b>B</b></font> <b>Göteborg Centralstation</b>',
        'by 2025-08-14 19:00',
        'Volvo V60 T6 AUT AWD NE PLUS D',
    ]
    assert kwargs['title'] == 'Arlanda → Göteborg C'
    assert (kwargs['url'], kwargs['url_title']) == ('https://hertz.example.com/#route-101', 'Show route')
    assert (kwargs['html'], kwargs['image']) == (True, b'map-jpeg')


def test_identical_cars_get_one_notification(api, pushover, owner):
    api[0]['routes'].append(route(103))
    make_search(owner)
    check_hertz()
    assert pushover.call_count == 1
    assert '2 × Volvo V60 T6 AUT AWD NE PLUS D' in pushover.call_args.args[0]
    assert set(NotifiedRide.objects.values_list('ride_id', flat=True)) == {'101', '103'}


def test_another_identical_car_does_not_notify_again(api, pushover, owner):
    make_search(owner)
    check_hertz()
    api[0]['routes'].append(route(103))
    check_hertz()
    assert pushover.call_count == 1


def test_ignores_rides_outside_the_search_dates(api, pushover, owner):
    make_search(owner, date_from=date(2025, 9, 1), date_to=date(2025, 9, 30))
    check_hertz()
    assert not pushover.called
    assert not NotifiedRide.objects.exists()


def test_ignores_rides_to_other_destinations(api, pushover, owner):
    make_search(owner, destination='Luleå*')
    check_hertz()
    assert not pushover.called


def test_survives_hertz_being_down(monkeypatch, pushover, owner):
    def broken():
        raise ConnectionError('timeout')

    monkeypatch.setattr('scheduler.hertz.fetch_routes', broken)
    make_search(owner)
    check_hertz()
    assert not pushover.called


def test_keeps_the_routes_for_the_dashboard(api, pushover):
    check_hertz()
    data, fetched_at = cache.get(hertz.SNAPSHOT_KEY)
    assert data == api
    assert fetched_at.tzinfo is not None


def test_failed_send_is_retried_on_the_next_run(api, pushover, owner):
    make_search(owner)
    pushover.return_value = False
    check_hertz()
    assert not NotifiedRide.objects.exists()
    pushover.return_value = True
    check_hertz()
    assert pushover.call_count == 2
    assert NotifiedRide.objects.get().ride_id == '101'


def test_send_error_releases_the_ride_and_the_run_goes_on(api, pushover, owner):
    make_search(owner, destination='*')
    pushover.side_effect = [RuntimeError('boom'), True]
    check_hertz()
    assert list(NotifiedRide.objects.values_list('ride_id', flat=True)) == ['102']


def test_notifies_without_a_map_when_it_cannot_be_drawn(api, pushover, owner, monkeypatch):
    monkeypatch.setattr('scheduler.routemap.render', lambda origin, destination: None)
    make_search(owner)
    check_hertz()
    assert pushover.call_args.kwargs['image'] is None
    assert NotifiedRide.objects.exists()


def test_skips_notifying_without_pushover(api, pushover, owner, monkeypatch):
    monkeypatch.delenv('PUSHOVER_TOKEN')
    make_search(owner)
    check_hertz()
    assert not pushover.called
    assert not NotifiedRide.objects.exists()
    assert cache.get(hertz.SNAPSHOT_KEY)  # the dashboard still gets fresh routes


def test_saves_hertz_times_as_swedish_time(api, pushover, owner):
    make_search(owner)
    with warnings.catch_warnings():
        warnings.simplefilter('error', RuntimeWarning)  # Django warns when a naive datetime is saved
        check_hertz()
    ride = NotifiedRide.objects.get()
    # 07:00 in Stockholm in August (summer time, UTC+2)
    assert ride.available_at == datetime(2025, 8, 12, 5, 0, tzinfo=UTC)
    assert ride.latest_return == datetime(2025, 8, 14, 17, 0, tzinfo=UTC)


def test_escapes_html_in_hertz_names(api, pushover, owner):
    api[0]['routes'][0]['returnLocation']['name'] = 'Göteborg <b>C</b> & Co'
    make_search(owner)
    check_hertz()
    message = pushover.call_args.args[0]
    assert '<b>Göteborg &lt;b&gt;C&lt;/b&gt; &amp; Co</b>' in message


def test_skips_routes_with_broken_times(api, pushover, owner):
    api[0]['routes'][0]['availableAt'] = None
    api[0]['routes'][1]['latestReturn'] = 'soon'
    make_search(owner, destination='*')
    check_hertz()
    assert not pushover.called
