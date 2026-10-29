import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# With DEBUG=0 the app refuses to start on this sample value (scheduler/checks.py)
SECRET_KEY = os.getenv('SECRET_KEY') or 'changeme'
DEBUG = int(os.getenv('DEBUG') or 0)

ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '127.0.0.1,localhost').split(',')
CSRF_TRUSTED_ORIGINS = [o for o in os.getenv('CSRF_TRUSTED_ORIGINS', '').split(',') if o]

# HTTPS=1 when the site is only reached through an HTTPS proxy such as Cloudflare: trust its
# X-Forwarded-Proto header and send the session and CSRF cookies over HTTPS only
if int(os.getenv('HTTPS') or 0):
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'scheduler',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'hertz_notifier.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'hertz_notifier.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME', 'db'),
        'USER': os.getenv('DB_USER', 'devuser'),
        'PASSWORD': os.getenv('DB_PASS', 'changeme'),
        'HOST': os.getenv('DB_HOST', 'db'),
        'PORT': os.getenv('DB_PORT', '5432'),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Europe/Stockholm'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# WhiteNoise configuration (STORAGES replaces STATICFILES_STORAGE, which Django 5.1 removed)
STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'hertz_notifier.storage.StaticStorage'},
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Django's cache lives in Redis database 1 (Celery's broker uses database 0). The worker keeps the latest
# Hertz routes there for the dashboard, and the notification maps keep their OpenStreetMap tiles there.
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': os.getenv('REDIS_URL', 'redis://redis:6379/1'),
    }
}

CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://redis:6379/0')
HERTZ_CHECK_INTERVAL = float(os.getenv('HERTZ_CHECK_INTERVAL') or 120)  # seconds
CELERY_BEAT_SCHEDULE = {
    'check_hertz_freerider': {
        'task': 'scheduler.tasks.check_hertz',
        'schedule': HERTZ_CHECK_INTERVAL,
    },
}

PUSHOVER_USER = os.getenv('PUSHOVER_USER')
PUSHOVER_TOKEN = os.getenv('PUSHOVER_TOKEN')
# The dashboard's address, e.g. https://hertz.example.com; the notification's button opens the route there
SITE_URL = os.getenv('SITE_URL', '').rstrip('/')

# Auth flow
LOGOUT_REDIRECT_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/'  # redirect to dashboard after successful login

# Everything at INFO and above to the console, which Docker collects (docker compose logs)
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {'plain': {'format': '%(asctime)s %(levelname)s %(name)s: %(message)s'}},
    'handlers': {'console': {'class': 'logging.StreamHandler', 'formatter': 'plain'}},
    'root': {'handlers': ['console'], 'level': 'INFO'},
    # Replaces Django's own console handler, which would print its messages a second time when DEBUG=1
    'loggers': {'django': {'handlers': ['console'], 'level': 'INFO', 'propagate': False}},
}
