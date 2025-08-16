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

# Start Celery beat (with optional debugpy when DEBUG=1)
if [ "$DEBUG" = "1" ]; then
    echo "Starting Celery Beat with debugpy..."
    exec python -m debugpy --listen 0.0.0.0:5678 -m celery -A hertz_notifier beat --loglevel=info
else
    echo "Starting Celery Beat..."
    exec celery -A hertz_notifier beat --loglevel=info
fi
