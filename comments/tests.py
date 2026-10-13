"""comments tests: settings switches, moderation modes, replies, spam rules, admin."""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase
from django.utils import timezone

from posts.models import Post
from siteconfig.models import SiteSettings

from .models import Comment


class Base(TestCase):
    def setUp(self):
        self.post = Post.objects.create(title='T', slug='t', body='<p>x</p>')
        self.url = '/comments/post/%d/' % self.post.pk

    def settings(self, **kw):
        s = SiteSettings.load()
        for k, v in kw.items():
            setattr(s, 'comments_' + k, v)
        s.save()
        return s

    def send(self, **over):
        data = {'author_name': 'Ann', 'author_email': 'ann@x.bg', 'body': 'Hello there'}
        data.update(over)
        return self.client.post(self.url, data)

    def page(self, query=''):
        return self.client.get('/posts/t' + query).content.decode()


class SwitchTests(Base):
    def test_enabled_by_default_shows_form(self):
        self.assertIn('Leave a comment', self.page())

    def test_global_switch_hides_everything_and_blocks_posting(self):
        self.settings(enabled=False)
        self.assertNotIn('id="comments"', self.page())
        self.assertEqual(self.send().status_code, 403)
        self.assertEqual(Comment.objects.count(), 0)

    def test_post_switch(self):
        Post.objects.filter(pk=self.post.pk).update(comments_open=False)
        self.assertIn('Comments are closed', self.page())
        self.assertEqual(self.send().status_code, 403)

    def test_close_after_days(self):
        self.settings(close_after_days=30)
        Post.objects.filter(pk=self.post.pk).update(date=timezone.now() - timedelta(days=31))
        self.assertEqual(self.send().status_code, 403)
        Post.objects.filter(pk=self.post.pk).update(date=timezone.now() - timedelta(days=5))
        self.assertEqual(self.send().status_code, 302)

    def test_list_shows_count_only_when_enabled(self):
        Comment.objects.create(post=self.post, author_name='a', body='b', status='approved')
        Comment.objects.create(post=self.post, author_name='a', body='c', status='pending')
        self.assertContains(self.client.get('/posts/'), '1 Comment<')
        self.settings(enabled=False)
        self.assertNotContains(self.client.get('/posts/'), 'Comment<')


class ModerationTests(Base):
    def test_manual_holds_comment_and_hides_it(self):
        r = self.send()
        self.assertIn('commented=pending', r['Location'])
        c = Comment.objects.get()
        self.assertEqual(c.status, 'pending')
        self.assertNotIn('Hello there', self.page())
        self.assertIn('awaiting moderation', self.page('?commented=pending'))

    def test_auto_publishes(self):
        self.settings(moderation='auto')
        r = self.send()
        self.assertIn('commented=approved', r['Location'])
        self.assertIn('Hello there', self.page())

    def test_returning_commenter(self):
        self.settings(moderation='returning')
        self.send()
        self.assertEqual(Comment.objects.get().status, 'pending')
        Comment.objects.update(status='approved')
        self.send(body='second')
        self.assertEqual(Comment.objects.get(body='second').status, 'approved')
        self.send(author_email='new@x.bg', body='third')
        self.assertEqual(Comment.objects.get(body='third').status, 'pending')

    def test_staff_always_approved(self):
        u = get_user_model().objects.create_user('s', 's@x.bg', 'pw', is_staff=True)
        self.client.force_login(u)
        self.client.post(self.url, {'body': 'staff says'})
        c = Comment.objects.get()
        self.assertEqual((c.status, c.author_name, c.user), ('approved', 's', u))

    def test_too_many_links_held_even_in_auto(self):
        self.settings(moderation='auto', max_links=1)
        self.send(body='http://a.com http://b.com')
        self.assertEqual(Comment.objects.get().status, 'pending')

    def test_blocked_words_are_spam_but_look_pending(self):
        self.settings(moderation='auto', blocked_words='viagra\nCasino ')
        r = self.send(body='Best CASINO ever')
        self.assertIn('commented=pending', r['Location'])
        self.assertEqual(Comment.objects.get().status, 'spam')

    def test_honeypot_saves_nothing(self):
        r = self.send(website='http://spam')
        self.assertEqual(r.status_code, 302)
        self.assertEqual(Comment.objects.count(), 0)

    def test_duplicate_rejected(self):
        self.send()
        r = self.send()
        self.assertEqual(r.status_code, 400)
        self.assertContains(r, 'Duplicate comment', status_code=400)

    def test_html_is_escaped(self):
        self.settings(moderation='auto')
        self.send(body='<script>alert(1)</script>', author_name='<b>x</b>')
        html = self.page()
        self.assertNotIn('<script>alert(1)', html)
        self.assertIn('&lt;script&gt;alert(1)', html)
        self.assertIn('&lt;b&gt;x&lt;/b&gt;', html)

    def test_name_email_required_toggle(self):
        r = self.client.post(self.url, {'body': 'hi'})
        self.assertEqual(r.status_code, 400)
        self.settings(require_name_email=False)
        self.client.post(self.url, {'body': 'hi'})
        self.assertEqual(Comment.objects.get().author_name, 'Anonymous')

    def test_registered_only(self):
        self.settings(registered_only=True)
        self.assertIn('to leave a comment', self.page())
        self.assertEqual(self.send().status_code, 403)
        u = get_user_model().objects.create_user('u', 'u@x.bg', 'pw')
        self.client.force_login(u)
        self.assertEqual(self.client.post(self.url, {'body': 'ok'}).status_code, 302)

    def test_admin_email_notification(self):
        s = self.settings(email_admin=True)
        s.admin_email = 'admin@x.bg'; s.save()
        self.send()
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['admin@x.bg'])


class ReplyTests(Base):
    def setUp(self):
        super().setUp()
        self.settings(moderation='auto')
        self.c1 = Comment.objects.create(post=self.post, author_name='A', body='top', status='approved')

    def test_reply_link_and_form(self):
        html = self.page()
        self.assertIn('?replytocom=%d#respond' % self.c1.pk, html)
        html = self.page('?replytocom=%d' % self.c1.pk)
        self.assertIn('Reply to A', html)
        self.assertIn('name="parent" value="%d"' % self.c1.pk, html)

    def test_reply_saved_and_nested(self):
        self.send(parent=self.c1.pk, body='reply text')
        r = Comment.objects.get(body='reply text')
        self.assertEqual(r.parent, self.c1)
        html = self.page()
        self.assertLess(html.index('top'), html.index('reply text'))
        self.assertIn('comment-children', html)

    def test_max_depth(self):
        self.settings(max_depth=2)
        self.send(parent=self.c1.pk, body='lvl2')
        lvl2 = Comment.objects.get(body='lvl2')
        r = self.send(parent=lvl2.pk, body='lvl3')
        self.assertEqual(r.status_code, 400)
        self.assertNotIn('replytocom=%d' % lvl2.pk, self.page())

    def test_replies_disabled(self):
        self.settings(threaded=False)
        self.assertNotIn('replytocom', self.page())
        self.send(parent=self.c1.pk, body='x')
        self.assertIsNone(Comment.objects.get(body='x').parent)

    def test_cannot_reply_to_unapproved_or_other_post_comment(self):
        other = Post.objects.create(title='O', slug='o', body='<p>x</p>')
        foreign = Comment.objects.create(post=other, author_name='Z', body='z', status='approved')
        pending = Comment.objects.create(post=self.post, author_name='P', body='p', status='pending')
        self.assertEqual(self.send(parent=foreign.pk).status_code, 400)
        self.assertEqual(self.send(parent=pending.pk, body='q').status_code, 400)

    def test_children_of_unapproved_parent_are_hidden(self):
        Comment.objects.create(post=self.post, parent=self.c1, author_name='R', body='child text', status='approved')
        self.assertIn('child text', self.page())
        Comment.objects.filter(pk=self.c1.pk).update(status='spam')
        self.assertNotIn('child text', self.page())


class AdminTests(Base):
    def test_admin_actions(self):
        get_user_model().objects.create_superuser('a', 'a@x.bg', 'pw')
        self.client.login(username='a', password='pw')
        c = Comment.objects.create(post=self.post, author_name='A', body='b')
        self.assertEqual(self.client.get('/admin/comments/comment/').status_code, 200)
        self.client.post('/admin/comments/comment/', {'action': 'approve', '_selected_action': [c.pk]})
        c.refresh_from_db(); self.assertEqual(c.status, 'approved')
        self.client.post('/admin/comments/comment/', {'action': 'mark_spam', '_selected_action': [c.pk]})
        c.refresh_from_db(); self.assertEqual(c.status, 'spam')
        self.assertEqual(self.client.get('/admin/comments/comment/%d/change/' % c.pk).status_code, 200)

    def test_settings_discussion_tab_saves(self):
        get_user_model().objects.create_superuser('a', 'a@x.bg', 'pw')
        self.client.login(username='a', password='pw')
        SiteSettings.load()
        url = '/admin/siteconfig/sitesettings/1/change/'
        r = self.client.get(url)
        self.assertContains(r, 'Discussion')
        s = SiteSettings.load()
        data = dict(site_title='S', date_format='d.m.Y', time_format='H:i', _save='Save',
                    comments_moderation='auto', comments_threaded='on', comments_max_depth=4,
                    comments_close_after_days=10, comments_max_links=1,   # comments_enabled unchecked
                    email_mode='default', email_host='localhost', email_port=25, email_security='none')
        self.assertEqual(self.client.post(url, data).status_code, 302)
        s = SiteSettings.load()
        self.assertFalse(s.comments_enabled)
        self.assertEqual((s.comments_moderation, s.comments_max_depth), ('auto', 4))
