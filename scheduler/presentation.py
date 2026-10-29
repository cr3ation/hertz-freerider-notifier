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

from .hertz import TZ, group_identical, rides

# Trailing "/ Self Service Kiosk", "& SSK" etc. carries no information for the user
KIOSK_SUFFIX = re.compile(r'\s*(/|&)?\s*(Self[ -]?Service( Kiosk)?|SSK)\b.*$', re.I)
# Just the kiosk words, wherever they are ("Skövde DT & Self Service Kiosk Brandt")
KIOSK_WORDS = re.compile(r'\s*[/&]?\s*(Self[ -]?Service( Kiosk)?|SSK)\b', re.I)
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


def station_name(name):
    """Hertz's own name for a station minus the kiosk words: 'Linköping (Tage Rejmes)/ Self Service Kiosk' ->
    'Linköping (Tage Rejmes)'. Unlike the short name it tells where in town the car is."""
    return _clean(re.sub(r'\s+', ' ', KIOSK_WORDS.sub(' ', name or '')).strip(' /-&,'))


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
        # tracCode is Hertz's unique station id
        'code': location.get('tracCode') or location.get('name', ''),
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
    (re.compile(r'manuell', re.I), 'Manual gearbox'),
)
# Notes like "PERSONBIL AUTOMAT" or "MINIBUSS" only restate the kind of car, so they are not shown as notes
CAR_TYPE_WORDS = {'PERSONBIL', 'AUTOMAT', 'MINIBUSS', 'ELBIL'}


def car_details(model, description='', information=''):
    """Readable car name, the rest of the fleet code and tags from e.g. 'VOLVO XC40 B3 FWD AUT PLUS DAR'."""
    raw = (model or '').strip()
    tokens = raw.upper().split()
    notes, electric_note, van_note = [], False, False
    for text in (description or '', information or ''):
        text = text.strip(' *')
        if not text:
            continue
        words = set(re.findall(r'\w+', text.upper()))
        if words <= CAR_TYPE_WORDS:
            electric_note |= 'ELBIL' in words
            van_note |= 'MINIBUSS' in words
            continue
        notes.append(next((label for pattern, label in NOTE_TRANSLATIONS if pattern.search(text)), text))

    if len(tokens) < 2:  # "Personbil" = model not announced
        return {
            'name': '',
            'spec': '',
            'raw': raw,
            'tags': ['Electric'] if electric_note else [],
            'van': van_note,
            'notes': notes,
        }

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
        'spec': ' '.join(raw.split()[1 + len(name_tokens) :]),
        'raw': raw,
        'tags': tags,
        'van': van_note or bool(VAN_WORDS.search(joined)),
        'notes': notes,
    }


def car_text(car, count=1):
    """'Volvo V60 T6 AUT AWD NE PLUS D', '3 × Volvo V60 …' or '3 cars (model TBA)'."""
    model = f"{car['name']} {car['spec']}".strip()
    if count > 1:
        return f'{count} × {model}' if model else f'{count} cars (model TBA)'
    return model or 'Car (model TBA)'


def drive(route):
    """(km, minutes) of the drive: Hertz's estimate of the actual trip, or the maximum when that is missing."""
    km = round(route.get('originalDistance') or route.get('distance') or 0)
    minutes = round(route.get('originalTravelTime') or route.get('travelTime') or 0)
    return km, minutes


def route_warnings(car, origin, destination):
    """What to watch out for on a route: Hertz's notes about the car, and stations without a key kiosk."""
    warnings = list(car['notes'])
    if not destination['kiosk']:
        warnings.append('Return only during opening hours')
    if not origin['kiosk']:
        warnings.append('Pickup only during opening hours')
    return warnings


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


def local_iso(moment):
    """'2025-08-12T07:00' in Swedish time, without an offset, as the route window's JavaScript expects."""
    return moment.astimezone(TZ).replace(tzinfo=None).isoformat(timespec='minutes')


def _alternative(ride, row_id):
    km, minutes = drive(ride.route)
    return {'id': row_id, 'km': km, 'minutes': minutes}


def build_routes(raw_data, searches, notified_ids, now):
    """Build grouped table rows plus the JSON for the route details window.

    Args:
        raw_data: list of location pairs from the transport-routes API.
        searches: the user's SavedSearch objects.
        notified_ids: set of ride ids that have triggered a notification.
        now: timezone-aware current time.

    Returns:
        (rows, details, match_counts). rows are dicts for the template. details is the JSON for the route
        window: each station once under its tracCode, routes keyed by row id and pointing at stations, and
        aliases from the other identical cars' ride ids to their row. match_counts maps search id -> rows.
    """
    all_rides = list(rides(raw_data))
    # Identical cars (same stations, times and model) become one row with a count, named after the first
    groups = group_identical(all_rides)
    row_of = {ride.id: members[0].id for members in groups for ride in members}
    by_offer = {}
    for ride in all_rides:
        by_offer.setdefault(ride.route.get('transportOfferId'), []).append(ride)

    match_counts = {s.id: 0 for s in searches}
    rows, stations, routes = [], {}, {}
    for members in groups:
        ride = members[0]
        route = ride.route
        ride_ids = [m.id for m in members]
        origin = location_details(ride.pickup)
        destination = location_details(ride.dropoff)
        stations.setdefault(origin['code'], origin)
        stations.setdefault(destination['code'], destination)
        car = car_details(route.get('carModel'), route.get('publicDescription'), route.get('publicInformation'))

        matches = [s.id for s in searches if s.matches(ride)]
        for search_id in matches:
            match_counts[search_id] += 1

        km, minutes = drive(route)
        available_now = ride.available_at <= now
        pickup_in = '' if available_now else format_until(ride.available_at, now)
        alternatives = [r for r in by_offer.get(route.get('transportOfferId'), []) if r.id not in ride_ids]

        rows.append(
            {
                'id': ride.id,
                'ride_ids': ride_ids,
                'origin': origin,
                'destination': destination,
                'search': ' | '.join(location_search_text(loc['name'], loc['city']) for loc in (origin, destination)),
                'count': len(members),
                'alternatives_count': len(alternatives),
                'available_at': ride.available_at,
                'latest_return': ride.latest_return,
                'available_now': available_now,
                'pickup_in': pickup_in,
                'km': km,
                'duration': format_duration(minutes),
                'car': car,
                'matches': matches,
                'notified': any(i in notified_ids for i in ride_ids),
            }
        )
        routes[ride.id] = {
            'id': ride.id,
            'from': origin['code'],
            'to': destination['code'],
            'availableAt': local_iso(ride.available_at),
            'latestReturn': local_iso(ride.latest_return),
            'availableNow': available_now,
            'pickupIn': pickup_in,
            'hoursAvailable': round((ride.latest_return - max(now, ride.available_at)).total_seconds() / 3600),
            'km': km,
            'maxKm': round(route.get('distance') or 0),
            'minutes': minutes,
            'car': car,
            'count': len(members),
            'warnings': route_warnings(car, origin, destination),
            'alternatives': [
                _alternative(r, row_of[r.id])
                for r in sorted(alternatives, key=lambda r: r.route.get('priorityOrder') or 0)
            ],
        }

    rows.sort(key=lambda r: (r['origin']['short'].lower(), r['available_at']))
    aliases = {ride_id: row_id for ride_id, row_id in row_of.items() if ride_id != row_id}
    return rows, {'stations': stations, 'routes': routes, 'aliases': aliases}, match_counts
