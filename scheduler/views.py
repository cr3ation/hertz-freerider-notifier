"""View layer for the Hertz freerider notifier dashboard.

Contains two views:
    dashboard     – main page showing: user searches (CRUD), live availability, notification history.
    delete_search – simple deletion endpoint (redirects back to dashboard).

The dashboard view performs three main tasks each request:
1. Build current live availability by calling the external API helper `fetch_routes()` and
   annotating every route with which user searches it matches.
2. Handle create/update (edit) of a SavedSearch using a single form (POST with optional hidden editing_id).
3. Produce a lightweight history list of recent notifications (capped at 50) for display.

Mobile/desktop tab selection is driven by a query parameter `?tab=` and the template uses the
`active_tab` context var to choose which tab is active at load. When editing a search we force
`active_tab = 'searches'` so the user sees the pre‑filled form immediately.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from .forms import SavedSearchForm
from .models import SavedSearch, NotifiedRide
from .utils import fetch_routes, wildcard_match
from datetime import datetime

@login_required
def dashboard(request):
    # All searches for the current user (used both for listing & matching live routes)
    searches = SavedSearch.objects.filter(owner=request.user)

    # Containers for live availability compilation
    available_routes = []               # list of dicts describing each current route
    search_match_counts = {s.id: 0 for s in searches}  # how many live routes match each search
    api_error = None                    # capture API errors to show a warning banner
    try:
        raw_data = fetch_routes()
    except Exception as e:
        raw_data = []
        api_error = str(e)

    # Parse API payload only if we got a list (graceful handling of errors / unexpected format)
    if isinstance(raw_data, list):
        for location_pair in raw_data:
            for route in location_pair.get('routes', []):
                route_id = str(route.get('id', ''))
                if not route_id:
                    continue
                pickup_location = route.get('pickupLocation', {})
                return_location = route.get('returnLocation', {})
                origin = pickup_location.get('name', '')
                destination = return_location.get('name', '')
                available_at_str = route.get('availableAt')
                latest_return_str = route.get('latestReturn')
                try:
                    pickup_date = datetime.fromisoformat(available_at_str[:10]).date() if available_at_str else None
                    return_date = datetime.fromisoformat(latest_return_str[:10]).date() if latest_return_str else None
                except Exception:
                    pickup_date = return_date = None

                car_model = route.get('carModel')
                distance = route.get('distance')
                travel_time = route.get('travelTime')  # minutes
                matches = []  # IDs of SavedSearch objects that match this route
                # Determine which of the user's searches match this route based on:
                #   * overlapping pickup/return date range
                #   * wildcard origin & destination text match
                for s in searches:
                    if pickup_date is None or return_date is None:
                        continue
                    # Overlap logic: intervals [s.date_from, s.date_to] and [pickup_date, return_date] overlap
                    if (s.date_to < pickup_date) or (s.date_from > return_date):
                        continue
                    if not wildcard_match(s.origin, origin):
                        continue
                    if not wildcard_match(s.destination, destination):
                        continue
                    matches.append(s.id)
                    search_match_counts[s.id] += 1

                # Collect normalized / display friendly values for template consumption
                available_routes.append({
                    'route_id': route_id,
                    'origin': origin,
                    'destination': destination,
                    'car_model': car_model,
                    'distance': distance,
                    'travel_time': travel_time,
                    'travel_hours': round(travel_time / 60, 1) if isinstance(travel_time, (int, float)) else None,
                    'available_at': available_at_str,
                    'latest_return': latest_return_str,
                    'available_at_display': (available_at_str.replace('T', ' ')[:16] if isinstance(available_at_str, str) else ''),
                    'latest_return_display': (latest_return_str.replace('T', ' ')[:16] if isinstance(latest_return_str, str) else ''),
                    'matches': matches,
                    'notified': NotifiedRide.objects.filter(ride_id=route_id).exists(),
                })
    editing_id = None                            # holds the ID of a search currently being edited
    active_tab = request.GET.get('tab') or 'live' # which UI tab should be active on initial render
    if request.method == 'POST':
        # Distinguish between create and update: hidden field 'editing_id' present => update
        editing_id = request.POST.get('editing_id') or None
        if editing_id:
            search_obj = get_object_or_404(SavedSearch, pk=editing_id, owner=request.user)
            form = SavedSearchForm(request.POST, instance=search_obj)
            active_tab = 'searches'
        else:
            form = SavedSearchForm(request.POST)
        if form.is_valid():
            # Persist search (owner always enforced server-side for safety)
            saved = form.save(commit=False)
            saved.owner = request.user
            saved.save()
            # Redirect using GET to avoid form resubmission on refresh and focus Searches tab
            return redirect(f"{reverse('dashboard')}?tab=searches")
    else:
        edit_param = request.GET.get('edit')
        if edit_param:
            search_obj = get_object_or_404(SavedSearch, pk=edit_param, owner=request.user)
            form = SavedSearchForm(instance=search_obj)
            editing_id = search_obj.id
            active_tab = 'searches'
        else:
            form = SavedSearchForm()
    # Build recent notification history (latest first, capped to 50) with lightweight dicts
    notified_history_raw = list(NotifiedRide.objects.order_by('-notified_at')[:50])
    notified_history = []
    for n in notified_history_raw:
        hours = round((n.travel_time or 0) / 60, 1) if n.travel_time else None
        notified_history.append({
            'notified_at': n.notified_at,
            'pickup_location_name': n.pickup_location_name,
            'return_location_name': n.return_location_name,
            'available_at': n.available_at,
            'latest_return': n.latest_return,
            'car_type': n.car_type,
            'distance': n.distance,
            'travel_time_hours': hours,
        })
    # Aggregate context for template
    return render(request, 'scheduler/dashboard.html', {
        'form': form,
        'searches': searches,
        'available_routes': available_routes,
        'search_match_counts': search_match_counts,
        'total_routes': len(available_routes),
        'matching_routes': sum(1 for r in available_routes if r['matches']),
        'api_error': api_error,
        'notified_history': notified_history,
        'editing_id': editing_id,
        'active_tab': active_tab,
    })

def delete_search(request, pk):
    """Delete a user's saved search and return to dashboard.

    Using GET (link) for simplicity; could be converted to POST for stricter semantics
    if desired (then guard with csrf + method check).
    """
    search = get_object_or_404(SavedSearch, pk=pk, owner=request.user)
    search.delete()
    return redirect('dashboard')
