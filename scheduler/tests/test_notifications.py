"""The notification text, in the design picked from the mockups: the car as title, then route, times and drive."""

from datetime import datetime

from scheduler.hertz import TZ, Ride
from scheduler.notifications import compose

NOW = datetime(2026, 10, 29, 9, 41, tzinfo=TZ)


def ride(id='68062', **route):
    data = {
        'id': id,
        'pickupLocation': {'name': 'Östersund DT', 'kiosk': True},
        'returnLocation': {'name': 'Linköping (Tage Rejmes)/ Self Service Kiosk', 'kiosk': False},
        'carModel': 'VOLVO XC60 T6 AUT AWD NE PL DA',
        'publicDescription': '***SOMMARDÄCK***',
        'distance': 900.0,
        'originalDistance': 750.2,
        'originalTravelTime': 506,
        **route,
    }
    return Ride(data, datetime(2026, 10, 30, 9, 0, tzinfo=TZ), datetime(2026, 10, 31, 19, 0, tzinfo=TZ))


def readable(message):
    return message.replace('\u2011', '-').replace('\u00a0', ' ').split('\n')


def test_one_ride(settings):
    settings.SITE_URL = ''
    n = compose([ride()], NOW)
    assert n.title == 'Volvo XC60 T6 AUT AWD NE PL DA'
    assert readable(n.message) == [
        '📍 <b>Östersund DT</b> → <b>Linköping (Tage Rejmes)</b>',
        '🕘 2026-10-30 09:00 – 2026-10-31 19:00',
        '🛣️ 750 km · 8h 26m',
        '<font color="#c25e00">⚠ Summer tyres · Return only during opening hours</font>',
    ]
    # Without SITE_URL the button goes to Hertz
    assert (n.url, n.url_title) == ('https://www.hertzfreerider.se/sv-se/', 'Book on Hertz')


def test_a_date_never_breaks_in_two():
    time_line = compose([ride()], NOW).message.split('\n')[1]
    assert time_line == '🕘 2026\u201110\u201130\u00a009:00 – 2026\u201110\u201131\u00a019:00'


def test_available_now(settings):
    n = compose([ride()], datetime(2026, 10, 30, 12, 0, tzinfo=TZ))
    assert readable(n.message)[1] == '🕘 2026-10-30 09:00 (now) – 2026-10-31 19:00'


def test_identical_cars_without_a_model(settings):
    settings.SITE_URL = 'https://hertz.example.com'
    group = [ride(id, carModel='Personbil', publicDescription='') for id in ('1', '2', '3')]
    n = compose(group, NOW)
    assert n.title == '3 cars (model TBA)'
    assert n.url == 'https://hertz.example.com/#route-1'
