import logging

from celery import shared_task
from django.db import IntegrityError, transaction
from django.utils import timezone

from . import hertz, pushover, routemap
from .models import NotifiedRide, SavedSearch
from .notifications import compose

logger = logging.getLogger(__name__)


@shared_task
def check_hertz():
    """Fetch the routes, which also refreshes the dashboard's snapshot, and notify about new matches."""
    try:
        data, _ = hertz.refresh_routes()
    except Exception as e:
        logger.warning('Could not fetch routes from Hertz: %s', e)
        return

    # A ride only counts as notified once Pushover has accepted it, so without Pushover there is nothing to do
    if not pushover.configured():
        logger.warning('Pushover is not configured (PUSHOVER_USER/PUSHOVER_TOKEN); nobody is notified')
        return

    searches = list(SavedSearch.objects.all())
    now = timezone.now()
    # Identical cars (same stations, times and model) get one notification together
    for group in hertz.group_identical(hertz.rides(data)):
        if any(search.matches(group[0]) for search in searches):
            notify(group, now)


def notify(group, now):
    """Send one notification for a group of identical rides, unless one of them was notified before."""
    ids = [ride.id for ride in group]
    if NotifiedRide.objects.filter(ride_id__in=ids).exists():
        return

    ride = group[0]
    notification = compose(group, now)
    pickup, dropoff = ride.pickup, ride.dropoff
    image = None
    if None not in (pickup.get('geoLat'), pickup.get('geoLon'), dropoff.get('geoLat'), dropoff.get('geoLon')):
        image = routemap.render((pickup['geoLat'], pickup['geoLon']), (dropoff['geoLat'], dropoff['geoLon']))

    # Reserve the rides before sending. ride_id is unique, so two overlapping runs can't both send them.
    try:
        with transaction.atomic():
            NotifiedRide.objects.bulk_create([_notified_ride(r) for r in group])
    except IntegrityError:
        return

    try:
        sent = pushover.send(
            notification.message,
            title=notification.title,
            url=notification.url,
            url_title=notification.url_title,
            html=True,
            image=image,
        )
    except Exception:
        logger.exception('Sending the notification for %s failed', ', '.join(ids))
        sent = False
    if sent:
        logger.info('Notified %s: %s → %s', ', '.join(ids), ride.origin, ride.destination)
    else:
        # Not delivered: release the rides so the next run tries again
        NotifiedRide.objects.filter(ride_id__in=ids).delete()


def _notified_ride(ride):
    return NotifiedRide(
        ride_id=ride.id,
        pickup_location_name=ride.origin,
        return_location_name=ride.destination,
        distance=ride.route.get('distance') or 0,
        available_at=ride.available_at,
        latest_return=ride.latest_return,
        travel_time=ride.route.get('travelTime'),
        car_type=ride.route.get('carModel') or 'Unknown car',
    )
