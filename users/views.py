"""
users.views - registration, login/logout and "forgot password".

URL map (``users/urls.py``, mounted at ``/users/``):

    register/                       register_view
    login/                          LoginView        (supports ?next=..., safe against open redirects)
    logout/                         LogoutView       (POST only - the "Logout" button is a small form)
    password-reset/                 ResetView        -> e-mail with a one-time link
    password-reset/done/            "check your e-mail" (shown even for unknown addresses)
    reset/<uidb64>/<token>/         ConfirmView      -> choose a new password
    reset/done/                     "password changed"

Django's own auth views do the real work (hashing, tokens, expiry, CSRF). Reset links expire after
``PASSWORD_RESET_TIMEOUT`` (3 days by default) and work once. E-mail delivery: see docs/accounts.md.
"""
from django.contrib.auth import views as auth_views
from django.shortcuts import redirect, render
from django.urls import reverse_lazy

from siteconfig.models import SiteSettings

from .forms import LoginForm, NewPasswordForm, RegisterForm, ResetRequestForm


def register_view(request):
    """Sign-up. On success the user is sent to the login page (not logged in automatically).

    New users are NOT staff: they cannot enter the admin or see draft pages.
    Template: ``users/templates/users/register.html``.
    """
    if request.user.is_authenticated:
        return redirect('posts:list')
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('%s?registered=1' % reverse_lazy('users:login'))
    else:
        form = RegisterForm()
    return render(request, 'users/register.html', {'form': form, 'page_title': 'Register',
                                                   'breadcrumbs': [('Register', '')]})


class LoginView(auth_views.LoginView):
    template_name = 'users/login.html'
    authentication_form = LoginForm
    redirect_authenticated_user = True      # a logged-in user opening /users/login/ is sent on

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        # Django's LoginView puts its own ``site`` (sites framework) in the context; the layout
        # needs OUR ``site`` (admin -> Settings), so put that one back.
        ctx.update(site=SiteSettings.load(), page_title='Log in', breadcrumbs=[('Log in', '')],
                   registered=self.request.GET.get('registered') == '1')
        return ctx


class LogoutView(auth_views.LogoutView):
    next_page = reverse_lazy('posts:list')


class ResetView(auth_views.PasswordResetView):
    template_name = 'users/password_reset_form.html'
    form_class = ResetRequestForm
    email_template_name = 'users/password_reset_email.txt'
    subject_template_name = 'users/password_reset_subject.txt'
    success_url = reverse_lazy('users:password_reset_done')

    def form_valid(self, form):
        self.extra_email_context = {'site_title': SiteSettings.load().site_title}
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        return {**super().get_context_data(**kwargs), 'page_title': 'Forgot password',
                'breadcrumbs': [('Log in', reverse_lazy('users:login')), ('Forgot password', '')]}


class ResetDoneView(auth_views.PasswordResetDoneView):
    template_name = 'users/password_reset_done.html'

    def get_context_data(self, **kwargs):
        return {**super().get_context_data(**kwargs), 'page_title': 'Check your e-mail',
                'breadcrumbs': [('Forgot password', reverse_lazy('users:password_reset')), ('Check your e-mail', '')]}


class ConfirmView(auth_views.PasswordResetConfirmView):
    template_name = 'users/password_reset_confirm.html'
    form_class = NewPasswordForm
    success_url = reverse_lazy('users:password_reset_complete')

    def get_context_data(self, **kwargs):
        return {**super().get_context_data(**kwargs), 'page_title': 'New password',
                'breadcrumbs': [('New password', '')]}


class CompleteView(auth_views.PasswordResetCompleteView):
    template_name = 'users/password_reset_complete.html'

    def get_context_data(self, **kwargs):
        return {**super().get_context_data(**kwargs), 'page_title': 'Password changed',
                'breadcrumbs': [('Password changed', '')]}
