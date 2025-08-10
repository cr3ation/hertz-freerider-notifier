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

                # Check if dates are within search criteria
                if not (search.date_from <= pickup_date <= search.date_to):
                    continue
                if not (search.date_from <= return_date <= search.date_to):
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
                
                msg = f"{origin} → {destination}\n{pickup_date} - {return_date}\n{car_model}\n{distance:.0f} km"
                ride_url = f"https://www.hertzfreerider.se/transport-routes/{route_id}"
                send_pushover(msg, ride_url)
                NotifiedRide.objects.create(ride_id=route_id)
