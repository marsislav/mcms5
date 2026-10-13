"""Editor "Columns" feature (docs/editor-columns.md): assets are wired into admin + front end."""
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.staticfiles import finders
from django.test import TestCase
from django.urls import reverse

from pages.models import Page


class EditorColumnsTests(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_superuser('a', 'a@a.bg', 'pw')
        self.client.force_login(self.admin)

    def test_static_files_exist(self):
        self.assertTrue(finders.find('js/ckeditor-columns.js'))
        css = finders.find('css/mcms-columns.css')
        self.assertTrue(css)
        text = open(css, encoding='utf-8').read()
        for n in (1, 2, 3, 4, 5, 6, 12):
            self.assertIn('.mcms-cols-%d' % n, text)

    def test_editor_css_configured(self):
        self.assertEqual(settings.CKEDITOR_5_CUSTOM_CSS, 'css/mcms-columns.css')

    def test_admin_pages_load_the_dropdown_script(self):
        for name in ('admin:pages_page_add', 'admin:posts_post_add'):
            self.assertContains(self.client.get(reverse(name)), 'js/ckeditor-columns.js')

    def test_columns_html_is_kept_and_front_end_loads_css(self):
        body = '<div class="mcms-cols mcms-cols-3"><div class="mcms-col"><p>A</p></div></div>'
        Page.objects.create(title='T', slug='cols', body=body, is_published=True)
        r = self.client.get('/cols/')
        self.assertContains(r, body, html=False)
        self.assertContains(r, 'css/mcms-columns.css')
