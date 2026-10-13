"""
users.urls - routes under ``/users/`` (mounted in ``mcms5/urls.py``).

Namespace ``users``:
    users:register                -> /users/register/
    users:profile                 -> /users/profile/                (log in required: edit my profile)
    users:author                  -> /users/author/<username>/      (public: author + all their posts)
    users:login                   -> /users/login/
    users:logout                  -> /users/logout/                 (POST)
    users:password_reset          -> /users/password-reset/         ("Forgot password?")
    users:password_reset_done     -> /users/password-reset/done/
    users:password_reset_confirm  -> /users/reset/<uidb64>/<token>/  (link from the e-mail)
    users:password_reset_complete -> /users/reset/done/
"""
from django.urls import path

from . import views

app_name = 'users'
urlpatterns = [
    path('register/', views.register_view, name='register'),
    path('profile/', views.profile_edit, name='profile'),
    path('author/<str:username>/', views.author_page, name='author'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('password-reset/', views.ResetView.as_view(), name='password_reset'),
    path('password-reset/done/', views.ResetDoneView.as_view(), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', views.ConfirmView.as_view(), name='password_reset_confirm'),
    path('reset/done/', views.CompleteView.as_view(), name='password_reset_complete'),
]
