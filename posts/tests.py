"""posts.tests - categories, related posts and the sidebar widgets."""
from django.test import TestCase
from django.urls import reverse

from .models import Category, Post


def make_post(title, slug, **kw):
    return Post.objects.create(title=title, slug=slug, body='<p>x</p>', **kw)


class CategoryTests(TestCase):
    def setUp(self):
        self.cat = Category.objects.create(name='News', slug='news')
        self.empty = Category.objects.create(name='Empty', slug='empty')
        self.a = make_post('A', 'a')
        self.b = make_post('B', 'b')
        self.a.categories.add(self.cat)

    def test_category_page_lists_only_its_posts(self):
        r = self.client.get(reverse('posts:category', kwargs={'slug': 'news'}))
        self.assertEqual(list(r.context['posts']), [self.a])

    def test_unknown_category_404(self):
        self.assertEqual(self.client.get('/posts/category/nope').status_code, 404)

    def test_sidebar_shows_non_empty_categories_with_count(self):
        r = self.client.get('/posts/')
        self.assertContains(r, 'News (1)')
        self.assertNotContains(r, 'Empty (')

    def test_post_page_shows_categories(self):
        self.assertContains(self.client.get('/posts/a'), '/posts/category/news')


class RelatedTests(TestCase):
    def test_manual_related_is_symmetrical(self):
        a, b = make_post('A', 'a'), make_post('B', 'b')
        a.related.add(b)
        self.assertEqual(b.related_posts(), [a])
        self.assertContains(self.client.get('/posts/b'), 'Related posts')

    def test_fallback_to_same_category(self):
        c = Category.objects.create(name='C', slug='c')
        a, b, other = make_post('A', 'a'), make_post('B', 'b'), make_post('O', 'o')
        a.categories.add(c)
        b.categories.add(c)
        self.assertEqual(a.related_posts(), [b])
        self.assertEqual(other.related_posts(), [])
        self.assertNotContains(self.client.get('/posts/o'), 'Related posts')

    def test_manual_overrides_fallback(self):
        c = Category.objects.create(name='C', slug='c')
        a, b, m = make_post('A', 'a'), make_post('B', 'b'), make_post('M', 'm')
        a.categories.add(c)
        b.categories.add(c)
        a.related.add(m)
        self.assertEqual(a.related_posts(), [m])


class RecentPostsWidgetTests(TestCase):
    def test_newest_first_max_five(self):
        for i in range(7):
            make_post('Post%d' % i, 'p%d' % i)
        html = self.client.get('/posts/').content.decode()
        side = html[html.index('Recent Posts'):]
        self.assertLess(side.index('Post6'), side.index('Post5'))
        self.assertIn('Post2</a>', side)
        self.assertNotIn('Post1</a>', side)
        self.assertNotIn('Post0</a>', side)


class AdminTests(TestCase):
    def test_category_admin_generates_slug(self):
        from .admin import CategoryAdminForm
        f = CategoryAdminForm(data={'name': 'Нови услуги'})
        self.assertTrue(f.is_valid(), f.errors)
        self.assertEqual(f.cleaned_data['slug'], 'novi-uslugi')
