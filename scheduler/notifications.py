"""What a notification says, in the design picked from the mockups.

The title is the car. Below it, each on its own line behind an icon: the route with the full station
names, the time window and the drive. Warnings come last, in orange. On the lock screen Pushover shows
the text without the HTML, cut after about four lines, so the route and the times come first.
"""

from html import escape
from typing import NamedTuple

from django.conf import settings

from .hertz import TZ
from .presentation import car_details, car_text, drive, format_duration, location_details, route_warnings, station_name

BOOK_URL = 'https://www.hertzfreerider.se/sv-se/'


class Notification(NamedTuple):
    title: str
    message: str  # Pushover HTML, lines separated by newlines
    url: str
    url_title: str


def _html(text):
    return escape(text, quote=False)


def _time(moment):
    """'2026-10-29 09:00' with a non-breaking hyphen and space: a time line too long for the lock screen then
    breaks at the dash between the two times, never inside a date."""
    return moment.astimezone(TZ).strftime('%Y-%m-%d %H:%M').replace('-', '\u2011').replace(' ', '\u00a0')


def compose(group, now):
    """The notification for a group of identical rides (hertz.Ride objects, as from group_identical)."""
    ride = group[0]
    origin, destination = location_details(ride.pickup), location_details(ride.dropoff)
    car = car_details(
        ride.route.get('carModel'), ride.route.get('publicDescription'), ride.route.get('publicInformation')
    )
    km, minutes = drive(ride.route)
    available = '\u00a0(now)' if ride.available_at <= now else ''
    lines = [
        f'📍 <b>{_html(station_name(ride.origin))}</b> → <b>{_html(station_name(ride.destination))}</b>',
        f'🕘 {_time(ride.available_at)}{available} – {_time(ride.latest_return)}',
        f'🛣️ {km} km · {format_duration(minutes)}',
    ]
    warnings = route_warnings(car, origin, destination)
    if warnings:
        lines.append(f'<font color="#c25e00">⚠ {_html(" · ".join(warnings))}</font>')
    # The button opens the route on the dashboard; without SITE_URL it goes to Hertz's booking page
    if settings.SITE_URL:
        url, url_title = f'{settings.SITE_URL}/#route-{ride.id}', 'Show route'
    else:
        url, url_title = BOOK_URL, 'Book on Hertz'
    return Notification(car_text(car, len(group)), '\n'.join(lines), url, url_title)
