"""
menus.tests - tests for the menu builder (save/validation) and the
``{% render_menu %}`` tag.

Run with::

    python manage.py test menus

Notes
-----
* ``setUp`` deletes the menus created by the seed migration so every test
  starts from a known, empty state.
* ``self.save(rows)`` posts to the real builder save endpoint as a superuser,
  so the tests exercise admin permissions, JSON parsing, ``builder.save_items``
  and the response format together.
"""
import json

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from pages.models import Page
from posts.models import Post
from .models import Menu, MenuItem


class MenuTests(TestCase):
    def setUp(self):
        """Create an empty menu, one page, one post and a staff superuser."""
        Menu.objects.all().delete()  # drop the seeded menus
        self.menu = Menu.objects.create(name='T', slug='t', ul_id='nav', ul_class='main', submenu_class='dropdown')
        self.page = Page.objects.create(title='Services', slug='services')
        self.post = Post.objects.create(title='Hello', slug='hello', body='x')
        self.staff = get_user_model().objects.create_user('s', password='p', is_staff=True, is_superuser=True)

    def save(self, rows):
        """POST ``rows`` (builder JSON) to the save endpoint as staff; returns the response."""
        self.client.force_login(self.staff)
        return self.client.post(reverse('admin:menus_menu_builder_save', args=[self.menu.pk]),
                                json.dumps({'items': rows}), content_type='application/json')

    def row(self, **kw):
        """Build one builder row: a valid custom link by default, overridable via kwargs."""
        base = dict(id=None, type='custom', object_id=None, label='L', url='/x/', depth=0)
        base.update(kw)
        return base

    def test_save_builds_tree_and_renders_attrs(self):
        """Saving builds the parent/child tree and the rendered HTML carries every attribute
        (ids, classes, target/rel, current-item highlighting, label fallback, post URL)."""
        r = self.save([
            self.row(type='page', object_id=self.page.pk, label='', css_classes='btn  big', element_id='m-1'),
            self.row(label='Sub', url='https://e.com', depth=1, new_tab=True, link_classes='lnk', rel='nofollow'),
            self.row(type='post', object_id=self.post.pk, label='Blog', depth=0),
        ])
        self.assertEqual(r.status_code, 200, r.content)
        items = list(self.menu.items.order_by('order'))
        self.assertEqual([i.parent_id for i in items], [None, items[0].pk, None])
        self.assertEqual(items[0].css_classes, 'btn big')

        from django.template import Context, Template
        from django.test import RequestFactory
        req = RequestFactory().get('/services/')
        req.user = self.staff
        out = Template("{% load menu_tags %}{% render_menu 't' %}").render(Context({'request': req}))
        self.assertIn('<ul id="nav" class="main">', out)
        self.assertIn('id="m-1"', out)
        self.assertIn('btn', out)
        self.assertIn('Services', out)                      # label falls back to the page title
        self.assertIn('<ul class="dropdown">', out)
        self.assertIn('target="_blank"', out)
        self.assertIn('rel="nofollow noopener noreferrer"', out)
        self.assertIn('class="lnk"', out)
        self.assertIn('current-menu-item', out)
        self.assertIn('/posts/hello', out)

    def test_hidden_item_and_branch_not_rendered(self):
        """An inactive parent hides itself AND its children for visitors."""
        self.save([self.row(label='Parent', is_active=False), self.row(label='Child', depth=1)])
        from django.template import Context, Template
        from django.test import RequestFactory
        req = RequestFactory().get('/')
        from django.contrib.auth.models import AnonymousUser
        req.user = AnonymousUser()
        out = Template("{% load menu_tags %}{% render_menu 't' %}").render(Context({'request': req}))
        self.assertNotIn('Parent', out)
        self.assertNotIn('Child', out)

    def test_delete_missing_items_and_validation(self):
        """Items missing from the payload are deleted; unsafe URLs / bad ids are rejected (400);
        an impossible depth is clamped instead of failing."""
        self.save([self.row(label='A'), self.row(label='B')])
        a = self.menu.items.get(label='A')
        self.save([self.row(id=a.pk, label='A2')])
        self.assertEqual(list(self.menu.items.values_list('label', flat=True)), ['A2'])
        self.assertEqual(self.save([self.row(url='javascript:alert(1)')]).status_code, 400)
        self.assertEqual(self.save([self.row(element_id='has space')]).status_code, 400)
        self.assertEqual(self.save([self.row(depth=3)]).status_code, 200)  # clamped to 0
        self.assertEqual(self.menu.items.get().parent_id, None)

    def test_deleted_page_hides_item_without_deleting_branch(self):
        """Deleting a Page keeps its menu items (flagged 'missing') instead of wiping the branch."""
        self.save([self.row(type='page', object_id=self.page.pk, label=''), self.row(label='Kid', depth=1)])
        self.page.delete()
        self.assertEqual(self.menu.items.count(), 2)
        self.assertTrue(self.menu.items.get(order=0).target_missing())

    def test_builder_page_requires_staff_and_loads(self):
        """Anonymous -> redirect to admin login (302); staff -> builder page loads (200)."""
        url = reverse('admin:menus_menu_builder', args=[self.menu.pk])
        self.assertEqual(self.client.get(url).status_code, 302)
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get(url).status_code, 200)
