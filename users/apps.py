"""users.apps - app configuration (registered as ``'users'`` in INSTALLED_APPS)."""
from django.apps import AppConfig


class UsersConfig(AppConfig):
    name = 'users'

    def ready(self):
        from . import signals  # noqa: F401  (registers the receivers)
