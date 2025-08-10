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

    # If the API returns a dict with 'results', otherwise adjust
    if isinstance(data, dict):
        routes = data.get('results', [])
    elif isinstance(data, list):
        routes = data
    else:
        routes = []

    for search in SavedSearch.objects.select_related('owner'):
        for ride in routes:
            ride_id = str(ride.get('id') or ride.get('reference') or ride.get('uuid'))
            origin = ride.get('start_city') or ride.get('fromLocation') or ''
            destination = ride.get('end_city') or ride.get('toLocation') or ''

            pickup_date_str = ride.get('start_date') or ride.get('pickupDate') or ''
            dropoff_date_str = ride.get('end_date') or ride.get('dropoffDate') or ''

            try:
                pickup_date = datetime.datetime.fromisoformat(pickup_date_str[:10]).date()
                dropoff_date = datetime.datetime.fromisoformat(dropoff_date_str[:10]).date()
            except Exception:
                continue

            if not (search.date_from <= pickup_date <= search.date_to):
                continue
            if not (search.date_from <= dropoff_date <= search.date_to):
                continue
            if not wildcard_match(search.origin, origin):
                continue
            if not wildcard_match(search.destination, destination):
                continue

            if NotifiedRide.objects.filter(ride_id=ride_id).exists():
                continue

            msg = f"{origin} → {destination} {pickup_date}–{dropoff_date}"
            ride_url = f"https://www.hertzfreerider.se/transport-routes/{ride_id}"
            send_pushover(msg, ride_url)
            NotifiedRide.objects.create(ride_id=ride_id)
