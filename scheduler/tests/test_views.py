"""Dashboard and search management, with the Hertz API mocked."""

from datetime import date, timedelta

import pytest
from django.core.cache import cache
from django.db import IntegrityError
from django.utils import timezone

from scheduler import hertz as hertz_api
from scheduler.models import NotifiedRide, SavedSearch

pytestmark = pytest.mark.django_db


@pytest.fixture
def hertz(monkeypatch, transport_routes):
    """Serve the fixture data instead of calling Hertz."""
    monkeypatch.setattr('scheduler.hertz.fetch_routes', lambda: transport_routes)
    monkeypatch.setattr(
        'scheduler.hertz.fetch_location_names', lambda: ['Stockholm Arlanda Flygplats', 'Kalmar Airport']
    )


@pytest.fixture
def user(django_user_model):
    return django_user_model.objects.create_user('henrik', password='secret-pass-123')


@pytest.fixture
def other_search(django_user_model):
    other = django_user_model.objects.create_user('someone', password='secret-pass-123')
    return SavedSearch.objects.create(
        owner=other, origin='Kalmar*', destination='*', date_from=date(2025, 8, 1), date_to=date(2025, 8, 31)
    )


@pytest.fixture
def logged_in(client, user):
    client.force_login(user)
    return client


def search_form(**overrides):
    data = {'date_from': '2025-08-01', 'date_to': '2025-08-31', 'origin': 'Stockholm*', 'destination': '*'}
    data.update(overrides)
    return data


def test_login_page_renders(client):
    response = client.get('/accounts/login/')
    assert response.status_code == 200
    assert b'Sign in' in response.content


def test_dashboard_requires_login(client):
    response = client.get('/')
    assert response.status_code == 302
    assert response.url.startswith('/accounts/login/')


def test_dashboard_lists_routes(logged_in, hertz):
    response = logged_in.get('/')
    assert response.status_code == 200
    assert len(response.context['available_routes']) == 82
    assert response.context['total_cars'] <= 95
    assert b'id="route-details-data"' in response.content
    assert b'<datalist id="hertz-locations">' in response.content


def test_dashboard_shows_api_errors(logged_in, monkeypatch):
    def broken():
        raise ConnectionError('Hertz is down')

    monkeypatch.setattr('scheduler.hertz.fetch_routes', broken)
    monkeypatch.setattr('scheduler.hertz.fetch_location_names', lambda: [])
    response = logged_in.get('/')
    assert response.status_code == 200
    assert b'Hertz is down' in response.content


def test_history_lists_notifications(logged_in, hertz):
    NotifiedRide.objects.create(
        ride_id='1', pickup_location_name='Kiruna AP', return_location_name='Luleå', car_type='VOLVO XC40 B3 FWD AUT'
    )
    response = logged_in.get('/')
    [entry] = response.context['notified_history']
    assert (entry['pickup_short'], entry['pickup_airport'], entry['car']['name']) == ('Kiruna', True, 'Volvo XC40')


def test_create_search(logged_in, hertz, user):
    response = logged_in.post('/searches/', search_form())
    assert response.status_code == 302
    assert response.url == '/?tab=searches'
    saved = SavedSearch.objects.get()
    assert (saved.owner, saved.origin) == (user, 'Stockholm*')


def test_update_own_search(logged_in, hertz, user):
    saved = SavedSearch.objects.create(owner=user, **search_form(origin='Kiruna*'))
    response = logged_in.post(f'/searches/{saved.pk}/', search_form(origin='Luleå*'))
    assert response.status_code == 302
    saved.refresh_from_db()
    assert saved.origin == 'Luleå*'


def test_cannot_edit_someone_elses_search(logged_in, hertz, other_search):
    assert logged_in.get(f'/?edit={other_search.pk}').status_code == 404
    response = logged_in.post(f'/searches/{other_search.pk}/', search_form(origin='Hacked*'))
    assert response.status_code == 404
    other_search.refresh_from_db()
    assert other_search.origin == 'Kalmar*'


def test_delete_own_search(logged_in, user):
    saved = SavedSearch.objects.create(owner=user, **search_form())
    assert logged_in.get(f'/searches/{saved.pk}/delete/').status_code == 405
    response = logged_in.post(f'/searches/{saved.pk}/delete/')
    assert response.status_code == 302
    assert not SavedSearch.objects.exists()


def test_cannot_delete_someone_elses_search(logged_in, other_search):
    assert logged_in.post(f'/searches/{other_search.pk}/delete/').status_code == 404
    assert SavedSearch.objects.filter(pk=other_search.pk).exists()


def test_search_dates_must_be_in_order(logged_in, hertz):
    response = logged_in.post('/searches/', search_form(date_from='2025-09-01', date_to='2025-08-01'))
    assert response.status_code == 200
    assert response.context['form'].errors == {'date_to': ['"Date to" must be on or after "Date from".']}
    assert response.context['active_tab'] == 'searches'
    assert not SavedSearch.objects.exists()


def test_database_refuses_reversed_dates(user):
    with pytest.raises(IntegrityError):
        SavedSearch.objects.create(owner=user, **search_form(date_from='2025-09-01', date_to='2025-08-01'))


@pytest.mark.parametrize('tab, active', [('notifications', 'notifications'), ("live');alert(1);//", 'live')])
def test_tab_parameter_only_takes_known_tabs(logged_in, hertz, tab, active):
    response = logged_in.get('/', {'tab': tab})
    assert response.context['active_tab'] == active
    assert b'alert(1)' not in response.content


def test_search_endpoints_only_take_posts(logged_in, user):
    saved = SavedSearch.objects.create(owner=user, **search_form())
    assert logged_in.get('/searches/').status_code == 405
    assert logged_in.get(f'/searches/{saved.pk}/').status_code == 405
    assert logged_in.post('/').status_code == 405


def test_edit_link_opens_the_search_in_the_form(logged_in, hertz, user):
    saved = SavedSearch.objects.create(owner=user, **search_form(origin='Kiruna*'))
    response = logged_in.get(f'/?edit={saved.pk}')
    assert response.context['form'].instance == saved
    assert response.context['active_tab'] == 'searches'
    assert f'action="/searches/{saved.pk}/"'.encode() in response.content


def test_searches_show_how_many_routes_match(logged_in, hertz, user):
    SavedSearch.objects.create(owner=user, **search_form(origin='Stockholm*', date_to='2025-12-31'))
    response = logged_in.get('/')
    [search] = response.context['searches']
    assert search.match_count == 25


def test_dashboard_uses_the_workers_snapshot(logged_in, monkeypatch, transport_routes):
    fetched_at = timezone.now() - timedelta(minutes=1)
    cache.set(hertz_api.SNAPSHOT_KEY, (transport_routes, fetched_at), None)

    def unreachable():
        raise AssertionError('the dashboard fetched although a fresh snapshot was there')

    monkeypatch.setattr('scheduler.hertz.fetch_routes', unreachable)
    monkeypatch.setattr('scheduler.hertz.fetch_location_names', lambda: [])
    response = logged_in.get('/')
    assert len(response.context['available_routes']) == 82
    assert response.context['updated_at'] == fetched_at
