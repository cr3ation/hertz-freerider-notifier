#!/bin/bash
set -e

echo "Starting Django application..."

# Wait for database to be ready
echo "Waiting for database..."
until python manage.py shell -c "from django.db import connection; connection.cursor()" 2>/dev/null; do
    echo 'Database not ready yet...';
    sleep 2;
done
echo 'Database is ready!'

# Start Celery beat (with optional debugpy when DEBUG=1)
if [ "$DEBUG" = "1" ]; then
    echo "Starting Celery Beat with debugpy..."
    exec python -m debugpy --listen 0.0.0.0:5678 -m celery -A hertz_notifier beat --loglevel=info
else
    echo "Starting Celery Beat..."
    exec celery -A hertz_notifier beat --loglevel=info
fi
