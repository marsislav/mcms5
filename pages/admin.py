"""
pages.admin - Django admin configuration for ``Page``.

Appears in the admin as "Pages". Notes for editors:
* ``is_published`` can be toggled straight from the list (``list_editable``).
* The slug is auto-filled from the title while typing (JavaScript in admin).
* ``parent`` uses an autocomplete search box; this works because
  ``search_fields`` is defined below (Django requires it for autocomplete).
"""
from django.contrib import admin
from .models import Page


@admin.register(Page)
class PageAdmin(admin.ModelAdmin):
    # Columns in the changelist. 'full_path' is a model method (see Page.full_path).
    list_display = ('title', 'full_path', 'is_published', 'updated')
    list_editable = ('is_published',)
    list_filter = ('is_published',)
    # Also required by Django for the ``autocomplete_fields`` of other admins/pages.
    search_fields = ('title', 'slug', 'body')
    prepopulated_fields = {'slug': ('title',)}  # slug is filled in while typing the title
    autocomplete_fields = ('parent',)
