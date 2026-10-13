"""Tests for the site search (search/views.py, search/sqlite.py)."""
from django.test import TestCase
from django.urls import reverse

from pages.models import Page
from posts.models import Post
from .views import parse_query, plain_text


class SearchTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        Page.objects.create(title='Уеб дизайн', slug='web', is_published=True,
                            body='<p>Правим <strong>Софтуер</strong> и сайтове</p>')
        Page.objects.create(title='Тайна', slug='draft', is_published=False, body='<p>Софтуер чернова</p>')
        Page.objects.create(title='Markup', slug='markup', is_published=True,
                            body='<div class="mcms-cols"><p>hello</p></div>')
        Post.objects.create(title='Нов софтуер', slug='soft', body='<p>Статия за дизайн</p>')
        Post.objects.create(title='Other', slug='other', body='<p>nothing &lt;script&gt;alert(1)&lt;/script&gt;</p>')

    def get(self, q, **kw):
        return self.client.get(reverse('search'), {'q': q, **kw})

    def titles(self, r):
        return [x['title'] for x in r.context['page_obj']]

    def test_cyrillic_case_insensitive(self):
        # stored "Софтуер", queried in lower case (SQLite LIKE alone would miss this)
        r = self.get('софтуер')
        self.assertEqual(set(self.titles(r)), {'Уеб дизайн', 'Нов софтуер'})
        self.assertEqual(set(self.titles(self.get('СОФТУЕР'))), {'Уеб дизайн', 'Нов софтуер'})

    def test_title_ranks_first(self):
        self.assertEqual(self.titles(self.get('софтуер'))[0], 'Нов софтуер')

    def test_all_words_required(self):
        self.assertEqual(set(self.titles(self.get('софтуер дизайн'))), {'Уеб дизайн', 'Нов софтуер'})
        self.assertEqual(self.titles(self.get('софтуер nothing')), [])

    def test_drafts_hidden(self):
        self.assertNotIn('Тайна', self.titles(self.get('чернова')))
        self.assertEqual(self.get('чернова').context['total'], 0)

    def test_html_markup_is_not_searchable(self):
        self.assertEqual(self.get('mcms').context['total'], 0)
        self.assertEqual(self.get('div').context['total'], 0)
        self.assertEqual(self.titles(self.get('hello')), ['Markup'])

    def test_snippet_highlights_and_escapes(self):
        r = self.get('script')
        html = r.content.decode()
        self.assertIn('<mark>script</mark>', html)
        self.assertNotIn('<script>alert', html)

    def test_short_or_empty_query(self):
        self.assertContains(self.get('a'), 'at least 2 characters')
        self.assertEqual(self.get('').status_code, 200)
        self.assertIsNone(self.get('').context['page_obj'])

    def test_links_and_pagination(self):
        r = self.get('софтуер')
        urls = [x['url'] for x in r.context['page_obj']]
        self.assertIn('/web/', urls)
        self.assertIn('/posts/soft', urls)
        for i in range(12):
            Post.objects.create(title='много %d' % i, slug='m%d' % i, body='<p>x</p>')
        r = self.get('много')
        self.assertEqual(r.context['total'], 12)
        self.assertEqual(len(r.context['page_obj']), 10)
        self.assertEqual(len(self.get('много', page=2).context['page_obj']), 2)

    def test_sidebar_form_points_to_search(self):
        html = self.client.get('/').content.decode()
        self.assertIn('action="/search/"', html)
        self.assertIn('name="q"', html)

    def test_helpers(self):
        self.assertEqual(parse_query('  Web  design web x '), ['Web', 'design'])
        self.assertEqual(plain_text('<p>a&nbsp;&amp; <b>b</b></p>'), 'a & b')
