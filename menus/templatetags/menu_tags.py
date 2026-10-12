"""
menus.templatetags.menu_tags - the ``{% render_menu %}`` template tag.

Usage in a template::

    {% load menu_tags %}
    {% render_menu 'primary' %}

Pipeline
--------
1. ``render_menu(context, slug)``   - finds the ``Menu`` by slug.
2. ``build_tree(menu, request)``    - loads items, drops invisible ones,
                                       builds ``Node`` trees, marks the current page.
3. ``menus/menu.html`` + ``menus/_items.html`` (recursive include) - emit HTML.

Requires the ``request`` context processor
(``django.template.context_processors.request`` in settings), because the
current URL and the user are read from ``request``.
"""
from django import template
from django.template.loader import render_to_string

from ..models import Menu, MenuItem

register = template.Library()


class Node:
    """Render-ready menu item: a ``MenuItem`` plus computed display data.

    Attributes
    ----------
    item         the underlying ``MenuItem``
    label, href  resolved text / URL (``MenuItem.get_label`` / ``get_url``)
    children     list of child ``Node`` objects
    is_current   True if href equals the URL being viewed
    is_ancestor  True if a DESCENDANT is the current page (used to highlight
                 the parent of the active sub-item)

    ``__slots__`` just saves memory/typos; it has no functional effect.
    """
    __slots__ = ('item', 'label', 'href', 'children', 'is_current', 'is_ancestor')

    def __init__(self, item):
        self.item = item
        self.label = item.get_label()
        self.href = item.get_url()
        self.children = []
        self.is_current = False
        self.is_ancestor = False

    @property
    def li_classes(self):
        """CSS classes of the ``<li>`` (WordPress-style names, so themes work).

        ``menu-item`` always; ``menu-item-has-children`` if it has a sub-menu;
        ``current-menu-item`` + ``active`` for the current page;
        ``current-menu-ancestor`` + ``active`` for its parents; plus the
        editor's own ``css_classes``.
        """
        cls = ['menu-item']
        if self.children:
            cls.append('menu-item-has-children')
        if self.is_current:
            cls += ['current-menu-item', 'active']
        elif self.is_ancestor:
            cls += ['current-menu-ancestor', 'active']
        if self.item.css_classes:
            cls.append(self.item.css_classes)
        return ' '.join(cls)

    @property
    def rel(self):
        """Value of the ``rel`` attribute.

        When "open in new window" is on, ``noopener noreferrer`` is appended
        automatically - required for security with ``target="_blank"``.
        """
        parts = self.item.rel.split()
        if self.item.new_tab:
            parts += [p for p in ('noopener', 'noreferrer') if p not in parts]
        return ' '.join(parts)


def _visible(item, user):
    """Apply the item's ``visibility`` rule to the current user."""
    v = item.visibility
    if v == MenuItem.Visibility.GUESTS:
        return not user.is_authenticated
    if v == MenuItem.Visibility.USERS:
        return user.is_authenticated
    if v == MenuItem.Visibility.STAFF:
        return user.is_staff
    return True


def _norm(path):
    """Normalise a URL path for comparison: drop ?query / #fragment and the
    trailing slash (``'/about/?x=1'`` -> ``'/about'``; root stays ``'/'``)."""
    path = path.split('?')[0].split('#')[0]
    return path.rstrip('/') or '/'


def build_tree(menu, request):
    """Return the list of top-level ``Node`` objects for ``menu``.

    Filtering rules (an item is left out when):
    * ``is_active`` is False;
    * its Page/Post target was deleted;
    * the visitor is not allowed by ``visibility``;
    * it links to an unpublished page and the visitor is not staff.
    A skipped item takes its whole branch with it, because its children can
    no longer find their parent in ``nodes``.

    Items are processed in ``order`` (parent before children), so a single
    pass with the ``nodes`` lookup builds the tree.
    """
    user = request.user
    items = (menu.items.filter(is_active=True)
             .select_related('page', 'post').order_by('order', 'id'))
    nodes, roots = {}, []  # nodes: item pk -> Node
    for item in items:
        # A hidden/invalid parent hides its whole branch, because its children never get attached.
        if item.target_missing() or not _visible(item, user):
            continue
        if item.page and not item.page.is_published and not user.is_staff:
            continue
        node = Node(item)
        if item.parent_id is None:
            roots.append(node)
        elif item.parent_id in nodes:
            nodes[item.parent_id].children.append(node)
        else:
            continue  # parent was filtered out -> drop this child too
        nodes[item.pk] = node

    # Highlight the item(s) matching the current URL, and their ancestors.
    current = _norm(request.path)

    def mark(children, ancestors):
        """Depth-first walk; returns True if anything below matched."""
        found = False
        for n in children:
            href = n.href
            # Only internal links can be "current" (external ones never match).
            if href and href.startswith('/') and _norm(href) == current:
                n.is_current = True
                for a in ancestors:
                    a.is_ancestor = True
                found = True
            if mark(n.children, ancestors + [n]):
                found = True
        return found

    mark(roots, [])
    return roots


@register.simple_tag(takes_context=True)
def render_menu(context, slug):
    """``{% render_menu 'primary' %}`` - outputs the nested ``<ul>`` for the menu with this slug.

    Returns an empty string (no error) when there is no ``request`` in the
    template context or no menu with that slug exists, so a missing menu never
    breaks the page.
    """
    request = context.get('request')
    if request is None:
        return ''
    try:
        menu = Menu.objects.get(slug=slug)
    except Menu.DoesNotExist:
        return ''
    return render_to_string('menus/menu.html', {
        'menu': menu,
        'nodes': build_tree(menu, request),
    })
