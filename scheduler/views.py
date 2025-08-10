from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .forms import SavedSearchForm
from .models import SavedSearch

@login_required
def dashboard(request):
    searches = SavedSearch.objects.filter(owner=request.user)
    if request.method == 'POST':
        form = SavedSearchForm(request.POST)
        if form.is_valid():
            saved = form.save(commit=False)
            saved.owner = request.user
            saved.save()
            return redirect('dashboard')
    else:
        form = SavedSearchForm()
    return render(request, 'scheduler/dashboard.html', {'form': form, 'searches': searches})

@login_required
def delete_search(request, pk):
    search = get_object_or_404(SavedSearch, pk=pk, owner=request.user)
    search.delete()
    return redirect('dashboard')
