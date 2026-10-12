"""
menus.models - data model for the navigation menu system.

Overview
--------
A site can have several named menus (e.g. "Main menu" with slug ``primary``,
"Footer" with slug ``footer``). Each ``Menu`` owns a tree of ``MenuItem`` rows.

    Menu (slug='primary')
     +-- MenuItem  order=0  "Home"      (custom link  -> '/')
     +-- MenuItem  order=1  "Services"  (page link    -> Page)
     |    +-- MenuItem order=2 "Web"    (child, parent=Services)
     +-- MenuItem  order=3  "Blog"      (post link    -> Post)

How it is used
--------------
* EDITING: admin -> Menus -> "Edit structure" opens the drag-and-drop builder
  (``menus/admin.py`` + ``menus/builder.py`` +
  ``menus/templates/admin/menus/menu/builder.html``).
* RENDERING: ``{% render_menu 'primary' %}`` in ``templates/layout.html``
  (``menus/templatetags/menu_tags.py``) turns the tree into nested ``<ul>``.

Depends on
----------
* ``pages.Page`` and ``posts.Post`` (foreign keys, see ``MenuItem``).
* Seed data is created by ``migrations/0002_seed_default_menus.py``.
"""
from django.db import models


class Menu(models.Model):
    """A named menu (Primary, Footer...). Rendered in templates with {% render_menu 'slug' %}.

    name           Admin-only display name.
    slug           Identifier used in templates: ``{% render_menu 'slug' %}``.
                   Must be unique. If no menu has this slug the tag renders
                   nothing (and does not raise an error).
    ul_id          Optional ``id`` attribute of the OUTER ``<ul>``.
    ul_class       Optional ``class`` attribute of the OUTER ``<ul>``.
    submenu_class  ``class`` of every NESTED ``<ul>`` (default ``dropdown``,
                   which the "classynav" theme CSS/JS expects for sub-menus).
    """

    name = models.CharField('Name', max_length=100)
    slug = models.SlugField('Slug', max_length=50, unique=True,
                            help_text="Used in the template: {% render_menu 'slug' %}")
    ul_id = models.CharField('ID of the main <ul>', max_length=100, blank=True)
    ul_class = models.CharField('Class(es) of the main <ul>', max_length=200, blank=True)
    submenu_class = models.CharField('Class(es) of the sub-menu <ul>s', max_length=200, blank=True,
                                     default='dropdown')

    class Meta:
        ordering = ['name']
        verbose_name = 'Menu'
        verbose_name_plural = 'Menus'

    def __str__(self):
        return self.name


class MenuItem(models.Model):
    """One entry of a menu. Can link to a Page, a Post, or any custom URL.

    Tree storage
    ------------
    The tree is stored with a ``parent`` foreign key PLUS a flat ``order``
    number. ``order`` is the position in the depth-first (top-to-bottom as
    displayed) list of the WHOLE menu, like WordPress ``menu_order``. The
    builder (``menus/builder.py``) renumbers ``order`` (0, 1, 2...) on every
    save, so you never need to maintain it by hand.

    Link target
    -----------
    ``item_type`` decides which field supplies the link:
        page    -> ``page``  (URL = ``Page.get_absolute_url()``)
        post    -> ``post``  (URL = ``/posts/<slug>``)
        custom  -> ``url``   (any of: /path, #anchor, ?query, http(s)://, mailto:, tel:)
    """

    class ItemType(models.TextChoices):
        PAGE = 'page', 'Page'
        POST = 'post', 'Post'
        CUSTOM = 'custom', 'Custom link'

    class Visibility(models.TextChoices):
        """Who may SEE the item in the rendered menu (checked in menu_tags._visible)."""
        ALL = 'all', 'Everyone'
        GUESTS = 'guests', 'Logged-out visitors only'
        USERS = 'users', 'Logged-in users only'
        STAFF = 'staff', 'Staff only'

    menu = models.ForeignKey(Menu, on_delete=models.CASCADE, related_name='items')
    # Deleting a parent item deletes its sub-items too (CASCADE).
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE,
                               related_name='children')
    # Position in the flat, depth-first list of the whole menu (like WordPress menu_order).
    order = models.PositiveIntegerField(default=0)

    item_type = models.CharField(max_length=10, choices=ItemType.choices, default=ItemType.CUSTOM)
    # The linked object is NOT cascaded: deleting a Page/Post must not silently wipe a menu branch.
    # Instead the FK becomes NULL and the item is flagged "missing" (see target_missing()).
    page = models.ForeignKey('pages.Page', null=True, blank=True, on_delete=models.SET_NULL,
                             related_name='+')
    post = models.ForeignKey('posts.Post', null=True, blank=True, on_delete=models.SET_NULL,
                             related_name='+')
    url = models.CharField('URL', max_length=500, blank=True)

    label = models.CharField('Title', max_length=200, blank=True,
                             help_text="Empty = use the page's/post's own title.")
    title_attr = models.CharField('Title attribute', max_length=200, blank=True)
    new_tab = models.BooleanField('Open in a new window', default=False)
    css_classes = models.CharField('CSS classes (on <li>)', max_length=200, blank=True)
    link_classes = models.CharField('CSS classes (on <a>)', max_length=200, blank=True)
    element_id = models.CharField('ID (on <li>)', max_length=100, blank=True)
    rel = models.CharField('rel', max_length=100, blank=True)
    visibility = models.CharField(max_length=10, choices=Visibility.choices, default=Visibility.ALL)
    is_active = models.BooleanField('Show', default=True)

    class Meta:
        ordering = ['menu', 'order', 'id']
        verbose_name = 'Menu item'
        verbose_name_plural = 'Menu items'

    def __str__(self):
        return self.get_label() or f'#{self.pk}'

    # -- resolved values -----------------------------------------------------
    def target(self):
        """Return the linked ``Page``/``Post`` object, or ``None`` for custom links
        (or when the linked object was deleted)."""
        if self.item_type == self.ItemType.PAGE:
            return self.page
        if self.item_type == self.ItemType.POST:
            return self.post
        return None

    def target_missing(self):
        """True if this is a page/post item whose target no longer exists.

        Such items are skipped when rendering (menu_tags.build_tree) and
        highlighted in red in the builder so the editor can remove them.
        """
        return self.item_type != self.ItemType.CUSTOM and self.target() is None

    def get_label(self):
        """Visible text: the explicit ``label`` if set, otherwise the target's title."""
        if self.label:
            return self.label
        t = self.target()
        return t.title if t else ''

    def get_url(self):
        """The ``href`` for this item ('' if the target is missing)."""
        if self.item_type == self.ItemType.CUSTOM:
            return self.url
        t = self.target()
        if t is None:
            return ''
        if self.item_type == self.ItemType.PAGE:
            return t.get_absolute_url()
        # Imported here (not at module top) to keep module import cheap and
        # avoid any chance of circular imports at startup.
        from django.urls import reverse
        return reverse('posts:page', kwargs={'slug': t.slug})
