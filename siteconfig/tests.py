"""siteconfig tests: singleton, formats, validation, admin pane, front-end output."""
import datetime
import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import SiteSettings

TMP_MEDIA = tempfile.mkdtemp()


def png(name='logo.png'):
    import io
    from PIL import Image
    buf = io.BytesIO()
    Image.new('RGB', (4, 4), 'red').save(buf, 'PNG')
    return SimpleUploadedFile(name, buf.getvalue(), content_type='image/png')


@override_settings(MEDIA_ROOT=TMP_MEDIA)
class SiteSettingsTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TMP_MEDIA, ignore_errors=True)

    def setUp(self):
        self.admin = get_user_model().objects.create_superuser('a', 'a@a.bg', 'pw')
        self.client.force_login(self.admin)
        SiteSettings.load()  # the admin form edits the existing singleton row
        self.url = reverse('admin:siteconfig_sitesettings_change', args=[1])

    def form(self, **over):
        data = dict(site_title='My Site', site_description='Desc', admin_email='me@x.bg',
                    location='Plovdiv', date_format='d.m.Y', date_format_custom='',
                    time_format='H:i', time_format_custom='', _save='Save',
                    comments_enabled='on', comments_moderation='manual', comments_threaded='on',
                    comments_max_depth=3, comments_close_after_days=0, comments_max_links=2,
                    email_mode='default', email_host='localhost', email_port=25, email_security='none')
        data.update(over)
        return data

    def test_load_is_singleton(self):
        a, b = SiteSettings.load(), SiteSettings.load()
        self.assertEqual(a.pk, 1)
        self.assertEqual(SiteSettings.objects.count(), 1)
        self.assertEqual(a.site_title, 'mCMS 5')

    def test_formats(self):
        s = SiteSettings.load()
        d = datetime.datetime(2026, 10, 12, 14, 5)
        self.assertEqual(s.format_date(d), '12 October 2026')
        s.date_format, s.time_format = 'd.m.Y', 'g:i A'
        self.assertEqual(s.format_datetime(d), '12.10.2026 2:05 PM')
        s.date_format, s.date_format_custom = 'custom', 'Y/m/d'
        self.assertEqual(s.format_date(d), '2026/10/12')

    def test_changelist_redirects_to_form(self):
        r = self.client.get(reverse('admin:siteconfig_sitesettings_changelist'))
        self.assertRedirects(r, self.url, fetch_redirect_response=False)
        self.assertContains(self.client.get(self.url), 'Site title')

    def test_save_and_show_on_frontend(self):
        r = self.client.post(self.url, self.form(logo=png(), favicon=png('f.png')))
        self.assertRedirects(r, self.url, fetch_redirect_response=False)
        s = SiteSettings.load()
        self.assertEqual(s.site_title, 'My Site')
        html = self.client.get('/').content.decode()
        self.assertIn('My Site', html)
        self.assertIn(s.logo.url, html)
        self.assertIn(s.favicon.url, html)
        self.assertIn('me@x.bg', html)

    def test_custom_format_required(self):
        r = self.client.post(self.url, self.form(date_format='custom'))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Enter a valid format')

    def test_bad_favicon_extension_rejected(self):
        bad = SimpleUploadedFile('x.exe', b'123')
        r = self.client.post(self.url, self.form(favicon=bad))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(SiteSettings.load().favicon.name, '')

    def test_old_logo_deleted_on_replace(self):
        self.client.post(self.url, self.form(logo=png('one.png')))
        first = SiteSettings.load().logo
        path = first.path
        self.client.post(self.url, self.form(logo=png('two.png')))
        import os
        self.assertFalse(os.path.exists(path))

    def test_cannot_delete_or_add(self):
        self.assertEqual(self.client.get(reverse('admin:siteconfig_sitesettings_delete', args=[1])).status_code, 403)
        SiteSettings.load()
        self.assertEqual(self.client.get(reverse('admin:siteconfig_sitesettings_add')).status_code, 403)

    def test_requires_staff(self):
        self.client.logout()
        self.assertEqual(self.client.get(self.url).status_code, 302)


class NotMigratedTests(TestCase):
    """Before ``migrate`` the site must still render (with default settings)."""

    def test_site_renders_without_table(self):
        from django.db import connection
        with connection.cursor() as c:
            c.execute('DROP TABLE siteconfig_sitesettings')
        r = self.client.get('/')
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'mCMS 5')
