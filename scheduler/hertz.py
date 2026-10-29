"""The Hertz Freerider API: fetching it, keeping the latest answer, and reading rides out of its JSON.

This is the only module that knows how the API is shaped. presentation.py turns rides into what the
dashboard shows, and tasks.py turns them into notifications.
"""

import logging
from datetime import datetime, timedelta
from typing import NamedTuple
from zoneinfo import ZoneInfo

import requests
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

logger = logging.getLogger(__name__)

ROUTES_URL = 'https://www.hertzfreerider.se/api/transport-routes/?country=SWEDEN'
LOCATIONS_URL = 'https://www.hertzfreerider.se/api/locations/'
# Hertz gives times in Swedish local time, without an offset
TZ = ZoneInfo('Europe/Stockholm')
SNAPSHOT_KEY = 'hertz:routes'


class Ride(NamedTuple):
    """One car offered on one route: the API's route dict plus its parsed times (aware, Swedish time)."""

    route: dict
    available_at: datetime
    latest_return: datetime

    @property
    def id(self):
        return str(self.route['id'])

    @property
    def pickup(self):
        return self.route.get('pickupLocation') or {}

    @property
    def dropoff(self):
        return self.route.get('returnLocation') or {}

    @property
    def origin(self):
        return self.pickup.get('name') or ''

    @property
    def destination(self):
        return self.dropoff.get('name') or ''


def parse_time(value):
    """'2025-08-12T07:00:00' from the API -> timezone-aware datetime in Swedish time."""
    parsed = datetime.fromisoformat(value)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=TZ)


def rides(data):
    """Every route in the API's list of station pairs as a Ride, skipping routes without an id or valid times."""
    for pair in data if isinstance(data, list) else []:
        for route in (pair.get('routes') or []) if isinstance(pair, dict) else []:
            if not isinstance(route, dict) or route.get('id') is None:
                continue
            try:
                yield Ride(route, parse_time(route.get('availableAt')), parse_time(route.get('latestReturn')))
            except TypeError, ValueError:
                continue


def group_identical(rides):
    """Identical cars (same stations, times and model) as lists of rides, in the API's order."""
    groups = {}
    for ride in rides:
        key = (ride.origin, ride.destination, ride.available_at, ride.latest_return, ride.route.get('carModel'))
        groups.setdefault(key, []).append(ride)
    return list(groups.values())


def _cache_get(key):
    try:
        return cache.get(key)
    except Exception as e:  # with Redis down the dashboard still works, it just fetches live
        logger.warning('Could not read %s from the cache: %s', key, e)
        return None


def _cache_set(key, value, timeout):
    try:
        cache.set(key, value, timeout)
    except Exception as e:
        logger.warning('Could not store %s in the cache: %s', key, e)


def fetch_routes():
    resp = requests.get(ROUTES_URL, timeout=10)
    resp.raise_for_status()
    return resp.json()


def refresh_routes():
    """Fetch the routes and keep them as the snapshot the dashboard reads. Returns (data, fetched_at)."""
    snapshot = (fetch_routes(), timezone.now())
    _cache_set(SNAPSHOT_KEY, snapshot, timeout=None)
    return snapshot


def latest_routes():
    """The worker's last snapshot, or a live fetch when it is missing or older than the worker would leave it.

    Returns (data, fetched_at); raises when the live fetch fails.
    """
    snapshot = _cache_get(SNAPSHOT_KEY)
    # The worker refreshes it every HERTZ_CHECK_INTERVAL; three missed runs mean it is down or stuck
    max_age = timedelta(seconds=max(300, 3 * settings.HERTZ_CHECK_INTERVAL))
    if snapshot and timezone.now() - snapshot[1] <= max_age:
        return snapshot
    return refresh_routes()


def fetch_location_names():
    """All Hertz station names (used for autocomplete), cached for a day."""
    names = _cache_get('hertz_location_names')
    if names is None:
        try:
            resp = requests.get(LOCATIONS_URL, timeout=10)
            resp.raise_for_status()
            names = sorted({loc['name'] for loc in resp.json() if loc.get('name')})
        except Exception as e:
            logger.warning('Could not fetch Hertz locations: %s', e)
            names = []
        # Retry failed lookups sooner than successful ones
        _cache_set('hertz_location_names', names, 24 * 3600 if names else 300)
    return names
