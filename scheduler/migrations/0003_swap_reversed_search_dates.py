from django.db import migrations, models


def swap_reversed_dates(apps, schema_editor):
    """Searches saved before the form checked the date order would block the constraint in 0004: swap their dates."""
    SavedSearch = apps.get_model('scheduler', 'SavedSearch')
    for search in SavedSearch.objects.filter(date_from__gt=models.F('date_to')):
        search.date_from, search.date_to = search.date_to, search.date_from
        search.save(update_fields=['date_from', 'date_to'])


class Migration(migrations.Migration):
    # Kept apart from the AddConstraint in 0004: PostgreSQL can refuse to alter a table in the same transaction
    # as a data change to it ("pending trigger events")
    dependencies = [
        ('scheduler', '0002_notifiedride_available_at_notifiedride_car_type_and_more'),
    ]

    operations = [
        migrations.RunPython(swap_reversed_dates, migrations.RunPython.noop),
    ]
