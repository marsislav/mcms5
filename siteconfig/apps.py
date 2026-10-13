"""siteconfig.apps - app configuration (registered as ``'siteconfig'`` in INSTALLED_APPS)."""
from django.apps import AppConfig


class SiteconfigConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'siteconfig'
    verbose_name = 'Settings'  # section title in the admin index (sidebar)
