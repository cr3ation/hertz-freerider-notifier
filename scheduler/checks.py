"""System checks. They run on `manage.py migrate`, `check` and `runserver`, so the app container stops at startup."""

from django.conf import settings
from django.core.checks import Error, Tags, register

SAMPLE_SECRET_KEY = 'changeme'


@register(Tags.security)
def secret_key_check(app_configs, **kwargs):
    """Refuse the sample SECRET_KEY from .env.sample outside DEBUG: anyone knowing it could forge sessions."""
    if settings.DEBUG or settings.SECRET_KEY != SAMPLE_SECRET_KEY:
        return []
    return [
        Error(
            'SECRET_KEY is not set or still the sample value "changeme", and DEBUG is off.',
            hint='Set SECRET_KEY in .env to a long random string, e.g. the output of '
            '`python -c "import secrets; print(secrets.token_urlsafe(50))"`.',
            id='scheduler.E001',
        )
    ]
