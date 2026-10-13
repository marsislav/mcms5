"""
users.views - registration, login/logout and "forgot password".

URL map (``users/urls.py``, mounted at ``/users/``):

    register/                       register_view    (e-mails the admin about the new user, if enabled)
    profile/                        profile_edit     (logged in: name, photo, short description...)
    author/<username>/              author_page      (public: profile + all posts of that author)
    login/                          LoginView        (supports ?next=..., safe against open redirects)
    logout/                         LogoutView       (POST only - the "Logout" button is a small form)
    password-reset/                 ResetView        -> e-mail with a one-time link
    password-reset/done/            "check your e-mail" (shown even for unknown addresses)
    reset/<uidb64>/<token>/         ConfirmView      -> choose a new password
    reset/done/                     "password changed"

Django's own auth views do the real work (hashing, tokens, expiry, CSRF). Reset links expire after
``PASSWORD_RESET_TIMEOUT`` (3 days by default) and work once. E-mail delivery: see docs/accounts.md.
"""
from django.contrib.auth import get_user_model
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy

from posts.models import Post
from siteconfig.mail import notify_admin
from siteconfig.models import SiteSettings

from .forms import LoginForm, NewPasswordForm, ProfileForm, RegisterForm, ResetRequestForm
from .models import Profile

POSTS_PER_PAGE = 10


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
            user = form.save()
            if SiteSettings.load().users_email_admin:
                notify_admin('New user registered',
                             'A new user registered on the site.\n\nUsername: %s\nE-mail: %s\n\nUsers: %s' % (
                                 user.get_username(), user.email,
                                 request.build_absolute_uri(reverse('admin:auth_user_changelist'))))
            return redirect('%s?registered=1' % reverse_lazy('users:login'))
    else:
        form = RegisterForm()
    return render(request, 'users/register.html', {'form': form, 'page_title': 'Register',
                                                   'breadcrumbs': [('Register', '')]})


@login_required
def profile_edit(request):
    """"My profile": the logged-in user edits the info shown with their posts.

    Template ``users/profile.html``. After saving the page reloads with ``?saved=1`` (a notice).
    """
    profile = Profile.for_user(request.user)
    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            return redirect('%s?saved=1' % reverse('users:profile'))
    else:
        form = ProfileForm(instance=profile)
    return render(request, 'users/profile.html', {
        'form': form, 'profile': profile, 'saved': request.GET.get('saved') == '1',
        'post_count': Post.objects.filter(author=request.user).count(),
        'page_title': 'My profile', 'breadcrumbs': [('My profile', '')]})


def author_page(request, username):
    """Public page of an author: the profile and all (not trashed) posts of the user, newest first.

    Only users who have at least one post are public (a user who never wrote anything is not listed);
    users can always open their own page. Unknown/inactive user -> 404. Template ``users/author.html``.
    """
    user = get_object_or_404(get_user_model(), username=username, is_active=True)
    posts = Post.objects.filter(author=user).order_by('-date')
    if not posts.exists() and request.user != user:
        raise Http404('No posts by this user.')
    page = Paginator(posts, POSTS_PER_PAGE).get_page(request.GET.get('page'))
    profile = Profile.of(user)
    return render(request, 'users/author.html', {
        'author': user, 'profile': profile, 'page_obj': page,
        'page_title': profile.name, 'breadcrumbs': [('Blog', reverse('posts:list')), (profile.name, '')]})


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
