import logging
import os
import re
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
from django.core.cache import cache

logger = logging.getLogger(__name__)

API_URL = 'https://www.hertzfreerider.se/api/transport-routes/?country=SWEDEN'
LOCATIONS_URL = 'https://www.hertzfreerider.se/api/locations/'
# Hertz gives times in Swedish local time, without an offset
HERTZ_TZ = ZoneInfo('Europe/Stockholm')


def fetch_routes():
    resp = requests.get(API_URL, timeout=10)
    resp.raise_for_status()
    return resp.json()


def parse_hertz_time(value):
    """'2025-08-12T07:00:00' from the API -> timezone-aware datetime in Swedish time."""
    parsed = datetime.fromisoformat(value)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=HERTZ_TZ)


def fetch_location_names():
    """All Hertz station names (used for autocomplete), cached for a day."""
    names = cache.get('hertz_location_names')
    if names is None:
        try:
            resp = requests.get(LOCATIONS_URL, timeout=10)
            resp.raise_for_status()
            names = sorted({loc['name'] for loc in resp.json() if loc.get('name')})
        except Exception as e:
            logger.warning('Could not fetch Hertz locations: %s', e)
            names = []
        # Retry failed lookups sooner than successful ones
        cache.set('hertz_location_names', names, 24 * 3600 if names else 300)
    return names


def wildcard_match(pattern, text):
    pattern = '^' + re.escape(pattern).replace('\\*', '.*') + '$'
    return re.match(pattern, text, re.IGNORECASE) is not None


def pushover_configured():
    return bool(os.getenv('PUSHOVER_USER') and os.getenv('PUSHOVER_TOKEN'))


def send_pushover(message, *, title='Hertz Freerider', url=None, url_title=None, html=False, priority=0):
    """Send a Pushover notification. Returns True when Pushover accepted it.

    Parameters:
        message (str): Body text. If html=True limited Pushover HTML tags are allowed
                       (<b>, <i>, <u>, <font color=..>, <a href="..">).
        title (str):   Notification title.
        url (str):     Optional supplementary URL (shows as button below message if url_title provided).
        url_title (str): Text for the URL button (defaults to URL if omitted).
        html (bool):   Enable limited HTML rendering.
        priority (int): Pushover priority (default 0).
    """
    if not pushover_configured():
        logger.warning('Pushover is not configured (PUSHOVER_USER/PUSHOVER_TOKEN)')
        return False

    payload = {
        'token': os.getenv('PUSHOVER_TOKEN'),
        'user': os.getenv('PUSHOVER_USER'),
        'message': message,
        'title': title,
        'priority': priority,
    }
    if url:
        payload['url'] = url
        if url_title:
            payload['url_title'] = url_title
    if html:
        payload['html'] = 1  # Enable HTML parsing on Pushover side

    try:
        r = requests.post('https://api.pushover.net/1/messages.json', data=payload, timeout=10)
        r.raise_for_status()
    except requests.RequestException as e:
        # Pushover explains a rejection in the body, e.g. {"errors":["application token is invalid"]}
        detail = e.response.text[:300] if e.response is not None else ''
        logger.error('Pushover did not accept the notification: %s %s', e, detail)
        return False
    return True
