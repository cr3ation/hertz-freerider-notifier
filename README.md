# Hertz Freerider Notifier

A Django & Celery based solution that monitors Hertz Freerider every 2 minutes and sends Pushover alerts whenever a car that matches your saved searches becomes available.

## Features

* **Mobile‑first dashboard** – manage unlimited search rules with wildcards.
* **Secure authentication** – uses Django’s built‑in auth.
* **Pushover notifications** – one alert per unique ride (no spam).
* **Dockerized** – includes PostgreSQL, Redis, Celery worker & beat.
* **English‑only UI** – regardless of backend locale.

## Quick start

```bash
git clone https://github.com/yourfork/hertz-freerider-notifier.git
cd hertz-freerider-notifier
docker compose up --build
```

Then open <http://localhost:8000>, log in with *admin / password*, and add your first alert rule.

## Environment variables

| Name | Description |
| ---- | ----------- |
| `PUSHOVER_USER` | Your Pushover user key |
| `PUSHOVER_TOKEN` | Your Pushover app token |

See `.env.sample` for full list.
