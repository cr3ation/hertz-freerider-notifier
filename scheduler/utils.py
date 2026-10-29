import logging
import os
import re

import requests
from django.core.cache import cache

API_URL = 'https://www.hertzfreerider.se/api/transport-routes/?country=SWEDEN'
LOCATIONS_URL = 'https://www.hertzfreerider.se/api/locations/'


def fetch_routes():
    resp = requests.get(API_URL, timeout=10)
    resp.raise_for_status()
    return resp.json()


def fetch_location_names():
    """All Hertz station names (used for autocomplete), cached for a day."""
    names = cache.get('hertz_location_names')
    if names is None:
        try:
            resp = requests.get(LOCATIONS_URL, timeout=10)
            resp.raise_for_status()
            names = sorted({loc['name'] for loc in resp.json() if loc.get('name')})
        except Exception as e:
            logging.warning('Could not fetch Hertz locations: %s', e)
            names = []
        # Retry failed lookups sooner than successful ones
        cache.set('hertz_location_names', names, 24 * 3600 if names else 300)
    return names


def wildcard_match(pattern, text):
    pattern = '^' + re.escape(pattern).replace('\\*', '.*') + '$'
    return re.match(pattern, text, re.IGNORECASE) is not None


def send_pushover(message, *, title='Hertz Freerider', url=None, url_title=None, html=False, priority=0):
    """Send a Pushover notification.

    Parameters:
        message (str): Body text. If html=True limited Pushover HTML tags are allowed
                       (<b>, <i>, <u>, <font color=..>, <a href="..">).
        title (str):   Notification title.
        url (str):     Optional supplementary URL (shows as button below message if url_title provided).
        url_title (str): Text for the URL button (defaults to URL if omitted).
        html (bool):   Enable limited HTML rendering.
        priority (int): Pushover priority (default 0).
    """
    user_key = os.getenv('PUSHOVER_USER')
    token = os.getenv('PUSHOVER_TOKEN')
    if not (user_key and token):
        logging.warning('Pushover not configured')
        return

    payload = {
        'token': token,
        'user': user_key,
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
    except Exception as e:
        logging.exception('Failed to send Pushover: %s', e)
