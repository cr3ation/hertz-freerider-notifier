import re

from django.contrib.auth import get_user_model
from django.db import models


def wildcard_match(pattern, text):
    """'Stockholm*' matches 'Stockholm Arlanda Flygplats': case-insensitive, * stands for anything."""
    regex = '^' + re.escape(pattern).replace('\\*', '.*') + '$'
    return re.match(regex, text or '', re.IGNORECASE) is not None


class SavedSearch(models.Model):
    owner = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    date_from = models.DateField()
    date_to = models.DateField()
    origin = models.CharField(max_length=100, help_text='Use * as wildcard')
    destination = models.CharField(max_length=100, help_text='Use * as wildcard')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            # The form gives a friendly error first; this keeps searches that can never match out of the database
            models.CheckConstraint(
                condition=models.Q(date_from__lte=models.F('date_to')), name='savedsearch_dates_in_order'
            ),
        ]

    def __str__(self):
        return f"{self.origin} → {self.destination} ({self.date_from} – {self.date_to})"

    def matches(self, ride):
        """The one matching rule, for the dashboard and the notifications alike (ride: a hertz.Ride).

        The search's dates must overlap the car's pickup–return window, and both station names must match.
        """
        if self.date_to < ride.available_at.date() or self.date_from > ride.latest_return.date():
            return False
        return wildcard_match(self.origin, ride.origin) and wildcard_match(self.destination, ride.destination)


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
