"""search.apps - app configuration (registered as ``'search'`` in INSTALLED_APPS)."""
from django.apps import AppConfig


class SearchConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'search'
    verbose_name = 'Search'

    def ready(self):
        # Make SQLite's LIKE (used by Django's ``icontains``) case-insensitive for
        # ALL languages, not only ASCII. See ``search/sqlite.py``.
        from django.db.backends.signals import connection_created
        from .sqlite import install_unicode_like
        connection_created.connect(install_unicode_like, dispatch_uid='search_unicode_like')
