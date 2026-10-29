"""The notification text, in the design picked from the mockups (A2)."""

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
        **route,
    }
    return Ride(data, datetime(2026, 10, 30, 9, 0, tzinfo=TZ), datetime(2026, 10, 31, 19, 0, tzinfo=TZ))


def test_one_ride(settings):
    settings.SITE_URL = ''
    n = compose([ride()], NOW)
    assert n.title == 'Östersund → Linköping'
    assert n.message.split('\n') == [
        '<font color="#e8890c"><b>A</b></font> <b>Östersund DT</b>',
        'from 2026-10-30 09:00',
        '<font color="#e0453a"><b>B</b></font> <b>Linköping (Tage Rejmes)</b>',
        'by 2026-10-31 19:00',
        'Volvo XC60 T6 AUT AWD NE PL DA',
        '<font color="#c25e00">⚠ Summer tyres · Return only during opening hours</font>',
    ]
    # Without SITE_URL the button goes to Hertz
    assert (n.url, n.url_title) == ('https://www.hertzfreerider.se/sv-se/', 'Book on Hertz')


def test_identical_cars_without_a_model(settings):
    settings.SITE_URL = 'https://hertz.example.com'
    group = [ride(id, carModel='Personbil', publicDescription='') for id in ('1', '2', '3')]
    n = compose(group, NOW)
    assert '3 cars (model TBA)' in n.message.split('\n')
    assert n.url == 'https://hertz.example.com/#route-1'
