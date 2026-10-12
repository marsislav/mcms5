"""
pages.tests - tests for page routing, drafts and BREADCRUMBS.

Run with::

    python manage.py test pages

What is verified
----------------
* ``Page.get_breadcrumbs`` returns the full ancestor chain, top-most first.
* The rendered HTML contains the breadcrumb bar with the right links, and the
  last item is marked ``active`` / ``aria-current="page"``.
* Home, About, the blog list and a post all get correct breadcrumbs.
* Drafts are 404 for anonymous visitors.
"""
from django.contrib.auth import get_user_model
from django.test import TestCase

from posts.models import Post
from .models import Page


class BreadcrumbTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        """Create a 2-level page tree (services > web) and one post."""
        cls.services = Page.objects.create(title='Services', slug='services')
        cls.web = Page.objects.create(title='Web', slug='web', parent=cls.services)
        cls.post = Post.objects.create(title='First post', slug='first', body='x')

    def crumbs_html(self, url):
        """Return the ``<ol class="breadcrumb">...</ol>`` markup of ``url``, whitespace-collapsed."""
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        start = html.index('<ol class="breadcrumb">')
        return ' '.join(html[start:html.index('</ol>', start)].split())

    def test_model_breadcrumbs_are_top_down(self):
        self.assertEqual(self.web.get_breadcrumbs(),
                         [('Services', '/services/'), ('Web', '/services/web/')])
        self.assertEqual(self.services.get_breadcrumbs(), [('Services', '/services/')])

    def test_nested_page_renders_full_trail(self):
        html = self.crumbs_html('/services/web/')
        self.assertIn('<a href="/"><i class="fa fa-home"></i> Home</a>', html)
        self.assertIn('<a href="/services/">Services</a>', html)
        # Last crumb: plain text, marked as the current page, not a link.
        self.assertIn('<li class="breadcrumb-item active" aria-current="page">Web</li>', html)

    def test_home_is_active_without_link(self):
        html = self.crumbs_html('/')
        self.assertIn('active', html)
        self.assertNotIn('<a href', html)

    def test_about_blog_and_post(self):
        self.assertIn('>About</li>', self.crumbs_html('/about/'))
        self.assertIn('>Blog</li>', self.crumbs_html('/posts/'))
        html = self.crumbs_html('/posts/first')
        self.assertIn('<a href="/posts/">Blog</a>', html)
        self.assertIn('aria-current="page">First post</li>', html)

    def test_unknown_post_is_404(self):
        self.assertEqual(self.client.get('/posts/nope').status_code, 404)


class DraftTests(TestCase):
    def test_draft_hidden_from_visitors_but_visible_to_staff(self):
        Page.objects.create(title='Secret', slug='secret', is_published=False)
        self.assertEqual(self.client.get('/secret/').status_code, 404)
        staff = get_user_model().objects.create_user('s', password='p', is_staff=True)
        self.client.force_login(staff)
        self.assertEqual(self.client.get('/secret/').status_code, 200)
