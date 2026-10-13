"""
siteconfig.admin - the "Settings" pane in the admin.

Behaviour
---------
* Sidebar/index: "Settings" -> "Settings". The list screen is skipped: clicking
  it opens the one and only settings form (``changelist_view`` redirects).
* The form is split into SECTIONS shown as tabs (one per ``fieldsets`` entry;
  tab behaviour lives in ``templates/admin/siteconfig/sitesettings/change_form.html``).
* E-mail section: the SMTP password field is never shown back (empty = keep the saved one) and the
  "Send a test e-mail" box sends a message to the Admin e-mail right after saving.
* Cannot add a second row or delete the row (singleton).
* After saving you stay on the form ("Save" returns here).

Add a section: append a ``(title, {'fields': (...)})`` entry to ``fieldsets``.
"""
from django import forms
from django.contrib import admin, messages
from django.core.mail import send_mail
from django.shortcuts import redirect
from django.urls import reverse

from .models import SiteSettings


class SiteSettingsForm(forms.ModelForm):
    """Adds two things to the generated form: a write-only SMTP password and the test-mail checkbox."""

    send_test_email = forms.BooleanField(
        label='Send a test e-mail after saving', required=False,
        help_text='Sends a short message to the Admin e-mail (General section) using the settings above, '
                  'so you can see at once whether sending works.')

    class Meta:
        model = SiteSettings
        fields = '__all__'
        widgets = {'email_password': forms.PasswordInput(render_value=False, attrs={'autocomplete': 'new-password'})}

    def clean_email_password(self):
        """The saved password is never sent to the browser, so an empty field means "unchanged"."""
        return self.cleaned_data.get('email_password') or self.instance.email_password


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    form = SiteSettingsForm
    change_form_template = 'admin/siteconfig/sitesettings/change_form.html'

    # Each entry = one section/tab. 'description' is shown under the tab title.
    fieldsets = (
        ('General', {
            'description': 'Basic information about the site.',
            'fields': (
                'site_title', 'site_description',
                'logo', 'favicon',
                'admin_email', 'location',
                'date_format', 'date_format_custom',
                'time_format', 'time_format_custom',
            ),
        }),
        ('Discussion', {
            'description': 'Comments on blog posts (the "comments" app).',
            'fields': (
                'comments_enabled',
                'comments_moderation',
                'comments_require_name_email', 'comments_registered_only',
                'comments_threaded', 'comments_max_depth',
                'comments_close_after_days',
                'comments_max_links', 'comments_blocked_words',
                'comments_email_admin',
            ),
        }),
        ('Users', {
            'description': 'Registered users, profiles and post authors (the "users" app).',
            'fields': ('users_email_admin', 'show_author_box'),
        }),
        ('E-mail', {
            'description': 'How the site sends e-mail (password resets, notifications to the Admin e-mail). '
                           'On a local server choose "SMTP server" with host localhost.',
            'fields': (
                'email_mode', 'email_host', 'email_port', 'email_security',
                'email_user', 'email_password', 'email_from',
                'send_test_email',
            ),
        }),
    )

    def has_add_permission(self, request):
        """Only until the single row exists."""
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        """Skip the list: go straight to the single settings form."""
        obj = SiteSettings.load()
        return redirect(reverse('admin:siteconfig_sitesettings_change', args=[obj.pk]))

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if form.cleaned_data.get('send_test_email'):
            self._send_test_email(request, obj)

    def _send_test_email(self, request, site):
        """Send the test message and report the real result (errors are shown, not hidden)."""
        to = site.admin_email or request.user.email
        if not to:
            self.message_user(request, 'Test e-mail not sent: fill in the Admin e-mail first.', messages.WARNING)
            return
        try:
            send_mail('[%s] Test e-mail' % site.site_title,
                      'This is a test message from %s.\nIf you can read it, sending e-mail works.' % site.site_title,
                      None, [to], fail_silently=False)
        except Exception as e:                      # connection refused, bad login, TLS error...
            self.message_user(request, 'Test e-mail FAILED: %s: %s' % (type(e).__name__, e), messages.ERROR)
        else:
            self.message_user(request, 'Test e-mail sent to %s (method: %s).' % (to, site.get_email_mode_display()),
                              messages.SUCCESS)

    def response_change(self, request, obj):
        """Stay on the settings form after saving (instead of going to the list)."""
        if '_save' in request.POST:
            self.message_user(request, 'Settings saved.')
            return redirect(reverse('admin:siteconfig_sitesettings_change', args=[obj.pk]))
        return super().response_change(request, obj)
