"""Tests for slug generation (mcms5/slugs.py + admin forms of Page and Post)."""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from pages.models import Page
from posts.models import Post
from .slugs import slugify_bg, unique_slug


class SlugifyTests(TestCase):
    def test_bulgarian(self):
        self.assertEqual(slugify_bg('Уеб дизайн'), 'ueb-dizayn')
        self.assertEqual(slugify_bg('Щастие и Ъгъл'), 'shtastie-i-agal')
        self.assertEqual(slugify_bg('Нови услуги 2026!'), 'novi-uslugi-2026')

    def test_latin_and_symbols(self):
        self.assertEqual(slugify_bg('  Café --  Hello, World!  '), 'cafe-hello-world')
        self.assertEqual(slugify_bg('!!!'), '')
        self.assertEqual(slugify_bg(''), '')

    def test_max_length(self):
        s = slugify_bg('а ' * 100, max_length=10)
        self.assertLessEqual(len(s), 10)
        self.assertFalse(s.endswith('-'))

    def test_unique_slug(self):
        Post.objects.create(title='x', slug='about', body='')
        Post.objects.create(title='x', slug='about-2', body='')
        self.assertEqual(unique_slug(Post.objects.all(), 'about'), 'about-3')
        self.assertEqual(unique_slug(Post.objects.all(), 'new'), 'new')


class AdminSlugTests(TestCase):
    def setUp(self):
        self.client.force_login(get_user_model().objects.create_superuser('a', 'a@a.bg', 'pw'))

    def page_data(self, **kw):
        d = dict(title='Нашите услуги', slug='', parent='', body='', meta_description='',
                 is_published='on', menu_order=0, _save='1')
        d.update(kw)
        return d

    def test_page_empty_slug_generated_and_unique(self):
        url = reverse('admin:pages_page_add')
        self.client.post(url, self.page_data())
        self.client.post(url, self.page_data())
        self.assertEqual(list(Page.objects.order_by('pk').values_list('slug', flat=True)),
                         ['nashite-uslugi', 'nashite-uslugi-2'])

    def test_page_manual_slug_kept(self):
        self.client.post(reverse('admin:pages_page_add'), self.page_data(slug='moy-slug'))
        self.assertTrue(Page.objects.filter(slug='moy-slug').exists())

    def test_page_duplicate_manual_slug_is_an_error(self):
        Page.objects.create(title='A', slug='dup')
        r = self.client.post(reverse('admin:pages_page_add'), self.page_data(slug='dup'))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(Page.objects.count(), 1)

    def test_same_title_under_different_parent_keeps_base_slug(self):
        parent = Page.objects.create(title='P', slug='p')
        self.client.post(reverse('admin:pages_page_add'), self.page_data(title='Info'))
        self.client.post(reverse('admin:pages_page_add'), self.page_data(title='Info', parent=parent.pk))
        self.assertEqual(sorted(Page.objects.filter(title='Info').values_list('slug', flat=True)), ['info', 'info'])

    def test_post_empty_slug_generated(self):
        d = dict(title='Първа статия', slug='', body='<p>x</p>', banner='', _save='1')
        self.client.post(reverse('admin:posts_post_add'), d)
        self.client.post(reverse('admin:posts_post_add'), d)
        self.assertEqual(list(Post.objects.order_by('pk').values_list('slug', flat=True)),
                         ['parva-statiya', 'parva-statiya-2'])

    def test_admin_loads_slug_script(self):
        for name in ('admin:pages_page_add', 'admin:posts_post_add'):
            self.assertContains(self.client.get(reverse(name)), 'js/admin-slug.js')
