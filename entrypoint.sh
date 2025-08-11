#!/bin/bash
set -e

echo "Starting Django application..."

# Wait for database to be ready
echo "Waiting for database..."
python manage.py shell -c "
import sys
from django.db import connection
from django.core.management.color import no_style
style = no_style()
try:
    connection.cursor()
except Exception as e:
    print('Database not ready yet, retrying...')
    sys.exit(1)
print('Database is ready!')
"

# Create migrations for all apps
echo "Creating migrations..."
python manage.py makemigrations

# Apply migrations
echo "Applying migrations..."
python manage.py migrate

# Create superuser if it doesn't exist
echo "Creating superuser if needed..."
python manage.py shell -c "
import os
from django.contrib.auth.models import User
username = os.environ.get('DJANGO_SUPERUSER_USERNAME', 'admin')
password = os.environ.get('DJANGO_SUPERUSER_PASSWORD', 'admin123')
if not User.objects.filter(username=username).exists():
    User.objects.create_superuser(username, f'{username}@example.com', password)
    print(f'Superuser created: {username}/{password}')
else:
    print('Superuser already exists')
"

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Decide how to start based on DEBUG variable
if [ "$DEBUG" = "1" ]; then
    echo "Starting Django development server (runserver) in debug mode with debugpy..."
    echo "Debugger listening on port 5678. You can attach VS Code debugger."
    # För att få appen att vänta på debugger-klient: lägg till flaggan --wait-for-client efter --listen
    exec python -m debugpy --listen 0.0.0.0:5678 manage.py runserver 0.0.0.0:8000
else
    echo "Starting Gunicorn..."
    exec gunicorn hertz_notifier.wsgi:application --bind 0.0.0.0:8000 --workers 3 --timeout 120
fi
