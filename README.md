# Hertz Freerider Notifier

A Django & Celery based solution that monitors Hertz Freerider every 2 minutes and sends Pushover alerts whenever a car that matches your saved searches becomes available.

## Features

* **Mobile‑first dashboard** – manage unlimited search rules with wildcards.
* **Secure authentication** – uses Django’s built‑in auth.
* **Pushover notifications** – one alert per unique ride (no spam).
* **Dockerized** – includes PostgreSQL, Redis, Celery worker & beat.
* **English‑only UI** – regardless of backend locale.

## Prerequisites

- Docker and Docker Compose
- A Pushover account (for notifications)

## Setup Instructions

### 1. Clone and setup environment

```bash
git clone https://github.com/yourfork/hertz-freerider-notifier.git
cd hertz-freerider-notifier
```

### 2. Configure environment variables

Copy the sample environment file and edit it with your settings:

```bash
cp .env.sample .env
```

Edit `.env` and update these important variables:
- `PUSHOVER_USER` - Your Pushover user key
- `PUSHOVER_TOKEN` - Your Pushover app token  
- `SECRET_KEY` - A secure random string for Django
- `DB_PASS` - A secure password for the database

### 3. Start the application

```bash
docker compose up --build -d
```

This will start all services:
- **app**: Django web application (port 8000)
- **db**: PostgreSQL database
- **redis**: Redis for Celery
- **worker**: Celery worker for background tasks
- **beat**: Celery beat scheduler

### 4. Start the application

```bash
docker compose up --build -d
```

This will automatically:
- **Build the containers** with all dependencies
- **Start all services**:
  - **app**: Django web application (port 8000)
  - **db**: PostgreSQL database
  - **redis**: Redis for Celery
  - **worker**: Celery worker for background tasks
  - **beat**: Celery beat scheduler
- **Initialize the database** (create migrations and run them)
- **Create a default admin user** (username: `admin`, password: `admin123`)
- **Collect static files**

### 5. Access the application

Open <http://localhost:8000> in your browser and log in with:
- **Username**: `admin`
- **Password**: `admin123`

You can now start adding search rules!

## Troubleshooting

### Database Connection Issues

If you see database authentication errors, you may have old database data. Clean up and restart:

```bash
docker compose down
docker volume rm hertz_freerider_notifier_postgres_data
docker compose up --build -d
```

The application will automatically recreate the database and admin user.

### Check Service Status

View running containers:
```bash
docker ps
```

View logs for specific services:
```bash
docker compose logs app
docker compose logs worker
docker compose logs beat
docker compose logs db
```

### Reset Admin Password

If you need to change the admin password:

```bash
docker compose exec app python manage.py shell -c "
from django.contrib.auth.models import User
user = User.objects.get(username='admin')
user.set_password('new_password')
user.save()
print('Password updated')
"
```

### Create Additional Users

To create additional admin users:

```bash
docker compose exec app python manage.py createsuperuser
```

## Environment variables

| Name | Description | Default |
| ---- | ----------- | ------- |
| `SECRET_KEY` | Django secret key | `changeme` |
| `DEBUG` | Debug mode (0 or 1) | `1` |
| `DB_NAME` | Database name | `db` |
| `DB_USER` | Database username | `devuser` |
| `DB_PASS` | Database password | `changeme` |
| `DB_HOST` | Database host | `db` |
| `DB_PORT` | Database port | `5432` |
| `ALLOWED_HOSTS` | Allowed hosts (comma-separated) | `127.0.0.1,localhost` |
| `PUSHOVER_USER` | Your Pushover user key | - |
| `PUSHOVER_TOKEN` | Your Pushover app token | - |
| `CELERY_BROKER_URL` | Redis URL for Celery | `redis://redis:6379/0` |

See `.env.sample` for the complete configuration template.

## How It Works

1. **Celery Beat** runs every 2 minutes and triggers the monitoring task
2. **Celery Worker** executes the task that:
   - Fetches available rides from Hertz Freerider API
   - Compares them against your saved search criteria
   - Sends Pushover notifications for new matches
   - Records notified rides to prevent duplicate alerts
3. **Django Web App** provides the user interface for managing search rules

## Development

To make changes to the code:

1. Edit files locally
2. Restart the relevant services:
   ```bash
   docker compose restart app worker beat
   ```

To view real-time logs:
```bash
docker compose logs -f worker beat
```
