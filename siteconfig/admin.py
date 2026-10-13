"""
siteconfig.admin - the "Settings" pane in the admin.

Behaviour
---------
* Sidebar/index: "Settings" -> "Settings". The list screen is skipped: clicking
  it opens the one and only settings form (``changelist_view`` redirects).
* The form is split into SECTIONS shown as tabs (one per ``fieldsets`` entry;
  tab behaviour lives in ``templates/admin/siteconfig/sitesettings/change_form.html``).
* Cannot add a second row or delete the row (singleton).
* After saving you stay on the form ("Save" returns here).

Add a section: append a ``(title, {'fields': (...)})`` entry to ``fieldsets``.
"""
from django.contrib import admin
from django.shortcuts import redirect
from django.urls import reverse

from .models import SiteSettings


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
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

    def response_change(self, request, obj):
        """Stay on the settings form after saving (instead of going to the list)."""
        if '_save' in request.POST:
            self.message_user(request, 'Settings saved.')
            return redirect(reverse('admin:siteconfig_sitesettings_change', args=[obj.pk]))
        return super().response_change(request, obj)
