import os, requests, logging, re
from datetime import datetime

API_URL = 'https://www.hertzfreerider.se/api/transport-routes/?country=SWEDEN'

def fetch_routes():
    resp = requests.get(API_URL, timeout=10)
    resp.raise_for_status()
    return resp.json()

def wildcard_match(pattern, text):
    pattern = '^' + re.escape(pattern).replace('\\*', '.*') + '$'
    return re.match(pattern, text, re.IGNORECASE) is not None

def send_pushover(message, url):
    user_key = os.getenv('PUSHOVER_USER')
    token = os.getenv('PUSHOVER_TOKEN')
    if not (user_key and token):
        logging.warning('Pushover not configured')
        return
    payload = {
        'token': token,
        'user': user_key,
        'message': message,
        'url': url,
        'title': 'Hertz Freerider',
        'priority': 0,
    }
    try:
        r = requests.post('https://api.pushover.net/1/messages.json', data=payload, timeout=10)
        r.raise_for_status()
    except Exception as e:
        logging.exception('Failed to send Pushover: %s', e)
