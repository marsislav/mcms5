"""Tests for the Trash (soft delete): posts, pages, categories, menus, admin."""
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from menus.models import Menu, MenuItem
from pages.models import Page
from posts.models import Category, Post


def post(title='P', slug='p'):
    return Post.objects.create(title=title, slug=slug, body='<p>x</p>')


class PostTrashTests(TestCase):
    def test_delete_hides_and_restore_brings_back(self):
        p = post()
        p.delete()
        self.assertEqual(Post.objects.count(), 0)
        self.assertEqual(Post.all_objects.count(), 1)
        self.assertEqual(self.client.get('/posts/p').status_code, 404)
        self.assertNotContains(self.client.get('/posts/'), 'Recent Posts')
        p.restore()
        self.assertEqual(self.client.get('/posts/p').status_code, 200)

    def test_queryset_delete_is_soft_and_hard_delete_is_real(self):
        post('A', 'a'); post('B', 'b')
        Post.objects.all().delete()
        self.assertEqual(Post.all_objects.dead().count(), 2)
        Post.all_objects.dead().hard_delete()
        self.assertEqual(Post.all_objects.count(), 0)

    def test_slug_of_trashed_post_cannot_be_reused_but_form_says_so(self):
        from posts.admin import PostAdminForm
        post().delete()
        f = PostAdminForm(data={'title': 'New', 'slug': 'p', 'body': '<p>x</p>'})
        self.assertFalse(f.is_valid())
        self.assertIn('slug', f.errors)
        # auto slug skips the trashed one
        f = PostAdminForm(data={'title': 'P', 'slug': '', 'body': '<p>x</p>'})
        self.assertTrue(f.is_valid(), f.errors)
        self.assertEqual(f.cleaned_data['slug'], 'p-2')

    def test_trashed_post_not_in_related_search_or_category_page(self):
        c = Category.objects.create(name='C', slug='c')
        a, b = post('A', 'a'), post('B', 'b')
        a.categories.add(c); b.categories.add(c); a.related.add(b)
        b.delete()
        self.assertEqual(a.related_posts(), [])
        r = self.client.get('/posts/category/c')
        self.assertEqual(list(r.context['posts']), [a])
        self.assertContains(self.client.get('/search/?q=B'), 'class')  # page renders
        self.assertNotContains(self.client.get('/posts/a'), 'Related posts')


class CategoryTrashTests(TestCase):
    def test_trashed_category_hidden_everywhere(self):
        c = Category.objects.create(name='Gone', slug='gone')
        p = post(); p.categories.add(c)
        c.delete()
        self.assertEqual(self.client.get('/posts/category/gone').status_code, 404)
        self.assertNotContains(self.client.get('/posts/'), 'Gone')
        self.assertNotContains(self.client.get('/posts/p'), 'Gone')
        c.restore()
        self.assertContains(self.client.get('/posts/p'), 'Gone')
        self.assertContains(self.client.get('/posts/'), 'Gone (1)')


class PageTrashTests(TestCase):
    def setUp(self):
        self.parent = Page.objects.create(title='Services', slug='services')
        self.child = Page.objects.create(title='Web', slug='web', parent=self.parent)
        self.other = Page.objects.create(title='Old', slug='old', parent=self.parent)

    def test_delete_parent_trashes_children_and_restore_brings_them(self):
        self.other.delete()                      # trashed earlier, separately
        self.parent.delete()
        self.assertEqual(Page.objects.count(), 0)
        self.assertEqual(self.client.get('/services/web/').status_code, 404)
        self.parent.restore()
        self.assertEqual(self.client.get('/services/web/').status_code, 200)
        self.assertEqual(self.client.get('/services/old/').status_code, 404)   # stays in Trash

    def test_cannot_restore_child_while_parent_in_trash(self):
        self.parent.delete()
        child = Page.all_objects.get(pk=self.child.pk)
        with self.assertRaises(ValidationError):
            child.restore()

    def test_form_rejects_slug_of_trashed_page(self):
        from pages.admin import PageAdminForm
        self.parent.delete()
        f = PageAdminForm(data={'title': 'New', 'slug': 'services', 'is_published': 'on', 'menu_order': 0})
        self.assertFalse(f.is_valid())
        self.assertTrue(f.errors)  # DB constraint 'unique_top_level_slug' also sees trashed pages


class MenuTrashTests(TestCase):
    def test_menu_item_to_trashed_page_is_skipped_and_returns_on_restore(self):
        menu = Menu.objects.create(name='M', slug='mm')
        page = Page.objects.create(title='Gone', slug='gone')
        item = MenuItem.objects.create(menu=menu, item_type='page', page=page)
        page.delete()
        item = MenuItem.objects.get(pk=item.pk)
        self.assertTrue(item.target_missing())
        page.restore()
        self.assertFalse(MenuItem.objects.get(pk=item.pk).target_missing())


class AdminTrashTests(TestCase):
    def setUp(self):
        U = get_user_model()
        U.objects.create_superuser('a', 'a@a.a', 'p')
        self.client.login(username='a', password='p')

    def test_admin_delete_goes_to_trash_and_restore_action(self):
        p = post()
        r = self.client.post('/admin/posts/post/%d/delete/' % p.pk, {'post': 'yes'})
        self.assertEqual(r.status_code, 302)
        self.assertTrue(Post.all_objects.get(pk=p.pk).is_deleted)
        self.assertNotContains(self.client.get('/admin/posts/post/'), 'class="field-title"')
        self.assertContains(self.client.get('/admin/posts/trashedpost/'), 'field-title')
        self.client.post('/admin/posts/trashedpost/', {'action': 'restore_selected', '_selected_action': [p.pk]})
        self.assertFalse(Post.all_objects.get(pk=p.pk).is_deleted)

    def test_bulk_delete_action_is_soft_and_purge_is_real(self):
        p = post()
        self.client.post('/admin/posts/post/', {'action': 'delete_selected', '_selected_action': [p.pk], 'post': 'yes'})
        self.assertTrue(Post.all_objects.get(pk=p.pk).is_deleted)
        self.client.post('/admin/posts/trashedpost/', {'action': 'delete_selected', '_selected_action': [p.pk], 'post': 'yes'})
        self.assertFalse(Post.all_objects.filter(pk=p.pk).exists())

    def test_trash_pages_render_for_all_three(self):
        for url in ('trashedpost', 'trashedcategory'):
            self.assertEqual(self.client.get('/admin/posts/%s/' % url).status_code, 200)
        self.assertEqual(self.client.get('/admin/pages/trashedpage/').status_code, 200)
        self.assertEqual(self.client.get('/admin/posts/trashedpost/add/').status_code, 403)
