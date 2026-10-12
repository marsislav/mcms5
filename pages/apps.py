"""pages.apps - app configuration (registered as ``'pages'`` in INSTALLED_APPS)."""
from django.apps import AppConfig


class PagesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'pages'
