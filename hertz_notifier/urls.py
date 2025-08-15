from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.views.decorators.csrf import csrf_protect
from django.utils.decorators import method_decorator
from django.contrib.auth.views import LogoutView


class PostOnlyLogoutView(LogoutView):
    """Force logout via POST to avoid accidental GET-triggered logout."""
    def dispatch(self, request, *args, **kwargs):
        if request.method != 'POST':
            # Optionally redirect instead of logging out on GET
            from django.shortcuts import redirect
            return redirect('dashboard') if request.user.is_authenticated else redirect('login')
        return super().dispatch(request, *args, **kwargs)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/login/', auth_views.LoginView.as_view(), name='login'),
    path('accounts/logout/', PostOnlyLogoutView.as_view(), name='logout'),
    path('', include('scheduler.urls')),
]
