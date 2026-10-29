"""The Celery task that checks Hertz and sends one Pushover notification per new matching ride."""

from datetime import date
from unittest import mock

import pytest

from scheduler.models import NotifiedRide, SavedSearch
from scheduler.tasks import check_hertz

pytestmark = pytest.mark.django_db


def route(id, pickup='Stockholm Arlanda Flygplats / Self Service Kiosk', ret='Göteborg Centralstation'):
    return {
        'id': id,
        'pickupLocation': {'name': pickup},
        'returnLocation': {'name': ret},
        'availableAt': '2025-08-12T07:00:00',
        'latestReturn': '2025-08-14T19:00:00',
        'carModel': 'VOLVO V60 T6 AUT AWD NE PLUS D',
        'distance': 520.0,
        'travelTime': 300,
    }


@pytest.fixture
def api(monkeypatch):
    payload = [{'pickupLocationName': 'x', 'returnLocationName': 'y', 'routes': [route(101), route(102, ret='Kalmar Airport')]}]
    monkeypatch.setattr('scheduler.tasks.fetch_routes', lambda: payload)
    return payload


@pytest.fixture
def pushover(monkeypatch):
    sender = mock.Mock()
    monkeypatch.setattr('scheduler.tasks.send_pushover', sender)
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

    monkeypatch.setattr('scheduler.tasks.fetch_routes', broken)
    make_search(owner)
    check_hertz()
    assert not pushover.called
