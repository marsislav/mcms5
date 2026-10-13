"""
siteconfig.context_processors - makes the settings available in EVERY template.

Enabled in ``mcms5/settings.py`` (TEMPLATES -> context_processors) as
``'siteconfig.context_processors.site_settings'``.

Adds one variable::

    site   the ``SiteSettings`` instance (one DB query per request)

Example: ``<title>{{ site.site_title }}</title>``.

Resilience: if the table does not exist yet (``python manage.py migrate`` has not
been run after installing this app) the site does NOT crash; it falls back to the
default, unsaved settings until the migration is applied.
"""
from django.db import OperationalError, ProgrammingError

from .models import SiteSettings


def site_settings(request):
    try:
        site = SiteSettings.load()
    except (OperationalError, ProgrammingError):  # "no such table" (SQLite) / "relation does not exist" (PostgreSQL)
        site = SiteSettings()
    return {'site': site}
