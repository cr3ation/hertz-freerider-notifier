import logging
from html import escape

from celery import shared_task

from .models import NotifiedRide, SavedSearch
from .utils import fetch_routes, parse_hertz_time, pushover_configured, send_pushover, wildcard_match

logger = logging.getLogger(__name__)


@shared_task
def check_hertz():
    # A ride only counts as notified once Pushover has accepted it, so without Pushover there is nothing to do
    if not pushover_configured():
        logger.warning('Pushover is not configured (PUSHOVER_USER/PUSHOVER_TOKEN); skipping the check')
        return

    try:
        data = fetch_routes()
    except Exception as e:
        logger.warning('Could not fetch routes from Hertz: %s', e)
        return

    # Handle the actual API structure: array of location pairs with routes
    if not isinstance(data, list):
        logger.warning('Unexpected API response format, expected list')
        return

    for search in SavedSearch.objects.select_related('owner'):
        for location_pair in data:
            # Each location pair has pickupLocationName, returnLocationName, and routes array
            routes = location_pair.get('routes', [])

            for route in routes:
                # Extract route data using correct API field names
                route_id = str(route.get('id', ''))
                if not route_id:
                    continue

                # Get pickup and return location details (Hertz sends null for missing values)
                pickup_location = route.get('pickupLocation') or {}
                return_location = route.get('returnLocation') or {}

                origin = pickup_location.get('name') or ''
                destination = return_location.get('name') or ''

                try:
                    available_at = parse_hertz_time(route.get('availableAt'))
                    latest_return = parse_hertz_time(route.get('latestReturn'))
                except TypeError, ValueError:
                    continue
                pickup_date, return_date = available_at.date(), latest_return.date()

                # Check if date ranges overlap (any overlap between search interval and route interval)
                # Overlap condition: not (search ends before route starts OR search starts after route ends)
                if (search.date_to < pickup_date) or (search.date_from > return_date):
                    continue

                # Check if locations match search criteria
                if not wildcard_match(search.origin, origin):
                    continue
                if not wildcard_match(search.destination, destination):
                    continue

                car_model = route.get('carModel') or 'Unknown car'
                distance = route.get('distance') or 0
                travel_time = route.get('travelTime', None)

                # Format dates in European style with weekday names
                pickup_str = pickup_date.strftime('%a %d/%m/%Y')
                return_str = return_date.strftime('%a %d/%m/%Y')

                # HTML message (limited tags supported by Pushover when html=1). Names and the car come from
                # Hertz, so they are escaped. Provide a direct clickable link.
                msg = (
                    f"🚗 <b>{escape(origin, quote=False)}</b> → <b>{escape(destination, quote=False)}</b><br><br>"
                    f"📅 {pickup_str} - {return_str}<br>"
                    f"🚙 {escape(car_model, quote=False)}<br>"
                    f"📍 {distance:.0f} km<br><br>"
                    f"Book ride <a href=\"https://www.hertzfreerider.se/sv-se/\">here</a>"
                )

                # Reserve the ride before sending. ride_id is unique, so two overlapping runs can't both send it,
                # and a ride notified earlier is skipped here.
                ride, created = NotifiedRide.objects.get_or_create(
                    ride_id=route_id,
                    defaults={
                        'pickup_location_name': origin,
                        'return_location_name': destination,
                        'distance': distance,
                        'available_at': available_at,
                        'latest_return': latest_return,
                        'travel_time': travel_time,
                        'car_type': car_model,
                    },
                )
                if not created:
                    continue

                try:
                    sent = send_pushover(msg, html=True)
                except Exception:
                    logger.exception('Sending the notification for ride %s failed', route_id)
                    sent = False
                if sent:
                    logger.info('Notified ride %s: %s → %s', route_id, origin, destination)
                else:
                    # Not delivered: release the ride so the next run tries again
                    ride.delete()
