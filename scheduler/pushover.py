"""Sending notifications through Pushover (https://pushover.net/api)."""

import logging
import os

import requests

logger = logging.getLogger(__name__)

API_URL = 'https://api.pushover.net/1/messages.json'


def configured():
    return bool(os.getenv('PUSHOVER_USER') and os.getenv('PUSHOVER_TOKEN'))


def send(message, *, title='Hertz Freerider', url=None, url_title=None, html=False, priority=0, image=None):
    """Send a Pushover notification. Returns True when Pushover accepted it.

    Parameters:
        message (str): Body text, at most 1024 characters. Newlines are line breaks. With html=True the
                       limited Pushover HTML tags are allowed (<b>, <i>, <u>, <font color=..>, <a href="..">).
        title (str):   Notification title.
        url (str):     Optional supplementary URL (shows as button below message if url_title provided).
        url_title (str): Text for the URL button (defaults to URL if omitted).
        html (bool):   Enable limited HTML rendering.
        priority (int): Pushover priority (default 0).
        image (bytes): Optional JPEG shown with the notification (Pushover allows one, up to 5 MB).
    """
    if not configured():
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
    files = {'attachment': ('route.jpg', image, 'image/jpeg')} if image else None

    try:
        r = requests.post(API_URL, data=payload, files=files, timeout=20)
        r.raise_for_status()
    except requests.RequestException as e:
        # Pushover explains a rejection in the body, e.g. {"errors":["application token is invalid"]}
        detail = e.response.text[:300] if e.response is not None else ''
        logger.error('Pushover did not accept the notification: %s %s', e, detail)
        return False
    return True
