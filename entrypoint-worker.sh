#!/bin/bash
set -e

echo "Starting Django application..."

echo "Waiting for database to be ready..."
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

echo "Collecting static files..."
python manage.py collectstatic --noinput

if [ "$DEBUG" = "1" ]; then
    echo "Starting Celery Worker with debugpy..."
    echo "Debugger listening on port 5678. You can attach VS Code debugger."
    # To make the worker wait for a debugger client: add --wait-for-client after --listen
    exec python -m debugpy --listen 0.0.0.0:5678 -m celery -A hertz_notifier worker --loglevel=info
else
    echo "Starting Celery Worker without debugpy..."
    exec celery -A hertz_notifier worker --loglevel=info
fi
