from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from .forms import SavedSearchForm
from .models import SavedSearch, NotifiedRide
from .utils import fetch_routes, wildcard_match
from datetime import datetime

@login_required
def dashboard(request):
    searches = SavedSearch.objects.filter(owner=request.user)
    # Prepare data structures for live availability
    available_routes = []
    search_match_counts = {s.id: 0 for s in searches}
    api_error = None
    try:
        raw_data = fetch_routes()
    except Exception as e:
        raw_data = []
        api_error = str(e)

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
                matches = []
                # Determine which of the user's searches match this route
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

                # Only include currently available routes (optionally could filter by expiry etc.)
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
    editing_id = None
    active_tab = request.GET.get('tab') or 'live'
    if request.method == 'POST':
        editing_id = request.POST.get('editing_id') or None
        if editing_id:
            search_obj = get_object_or_404(SavedSearch, pk=editing_id, owner=request.user)
            form = SavedSearchForm(request.POST, instance=search_obj)
            active_tab = 'searches'
        else:
            form = SavedSearchForm(request.POST)
        if form.is_valid():
            saved = form.save(commit=False)
            saved.owner = request.user
            saved.save()
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
    # Recent notification history (latest first)
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

@login_required
def delete_search(request, pk):
    search = get_object_or_404(SavedSearch, pk=pk, owner=request.user)
    search.delete()
    return redirect('dashboard')
