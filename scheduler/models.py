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
