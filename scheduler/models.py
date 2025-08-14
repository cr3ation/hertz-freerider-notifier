from django.db import models
from django.contrib.auth import get_user_model

class SavedSearch(models.Model):
    owner = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    date_from = models.DateField()
    date_to = models.DateField()
    origin = models.CharField(max_length=100, help_text='Use * as wildcard')
    destination = models.CharField(max_length=100, help_text='Use * as wildcard')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.origin} → {self.destination} ({self.date_from} – {self.date_to})"

class NotifiedRide(models.Model):
    ride_id = models.CharField(max_length=100, unique=True)
    notified_at = models.DateTimeField(auto_now_add=True)
    pickup_location_name = models.CharField(max_length=255, null=True, blank=True)
    return_location_name = models.CharField(max_length=255, null=True, blank=True)
    distance = models.FloatField(null=True, blank=True)
    available_at = models.DateTimeField(null=True, blank=True)
    latest_return = models.DateTimeField(null=True, blank=True)
    travel_time = models.IntegerField(null=True, blank=True)
    car_type = models.CharField(max_length=255, null=True, blank=True)
