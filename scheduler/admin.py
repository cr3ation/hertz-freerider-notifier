from django.contrib import admin
from .models import SavedSearch, NotifiedRide

@admin.register(SavedSearch)
class SavedSearchAdmin(admin.ModelAdmin):
    list_display = ('owner', 'origin', 'destination', 'date_from', 'date_to', 'created_at')

@admin.register(NotifiedRide)
class NotifiedRideAdmin(admin.ModelAdmin):
    list_display = ('ride_id', 'notified_at')
