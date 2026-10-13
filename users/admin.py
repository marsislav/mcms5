"""
users.admin - ``User`` in the admin, with the public ``Profile`` editable on the same screen.

The stock ``UserAdmin`` is re-registered with a ``Profile`` inline (display name, photo, about, location,
website), so an administrator can fix a profile (e.g. remove an inappropriate photo).
"""
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import Profile

User = get_user_model()


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    extra = 0
    verbose_name = verbose_name_plural = 'Public profile'


class UserAdmin(BaseUserAdmin):
    inlines = [ProfileInline]


admin.site.unregister(User)
admin.site.register(User, UserAdmin)
