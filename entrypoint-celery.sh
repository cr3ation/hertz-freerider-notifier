#!/bin/bash
set -e

ROLE=${CELERY_ROLE:-worker}

echo "Starting Celery (${ROLE})..."

echo "Waiting for database..."
python manage.py shell -c "
import sys
from django.db import connection
try:
    connection.cursor()
except Exception:
    print('Database not ready yet, retrying...')
    sys.exit(1)
print('Database is ready!')
"

# Collect static files (only needed once; harmless if repeated). Useful when code mounted as volume.
if [ "${ROLE}" = "worker" ]; then
  echo "Collecting static files (worker)..."
  python manage.py collectstatic --noinput >/dev/null 2>&1 || true
fi

if [ "${ROLE}" = "worker" ]; then
  if [ "${DEBUG}" = "1" ]; then
    echo "Launching Celery worker with debugpy on 0.0.0.0:5678"
    # Add --wait-for-client after --listen to pause until debugger attaches (optional)
    exec python -m debugpy --listen 0.0.0.0:5678 -m celery -A hertz_notifier worker --loglevel=info
  else
    echo "Launching Celery worker"
    exec celery -A hertz_notifier worker --loglevel=info
  fi
elif [ "${ROLE}" = "beat" ]; then
  echo "Launching Celery beat scheduler"
  exec celery -A hertz_notifier beat --loglevel=info
else
  echo "Unknown CELERY_ROLE='${ROLE}' (expected 'worker' or 'beat')" >&2
  exit 1
fi
