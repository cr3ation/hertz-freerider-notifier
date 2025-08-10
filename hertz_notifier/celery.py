import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hertz_notifier.settings')
app = Celery('hertz_notifier')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
