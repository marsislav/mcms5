"""
siteconfig.templatetags.site_tags - format dates/times with the admin-selected formats.

Usage::

    {% load site_tags %}
    {{ post.date|site_date }}        -> 12.10.2026      (Settings -> Date format)
    {{ post.date|site_time }}        -> 14:05           (Settings -> Time format)
    {{ post.date|site_datetime }}    -> 12.10.2026 14:05

Falls back to the defaults if the value is empty. Datetimes are converted to
the current time zone (``TIME_ZONE``) like Django's built-in ``|date`` filter.
"""
from django import template

from django.db import OperationalError, ProgrammingError

from ..models import SiteSettings

register = template.Library()


def _settings():
    """The settings row, or unsaved defaults if the migration has not been applied yet."""
    try:
        return SiteSettings.load()
    except (OperationalError, ProgrammingError):
        return SiteSettings()


@register.filter
def site_date(value):
    return _settings().format_date(value)


@register.filter
def site_time(value):
    return _settings().format_time(value)


@register.filter
def site_datetime(value):
    return _settings().format_datetime(value)
