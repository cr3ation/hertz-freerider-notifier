"""The presentation helpers turn Hertz's raw names, fleet codes and routes into what the dashboard shows."""

import json
from datetime import date, datetime

import pytest

from scheduler.hertz import TZ
from scheduler.models import SavedSearch
from scheduler.presentation import (
    build_routes,
    car_details,
    car_text,
    format_duration,
    format_until,
    is_airport,
    local_iso,
    location_names,
    location_search_text,
    station_name,
)


@pytest.mark.parametrize(
    'name, expected',
    [
        ('Stockholm Arlanda Flygplats / Self Service Kiosk', ('Arlanda', 'Stockholm Arlanda Flygplats')),
        ('Göteborg Landvetter Flygplats / Self Service Kiosk', ('Landvetter', 'Göteborg Landvetter Flygplats')),
        ('Stockholm Centralstation / Self Service Kiosk', ('Stockholm C', 'Central Station')),
        ('Kiruna AP', ('Kiruna', 'Airport')),
        ('Eslöv DT / Self Service Kiosk', ('Eslöv', 'Downtown')),
        ('OSLO LUFTHAVN', ('Oslo', 'Airport')),
        ('Stockholm Solna Bilia & SSK', ('Stockholm', 'Solna Bilia')),
        ('Göteborg Almedal (Bilia)', ('Göteborg', 'Almedal Bilia')),
        ('Halmstad Railway Station', ('Halmstad', 'Railway Station')),
        ('Bollnäs & Self Service Kiosk', ('Bollnäs', '')),
        ('Ystad & Self Service Kiosk', ('Ystad', '')),
    ],
)
def test_location_names(name, expected):
    assert location_names(name) == expected


def test_location_names_falls_back_to_city():
    assert location_names('', 'KALMAR') == ('Kalmar', '')
    assert location_names(None) == ('', '')


@pytest.mark.xfail(reason='Known quirk: the comma after the city is kept', strict=True)
def test_location_names_strips_trailing_comma():
    assert location_names('Borås, Borås Bil / Self Service Kiosk') == ('Borås', 'Borås Bil')


@pytest.mark.xfail(reason='Known quirk: multi-word town names are cut at the first word', strict=True)
def test_location_names_keeps_multi_word_town():
    assert location_names('MO I RANA LUFTHAVN')[0] == 'Mo I Rana'


@pytest.mark.parametrize(
    'name, airport',
    [
        ('Stockholm Arlanda Flygplats / Self Service Kiosk', True),
        ('Kiruna AP', True),
        ('OSLO LUFTHAVN', True),
        ('Kalmar Airport', True),
        ('Stockholm Centralstation / Self Service Kiosk', False),
        ('Kalmar Self Service Kiosk', False),
        ('Eslöv DT / Self Service Kiosk', False),
    ],
)
def test_is_airport(name, airport):
    assert is_airport(name) is airport


@pytest.mark.parametrize(
    'name, city, query',
    [
        ('Stockholm Centralstation / Self Service Kiosk', 'STOCKHOLM', 'stockholm central'),
        ('Stockholm Centralstation / Self Service Kiosk', 'STOCKHOLM', 'stockholm cent'),
        ('Stockholm Centralstation / Self Service Kiosk', 'STOCKHOLM', 'stockholm c'),
        ('Stockholm Arlanda Flygplats / Self Service Kiosk', 'Stockholm (Arlanda)', 'stockholm arlanda'),
        ('Stockholm Arlanda Flygplats / Self Service Kiosk', 'Stockholm (Arlanda)', 'arlanda airport'),
    ],
)
def test_location_search_text_finds_common_spellings(name, city, query):
    assert query in location_search_text(name, city).lower()


@pytest.mark.parametrize(
    'code, name, spec, tags, van',
    [
        ('CITROEN SPACETOURER AUT 9PAX', 'Citroen Spacetourer', 'AUT 9PAX', ['9 seats'], True),
        ('DACIA DUSTER AUT AWD', 'Dacia Duster', 'AUT AWD', ['AWD'], False),
        ('FORD KUGA AUT AWD ST-LINE 190A', 'Ford Kuga', 'AUT AWD ST-LINE 190A', ['AWD'], False),
        ('FORD TOURNEO AUT PHEV 9PAX', 'Ford Tourneo', 'AUT PHEV 9PAX', ['Plug-in hybrid', '9 seats'], True),
        ('LYNK&CO 01 AUT LADDHYBRID', 'Lynk & Co 01', 'AUT LADDHYBRID', ['Plug-in hybrid'], False),
        ('PEUGEOT 2008 AUT ALLURE MHEV', 'Peugeot 2008', 'AUT ALLURE MHEV', ['Mild hybrid'], False),
        ('POLESTAR 4 LRDM 100KWH AUT BE', 'Polestar 4', 'LRDM 100KWH AUT BE', ['Electric', '100 kWh'], False),
        ('RENAULT CAPTUR 140TCE AUT BENS', 'Renault Captur', '140TCE AUT BENS', ['Petrol'], False),
        ('TOYOTA COROLLA AUT HGV 1,8 HYB', 'Toyota Corolla', 'AUT HGV 1,8 HYB', ['Hybrid'], False),
        ('TOYOTA PROACE VERSO 2,0 AUT DI', 'Toyota Proace Verso', '2,0 AUT DI', [], True),
        ('TOYOTA YARIS CROSS AUT BENSIN', 'Toyota Yaris Cross', 'AUT BENSIN', ['Petrol'], False),
        ('VOLVO EX30 AUT 69KWH SMER CORE', 'Volvo EX30', 'AUT 69KWH SMER CORE', ['Electric', '69 kWh'], False),
        ('VOLVO EX40 AUT 82KWH PLUS EDT', 'Volvo EX40', 'AUT 82KWH PLUS EDT', ['Electric', '82 kWh'], False),
        ('VOLVO V60 T6 AUT AWD NE PLUS D', 'Volvo V60', 'T6 AUT AWD NE PLUS D', ['AWD'], False),
        ('VOLVO V90 T6 RECH AUT R-DESIGN', 'Volvo V90', 'T6 RECH AUT R-DESIGN', ['Plug-in hybrid'], False),
        ('VOLVO XC40 B3 FWD AUT PLUS DAR', 'Volvo XC40', 'B3 FWD AUT PLUS DAR', ['Mild hybrid'], False),
        ('VOLVO XC60 T6RECH AUT AWD PLD', 'Volvo XC60', 'T6RECH AUT AWD PLD', ['Plug-in hybrid', 'AWD'], False),
        ('VW TIGUAN 1,5ETSI AUT FWD', 'VW Tiguan', '1,5ETSI AUT FWD', ['Petrol'], False),
    ],
)
def test_car_details(code, name, spec, tags, van):
    car = car_details(code)
    assert (car['name'], car['spec'], car['tags'], car['van']) == (name, spec, tags, van)
    # Name plus spec is the full fleet code, so nothing Hertz wrote is hidden
    assert f"{car['name'].upper().replace('LYNK & CO', 'LYNK&CO')} {car['spec']}".split() == code.split()


def test_car_details_model_not_announced():
    car = car_details('Personbil')
    assert (car['name'], car['spec'], car['tags']) == ('', '', [])


def test_car_details_reads_notes():
    assert car_details('Personbil', 'Elbil')['tags'] == ['Electric']
    assert car_details('VOLVO V60 T6 AUT AWD NE PLUS D', 'Bilen har sommardäck')['notes'] == ['Summer tyres']


@pytest.mark.parametrize(
    'description, information, notes, van',
    [
        ('***SOMMARDÄCK***', '', ['Summer tyres'], False),
        ('', 'OBS FÄRJEBILJETT INGÅR EJ.', ['Ferry ticket not included'], False),
        ('MANUELL', '', ['Manual gearbox'], False),
        ('V60 CC', '', ['V60 CC'], False),
        # These only say what kind of car it is, so they are not notes (they used to show as orange warnings)
        ('PERSONBIL AUTOMAT', '', [], False),
        ('AUTOMAT', '', [], False),
        ('AUTOMAT MINIBUSS', 'MINIBUSS', [], True),
        ('Minibuss', '', [], True),
    ],
)
def test_car_details_notes_that_matter(description, information, notes, van):
    car = car_details('RENAULT AUSTRAL AUT TCE 160 TE', description, information)
    assert (car['notes'], car['van']) == (notes, van)


@pytest.mark.parametrize(
    'name, full',
    [
        ('Linköping (Tage Rejmes)/ Self Service Kiosk', 'Linköping (Tage Rejmes)'),
        ('Stockholm Kungsholmen/Self Service Kiosk', 'Stockholm Kungsholmen'),
        ('Göteborg Landvetter Flygplats / Self Service Kiosk', 'Göteborg Landvetter Flygplats'),
        ('Skövde DT & Self Service Kiosk Brandt', 'Skövde DT Brandt'),
        ('Kristianstad DT & SSK', 'Kristianstad DT'),
        ('Ystad & Self Service Kiosk', 'Ystad'),
        ('Östersund DT', 'Östersund DT'),
        ('EVENES LUFTHAVN', 'Evenes Lufthavn'),
    ],
)
def test_station_name_keeps_where_in_town(name, full):
    assert station_name(name) == full


def test_car_text():
    volvo, unknown = car_details('VOLVO V60 T6 AUT AWD NE PLUS D'), car_details('Personbil')
    assert car_text(volvo) == 'Volvo V60 T6 AUT AWD NE PLUS D'
    assert car_text(volvo, 2) == '2 × Volvo V60 T6 AUT AWD NE PLUS D'
    assert (car_text(unknown), car_text(unknown, 3)) == ('Car (model TBA)', '3 cars (model TBA)')


@pytest.mark.parametrize('minutes, text', [(0, '0m'), (45, '45m'), (60, '1h'), (137, '2h 17m'), (None, '0m')])
def test_format_duration(minutes, text):
    assert format_duration(minutes) == text


@pytest.mark.parametrize(
    'target, text',
    [
        (datetime(2025, 8, 12, 12, 30), 'in 30 min'),
        (datetime(2025, 8, 12, 15, 20), 'in 3 h 20 min'),
        (datetime(2025, 8, 13, 16, 0), 'in 1 d 4 h'),
        (datetime(2025, 8, 14, 12, 0), 'in 2 d'),
    ],
)
def test_format_until(target, text):
    assert format_until(target, datetime(2025, 8, 12, 12, 0)) == text


NOW = datetime(2025, 8, 12, 12, 0, tzinfo=TZ)


def search(id, origin='*', destination='*', date_from=date(2025, 1, 1), date_to=date(2026, 12, 31)):
    return SavedSearch(id=id, origin=origin, destination=destination, date_from=date_from, date_to=date_to)


def test_build_routes_groups_every_route_once(transport_routes):
    rows, details, _ = build_routes(transport_routes, [], set(), NOW)
    ride_ids = [ride_id for row in rows for ride_id in row['ride_ids']]
    api_ids = [str(r['id']) for pair in transport_routes for r in pair['routes']]
    assert sorted(ride_ids) == sorted(api_ids)
    assert len(rows) == 82  # 95 cars, identical ones grouped
    assert sum(row['count'] for row in rows) == 95
    assert set(details['routes']) == {row['id'] for row in rows}


def test_build_routes_sorts_by_origin_then_pickup(transport_routes):
    rows, _, _ = build_routes(transport_routes, [], set(), NOW)
    keys = [(row['origin']['short'].lower(), row['available_at']) for row in rows]
    assert keys == sorted(keys)


def test_build_routes_alternatives_point_at_listed_rows(transport_routes):
    rows, details, _ = build_routes(transport_routes, [], set(), NOW)
    offer_of = {str(r['id']): r['transportOfferId'] for pair in transport_routes for r in pair['routes']}
    for row in rows:
        for alt in details['routes'][row['id']]['alternatives']:
            assert alt['id'] in details['routes']
            assert offer_of[alt['id']] == offer_of[row['id']]
            assert alt['id'] not in row['ride_ids']


def test_build_routes_matches_searches(transport_routes):
    anywhere, from_stockholm = search(1), search(2, origin='Stockholm*')
    too_early = search(3, date_from=date(2024, 1, 1), date_to=date(2024, 12, 31))
    rows, _, counts = build_routes(transport_routes, [anywhere, from_stockholm, too_early], set(), NOW)
    assert counts == {1: 82, 2: 25, 3: 0}
    for row in rows:
        assert (2 in row['matches']) == row['origin']['name'].lower().startswith('stockholm')


def test_build_routes_marks_notified_rows(transport_routes):
    first_id = str(transport_routes[0]['routes'][0]['id'])
    rows, _, _ = build_routes(transport_routes, [], {first_id}, NOW)
    assert [row['notified'] for row in rows].count(True) == 1


def test_build_routes_warns_when_station_has_no_kiosk(transport_routes):
    rows, details, _ = build_routes(transport_routes, [], set(), NOW)
    for row in rows:
        warnings = details['routes'][row['id']]['warnings']
        assert ('Return only during opening hours' in warnings) == (not row['destination']['kiosk'])
        assert ('Pickup only during opening hours' in warnings) == (not row['origin']['kiosk'])


def test_build_routes_survives_bad_input():
    empty = ([], {'stations': {}, 'routes': {}, 'aliases': {}}, {})
    assert build_routes(None, [], set(), NOW) == empty
    assert build_routes([{'routes': [{'id': 1}]}, 'junk'], [], set(), NOW) == empty


def test_build_routes_sends_each_station_once(transport_routes):
    rows, details, _ = build_routes(transport_routes, [], set(), NOW)
    stations, routes = details['stations'], details['routes']
    codes = {
        r[k]['tracCode']
        for pair in transport_routes
        for r in pair['routes']
        for k in ('pickupLocation', 'returnLocation')
    }
    assert set(stations) == codes
    for row in rows:
        route = routes[row['id']]
        assert stations[route['from']]['name'] == row['origin']['name']
        assert stations[route['to']]['name'] == row['destination']['name']
    # The window JSON used to repeat both stations in every route; keyed stations make it much smaller
    assert len(json.dumps(details)) < 0.6 * len(
        json.dumps([{**r, 'from': stations[r['from']], 'to': stations[r['to']]} for r in routes.values()])
    )


def test_build_routes_aliases_point_identical_cars_at_their_row(transport_routes):
    rows, details, _ = build_routes(transport_routes, [], set(), NOW)
    for row in rows:
        assert [details['aliases'].get(ride_id, ride_id) for ride_id in row['ride_ids']] == [row['id']] * row['count']


def test_build_routes_times_and_minutes(transport_routes):
    rows, details, _ = build_routes(transport_routes, [], set(), NOW)
    route = details['routes'][rows[0]['id']]
    assert route['availableAt'] == local_iso(rows[0]['available_at'])
    assert len(route['availableAt']) == len('2025-08-12T07:00')  # Swedish time, no offset
    assert isinstance(route['minutes'], int)
    assert format_duration(route['minutes']) == rows[0]['duration']


def test_local_iso():
    assert local_iso(datetime(2025, 8, 12, 5, 0, tzinfo=TZ).astimezone(TZ)) == '2025-08-12T05:00'
