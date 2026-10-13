"""users tests: profiles, photo upload, author page, author box on posts, admin notifications."""
import io
import os
import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from posts.models import Post
from siteconfig.models import SiteSettings

from .models import Profile

User = get_user_model()
TMP_MEDIA = tempfile.mkdtemp()
LOCMEM = 'django.core.mail.backends.locmem.EmailBackend'


def image(name='me.png', size=(8, 8), fmt='PNG', noise=False):
    from PIL import Image
    buf = io.BytesIO()
    if noise:
        Image.frombytes('RGB', size, os.urandom(size[0] * size[1] * 3)).save(buf, fmt)
    else:
        Image.new('RGB', size, 'blue').save(buf, fmt)
    return SimpleUploadedFile(name, buf.getvalue(), content_type='image/' + fmt.lower())


def make_post(author=None, title='A post', slug=None, **kw):
    return Post.objects.create(title=title, slug=slug or title.lower().replace(' ', '-'), body='<p>Hello world</p>',
                               author=author, **kw)


@override_settings(MEDIA_ROOT=TMP_MEDIA)
class ProfileTestCase(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TMP_MEDIA, ignore_errors=True)

    def setUp(self):
        self.user = User.objects.create_user('ann', 'secret@x.bg', 'S3cure-pass-77')


class ProfileModelTests(ProfileTestCase):
    def test_profile_is_created_with_the_user(self):
        self.assertTrue(Profile.objects.filter(user=self.user).exists())
        self.assertEqual(Profile.objects.count(), 1)

    def test_name_falls_back_to_full_name_then_username(self):
        p = Profile.of(self.user)
        self.assertEqual((p.name, p.initial), ('ann', 'A'))
        self.user.first_name, self.user.last_name = 'Ann', 'Lee'
        self.assertEqual(p.name, 'Ann Lee')
        p.display_name = '  Anna  '
        self.assertEqual(p.name, 'Anna')

    def test_of_returns_an_unsaved_profile_when_the_row_is_missing(self):
        Profile.objects.all().delete()
        user = User.objects.get(pk=self.user.pk)
        p = Profile.of(user)
        self.assertIsNone(p.pk)
        self.assertEqual(p.name, 'ann')
        self.assertEqual(Profile.objects.count(), 0)               # reading never writes
        self.assertIsNotNone(Profile.for_user(user).pk)

    def test_absolute_url(self):
        self.assertEqual(Profile.of(self.user).get_absolute_url(), '/users/author/ann/')


class ProfileEditTests(ProfileTestCase):
    url = '/users/profile/'

    def post(self, **over):
        data = dict(display_name='Ann L.', bio='Hello there', location='Plovdiv', website='https://ann.bg')
        data.update(over)
        return self.client.post(self.url, data)

    def test_login_required(self):
        r = self.client.get(self.url)
        self.assertRedirects(r, '/users/login/?next=/users/profile/', fetch_redirect_response=False)
        self.assertEqual(self.client.post(self.url, {'bio': 'x'}).status_code, 302)
        self.assertEqual(Profile.of(self.user).bio, '')

    def test_save_fields(self):
        self.client.force_login(self.user)
        self.assertContains(self.client.get(self.url), 'About me')
        r = self.post()
        self.assertRedirects(r, '/users/profile/?saved=1', fetch_redirect_response=False)
        p = Profile.objects.get(user=self.user)
        self.assertEqual((p.display_name, p.bio, p.location, p.website),
                         ('Ann L.', 'Hello there', 'Plovdiv', 'https://ann.bg'))
        self.assertContains(self.client.get(self.url + '?saved=1'), 'Profile saved.')

    def test_only_own_profile_is_edited(self):
        other = User.objects.create_user('bob', 'bob@x.bg', 'S3cure-pass-77')
        self.client.force_login(self.user)
        self.post(user=other.pk, id=Profile.of(other).pk)
        self.assertEqual(Profile.of(other).bio, '')

    def test_website_must_be_http_or_https(self):
        self.client.force_login(self.user)
        for bad in ('javascript:alert(1)', 'ftp://files.example.com', 'not a url'):
            self.assertEqual(self.post(website=bad).status_code, 200, bad)
        self.assertEqual(self.post(website='http://ok.bg').status_code, 302)

    def test_bio_limit(self):
        self.client.force_login(self.user)
        self.assertEqual(self.post(bio='x' * 501).status_code, 200)
        self.assertEqual(self.post(bio='x' * 500).status_code, 302)

    def test_photo_upload_replace_and_clear(self):
        self.client.force_login(self.user)
        self.post(avatar=image('one.png'))
        first = Profile.of(User.objects.get(pk=self.user.pk)).avatar
        self.assertTrue(first.name.startswith('avatars/'))
        self.assertTrue(os.path.exists(first.path))
        path1 = first.path
        self.post(avatar=image('two.png'))
        self.assertFalse(os.path.exists(path1))                    # old file removed
        second = Profile.objects.get(user=self.user).avatar
        self.assertTrue(os.path.exists(second.path))
        self.post(**{'avatar-clear': 'on'})
        self.assertFalse(os.path.exists(second.path))
        self.assertFalse(Profile.objects.get(user=self.user).avatar)

    def test_photo_validation(self):
        self.client.force_login(self.user)
        text = SimpleUploadedFile('me.png', b'this is not an image', content_type='image/png')
        self.assertEqual(self.post(avatar=text).status_code, 200)
        bmp = image('me.bmp', fmt='BMP')
        self.assertEqual(self.post(avatar=bmp).status_code, 200)            # extension not allowed
        svg = SimpleUploadedFile('me.svg', b'<svg xmlns="http://www.w3.org/2000/svg"><script>1</script></svg>')
        self.assertEqual(self.post(avatar=svg).status_code, 200)
        big = image('big.png', size=(1000, 1000), noise=True)
        self.assertGreater(big.size, 2 * 1024 * 1024)
        r = self.post(avatar=big)
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'File too large')
        self.assertFalse(Profile.objects.get(user=self.user).avatar)

    def test_deleting_the_user_deletes_the_photo(self):
        self.client.force_login(self.user)
        self.post(avatar=image())
        path = Profile.objects.get(user=self.user).avatar.path
        self.assertTrue(os.path.exists(path))
        self.user.delete()
        self.assertFalse(os.path.exists(path))

    def test_header_links_to_the_profile(self):
        self.client.force_login(self.user)
        self.assertContains(self.client.get('/posts/'), 'href="/users/profile/"')


class AuthorPageTests(ProfileTestCase):
    def setUp(self):
        super().setUp()
        p = Profile.of(self.user)
        p.display_name, p.bio, p.location, p.website = 'Ann Author', 'Line one\nLine two', 'Plovdiv', 'https://ann.bg'
        p.save()
        self.other = User.objects.create_user('bob', 'bob@x.bg', 'S3cure-pass-77')

    def test_lists_only_live_posts_of_the_author_newest_first(self):
        old = make_post(self.user, 'Old one')
        new = make_post(self.user, 'New one')
        gone = make_post(self.user, 'Trashed one')
        gone.delete()
        make_post(self.other, 'Bobs post')
        make_post(None, 'Nobodys post')
        r = self.client.get('/users/author/ann/')
        self.assertEqual(r.status_code, 200)
        self.assertEqual([p.title for p in r.context['page_obj']], ['New one', 'Old one'])
        html = r.content.decode()
        heading = '<h2><a href="%s">%s</a></h2>'
        self.assertIn(heading % (new.get_absolute_url(), 'New one'), html)
        self.assertIn(heading % (old.get_absolute_url(), 'Old one'), html)
        self.assertNotIn(heading % (gone.get_absolute_url(), 'Trashed one'), html)
        self.assertNotIn(heading % (Post.all_objects.get(title='Bobs post').get_absolute_url(), 'Bobs post'), html)
        self.assertIn('Ann Author', html)
        self.assertIn('Line one<br>Line two', html)
        self.assertIn('rel="nofollow noopener ugc"', html)
        self.assertNotIn('secret@x.bg', html)
        self.assertIn(new.get_absolute_url(), html)

    def test_pagination(self):
        for i in range(12):
            make_post(self.user, 'Post %02d' % i)
        r = self.client.get('/users/author/ann/')
        self.assertEqual(len(r.context['page_obj']), 10)
        self.assertContains(r, '?page=2')
        r = self.client.get('/users/author/ann/?page=2')
        self.assertEqual(len(r.context['page_obj']), 2)

    def test_user_without_posts_is_not_public_but_sees_own_page(self):
        self.assertEqual(self.client.get('/users/author/ann/').status_code, 404)
        self.client.force_login(self.other)
        self.assertEqual(self.client.get('/users/author/ann/').status_code, 404)
        self.client.force_login(self.user)
        r = self.client.get('/users/author/ann/')
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Edit my profile')

    def test_trashed_only_posts_do_not_make_an_author_public(self):
        make_post(self.user, 'Only one').delete()
        self.assertEqual(self.client.get('/users/author/ann/').status_code, 404)

    def test_unknown_and_inactive_users(self):
        self.assertEqual(self.client.get('/users/author/nobody/').status_code, 404)
        make_post(self.user)
        self.user.is_active = False
        self.user.save()
        self.assertEqual(self.client.get('/users/author/ann/').status_code, 404)

    def test_profile_text_is_escaped(self):
        p = Profile.of(self.user)
        p.display_name, p.bio = '<b>Ann</b>', '<script>alert(1)</script>'
        p.save()
        make_post(self.user)
        html = self.client.get('/users/author/ann/').content.decode()
        self.assertNotIn('<script>alert(1)</script>', html)
        self.assertNotIn('<b>Ann</b>', html)
        self.assertIn('&lt;script&gt;', html)

    def test_username_with_special_characters(self):
        u = User.objects.create_user('a.b+c@d', 'abc@x.bg', 'S3cure-pass-77')
        make_post(u, 'Special')
        r = self.client.get(Profile.of(u).get_absolute_url())
        self.assertEqual(r.status_code, 200)


class AuthorBoxTests(ProfileTestCase):
    def setUp(self):
        super().setUp()
        p = Profile.of(self.user)
        p.display_name, p.bio, p.location, p.website = 'Ann Author', 'I write things', 'Plovdiv', 'https://ann.bg'
        p.save()
        self.post = make_post(self.user, 'With author')

    def page(self, post=None):
        return self.client.get((post or self.post).get_absolute_url())

    def test_box_after_the_post(self):
        r = self.page()
        self.assertContains(r, 'class="author-box"')
        html = r.content.decode()
        self.assertLess(html.index('Hello world'), html.index('class="author-box"'))
        for text in ('Ann Author', 'I write things', 'Plovdiv', 'All posts by Ann Author (1)',
                     'href="/users/author/ann/"', 'href="https://ann.bg"', 'nofollow noopener ugc'):
            self.assertContains(r, text)
        self.assertNotContains(r, 'secret@x.bg')

    def test_count_includes_only_live_posts(self):
        make_post(self.user, 'Second')
        make_post(self.user, 'Third').delete()
        self.assertContains(self.page(), 'All posts by Ann Author (2)')

    def test_initial_is_shown_without_a_photo_and_the_photo_with_one(self):
        self.assertContains(self.page(), '<span class="author-initial">A</span>')
        p = Profile.of(self.user)
        p.avatar = image('face.png')
        p.save()
        r = self.page()
        self.assertContains(r, '/media/avatars/')
        self.assertNotContains(r, 'author-initial')

    def test_no_author_no_box(self):
        r = self.page(make_post(None, 'Orphan'))
        self.assertNotContains(r, 'author-box')
        self.assertNotContains(r, 'post-byline')

    def test_switch_in_settings_hides_everything(self):
        s = SiteSettings.load()
        s.show_author_box = False
        s.save()
        for r in (self.page(), self.client.get('/posts/')):
            self.assertNotContains(r, 'author-box')
            self.assertNotContains(r, 'post-byline')
            self.assertNotContains(r, '/users/author/ann/')

    def test_inactive_author_is_not_shown(self):
        self.user.is_active = False
        self.user.save()
        self.assertNotContains(self.page(), 'author-box')

    def test_byline_on_the_post_and_in_the_list(self):
        self.assertContains(self.page(), 'by <a href="/users/author/ann/">Ann Author</a>')
        self.assertContains(self.client.get('/posts/'), '<i class="fa fa-user-o"></i> Ann Author')

    def test_list_author_queries_do_not_grow_with_the_number_of_authors(self):
        """Author + profile come with the posts (select_related): no extra query per post."""
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        def author_queries():
            with CaptureQueriesContext(connection) as ctx:
                self.assertEqual(self.client.get('/posts/').status_code, 200)
            return len([q for q in ctx.captured_queries if 'users_profile' in q['sql'] or 'auth_user' in q['sql']])

        def add(n):
            for i in range(n):
                make_post(User.objects.create_user('writer%d_%d' % (n, i), '', 'pw'), 'Post %d %d' % (n, i))
        add(2)
        few = author_queries()
        add(6)
        self.assertEqual(author_queries(), few)

    def test_category_page_shows_the_byline(self):
        from posts.models import Category
        c = Category.objects.create(name='News', slug='news')
        self.post.categories.add(c)
        self.assertContains(self.client.get('/posts/category/news'), 'Ann Author')


@override_settings(EMAIL_BACKEND=LOCMEM)
class RegistrationNotificationTests(TestCase):
    data = {'username': 'bob', 'email': 'bob@x.bg', 'password1': 'S3cure-pass-77', 'password2': 'S3cure-pass-77'}

    def configure(self, **kw):
        s = SiteSettings.load()
        for k, v in kw.items():
            setattr(s, k, v)
        s.save()

    def test_admin_is_told_about_a_new_user(self):
        self.configure(admin_email='admin@x.bg', site_title='My Site')
        r = self.client.post('/users/register/', self.data)
        self.assertEqual(r.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        m = mail.outbox[0]
        self.assertEqual(m.to, ['admin@x.bg'])
        self.assertEqual(m.subject, '[My Site] New user registered')
        self.assertIn('bob', m.body)
        self.assertIn('bob@x.bg', m.body)
        self.assertNotIn('S3cure-pass-77', m.body)

    def test_not_sent_without_admin_email_or_when_switched_off(self):
        self.client.post('/users/register/', self.data)
        self.assertEqual(mail.outbox, [])
        self.configure(admin_email='admin@x.bg', users_email_admin=False)
        self.client.post('/users/register/', dict(self.data, username='bob2', email='bob2@x.bg'))
        self.assertEqual(mail.outbox, [])
        self.assertTrue(User.objects.filter(username='bob2').exists())

    def test_registration_survives_a_dead_mail_server(self):
        import socket
        s = socket.socket()
        s.bind(('127.0.0.1', 0))
        port = s.getsockname()[1]
        s.close()
        self.configure(admin_email='admin@x.bg', email_mode='smtp', email_host='127.0.0.1', email_port=port)
        with override_settings(EMAIL_BACKEND='siteconfig.mail.SiteEmailBackend'):
            r = self.client.post('/users/register/', self.data)
        self.assertRedirects(r, '/users/login/?registered=1', fetch_redirect_response=False)
        self.assertTrue(User.objects.filter(username='bob').exists())


class AdminIntegrationTests(ProfileTestCase):
    def setUp(self):
        super().setUp()
        self.admin = User.objects.create_superuser('root', 'root@x.bg', 'pw')
        self.client.force_login(self.admin)

    def add_post(self, **over):
        data = dict(title='From admin', slug='', body='<p>Text</p>', comments_open='on', _save='Save')
        data.update(over)
        return self.client.post(reverse('admin:posts_post_add'), data)

    def test_new_post_gets_the_logged_in_user_as_author(self):
        r = self.add_post()
        self.assertEqual(r.status_code, 302, getattr(r, 'context', None) and r.context['adminform'].form.errors)
        self.assertEqual(Post.objects.get(title='From admin').author, self.admin)

    def test_explicit_author_is_kept_and_editing_does_not_change_it(self):
        self.add_post(title='Written by ann', author=self.user.pk)
        post = Post.objects.get(title='Written by ann')
        self.assertEqual(post.author, self.user)
        r = self.client.post(reverse('admin:posts_post_change', args=[post.pk]),
                             dict(title='Renamed', slug=post.slug, body='<p>Text</p>', author=self.user.pk,
                                  comments_open='on', _save='Save'))
        self.assertEqual(r.status_code, 302)
        post.refresh_from_db()
        self.assertEqual((post.title, post.author), ('Renamed', self.user))

    def test_deleting_the_author_keeps_the_post(self):
        post = make_post(self.user, 'Stays')
        self.user.delete()
        post.refresh_from_db()
        self.assertIsNone(post.author)

    def test_user_admin_shows_the_profile(self):
        r = self.client.get(reverse('admin:auth_user_change', args=[self.user.pk]))
        self.assertContains(r, 'Public profile')
        self.assertContains(r, 'About me')
        self.assertEqual(self.client.get(reverse('admin:auth_user_add')).status_code, 200)

    def test_post_list_shows_the_author_column(self):
        make_post(self.user, 'Listed')
        self.assertContains(self.client.get(reverse('admin:posts_post_changelist')), 'ann')
