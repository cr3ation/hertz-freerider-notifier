"""Reading rides out of the API's JSON, and the routes snapshot the worker keeps for the dashboard."""

from datetime import timedelta

import pytest
from django.core.cache import cache
from django.utils import timezone

from scheduler import hertz


def test_rides_parses_times_as_swedish_time(transport_routes):
    rides = list(hertz.rides(transport_routes))
    assert len(rides) == 95
    ride = rides[0]
    assert ride.available_at.tzinfo == hertz.TZ
    assert ride.available_at.isoformat(timespec='minutes')[:16] == ride.route['availableAt'][:16]
    assert ride.origin == ride.route['pickupLocation']['name']


def test_rides_skips_what_it_cannot_read():
    data = [
        {'routes': [{'id': 1, 'availableAt': '2025-08-12T07:00:00', 'latestReturn': '2025-08-13T07:00:00'}]},
        {'routes': [{'availableAt': '2025-08-12T07:00:00', 'latestReturn': '2025-08-13T07:00:00'}]},  # no id
        {'routes': [{'id': 2, 'availableAt': None, 'latestReturn': '2025-08-13T07:00:00'}]},
        {'routes': [{'id': 3, 'availableAt': 'soon', 'latestReturn': '2025-08-13T07:00:00'}]},
        {'routes': None},
        'junk',
    ]
    assert [ride.id for ride in hertz.rides(data)] == ['1']
    assert list(hertz.rides(None)) == []


def test_group_identical_cars(transport_routes):
    groups = hertz.group_identical(hertz.rides(transport_routes))
    assert len(groups) == 82
    for group in groups:
        first = group[0]
        for ride in group:
            assert (ride.origin, ride.destination, ride.available_at, ride.route['carModel']) == (
                first.origin,
                first.destination,
                first.available_at,
                first.route['carModel'],
            )


@pytest.fixture
def live(monkeypatch):
    calls = []

    def fetch():
        calls.append(1)
        return [{'routes': []}]

    monkeypatch.setattr(hertz, 'fetch_routes', fetch)
    return calls


def test_latest_routes_uses_a_fresh_snapshot(live):
    snapshot = ([{'routes': ['cached']}], timezone.now() - timedelta(minutes=3))
    cache.set(hertz.SNAPSHOT_KEY, snapshot, None)
    assert hertz.latest_routes() == snapshot
    assert live == []


def test_latest_routes_fetches_when_the_snapshot_is_old(live):
    cache.set(hertz.SNAPSHOT_KEY, ([], timezone.now() - timedelta(hours=1)), None)
    data, fetched_at = hertz.latest_routes()
    assert (data, len(live)) == ([{'routes': []}], 1)
    assert cache.get(hertz.SNAPSHOT_KEY) == (data, fetched_at)


def test_latest_routes_works_without_the_cache(live, monkeypatch):
    def down(*args, **kwargs):
        raise ConnectionError('Redis is down')

    monkeypatch.setattr(cache, 'get', down)
    monkeypatch.setattr(cache, 'set', down)
    assert hertz.latest_routes()[0] == [{'routes': []}]
    assert hertz.fetch_location_names() == []  # the locations call is blocked by the test, then cached nowhere
