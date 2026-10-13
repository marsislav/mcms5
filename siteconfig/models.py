"""
siteconfig.models - site-wide settings editable from the admin (Settings pane).

Overview
--------
``SiteSettings`` is a SINGLETON: the table always holds exactly one row
(``pk=1``). Get it anywhere in Python with::

    from siteconfig.models import SiteSettings
    s = SiteSettings.load()          # creates the row with defaults on first use
    s.site_title, s.logo, s.format_date(some_date) ...

In templates use the ``site`` variable from the context processor
(``siteconfig.context_processors.site_settings``)::

    {{ site.site_title }}   {% if site.logo %}<img src="{{ site.logo.url }}">{% endif %}

Sections
--------
The admin form is split into SECTIONS (tabs). Each section is one
``fieldsets`` entry in ``siteconfig/admin.py``. Currently there is one:

  General   site title, description, favicon, admin e-mail, location,
            date format, time format, logo

To add a section (e.g. "SEO"): add the fields below + a migration, then add a
fieldset to ``SiteSettingsAdmin.fieldsets``. See ``docs/settings.md``.

Files
-----
Uploads go to ``MEDIA_ROOT/site/logo/`` and ``MEDIA_ROOT/site/favicon/``.
Replacing or clearing an image deletes the old file from disk (``save``).
"""
import datetime

from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models
from django.template.defaultfilters import date as date_filter, time as time_filter
from django.utils.deconstruct import deconstructible
from django.utils.dateformat import format as dj_format

# --- choices for the date / time format fields -------------------------------
# Values use DJANGO date-format syntax (the same as the ``|date`` template
# filter): https://docs.djangoproject.com/en/6.1/ref/templates/builtins/#date
# The label shows what the format looks like (12 Oct 2026 / 14:05).
CUSTOM = 'custom'

DATE_FORMAT_CHOICES = [
    ('j F Y', '12 October 2026  (j F Y)'),
    ('d.m.Y', '12.10.2026  (d.m.Y)'),
    ('d/m/Y', '12/10/2026  (d/m/Y)'),
    ('m/d/Y', '10/12/2026  (m/d/Y)'),
    ('Y-m-d', '2026-10-12  (Y-m-d)'),
    ('F j, Y', 'October 12, 2026  (F j, Y)'),
    (CUSTOM, 'Custom...'),
]
TIME_FORMAT_CHOICES = [
    ('H:i', '14:05  (H:i) - 24-hour'),
    ('H:i:s', '14:05:09  (H:i:s) - 24-hour with seconds'),
    ('g:i A', '2:05 PM  (g:i A) - 12-hour'),
    ('g:i a', '2:05 pm  (g:i a) - 12-hour'),
    (CUSTOM, 'Custom...'),
]

# Max upload sizes (bytes) - validated in the form (``clean_*`` below).
MAX_LOGO_SIZE = 2 * 1024 * 1024      # 2 MB
MAX_FAVICON_SIZE = 512 * 1024        # 512 KB


@deconstructible
class MaxFileSize:
    """Validator rejecting files larger than ``max_bytes`` (``deconstructible`` = migration-safe)."""

    def __init__(self, max_bytes):
        self.max_bytes = max_bytes

    def __call__(self, f):
        if f.size > self.max_bytes:
            raise ValidationError('File too large (%(size).1f MB). Maximum is %(max).1f MB.',
                                  params={'size': f.size / 1048576, 'max': self.max_bytes / 1048576},
                                  code='too_large')

    def __eq__(self, other):
        return isinstance(other, MaxFileSize) and other.max_bytes == self.max_bytes


def _check_format(value):
    """A custom format must not be empty and must produce some output."""
    if not value or not dj_format(datetime.datetime(2026, 10, 12, 14, 5, 9), value).strip():
        raise ValidationError('Enter a valid format, e.g. d.m.Y', code='bad_format')


class SiteSettings(models.Model):
    """The single row with all site-wide settings. See module docstring."""

    # ------------------------------------------------------------------ General
    site_title = models.CharField(
        'Site title', max_length=120, default='mCMS 5',
        help_text='Name of the site. Used in the browser tab title and as the fallback logo text.')
    site_description = models.TextField(
        'Site description', blank=True, max_length=300,
        help_text='Short tagline / summary of the site (up to 300 characters). '
                  'Used as the "description" meta tag (shown by search engines).')
    favicon = models.FileField(
        'Favicon', upload_to='site/favicon/', blank=True,
        validators=[FileExtensionValidator(['ico', 'png', 'svg', 'gif', 'jpg', 'jpeg']),
                    MaxFileSize(MAX_FAVICON_SIZE)],
        help_text='Small icon shown in the browser tab. Allowed: .ico, .png, .svg, .gif, .jpg '
                  '(max 512 KB). Recommended: square PNG/ICO, at least 32x32 px.')
    admin_email = models.EmailField(
        'Admin e-mail', blank=True,
        help_text='Main contact / administrator e-mail address of the site. Shown in the page header '
                  'and footer, and the address system notifications should be sent to.')
    location = models.CharField(
        'Location', max_length=255, blank=True,
        help_text='Physical address or place, e.g. "Str 28, Plovdiv, 4000, Bulgaria". '
                  'Shown in the page header and footer.')
    date_format = models.CharField(
        'Date format', max_length=40, choices=DATE_FORMAT_CHOICES, default='j F Y',
        help_text='How dates are displayed on the site. Choose "Custom..." to type your own format.')
    date_format_custom = models.CharField(
        'Custom date format', max_length=40, blank=True,
        help_text='Used only when "Date format" is "Custom...". Django syntax: '
                  'd=day, j=day (no zero), m=month number, M=Oct, F=October, Y=2026, y=26. '
                  'Example: d.m.Y')
    time_format = models.CharField(
        'Time format', max_length=40, choices=TIME_FORMAT_CHOICES, default='H:i',
        help_text='How times are displayed on the site. Choose "Custom..." to type your own format.')
    time_format_custom = models.CharField(
        'Custom time format', max_length=40, blank=True,
        help_text='Used only when "Time format" is "Custom...". Django syntax: '
                  'H=hour 00-23, g=hour 1-12, i=minutes, s=seconds, A=AM/PM. Example: H:i')
    logo = models.ImageField(
        'Logo', upload_to='site/logo/', blank=True,
        validators=[MaxFileSize(MAX_LOGO_SIZE)],
        help_text='Site logo shown in the header and footer. PNG/SVG-like transparent images work best '
                  '(JPG, PNG, GIF, WebP; max 2 MB). If empty, the site title is shown as text.')

    class Meta:
        verbose_name = 'Settings'
        verbose_name_plural = 'Settings'

    def __str__(self):
        return 'Site settings'

    # ------------------------------------------------------------------ singleton
    @classmethod
    def load(cls):
        """Return THE settings row, creating it with defaults if it does not exist yet."""
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def clean(self):
        """Cross-field validation: a custom format is required when "Custom..." is chosen."""
        errors = {}
        if self.date_format == CUSTOM:
            try:
                _check_format(self.date_format_custom)
            except ValidationError as e:
                errors['date_format_custom'] = e
        if self.time_format == CUSTOM:
            try:
                _check_format(self.time_format_custom)
            except ValidationError as e:
                errors['time_format_custom'] = e
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        """Force the singleton pk and delete replaced/cleared image files from disk."""
        self.pk = 1
        old = type(self).objects.filter(pk=1).first()
        super().save(*args, **kwargs)
        if old:
            for name in ('logo', 'favicon'):
                old_file, new_file = getattr(old, name), getattr(self, name)
                if old_file and old_file.name != (new_file.name if new_file else None):
                    old_file.storage.delete(old_file.name)

    def delete(self, *args, **kwargs):
        """The singleton cannot be deleted (it would just be re-created with defaults)."""
        raise ValidationError('The site settings cannot be deleted.')

    # ------------------------------------------------------------------ helpers
    @property
    def date_format_string(self):
        """The effective Django date format string (custom value if "Custom..." is selected)."""
        if self.date_format == CUSTOM and self.date_format_custom:
            return self.date_format_custom
        return self.date_format if self.date_format != CUSTOM else 'j F Y'

    @property
    def time_format_string(self):
        """The effective Django time format string."""
        if self.time_format == CUSTOM and self.time_format_custom:
            return self.time_format_custom
        return self.time_format if self.time_format != CUSTOM else 'H:i'

    def format_date(self, value):
        """Format a date/datetime with the site date format (datetimes are converted to local time)."""
        return date_filter(value, self.date_format_string) if value else ''

    def format_time(self, value):
        """Format a time/datetime with the site time format."""
        return time_filter(value, self.time_format_string) if value else ''

    def format_datetime(self, value):
        """``"<date> <time>"`` using both site formats."""
        if not value:
            return ''
        return '%s %s' % (self.format_date(value), self.format_time(value))
