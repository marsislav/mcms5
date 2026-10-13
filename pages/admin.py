"""
pages.admin - Django admin configuration for ``Page``.

Appears in the admin as "Pages". Notes for editors:
* ``is_published`` can be toggled straight from the list (``list_editable``).
* The slug is filled from the title while typing (``static/js/admin-slug.js``) and stays
  editable. If it is left EMPTY on save the server builds it from the title and makes it
  unique among siblings (``PageAdminForm``, ``mcms5/slugs.py``).
* Deleting moves to "Trash: Pages" (sub-pages go with it); restore there. See ``mcms5/softdelete.py``.
* ``parent`` uses an autocomplete search box; this works because
  ``search_fields`` is defined below (Django requires it for autocomplete).
"""
from django import forms
from django.contrib import admin

from mcms5.slugs import slugify_bg, unique_slug
from mcms5.softdelete_admin import SoftDeleteAdminMixin, TrashAdmin
from .models import Page, TrashedPage


class PageAdminForm(forms.ModelForm):
    """Makes the slug optional: an empty slug is generated from the title.

    The generated slug is unique among pages with the same parent (``-2``, ``-3``...).
    A slug typed by the editor is kept as is; if it is already taken Django shows the
    usual "already exists" error instead of silently changing it.
    """

    class Meta:
        model = Page
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        slug = self.fields['slug']
        slug.required = False
        slug.help_text = 'Filled from the title automatically; you can change it. Leave empty to generate it.'

    def clean(self):
        data = super().clean()
        if not data.get('slug') and data.get('title'):
            base = slugify_bg(data['title']) or 'page'
            siblings = Page.all_objects.filter(parent=data.get('parent')).exclude(pk=self.instance.pk)
            data['slug'] = unique_slug(siblings, base)
        return data


@admin.register(Page)
class PageAdmin(SoftDeleteAdminMixin, admin.ModelAdmin):
    form = PageAdminForm
    # Columns in the changelist. 'full_path' is a model method (see Page.full_path).
    list_display = ('title', 'full_path', 'is_published', 'updated')
    list_editable = ('is_published',)
    list_filter = ('is_published',)
    # Also required by Django for the ``autocomplete_fields`` of other admins/pages.
    search_fields = ('title', 'slug', 'body')
    autocomplete_fields = ('parent',)

    class Media:
        js = ('js/admin-slug.js', 'js/ckeditor-columns.js')  # "Columns" dropdown in the editor toolbar (docs/editor-columns.md)


@admin.register(TrashedPage)
class TrashedPageAdmin(TrashAdmin):
    list_display = ('title', 'full_path', 'deleted_at')
    search_fields = ('title', 'slug')
