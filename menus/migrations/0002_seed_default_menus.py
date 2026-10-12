"""
Data migration: create the two default menus on a fresh install.

Creates
-------
* ``primary`` ("Main menu")  - id ``nav``, sub-menu class ``dropdown``;
  rendered by ``{% render_menu 'primary' %}`` in the site header.
* ``footer``  ("Footer")     - class ``quick-links``;
  rendered by ``{% render_menu 'footer' %}`` in the site footer.

Both start with the links Home (/), About (/about/) and Posts (/posts/).
The primary menu additionally receives every published page that had the legacy
``Page.show_in_menu`` flag, in ``menu_order``, keeping the parent/child nesting
(children whose parent is not in the menu are promoted to top level).

Safety
------
* Does nothing if ANY menu already exists, so it never overwrites an
  existing setup.
* Reverse operation is a no-op (``RunPython.noop``): un-applying this
  migration does not delete menus.
* Uses historical models (``apps.get_model``) - NOT the real model classes -
  so it keeps working even after the models change in later migrations.
"""
from django.db import migrations


def seed(apps, schema_editor):
    """Forward step: create default menus + items (see module docstring)."""
    Menu = apps.get_model('menus', 'Menu')
    Item = apps.get_model('menus', 'MenuItem')
    Page = apps.get_model('pages', 'Page')
    if Menu.objects.exists():
        return

    primary = Menu.objects.create(name='Main menu', slug='primary', ul_id='nav', submenu_class='dropdown')
    footer = Menu.objects.create(name='Footer', slug='footer', ul_class='quick-links', submenu_class='')

    base = [('Home', '/'), ('About', '/about/'), ('Posts', '/posts/')]
    order = 0
    for label, url in base:
        Item.objects.create(menu=primary, order=order, item_type='custom', label=label, url=url)
        Item.objects.create(menu=footer, order=order, item_type='custom', label=label, url=url)
        order += 1

    # Carry over what used to be controlled by Page.show_in_menu / Page.menu_order.
    pages = list(Page.objects.filter(show_in_menu=True, is_published=True).order_by('menu_order', 'title'))
    in_menu = {p.pk for p in pages}
    created = {}

    def add(page, parent):
        """Create the item for ``page`` under ``parent``, then recurse into its children."""
        nonlocal order
        item = Item.objects.create(menu=primary, order=order, item_type='page', page=page, parent=parent)
        order += 1
        created[page.pk] = item
        for child in pages:
            if child.parent_id == page.pk:
                add(child, item)

    for p in pages:
        if p.parent_id is None or p.parent_id not in in_menu:
            add(p, None)


class Migration(migrations.Migration):

    dependencies = [
        ('menus', '0001_initial'),
        ('pages', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed, migrations.RunPython.noop),
    ]
