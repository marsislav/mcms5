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
``fieldsets`` entry in ``siteconfig/admin.py``. Currently there are four:

  General     site title, description, favicon, admin e-mail, location,
              date format, time format, logo
  Discussion  comments on/off, approval mode, replies, spam rules (comments app)
  Users       e-mail the admin about new registrations, show the post author (users app)
  E-mail      how the site SENDS mail: server default / console / files / SMTP (local or remote),
              From address, "send a test e-mail" (see ``siteconfig/mail.py``)

To add a section (e.g. "SEO"): add the fields below + a migration, then add a
fieldset to ``SiteSettingsAdmin.fieldsets``. See ``docs/settings.md``.

Files
-----
Uploads go to ``MEDIA_ROOT/site/logo/`` and ``MEDIA_ROOT/site/favicon/``.
Replacing or clearing an image deletes the old file from disk (``save``).
"""
import datetime

from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator, MaxValueValidator, MinValueValidator
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

# Discussion -> how new comments are treated (see comments/services.py::decide_status).
MODERATION_MANUAL = 'manual'
MODERATION_AUTO = 'auto'
MODERATION_RETURNING = 'returning'
COMMENT_MODERATION_CHOICES = [
    (MODERATION_MANUAL, 'Manual approval - every comment waits until an admin approves it'),
    (MODERATION_AUTO, 'Automatic approval - comments are published immediately'),
    (MODERATION_RETURNING, 'Automatic for returning commenters - only the first comment of an e-mail waits for approval'),
]

# E-mail -> how outgoing mail is delivered (see siteconfig/mail.py::SiteEmailBackend).
EMAIL_MODE_DEFAULT = 'default'
EMAIL_MODE_CONSOLE = 'console'
EMAIL_MODE_FILE = 'file'
EMAIL_MODE_SMTP = 'smtp'
EMAIL_MODE_CHOICES = [
    (EMAIL_MODE_DEFAULT, 'Server default (settings.py / environment variables)'),
    (EMAIL_MODE_CONSOLE, 'Print in the server console (development, nothing is sent)'),
    (EMAIL_MODE_FILE, 'Save as .eml files in the "sent_emails" folder (development, nothing is sent)'),
    (EMAIL_MODE_SMTP, 'SMTP server (this computer\'s local mail server, or any other)'),
]
EMAIL_SECURITY_NONE = 'none'
EMAIL_SECURITY_STARTTLS = 'starttls'
EMAIL_SECURITY_SSL = 'ssl'
EMAIL_SECURITY_CHOICES = [
    (EMAIL_SECURITY_NONE, 'None (typical for a local server, port 25 / 1025)'),
    (EMAIL_SECURITY_STARTTLS, 'STARTTLS (usually port 587)'),
    (EMAIL_SECURITY_SSL, 'SSL/TLS (usually port 465)'),
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
        help_text='Administrator e-mail address. Shown in the page header and footer, and ALL system '
                  'notifications are sent to it (new comments, new registrations, the test e-mail). '
                  'Sending itself is configured in the "E-mail" section.')
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

    # --------------------------------------------------------------- Discussion
    comments_enabled = models.BooleanField(
        'Enable comments', default=True,
        help_text='Master switch. When off, the comment form and existing comments are hidden on the whole site '
                  '(nothing is deleted).')
    comments_moderation = models.CharField(
        'Comment approval', max_length=10, choices=COMMENT_MODERATION_CHOICES, default=MODERATION_MANUAL,
        help_text='Staff (logged-in users with the staff flag) are always approved automatically.')
    comments_require_name_email = models.BooleanField(
        'Name and e-mail required', default=True,
        help_text='Visitors must fill in a name and an e-mail address (the e-mail is never shown publicly).')
    comments_registered_only = models.BooleanField(
        'Only registered users can comment', default=False,
        help_text='Visitors must be logged in to see the comment form.')
    comments_threaded = models.BooleanField(
        'Enable replies (threaded comments)', default=True,
        help_text='Adds a "Reply" link to comments; replies are shown under the comment they answer.')
    comments_max_depth = models.PositiveSmallIntegerField(
        'Reply depth', default=3, validators=[MinValueValidator(2), MaxValueValidator(10)],
        help_text='Number of levels, 2-10. 3 = comment, reply, reply to the reply. Used only when replies are enabled.')
    comments_close_after_days = models.PositiveSmallIntegerField(
        'Close comments after (days)', default=0, validators=[MaxValueValidator(3650)],
        help_text='Automatically close comments on posts older than this many days. 0 = never.')
    comments_max_links = models.PositiveSmallIntegerField(
        'Hold for approval if more links than', default=2, validators=[MaxValueValidator(50)],
        help_text='A comment with more links than this always waits for approval, even with automatic approval.')
    comments_blocked_words = models.TextField(
        'Blocked words', blank=True,
        help_text='One word or phrase per line. A comment (text, name or e-mail) containing any of them is '
                  'marked as spam and never shown. Not case sensitive.')
    comments_email_admin = models.BooleanField(
        'E-mail me about new comments', default=False,
        help_text='Send a message to the Admin e-mail (General section) when a comment is posted or waits for approval. '
                  'Needs working e-mail settings on the server.')

    # -------------------------------------------------------------------- Users
    users_email_admin = models.BooleanField(
        'E-mail me about new registrations', default=True,
        help_text='Send a message to the Admin e-mail (General section) when someone registers. '
                  'Needs working e-mail settings (E-mail section).')
    show_author_box = models.BooleanField(
        'Show the post author', default=True,
        help_text='Show "by <author>" under the post title and the author box (photo, short description, '
                  'link to all posts of the author) after every post that has an author.')

    # ------------------------------------------------------------------- E-mail
    email_mode = models.CharField(
        'Sending method', max_length=10, choices=EMAIL_MODE_CHOICES, default=EMAIL_MODE_DEFAULT,
        help_text='"Server default" keeps whatever settings.py / the environment says (the console, unless '
                  'DJANGO_EMAIL_BACKEND is set). For a local server pick "SMTP server" and use host '
                  '"localhost" (or "127.0.0.1").')
    email_host = models.CharField(
        'SMTP host', max_length=255, blank=True, default='localhost',
        help_text='Local mail server: localhost. Remote: e.g. smtp.example.com.')
    email_port = models.PositiveIntegerField(
        'SMTP port', default=25, validators=[MinValueValidator(1), MaxValueValidator(65535)],
        help_text='25 = local Postfix/Exim; 1025 = Mailpit/MailHog (local test inbox); 587 = STARTTLS; 465 = SSL.')
    email_security = models.CharField(
        'Connection security', max_length=10, choices=EMAIL_SECURITY_CHOICES, default=EMAIL_SECURITY_NONE)
    email_user = models.CharField(
        'SMTP user', max_length=255, blank=True,
        help_text='Leave empty if the server needs no login (typical for a local server).')
    email_password = models.CharField(
        'SMTP password', max_length=255, blank=True,
        help_text='Stored in the database as plain text (it must be readable to log in). Leave the field empty '
                  'to keep the saved password.')
    email_from = models.EmailField(
        '"From" address', blank=True,
        help_text='Sender of the messages the site sends (e.g. no-reply@yourdomain). Empty = '
                  'DEFAULT_FROM_EMAIL from settings.py. Many servers only accept addresses of their own domain.')

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
