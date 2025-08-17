#!/bin/bash
set -e

# Unified worker entrypoint.
# This script now covers BOTH the previous normal worker and the old
# entrypoint-worker-debug.sh functionality.
# Debug mode: set DEBUG=1 (as already done for the app service when you want debugging)
#   When DEBUG=1 the Celery worker is started under debugpy on port 5678.
#   Attach VS Code using the "Python: Remote Attach" configuration (host: localhost, port: 5679 on the host as mapped in docker-compose).
# Normal mode: any other value (or empty) for DEBUG starts a plain Celery worker.
# The former entrypoint-worker-debug.sh file can now be deleted safely.

echo "Starting Django application..."

echo "Waiting for database to be ready..."
until python manage.py shell -c "from django.db import connection; connection.cursor()" 2>/dev/null; do
    echo 'Database not ready yet...';
    sleep 2;
done
echo 'Database is ready!'

echo "Collecting static files..."
python manage.py collectstatic --noinput

if [ "$DEBUG" = "1" ]; then
    echo "Starting Celery Worker with debugpy..."
    echo "Debugger listening on port 5678 (container). Host port is mapped via docker-compose (e.g. 5679:5678)."
    # To have the worker wait for the debugger to attach, append: --wait-for-client
    exec python -m debugpy --listen 0.0.0.0:5678 -m celery -A hertz_notifier worker --loglevel=info
else
    echo "Starting Celery Worker without debugpy..."
    exec celery -A hertz_notifier worker --loglevel=info
fi
