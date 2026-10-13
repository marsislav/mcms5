"""users tests: register, login/logout, forgot-password flow."""
import re

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase

User = get_user_model()


class RegisterTests(TestCase):
    def test_register_needs_unique_email_and_redirects_to_login(self):
        data = {'username': 'bob', 'email': 'bob@x.bg', 'password1': 'S3cure-pass-77', 'password2': 'S3cure-pass-77'}
        r = self.client.post('/users/register/', data)
        self.assertRedirects(r, '/users/login/?registered=1', fetch_redirect_response=False)
        self.assertEqual(User.objects.get(username='bob').email, 'bob@x.bg')
        # same e-mail, different case
        r = self.client.post('/users/register/', dict(data, username='bob2', email='BOB@x.bg'))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'already exists')
        r = self.client.post('/users/register/', dict(data, username='bob3', email=''))
        self.assertEqual(r.status_code, 200)

    def test_pages_render(self):
        self.assertContains(self.client.get('/users/register/'), 'Register a new user')
        self.assertContains(self.client.get('/users/login/?registered=1'), 'Account created')


class LoginTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('ann', 'ann@x.bg', 'S3cure-pass-77')

    def test_login_page_links(self):
        r = self.client.get('/users/login/')
        self.assertContains(r, 'Forgot your password?')
        self.assertContains(r, '/users/password-reset/')

    def test_login_success_default_and_next(self):
        r = self.client.post('/users/login/', {'username': 'ann', 'password': 'S3cure-pass-77'})
        self.assertRedirects(r, '/posts/', fetch_redirect_response=False)
        self.client.logout()
        r = self.client.post('/users/login/', {'username': 'ann', 'password': 'S3cure-pass-77', 'next': '/about/'})
        self.assertRedirects(r, '/about/', fetch_redirect_response=False)

    def test_open_redirect_is_ignored(self):
        r = self.client.post('/users/login/', {'username': 'ann', 'password': 'S3cure-pass-77',
                                               'next': 'https://evil.example/'})
        self.assertRedirects(r, '/posts/', fetch_redirect_response=False)

    def test_wrong_password(self):
        r = self.client.post('/users/login/', {'username': 'ann', 'password': 'nope'})
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Please enter a correct')
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_logged_in_user_is_redirected_from_login(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get('/users/login/').status_code, 302)

    def test_top_bar_links_and_logout_is_post_only(self):
        html = self.client.get('/').content.decode()
        self.assertIn('/users/login/', html)
        self.client.force_login(self.user)
        html = self.client.get('/').content.decode()
        self.assertIn('Logout', html)
        self.assertEqual(self.client.get('/users/logout/').status_code, 405)
        r = self.client.post('/users/logout/')
        self.assertRedirects(r, '/posts/', fetch_redirect_response=False)
        self.assertNotIn('_auth_user_id', self.client.session)


class PasswordResetTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('ann', 'ann@x.bg', 'Old-pass-12345')

    def test_full_flow(self):
        r = self.client.post('/users/password-reset/', {'email': 'ann@x.bg'})
        self.assertRedirects(r, '/users/password-reset/done/', fetch_redirect_response=False)
        self.assertEqual(len(mail.outbox), 1)
        msg = mail.outbox[0]
        self.assertEqual(msg.to, ['ann@x.bg'])
        self.assertIn('Password reset on', msg.subject)
        self.assertNotIn('\n', msg.subject)
        link = re.search(r'http://testserver(/users/reset/\S+)', msg.body).group(1)

        r = self.client.get(link, follow=True)           # token is swapped for "set-password" in the session
        self.assertContains(r, 'Choose a new password')
        set_url = r.redirect_chain[-1][0]
        r = self.client.post(set_url, {'new_password1': 'Brand-new-pass-99', 'new_password2': 'Brand-new-pass-99'})
        self.assertRedirects(r, '/users/reset/done/', fetch_redirect_response=False)
        self.assertContains(self.client.get('/users/reset/done/'), 'Password changed')

        self.assertTrue(self.client.login(username='ann', password='Brand-new-pass-99'))
        self.client.logout()
        self.assertFalse(self.client.login(username='ann', password='Old-pass-12345'))
        # the link works only once
        r = self.client.get(link, follow=True)
        self.assertContains(r, 'Link not valid')

    def test_unknown_email_looks_the_same_and_sends_nothing(self):
        r = self.client.post('/users/password-reset/', {'email': 'ghost@x.bg'})
        self.assertRedirects(r, '/users/password-reset/done/', fetch_redirect_response=False)
        self.assertEqual(len(mail.outbox), 0)

    def test_mismatched_passwords_rejected(self):
        self.client.post('/users/password-reset/', {'email': 'ann@x.bg'})
        link = re.search(r'http://testserver(/users/reset/\S+)', mail.outbox[0].body).group(1)
        set_url = self.client.get(link, follow=True).redirect_chain[-1][0]
        r = self.client.post(set_url, {'new_password1': 'Brand-new-pass-99', 'new_password2': 'different-99'})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(User.objects.get(pk=self.user.pk).check_password('Old-pass-12345'))

    def test_bad_token(self):
        r = self.client.get('/users/reset/Mg/abc-123/', follow=True)
        self.assertContains(r, 'Link not valid')

    def test_forgot_page_renders(self):
        self.assertContains(self.client.get('/users/password-reset/'), 'Send reset link')
