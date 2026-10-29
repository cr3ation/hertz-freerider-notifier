"""View layer for the Hertz freerider notifier dashboard.

    dashboard      GET  /                         the page: searches, live availability, notification history
    create_search  POST /searches/                add a search
    update_search  POST /searches/<pk>/           change one of your searches
    delete_search  POST /searches/<pk>/delete/    remove one of your searches

The routes come from the worker's latest snapshot of the Hertz API (hertz.latest_routes), which falls back
to a live fetch. build_routes() turns them into table rows (short names, car tags, identical cars grouped,
matches against the user's searches) and the JSON for the route details window.

Phones show one tab at a time, picked with `?tab=`. `?edit=<pk>` opens a search in the form, on the
Searches tab. A search form with errors is shown again on that tab, with the errors.
"""

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from . import hertz
from .forms import SavedSearchForm
from .models import NotifiedRide, SavedSearch
from .presentation import build_routes, car_details, is_airport, location_names, location_search_text

TABS = ('live', 'searches', 'notifications')


@login_required
@require_GET
def dashboard(request):
    edit = request.GET.get('edit')
    if edit:
        search = get_object_or_404(SavedSearch, pk=edit, owner=request.user)
        return _render_dashboard(request, SavedSearchForm(instance=search), editing_id=search.pk)
    # The tab ends up in a script, so only known tabs pass
    tab = request.GET.get('tab')
    return _render_dashboard(request, SavedSearchForm(), active_tab=tab if tab in TABS else 'live')


@login_required
@require_POST
def create_search(request):
    return _save_search(request, SavedSearchForm(request.POST))


@login_required
@require_POST
def update_search(request, pk):
    search = get_object_or_404(SavedSearch, pk=pk, owner=request.user)
    return _save_search(request, SavedSearchForm(request.POST, instance=search), editing_id=pk)


@login_required
@require_POST
def delete_search(request, pk):
    """Delete a user's saved search and return to dashboard (POST + CSRF, confirmed in the UI)."""
    search = get_object_or_404(SavedSearch, pk=pk, owner=request.user)
    search.delete()
    return redirect(f"{reverse('dashboard')}?tab=searches")


def _save_search(request, form, editing_id=None):
    if not form.is_valid():
        return _render_dashboard(request, form, editing_id=editing_id)
    search = form.save(commit=False)
    search.owner = request.user  # always the logged-in user, whatever the form says
    search.save()
    # Redirect so a refresh doesn't post the form again
    return redirect(f"{reverse('dashboard')}?tab=searches")


def _render_dashboard(request, form, editing_id=None, active_tab='searches'):
    searches = list(SavedSearch.objects.filter(owner=request.user))
    now = timezone.now()
    api_error = None  # shown as a warning banner
    try:
        raw_data, fetched_at = hertz.latest_routes()
    except Exception as e:
        raw_data, fetched_at, api_error = [], now, str(e)

    rides = list(hertz.rides(raw_data))
    # One car can be offered to several destinations (same transportOfferId), so count each car once
    total_cars = len({ride.route.get('transportOfferId') or ride.id for ride in rides})
    notified_ids = set(
        NotifiedRide.objects.filter(ride_id__in=[ride.id for ride in rides]).values_list('ride_id', flat=True)
    )
    available_routes, route_details, match_counts = build_routes(raw_data, searches, notified_ids, now)
    for search in searches:
        search.match_count = match_counts[search.id]

    # Recent notifications (latest first, capped to 50). Rides that are still listed link to the same
    # details window as the live table.
    row_for_ride = {ride_id: row['id'] for row in available_routes for ride_id in row['ride_ids']}
    notified_history = []
    for n in NotifiedRide.objects.order_by('-notified_at')[:50]:
        notified_history.append(
            {
                'notified_at': n.notified_at,
                'pickup_location_name': n.pickup_location_name,
                'return_location_name': n.return_location_name,
                'pickup_short': location_names(n.pickup_location_name)[0],
                'return_short': location_names(n.return_location_name)[0],
                'pickup_airport': is_airport(n.pickup_location_name),
                'return_airport': is_airport(n.return_location_name),
                'search': ' | '.join(
                    location_search_text(name) for name in (n.pickup_location_name, n.return_location_name)
                ),
                'available_at': n.available_at,
                'latest_return': n.latest_return,
                'car_type': n.car_type,
                'car': car_details(n.car_type),
                'distance': n.distance,
                'row_id': row_for_ride.get(n.ride_id),
            }
        )
    return render(
        request,
        'scheduler/dashboard.html',
        {
            'form': form,
            'searches': searches,
            'available_routes': available_routes,
            'route_details': route_details,
            'total_routes': len(available_routes),
            'total_cars': total_cars,
            'matching_routes': sum(1 for r in available_routes if r['matches']),
            'api_error': api_error,
            'notified_history': notified_history,
            'location_names': hertz.fetch_location_names(),
            'updated_at': fetched_at,
            'editing_id': editing_id,
            'active_tab': active_tab,
        },
    )
