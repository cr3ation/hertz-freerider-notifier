#!/bin/sh
# One image, three roles: docker-entrypoint.sh app | worker | beat (the compose file passes the role).
# DEV_SERVER=1 (compose.dev.yml) runs Django's dev server, and the app and worker under debugpy.
# Compose starts the containers once Postgres and Redis answer (healthchecks), so there is no waiting here.
set -e

case "${1:-app}" in
  app)
    # Migrations are created in development and committed, never generated here
    python manage.py migrate --noinput
    # On the first start, create the admin login from DJANGO_SUPERUSER_USERNAME / DJANGO_SUPERUSER_PASSWORD
    python manage.py shell --no-imports -c "
import os
from django.contrib.auth.models import User
username = os.environ.get('DJANGO_SUPERUSER_USERNAME') or 'admin'
if not User.objects.filter(username=username).exists():
    User.objects.create_superuser(username, f'{username}@example.com', os.environ.get('DJANGO_SUPERUSER_PASSWORD') or 'admin123')
    print(f'Superuser created: {username}')
"
    if [ "$DEV_SERVER" = "1" ]; then
      exec python -m debugpy --listen 0.0.0.0:5678 manage.py runserver 0.0.0.0:8000
    fi
    exec gunicorn hertz_notifier.wsgi:application --bind 0.0.0.0:8000 --workers 3 --timeout 120
    ;;
  worker)
    if [ "$DEV_SERVER" = "1" ]; then
      exec python -m debugpy --listen 0.0.0.0:5678 -m celery -A hertz_notifier worker --loglevel=info
    fi
    exec celery -A hertz_notifier worker --loglevel=info
    ;;
  beat)
    # The schedule file goes to /tmp, which is always writable
    exec celery -A hertz_notifier beat --loglevel=info --schedule /tmp/celerybeat-schedule
    ;;
  *)
    # Anything else, e.g. docker compose run app python manage.py createsuperuser
    exec "$@"
    ;;
esac
