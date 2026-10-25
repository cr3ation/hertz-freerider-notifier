"""Turn raw Hertz Freerider API data into display-ready rows for the dashboard.

The API returns long official station names ("Stockholm Arlanda Flygplats / Self Service Kiosk"),
raw fleet codes ("VOLVO XC40 B3 FWD AUT PLUS DAR") and one entry per car even when several
identical cars exist. This module derives:

    * short location names with a secondary line (station / dealer)
    * a readable car name plus tags (Electric, Plug-in hybrid, AWD ...)
    * grouping of identical routes (same stations, times and model) into one row with a count
    * alternative destinations for the same car (routes sharing transportOfferId)
    * a JSON-serialisable detail payload used by the route details modal
"""

import re
from datetime import datetime

from .utils import wildcard_match

# Trailing "/ Self Service Kiosk", "& SSK" etc. carries no information for the user
KIOSK_SUFFIX = re.compile(r'\s*(/|&)?\s*(Self[ -]?Service( Kiosk)?|SSK)\b.*$', re.I)
AIRPORT_WORDS = {'flygplats', 'airport', 'lufthavn'}
ABBREVIATIONS = {'AP': 'Airport', 'DT': 'Downtown', 'Flygplats': 'Airport', 'Lufthavn': 'Airport'}
# Extra spellings for the live filter, so "Stockholm Central" or "Arlanda Airport" finds the station
SEARCH_SYNONYMS = (
    (re.compile(r'\b(Flygplats|Lufthavn|AP)\b', re.I), 'Airport'),
    (re.compile(r'\b(Centralstation|Sentralstasjon)\b', re.I), 'Central Station'),
    (re.compile(r'\bDT\b'), 'Downtown'),
)


def _clean(text):
    text = (text or '').strip()
    return text.title() if text.isupper() else text


def location_names(name, city=''):
    """Return (short, sub) for a station, e.g. ('Arlanda', 'Stockholm Arlanda Flygplats')."""
    base = _clean(KIOSK_SUFFIX.sub('', name or '').strip(' /-&,') or name or '')
    parts = [p.strip(' -&,') for p in re.split(r'\s*/\s*', base) if p.strip(' -&,')]
    if not parts:
        return _clean(city), ''
    words = parts[0].split()
    head, rest = words[0], [w.strip('()') for w in words[1:]]
    lowered = [w.lower() for w in rest]
    # "Stockholm Arlanda Flygplats" -> Arlanda, "Malmö Sturup Flygplats" -> Sturup
    for i, w in enumerate(lowered):
        if w in AIRPORT_WORDS and i > 0:
            return ' '.join(rest[:i]), parts[0]
    # "Stockholm Centralstation" -> Stockholm C
    if lowered and lowered[0].startswith('centralstation'):
        return f'{head} C', 'Central Station'
    sub = ' '.join([ABBREVIATIONS.get(w, w) for w in rest if w and w != '-'] + parts[1:])
    return head, sub


def is_airport(name):
    words = re.findall(r'\w+', KIOSK_SUFFIX.sub('', name or '').lower())
    return any(w in AIRPORT_WORDS or w == 'ap' for w in words)


def location_search_text(name, city=''):
    """Every spelling of a station the live filter should find: official, English and short name."""
    full = re.sub(r'\s*/\s*', ' ', _clean(KIOSK_SUFFIX.sub('', name or '').strip(' /-&,')))
    english = full
    for pattern, replacement in SEARCH_SYNONYMS:
        english = pattern.sub(replacement, english)
    short, sub = location_names(name, city)
    variants = [full, english, f'{short} {sub}'.strip(), f'{short} Airport' if is_airport(name) else '', _clean(city)]
    return ' | '.join(dict.fromkeys(v for v in variants if v))


def _opening_hours(location):
    """Seven [open, close] pairs (Monday first) or None for closed days."""
    hours = []
    for day in range(1, 8):
        entry = (location.get('regularOpeningHours') or {}).get(str(day)) or {}
        opening, closing = entry.get('openingTime'), entry.get('closingTime')
        hours.append([opening[11:16], closing[11:16]] if opening and closing else None)
    return hours


def _info(location, key):
    """Hertz instruction text, English first with Swedish/Norwegian as fallback."""
    return (location.get(key + 'English') or location.get(key + 'Native') or '').strip()


def location_details(location):
    short, sub = location_names(location.get('name'), location.get('city'))
    return {
        'name': location.get('name', ''),
        'short': short,
        'sub': sub,
        'address': _clean(location.get('address')),
        'city': _clean(location.get('city')),
        'phone': location.get('phoneNumber') or '',
        'lat': location.get('geoLat'),
        'lon': location.get('geoLon'),
        'kiosk': bool(location.get('kiosk')),
        'airport': is_airport(location.get('name')),
        'hours': _opening_hours(location),
        'info': {
            'location': _info(location, 'infoTextLocation'),
            'parking': _info(location, 'infoTextParking'),
            'return': _info(location, 'infoTextReturn') or _info(location, 'infoTextDropOff'),
            'misc': _info(location, 'infoTextMisc'),
        },
    }


# Fleet code tokens that describe engine/trim rather than the model name
SPEC_TOKEN = re.compile(
    r'^(AUT|AWD|FWD|4X4|[BT]\d\w*|RECH|M?HEV|HYB|HGV|PHEV|BEV|BENS\w*|DIESEL|ELBIL|LADDHYBRID|\d+KWH|'
    r'\d+,\d\w*|\d+TCE|TCE\d+|PLUS|CORE|DARK?|SMER|ULT|NE|PL|DA|PLD|ALLURE|LRDM|BE|EDT|ED|SE|ADV\w*|'
    r'ESSENTIA|ST-LINE|SKYACTIVE|\d+PAX|MO/AD/ED|EDI|EDITION)$'
)
BRANDS = {'VW': 'VW', 'LYNK&CO': 'Lynk & Co', 'BMW': 'BMW', 'KIA': 'Kia', 'MG': 'MG'}
EV_MODELS = re.compile(r'\b(EX30|EX40|EC40|EX90|EM90|POLESTAR|ID\.\d)\b')
VAN_WORDS = re.compile(r'\b(PROACE|TRANSIT|VITO|SPRINTER|TRAFIC|VIVARO|JUMPY|CARAVELLE|MULTIVAN|\d+PAX)\b')
NOTE_TRANSLATIONS = (
    (re.compile(r'sommardäck', re.I), 'Summer tyres'),
    (re.compile(r'färj', re.I), 'Ferry ticket not included'),
)


def car_details(model, description='', information=''):
    """Readable car name, the rest of the fleet code and tags from e.g. 'VOLVO XC40 B3 FWD AUT PLUS DAR'."""
    raw = (model or '').strip()
    tokens = raw.upper().split()
    notes, electric_note = [], False
    for text in (description or '', information or ''):
        text = text.strip()
        if not text:
            continue
        if text.lower() == 'elbil':
            electric_note = True
            continue
        notes.append(next((label for pattern, label in NOTE_TRANSLATIONS if pattern.search(text)), text))

    if len(tokens) < 2:  # "Personbil" = model not announced
        return {'name': '', 'spec': '', 'raw': raw, 'tags': ['Electric'] if electric_note else [], 'van': False, 'notes': notes}

    brand = BRANDS.get(tokens[0], tokens[0].title())
    name_tokens = []
    for token in tokens[1:]:
        if SPEC_TOKEN.match(token) or len(name_tokens) == 2:
            break
        name_tokens.append(token if any(c.isdigit() for c in token) or len(token) <= 2 else token.title())

    joined = ' '.join(tokens)
    tags = []
    if electric_note or re.search(r'\d+KWH|\bBEV\b', joined) or EV_MODELS.search(joined):
        tags.append('Electric')
    elif re.search(r'RECH|LADDHYBRID|PHEV', joined):
        tags.append('Plug-in hybrid')
    elif re.search(r'\bMHEV\b', joined) or (tokens[0] == 'VOLVO' and re.search(r'\bB[345]\b', joined)):
        tags.append('Mild hybrid')
    elif re.search(r'\b(HEV|HYB)\b', joined):
        tags.append('Hybrid')
    elif re.search(r'\bBENS\w*|TCE|TSI\b', joined):
        tags.append('Petrol')
    if re.search(r'\b(AWD|4X4)\b', joined):
        tags.append('AWD')
    battery = re.search(r'(\d+)KWH', joined)
    if battery:
        tags.append(f'{battery.group(1)} kWh')
    seats = re.search(r'(\d+)PAX', joined)
    if seats:
        tags.append(f'{seats.group(1)} seats')
    return {
        'name': f"{brand} {' '.join(name_tokens)}".strip(),
        # Everything after brand and model, as Hertz wrote it ('B3 FWD AUT PLUS DAR')
        'spec': ' '.join(raw.split()[1 + len(name_tokens):]),
        'raw': raw,
        'tags': tags,
        'van': bool(VAN_WORDS.search(joined)),
        'notes': notes,
    }


def format_duration(minutes):
    minutes = int(round(minutes or 0))
    hours, rest = divmod(minutes, 60)
    if not hours:
        return f'{rest}m'
    return f'{hours}h {rest}m' if rest else f'{hours}h'


def format_until(target, now):
    """'in 1 d 16 h' style countdown."""
    total = max(0, int((target - now).total_seconds() // 60))
    days, rest = divmod(total, 24 * 60)
    hours, minutes = divmod(rest, 60)
    if days:
        return f'in {days} d {hours} h' if hours else f'in {days} d'
    if hours:
        return f'in {hours} h {minutes} min' if hours < 6 and minutes else f'in {hours} h'
    return f'in {minutes} min'


def _parse(value):
    try:
        return datetime.fromisoformat(value) if value else None
    except ValueError:
        return None


def build_routes(raw_data, searches, notified_ids, now):
    """Build grouped table rows plus modal details.

    Args:
        raw_data: list of location pairs from the transport-routes API.
        searches: the user's SavedSearch objects.
        notified_ids: set of ride ids that have triggered a notification.
        now: naive local datetime (the API uses naive Swedish local time).

    Returns:
        (rows, details, match_counts) where rows are dicts for the template, details maps
        row id -> JSON payload for the modal, and match_counts maps search id -> matching rows.
    """
    routes = []
    for location_pair in raw_data if isinstance(raw_data, list) else []:
        for route in location_pair.get('routes', []) if isinstance(location_pair, dict) else []:
            available_at = _parse(route.get('availableAt'))
            latest_return = _parse(route.get('latestReturn'))
            if route.get('id') is None or not available_at or not latest_return:
                continue
            routes.append((route, available_at, latest_return))

    # Identical cars (same stations, times and model) become one row with a count
    groups = {}
    for route, available_at, latest_return in routes:
        key = ((route.get('pickupLocation') or {}).get('name'), (route.get('returnLocation') or {}).get('name'),
               route.get('availableAt'), route.get('latestReturn'), route.get('carModel'))
        groups.setdefault(key, []).append((route, available_at, latest_return))
    representative = {}
    for members in groups.values():
        for route, _, _ in members:
            representative[str(route['id'])] = str(members[0][0]['id'])
    by_offer = {}
    for route, _, _ in routes:
        by_offer.setdefault(route.get('transportOfferId'), []).append(route)

    match_counts = {s.id: 0 for s in searches}
    rows, details = [], {}
    for members in groups.values():
        route, available_at, latest_return = members[0]
        ride_ids = [str(m[0]['id']) for m in members]
        row_id = ride_ids[0]
        origin = location_details(route.get('pickupLocation') or {})
        destination = location_details(route.get('returnLocation') or {})
        car = car_details(route.get('carModel'), route.get('publicDescription'), route.get('publicInformation'))

        # Same matching rules as before: overlapping dates and wildcard location names
        matches = []
        for s in searches:
            if s.date_to < available_at.date() or s.date_from > latest_return.date():
                continue
            if wildcard_match(s.origin, origin['name']) and wildcard_match(s.destination, destination['name']):
                matches.append(s)
                match_counts[s.id] += 1

        km = round(route.get('originalDistance') or route.get('distance') or 0)
        minutes = route.get('originalTravelTime') or route.get('travelTime') or 0
        available_now = available_at <= now
        warnings = list(car['notes'])
        if not destination['kiosk']:
            warnings.append('Return only during opening hours')
        if not origin['kiosk']:
            warnings.append('Pickup only during opening hours')
        alternatives = [r for r in by_offer.get(route.get('transportOfferId'), []) if str(r['id']) not in ride_ids]

        rows.append({
            'id': row_id,
            'ride_ids': ride_ids,
            'origin': origin,
            'destination': destination,
            'search': ' | '.join(location_search_text(loc['name'], loc['city']) for loc in (origin, destination)),
            'count': len(members),
            'alternatives_count': len(alternatives),
            'available_at': available_at,
            'latest_return': latest_return,
            'available_now': available_now,
            'pickup_in': '' if available_now else format_until(available_at, now),
            'km': km,
            'duration': format_duration(minutes),
            'car': car,
            'matches': [s.id for s in matches],
            'notified': any(i in notified_ids for i in ride_ids),
        })
        details[row_id] = {
            'id': row_id,
            'from': origin,
            'to': destination,
            'availableAt': available_at.isoformat(timespec='minutes'),
            'latestReturn': latest_return.isoformat(timespec='minutes'),
            'availableNow': available_now,
            'pickupIn': '' if available_now else format_until(available_at, now),
            'hoursAvailable': round((latest_return - max(now, available_at)).total_seconds() / 3600),
            'km': km,
            'maxKm': round(route.get('distance') or 0),
            'duration': format_duration(minutes),
            'car': car,
            'count': len(members),
            'warnings': warnings,
            'alternatives': [{
                'id': representative.get(str(r['id']), str(r['id'])),
                'to': location_names((r.get('returnLocation') or {}).get('name'), (r.get('returnLocation') or {}).get('city'))[0],
                'km': round(r.get('originalDistance') or r.get('distance') or 0),
                'duration': format_duration(r.get('originalTravelTime') or r.get('travelTime')),
            } for r in sorted(alternatives, key=lambda r: r.get('priorityOrder') or 0)],
        }

    rows.sort(key=lambda r: (r['origin']['short'].lower(), r['available_at']))
    return rows, details, match_counts
