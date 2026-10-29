"""What a notification says, in the design picked from the mockups ("A2").

The title has the short names. Then each station gets a line with its full name, followed by a line with
its time; the car has a line of its own and warnings come last, in orange. On the lock screen Pushover
shows the text without the HTML, cut after about four lines, so the stations and times come first.
"""

from html import escape
from typing import NamedTuple

from django.conf import settings

from .hertz import TZ
from .presentation import car_details, car_text, location_details, route_warnings, station_name

BOOK_URL = 'https://www.hertzfreerider.se/sv-se/'


class Notification(NamedTuple):
    title: str
    message: str  # Pushover HTML, lines separated by newlines
    url: str
    url_title: str


def _html(text):
    return escape(text, quote=False)


def _time(moment):
    return moment.astimezone(TZ).strftime('%Y-%m-%d %H:%M')


def compose(group, now):
    """The notification for a group of identical rides (hertz.Ride objects, as from group_identical)."""
    ride = group[0]
    origin, destination = location_details(ride.pickup), location_details(ride.dropoff)
    car = car_details(
        ride.route.get('carModel'), ride.route.get('publicDescription'), ride.route.get('publicInformation')
    )
    lines = [
        f'<font color="#e8890c"><b>A</b></font> <b>{_html(station_name(ride.origin))}</b>',
        f'from {_time(ride.available_at)}' + (' (now)' if ride.available_at <= now else ''),
        f'<font color="#e0453a"><b>B</b></font> <b>{_html(station_name(ride.destination))}</b>',
        f'by {_time(ride.latest_return)}',
        _html(car_text(car, len(group))),
    ]
    warnings = route_warnings(car, origin, destination)
    if warnings:
        lines.append(f'<font color="#c25e00">⚠ {_html(" · ".join(warnings))}</font>')
    # The button opens the route on the dashboard; without SITE_URL it goes to Hertz's booking page
    if settings.SITE_URL:
        url, url_title = f'{settings.SITE_URL}/#route-{ride.id}', 'Show route'
    else:
        url, url_title = BOOK_URL, 'Book on Hertz'
    return Notification(f'{origin["short"]} → {destination["short"]}', '\n'.join(lines), url, url_title)
