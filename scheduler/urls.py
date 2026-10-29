from django.urls import path

from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('searches/', views.create_search, name='create_search'),
    path('searches/<int:pk>/', views.update_search, name='update_search'),
    path('searches/<int:pk>/delete/', views.delete_search, name='delete_search'),
]
