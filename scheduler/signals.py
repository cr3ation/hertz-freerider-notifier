from django.db.models.signals import post_migrate
from django.dispatch import receiver
from django.conf import settings
from django.contrib.auth import get_user_model

@receiver(post_migrate)
def create_default_superuser(sender, **kwargs):
    if settings.DEBUG:
        User = get_user_model()
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser('admin', 'admin@example.com', 'password')
