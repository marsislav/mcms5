"""
posts.admin - ``Post`` in the Django admin.

* The slug is filled from the title while typing (``static/js/admin-slug.js``) and stays
  editable. If it is left EMPTY on save the server builds it from the title and makes it
  unique (``PostAdminForm``, ``mcms5/slugs.py``).
* Deleting moves to the Trash ("Trash: Posts"/"Trash: Categories"), see ``mcms5/softdelete.py``.
* A new post gets the logged-in user as ``author`` when the author field is left empty.
* The editor toolbar gets the "Columns" dropdown (docs/editor-columns.md).
"""
from django import forms
from django.contrib import admin

from mcms5.slugs import slugify_bg, unique_slug
from mcms5.softdelete_admin import AliveRelatedFieldListFilter, SoftDeleteAdminMixin, TrashAdmin
from .models import Category, Post, TrashedCategory, TrashedPost


class PostAdminForm(forms.ModelForm):
    """Makes the slug optional: an empty slug is generated from the title (unique: ``-2``, ``-3``...)."""

    class Meta:
        model = Post
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        slug = self.fields['slug']
        slug.required = False
        slug.help_text = 'Filled from the title automatically; you can change it. Leave empty to generate it.'

    def clean(self):
        data = super().clean()
        if not data.get('slug') and data.get('title'):
            base = slugify_bg(data['title']) or 'post'
            data['slug'] = unique_slug(Post.all_objects.exclude(pk=self.instance.pk), base)
        return data


class CategoryAdminForm(forms.ModelForm):
    """Same slug behaviour as posts: an empty slug is generated from the name."""

    class Meta:
        model = Category
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        slug = self.fields['slug']
        slug.required = False
        slug.help_text = 'Filled from the name automatically; you can change it. Leave empty to generate it.'

    def clean(self):
        data = super().clean()
        if not data.get('slug') and data.get('name'):
            base = slugify_bg(data['name']) or 'category'
            data['slug'] = unique_slug(Category.all_objects.exclude(pk=self.instance.pk), base)
        return data


@admin.register(Category)
class CategoryAdmin(SoftDeleteAdminMixin, admin.ModelAdmin):
    form = CategoryAdminForm
    list_display = ('name', 'slug')
    search_fields = ('name',)

    class Media:
        js = ('js/admin-slug.js',)


@admin.register(Post)
class PostAdmin(SoftDeleteAdminMixin, admin.ModelAdmin):
    form = PostAdminForm
    list_display = ('title', 'author', 'date')
    list_filter = (('categories', AliveRelatedFieldListFilter), 'author')
    search_fields = ('title',)
    filter_horizontal = ('categories', 'related')

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('author')

    def save_model(self, request, obj, form, change):
        """New post without an author -> the user who creates it."""
        if not change and obj.author_id is None:
            obj.author = request.user
        super().save_model(request, obj, form, change)

    class Media:
        js = ('js/admin-slug.js', 'js/ckeditor-columns.js')


@admin.register(TrashedPost)
class TrashedPostAdmin(TrashAdmin):
    list_display = ('title', 'slug', 'deleted_at')
    search_fields = ('title',)


@admin.register(TrashedCategory)
class TrashedCategoryAdmin(TrashAdmin):
    list_display = ('name', 'slug', 'deleted_at')
    search_fields = ('name',)
