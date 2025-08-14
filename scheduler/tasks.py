import datetime, logging
from celery import shared_task
from .models import SavedSearch, NotifiedRide
from .utils import fetch_routes, wildcard_match, send_pushover

@shared_task
def check_hertz():
    try:
        data = fetch_routes()
    except Exception as e:
        logging.exception('Fetching error: %s', e)
        return

    # Handle the actual API structure: array of location pairs with routes
    if not isinstance(data, list):
        logging.warning('Unexpected API response format, expected list')
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
                
                # Get pickup and return location details
                pickup_location = route.get('pickupLocation', {})
                return_location = route.get('returnLocation', {})
                
                origin = pickup_location.get('name', '')
                destination = return_location.get('name', '')
                
                # Get datetime strings and convert to dates
                pickup_datetime_str = route.get('availableAt', '')
                return_datetime_str = route.get('latestReturn', '')
                
                try:
                    pickup_date = datetime.datetime.fromisoformat(pickup_datetime_str[:10]).date()
                    return_date = datetime.datetime.fromisoformat(return_datetime_str[:10]).date()
                except (ValueError, IndexError):
                    continue

                # Check if date ranges overlap (any overlap between search interval and route interval)
                # Overlap condition: not (search ends before route starts OR search starts after route ends)
                if (search.date_to < pickup_date) or (search.date_from > return_date):
                    continue
                    
                # Check if locations match search criteria
                if not wildcard_match(search.origin, origin):
                    continue
                if not wildcard_match(search.destination, destination):
                    continue

                # Skip if already notified
                if NotifiedRide.objects.filter(ride_id=route_id).exists():
                    continue

                # Send notification with additional useful info
                car_model = route.get('carModel', 'Unknown car')
                distance = route.get('distance', 0)
                travel_time = route.get('travelTime', None)
                # Parse datetimes for DB fields
                available_at = None
                latest_return = None
                available_at = datetime.datetime.fromisoformat(route.get('availableAt', ''))
                latest_return = datetime.datetime.fromisoformat(route.get('latestReturn', ''))
                
                # Format dates in European style with weekday names
                pickup_str = pickup_date.strftime('%a %d/%m/%Y')
                return_str = return_date.strftime('%a %d/%m/%Y')

                # Create message with appropriate emojis
                msg = (
                    f"🚗 {origin} → {destination}\n\n"
                    f"📅 {pickup_str} - {return_str}\n"
                    f"🚙 {car_model}\n"
                    f"📍 {distance:.0f} km"
                )

                url = f"https://www.hertzfreerider.se/sv-se/"
                send_pushover(msg, url)
                NotifiedRide.objects.create(
                    ride_id=route_id,
                    pickup_location_name=origin,
                    return_location_name=destination,
                    distance=distance,
                    available_at=available_at,
                    latest_return=latest_return,
                    travel_time=travel_time,
                    car_type=car_model
                )
