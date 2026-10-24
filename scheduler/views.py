"""View layer for the Hertz freerider notifier dashboard.

Contains two views:
    dashboard     – main page showing: user searches (CRUD), live availability, notification history.
    delete_search – deletion endpoint (POST only, redirects back to dashboard).

The dashboard view performs three main tasks each request:
1. Build current live availability by calling the external API helper `fetch_routes()` and turning
   it into display rows with `build_routes()` (short names, car tags, grouping of identical cars,
   matches against the user's searches and the JSON payload for the route details modal).
2. Handle create/update (edit) of a SavedSearch using a single form (POST with optional hidden editing_id).
3. Produce a lightweight history list of recent notifications (capped at 50) for display.

Mobile/desktop tab selection is driven by a query parameter `?tab=` and the template uses the
`active_tab` context var to choose which tab is active at load. When editing a search we force
`active_tab = 'searches'` so the user sees the pre‑filled form immediately.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.urls import reverse
from django.utils import timezone
from .forms import SavedSearchForm
from .models import SavedSearch, NotifiedRide
from .presentation import build_routes, location_names
from .utils import fetch_routes, fetch_location_names

@login_required
def dashboard(request):
    # All searches for the current user (used both for listing & matching live routes)
    searches = list(SavedSearch.objects.filter(owner=request.user))

    # The API uses naive Swedish local time, so compare against naive local "now"
    now = timezone.localtime().replace(tzinfo=None)
    api_error = None                    # capture API errors to show a warning banner
    try:
        raw_data = fetch_routes()
    except Exception as e:
        raw_data = []
        api_error = str(e)

    ride_ids = [str(r.get('id')) for pair in raw_data if isinstance(pair, dict) for r in pair.get('routes', [])] \
        if isinstance(raw_data, list) else []
    notified_ids = set(NotifiedRide.objects.filter(ride_id__in=ride_ids).values_list('ride_id', flat=True))
    available_routes, route_details, search_match_counts = build_routes(raw_data, searches, notified_ids, now)

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
    # Build recent notification history (latest first, capped to 50) with lightweight dicts.
    # Rides that are still listed link to the same details modal as the live table.
    row_for_ride = {ride_id: row['id'] for row in available_routes for ride_id in row['ride_ids']}
    notified_history = []
    for n in NotifiedRide.objects.order_by('-notified_at')[:50]:
        notified_history.append({
            'notified_at': n.notified_at,
            'pickup_location_name': n.pickup_location_name,
            'return_location_name': n.return_location_name,
            'pickup_short': location_names(n.pickup_location_name)[0],
            'return_short': location_names(n.return_location_name)[0],
            'available_at': n.available_at,
            'latest_return': n.latest_return,
            'car_type': n.car_type,
            'distance': n.distance,
            'row_id': row_for_ride.get(n.ride_id),
        })
    # Aggregate context for template
    return render(request, 'scheduler/dashboard.html', {
        'form': form,
        'searches': searches,
        'available_routes': available_routes,
        'route_details': route_details,
        'search_match_counts': search_match_counts,
        'total_routes': len(available_routes),
        'total_cars': sum(r['count'] for r in available_routes),
        'matching_routes': sum(1 for r in available_routes if r['matches']),
        'api_error': api_error,
        'notified_history': notified_history,
        'location_names': fetch_location_names(),
        'updated_at': now,
        'editing_id': editing_id,
        'active_tab': active_tab,
    })

@login_required
@require_POST
def delete_search(request, pk):
    """Delete a user's saved search and return to dashboard (POST + CSRF, confirmed in the UI)."""
    search = get_object_or_404(SavedSearch, pk=pk, owner=request.user)
    search.delete()
    return redirect(f"{reverse('dashboard')}?tab=searches")
