"""siteconfig e-mail tests: the sending methods, the "From" address, notify_admin, the admin test mail."""
import contextlib
import io
import os
import shutil
import socket
import tempfile
import threading

from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.core import mail
from django.core.mail import send_mail
from django.core.mail.backends import console, filebased, smtp
from django.test import TestCase, override_settings
from django.urls import reverse

from .mail import SiteEmailBackend, notify_admin
from .models import SiteSettings

LOCMEM = 'django.core.mail.backends.locmem.EmailBackend'
SITE = 'siteconfig.mail.SiteEmailBackend'


class FakeSMTPServer:
    """A tiny local SMTP server (one thread) that records the messages it receives - stands in for the
    "local mail server" so the real SMTP code path is tested end to end."""

    def __init__(self):
        self.messages = []
        self.sock = socket.socket()
        self.sock.bind(('127.0.0.1', 0))
        self.sock.listen(5)
        self.port = self.sock.getsockname()[1]
        self.thread = threading.Thread(target=self._serve, daemon=True)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *exc):
        self.sock.close()

    def _serve(self):
        while True:
            try:
                conn, _ = self.sock.accept()
            except OSError:
                return
            with conn:
                self._session(conn.makefile('rwb', buffering=0))

    def _session(self, f):
        f.write(b'220 fake ESMTP\r\n')
        data_mode, buf, sender, rcpts = False, [], None, []
        while True:
            line = f.readline()
            if not line:
                return
            if data_mode:
                if line == b'.\r\n':
                    self.messages.append({'from': sender, 'to': rcpts, 'data': b''.join(buf).decode('utf-8', 'replace')})
                    data_mode, buf = False, []
                    f.write(b'250 queued\r\n')
                else:
                    buf.append(line)
                continue
            cmd = line[:4].upper()
            if cmd in (b'EHLO', b'HELO'):
                f.write(b'250 fake\r\n')
            elif cmd == b'MAIL':
                sender, rcpts = line.decode().split(':', 1)[1].strip().strip('<>').split('>')[0], []
                f.write(b'250 ok\r\n')
            elif cmd == b'RCPT':
                rcpts.append(line.decode().split(':', 1)[1].strip().strip('<>').split('>')[0])
                f.write(b'250 ok\r\n')
            elif cmd == b'DATA':
                data_mode = True
                f.write(b'354 go\r\n')
            elif cmd == b'QUIT':
                f.write(b'221 bye\r\n')
                return
            else:
                f.write(b'250 ok\r\n')


def closed_port():
    s = socket.socket()
    s.bind(('127.0.0.1', 0))
    port = s.getsockname()[1]
    s.close()
    return port


def configure(**fields):
    s = SiteSettings.load()
    for k, v in fields.items():
        setattr(s, k, v)
    s.save()
    return s


@override_settings(EMAIL_BACKEND=SITE, EMAIL_FALLBACK_BACKEND=LOCMEM, DEFAULT_FROM_EMAIL='webmaster@localhost')
class BackendTests(TestCase):
    def test_default_method_uses_the_server_default_backend(self):
        send_mail('Hi', 'Body', None, ['to@x.bg'])
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].from_email, 'webmaster@localhost')

    @override_settings(EMAIL_FALLBACK_BACKEND=SITE)
    def test_fallback_pointing_at_itself_does_not_loop(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            send_mail('Loop?', 'Body', None, ['to@x.bg'])
        self.assertIn('Loop?', out.getvalue())

    def test_console_method(self):
        configure(email_mode='console')
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            send_mail('Printed', 'Body', None, ['to@x.bg'])
        self.assertIn('Subject: Printed', out.getvalue())
        self.assertEqual(mail.outbox, [])

    def test_file_method_writes_eml_files(self):
        folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, folder, True)
        configure(email_mode='file')
        with override_settings(EMAIL_FILE_PATH=folder):
            send_mail('Saved', 'Body', None, ['to@x.bg'])
        files = os.listdir(folder)
        self.assertEqual(len(files), 1)
        self.assertTrue(files[0].endswith('.log'))        # Django's file backend names them *.log
        self.assertIn('Subject: Saved', open(os.path.join(folder, files[0]), encoding='utf-8').read())

    def test_smtp_method_builds_the_smtp_backend_from_the_settings(self):
        site = configure(email_mode='smtp', email_host='mail.example.com', email_port=587,
                         email_security='starttls', email_user='u', email_password='p')
        b = SiteEmailBackend()._delegate(site)
        self.assertIsInstance(b, smtp.EmailBackend)
        self.assertEqual((b.host, b.port, b.username, b.password, b.use_tls, b.use_ssl),
                         ('mail.example.com', 587, 'u', 'p', True, False))
        site = configure(email_security='ssl', email_user='', email_password='')
        b = SiteEmailBackend()._delegate(site)
        self.assertEqual((b.use_tls, b.use_ssl, b.username, b.password), (False, True, '', ''))
        self.assertEqual(b.timeout, 10)

    def test_other_methods_build_the_matching_backends(self):
        folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, folder, True)
        self.assertIsInstance(SiteEmailBackend()._delegate(configure(email_mode='console')), console.EmailBackend)
        with override_settings(EMAIL_FILE_PATH=folder):
            self.assertIsInstance(SiteEmailBackend()._delegate(configure(email_mode='file')), filebased.EmailBackend)

    def test_real_delivery_to_a_local_smtp_server(self):
        with FakeSMTPServer() as server:
            configure(email_mode='smtp', email_host='127.0.0.1', email_port=server.port, email_security='none')
            sent = send_mail('Local hello', 'Sent from the local server', 'site@localhost', ['admin@x.bg'])
        self.assertEqual(sent, 1)
        self.assertEqual(len(server.messages), 1)
        got = server.messages[0]
        self.assertEqual((got['from'], got['to']), ('site@localhost', ['admin@x.bg']))
        self.assertIn('Subject: Local hello', got['data'])
        self.assertIn('Sent from the local server', got['data'])
        self.assertEqual(mail.outbox, [])

    def test_smtp_server_down_raises_unless_fail_silently(self):
        configure(email_mode='smtp', email_host='127.0.0.1', email_port=closed_port())
        with self.assertRaises(OSError):
            send_mail('x', 'y', None, ['to@x.bg'])
        self.assertEqual(send_mail('x', 'y', None, ['to@x.bg'], fail_silently=True), 0)

    def test_from_address_replaces_only_the_default_sender(self):
        configure(email_from='no-reply@site.bg')
        send_mail('Default sender', 'b', None, ['to@x.bg'])
        send_mail('Own sender', 'b', 'me@x.bg', ['to@x.bg'])
        self.assertEqual([m.from_email for m in mail.outbox], ['no-reply@site.bg', 'me@x.bg'])

    def test_empty_message_list(self):
        self.assertEqual(SiteEmailBackend().send_messages([]), 0)


@override_settings(EMAIL_BACKEND=SITE, EMAIL_FALLBACK_BACKEND=LOCMEM)
class NotifyAdminTests(TestCase):
    def test_without_admin_email_nothing_is_sent(self):
        self.assertFalse(notify_admin('Hello', 'Body'))
        self.assertEqual(mail.outbox, [])

    def test_sends_to_admin_email_with_site_title_prefix(self):
        configure(admin_email='admin@x.bg', site_title='My Site')
        self.assertTrue(notify_admin('Hello\nBcc: evil@x.bg', 'Body'))
        m = mail.outbox[0]
        self.assertEqual(m.to, ['admin@x.bg'])
        self.assertEqual(m.subject, '[My Site] Hello Bcc: evil@x.bg')      # one line, no header injection
        self.assertEqual(m.extra_headers, {})

    def test_failure_never_raises(self):
        configure(admin_email='admin@x.bg', email_mode='smtp', email_host='127.0.0.1', email_port=closed_port())
        self.assertFalse(notify_admin('Hello', 'Body'))


@override_settings(EMAIL_BACKEND=SITE, EMAIL_FALLBACK_BACKEND=LOCMEM)
class AdminEmailSectionTests(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_superuser('a', 'a@a.bg', 'pw')
        self.client.force_login(self.admin)
        SiteSettings.load()
        self.url = reverse('admin:siteconfig_sitesettings_change', args=[1])

    def form(self, **over):
        data = dict(site_title='S', admin_email='admin@x.bg', date_format='d.m.Y', time_format='H:i',
                    comments_moderation='manual', comments_max_depth=3, comments_close_after_days=0,
                    comments_max_links=2, email_mode='default', email_host='localhost', email_port=25,
                    email_security='none', _save='Save')
        data.update(over)
        return data

    def messages(self, response):
        return [str(m) for m in get_messages(response.wsgi_request)]

    def test_sections_are_present(self):
        r = self.client.get(self.url)
        for text in ('Admin e-mail', 'Sending method', 'SMTP host', 'Show the post author',
                     'E-mail me about new registrations', 'Send a test e-mail after saving'):
            self.assertContains(r, text)

    def test_save_email_settings(self):
        r = self.client.post(self.url, self.form(email_mode='smtp', email_host='localhost', email_port=1025,
                                                 email_from='no-reply@site.bg'))
        self.assertEqual(r.status_code, 302)
        s = SiteSettings.load()
        self.assertEqual((s.email_mode, s.email_host, s.email_port, s.email_from),
                         ('smtp', 'localhost', 1025, 'no-reply@site.bg'))
        self.assertEqual(mail.outbox, [])                  # no test mail unless asked

    def test_port_must_be_valid(self):
        r = self.client.post(self.url, self.form(email_port=70000))
        self.assertEqual(r.status_code, 200)

    def test_password_is_write_only_and_kept_when_empty(self):
        self.client.post(self.url, self.form(email_user='u', email_password='s3cret-pw'))
        self.assertEqual(SiteSettings.load().email_password, 's3cret-pw')
        self.assertNotContains(self.client.get(self.url), 's3cret-pw')
        self.client.post(self.url, self.form(email_user='u', email_password=''))
        self.assertEqual(SiteSettings.load().email_password, 's3cret-pw')
        self.client.post(self.url, self.form(email_user='u', email_password='new-pw'))
        self.assertEqual(SiteSettings.load().email_password, 'new-pw')

    def test_test_email_goes_to_the_admin_email(self):
        r = self.client.post(self.url, self.form(send_test_email='on'))
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['admin@x.bg'])
        self.assertIn('Test e-mail', mail.outbox[0].subject)
        self.assertTrue(any('Test e-mail sent to admin@x.bg' in m for m in self.messages(r)))

    def test_test_email_falls_back_to_the_user_email_then_warns(self):
        self.client.post(self.url, self.form(admin_email='', send_test_email='on'))
        self.assertEqual(mail.outbox[0].to, ['a@a.bg'])
        self.admin.email = ''
        self.admin.save()
        r = self.client.post(self.url, self.form(admin_email='', send_test_email='on'))
        self.assertEqual(len(mail.outbox), 1)
        self.assertTrue(any('fill in the Admin e-mail' in m for m in self.messages(r)))

    def test_test_email_failure_is_reported(self):
        r = self.client.post(self.url, self.form(email_mode='smtp', email_host='127.0.0.1',
                                                 email_port=closed_port(), send_test_email='on'))
        self.assertEqual(r.status_code, 302)
        self.assertTrue(any('Test e-mail FAILED' in m for m in self.messages(r)))
        self.assertEqual(SiteSettings.load().email_mode, 'smtp')           # the settings were still saved
