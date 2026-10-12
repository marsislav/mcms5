"""
pages.models - the ``Page`` model: static, hierarchical CMS pages.

Where this fits
---------------
* A ``Page`` is a "static" page (About, Contact, Services...). Dated blog
  articles live in ``posts.models.Post`` instead.
* Pages form a tree through the self-referencing ``parent`` foreign key. A page
  with slug ``web`` whose parent has slug ``services`` is served at
  ``/services/web/``.
* URLs are resolved by ``pages.views.page_detail`` (see ``pages/urls.py``).
* Pages are referenced by:
    - ``menus.models.MenuItem.page``  (navigation menus)
    - breadcrumbs, via ``Page.get_breadcrumbs()`` (used by ``pages.views``)

Depends on
----------
* ``django_ckeditor_5`` for the rich-text ``body`` field
  (configured in ``mcms5/settings.py`` -> ``CKEDITOR_5_CONFIGS``).
* Pillow (for ``ImageField``) and ``MEDIA_ROOT`` / ``MEDIA_URL`` from settings.
"""
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from django_ckeditor_5.fields import CKEditor5Field


class Page(models.Model):
    """A static page (About, Contact, Services...) as opposed to a dated blog Post.

    Pages can be nested: a page with parent "services" and slug "web" is served
    at /services/web/.

    Fields
    ------
    title             Human title. Used as <title>, hero heading, menu label
                      (when a menu item has no label of its own) and as the
                      breadcrumb label.
    slug              ONE URL segment only (no slashes). The full URL is built
                      from the slugs of the whole parent chain (``full_path``).
    parent            Optional parent page; makes this page a sub-page.
    body              Rich-text HTML edited with CKEditor 5.
    banner            Optional image shown at the top of the page.
    meta_description  SEO description (max 160 chars). Not yet rendered by the
                      templates - add it to ``layout.html`` if you want it.
    is_published      Drafts return 404 for anonymous visitors; staff can
                      still preview them (see ``pages.views.page_detail``).
    show_in_menu /    LEGACY. Before the menu builder (``menus`` app) existed,
    menu_order        these two fields controlled the site menu. They are now
                      only read once, by the data migration
                      ``menus/migrations/0002_seed_default_menus.py``, to seed
                      the initial "primary" menu. Menus are edited in the admin
                      under "Menus" afterwards; changing these fields has no
                      effect on the live menu.
    created/updated   Automatic timestamps.
    """

    title = models.CharField(max_length=150)
    # Slug is only ONE URL segment; the full URL is built from the parent chain.
    slug = models.SlugField(max_length=75)
    parent = models.ForeignKey(
        'self', null=True, blank=True, on_delete=models.CASCADE,
        related_name='children',
        help_text='Optional. Makes this page a sub-page: /parent-slug/this-slug/',
    )
    body = CKEditor5Field('Content', config_name='default', blank=True)
    banner = models.ImageField(upload_to='pages/', blank=True)
    meta_description = models.CharField(
        max_length=160, blank=True, help_text='SEO description (max 160 chars).')
    is_published = models.BooleanField(
        default=True, help_text='Unpublished pages return 404 for visitors (staff can still preview).')
    show_in_menu = models.BooleanField(default=False, help_text='List this page in the site menu.')
    menu_order = models.PositiveIntegerField(default=0, help_text='Lower numbers appear first in the menu.')
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['menu_order', 'title']
        constraints = [
            # Same slug is allowed under different parents, but not twice under one parent.
            models.UniqueConstraint(fields=['parent', 'slug'], name='unique_slug_per_parent'),
            # SQL treats NULLs as distinct, so top-level pages need their own constraint.
            models.UniqueConstraint(fields=['slug'], condition=models.Q(parent__isnull=True),
                                    name='unique_top_level_slug'),
        ]

    def __str__(self):
        return self.full_path()

    def full_path(self):
        """Return the URL path of this page *without* leading/trailing slashes.

        Example: ``'services/web'`` - the slugs of all ancestors (top-most
        first) joined with ``/``.

        Used by: ``get_absolute_url()``, the admin list column, and
        ``menus.builder.available_objects()``.

        The ``seen`` set protects against an (invalid) parent cycle so this
        method can never loop forever, even if bad data got into the database.
        """
        parts, node, seen = [], self, set()
        while node is not None and node.pk not in seen:
            seen.add(node.pk)
            parts.append(node.slug)
            node = node.parent
        return '/'.join(reversed(parts))

    def get_breadcrumbs(self):
        """Return the breadcrumb trail for this page as ``[(label, url), ...]``.

        The list starts with the top-most ancestor and ends with this page
        itself, e.g. for /services/web/::

            [('Services', '/services/'), ('Web', '/services/web/')]

        The site root ("Home") is NOT included - ``templates/layout.html``
        always prepends it.

        Data flow:
            pages.views.page_detail -> context['breadcrumbs'] -> layout.html
            ``{% for label, url in breadcrumbs %}``

        Cost: one query per ancestor (the ``parent`` attribute is lazily
        loaded). Page trees are shallow, so this is fine; add
        ``select_related`` chains if that ever changes.

        Implementation note: it walks up the ``parent`` chain collecting
        crumbs (so the list is built child -> root) and reverses it at the
        end. The ``seen`` set guards against parent cycles, exactly like
        ``full_path()``.
        """
        crumbs, node, seen = [], self, set()
        while node is not None and node.pk not in seen:
            seen.add(node.pk)
            crumbs.append((node.title, node.get_absolute_url()))
            node = node.parent
        return crumbs[::-1]

    def get_absolute_url(self):
        """Public URL, e.g. ``/services/web/``.

        Reverses the ``pages:detail`` route defined in ``pages/urls.py``. Used
        by menus, breadcrumbs and the "View on site" button in the admin.
        """
        return reverse('pages:detail', kwargs={'path': self.full_path()})

    def clean(self):
        """Model validation (runs in the admin form and ``full_clean()``).

        Prevents a page from becoming its own ancestor - that would create an
        infinite loop in ``full_path()``/``get_breadcrumbs()`` and in the URL
        resolver.
        """
        # Stop a page from becoming its own ancestor (would loop forever).
        node = self.parent
        while node is not None:
            if node.pk is not None and node.pk == self.pk:
                raise ValidationError({'parent': 'A page cannot be a child of itself or its own descendant.'})
            node = node.parent
