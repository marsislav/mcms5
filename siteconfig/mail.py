"""
siteconfig.mail - e-mail sending that follows admin -> Settings -> E-mail.

``SiteEmailBackend`` is the project's ``EMAIL_BACKEND`` (``mcms5/settings.py``). On every send it
reads the settings row and hands the messages to the matching Django backend:

====================  ==========================================================================
Sending method        Delegate
====================  ==========================================================================
Server default        ``settings.EMAIL_FALLBACK_BACKEND`` (env ``DJANGO_EMAIL_BACKEND``; the
                      console backend unless set) with the EMAIL_* values of ``settings.py``.
                      This is how the site behaved before the E-mail section existed.
Console               prints the message in the terminal running ``runserver``.
Files                 writes one ``.eml`` file per message into ``settings.EMAIL_FILE_PATH``
                      (``sent_emails/``). Open them with any mail client.
SMTP server           host / port / security / user / password from the settings row.
                      Local server: host ``localhost``, port 25 (or 1025 for Mailpit/MailHog),
                      security "None", no user.
====================  ==========================================================================

The optional "From" address replaces ``DEFAULT_FROM_EMAIL`` on messages that did not choose a sender
(password reset, notifications), so it also applies to Django's own e-mails.

Nothing is cached: change the settings and the next message uses them (no restart needed).

``notify_admin()`` is the one-liner for "tell the administrator" messages.
"""
from django.conf import settings
from django.core.mail import get_connection, send_mail
from django.core.mail.backends.base import BaseEmailBackend
from django.db import OperationalError, ProgrammingError

from .models import (EMAIL_MODE_CONSOLE, EMAIL_MODE_FILE, EMAIL_MODE_SMTP, EMAIL_SECURITY_SSL,
                     EMAIL_SECURITY_STARTTLS, SiteSettings)

CONSOLE = 'django.core.mail.backends.console.EmailBackend'
FILE = 'django.core.mail.backends.filebased.EmailBackend'
SMTP = 'django.core.mail.backends.smtp.EmailBackend'
SMTP_TIMEOUT = 10  # seconds - a dead mail server must not hang a page for minutes


def _site():
    """The settings row, or unsaved defaults before ``migrate`` has been run."""
    try:
        return SiteSettings.load()
    except (OperationalError, ProgrammingError):
        return SiteSettings()


class SiteEmailBackend(BaseEmailBackend):
    """Delivers through the method chosen in Settings -> E-mail (see the module docstring)."""

    def _delegate(self, site):
        silent = self.fail_silently
        if site.email_mode == EMAIL_MODE_CONSOLE:
            return get_connection(CONSOLE, fail_silently=silent)
        if site.email_mode == EMAIL_MODE_FILE:
            return get_connection(FILE, fail_silently=silent, file_path=settings.EMAIL_FILE_PATH)
        if site.email_mode == EMAIL_MODE_SMTP:
            return get_connection(
                SMTP, fail_silently=silent,
                host=site.email_host or 'localhost', port=site.email_port or 25,
                username=site.email_user, password=site.email_password,   # '' = no login (never the env values)
                use_tls=site.email_security == EMAIL_SECURITY_STARTTLS,
                use_ssl=site.email_security == EMAIL_SECURITY_SSL,
                timeout=SMTP_TIMEOUT)
        fallback = getattr(settings, 'EMAIL_FALLBACK_BACKEND', CONSOLE)
        if fallback == '%s.%s' % (__name__, type(self).__name__):   # would call itself forever
            fallback = CONSOLE
        return get_connection(fallback, fail_silently=silent)

    def send_messages(self, email_messages):
        if not email_messages:
            return 0
        site = _site()
        if site.email_from:
            for message in email_messages:
                if message.from_email == settings.DEFAULT_FROM_EMAIL:
                    message.from_email = site.email_from
        return self._delegate(site).send_messages(email_messages)


def notify_admin(subject, message):
    """E-mail the administrator (Settings -> General -> Admin e-mail). Never raises.

    Returns True when a message was handed to the mail backend, False when there is no admin
    e-mail or sending failed (the site keeps working without mail).
    """
    site = _site()
    if not site.admin_email:
        return False
    subject = '[%s] %s' % (site.site_title, ' '.join(subject.split()))   # one line: no header injection
    try:
        return bool(send_mail(subject, message, None, [site.admin_email], fail_silently=True))
    except Exception:       # e.g. a backend that raises despite fail_silently
        return False
