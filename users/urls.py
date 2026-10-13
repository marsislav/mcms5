"""
users.urls - routes under ``/users/`` (mounted in ``mcms5/urls.py``).

Namespace ``users``:
    users:register -> /users/register/
"""
from django.urls import path
from . import views

app_name = 'users'
urlpatterns = [
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
]
