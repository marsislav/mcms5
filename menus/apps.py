"""menus.apps - app configuration (registered as ``'menus'`` in INSTALLED_APPS)."""
from django.apps import AppConfig


class MenusConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'menus'
    verbose_name = 'Menus'  # section title in the admin index
