"""
menus.builder - (de)serialisation and saving for the drag-and-drop menu builder.

This module is the ONLY place that knows how the builder's JSON maps to
``MenuItem`` rows. It is used by ``menus/admin.py``.

The wire format ("flat list with depth")
----------------------------------------
The JavaScript builder (``builder.html``) keeps the menu as a FLAT, ordered
list; nesting is expressed with an integer ``depth`` per row::

    [ {label:'Services', depth:0},
      {label:'Web',      depth:1},     <- child of 'Services'
      {label:'Blog',     depth:0} ]

The database stores a real tree (``parent`` FK + ``order``). Conversion:

* ``serialize_items``  DB tree  -> flat list with ``depth``   (page load / after save)
* ``save_items``       flat list -> DB tree                   (Save button)

Row keys (both directions)
--------------------------
id           database id of an existing item, or null for a new one
type         'page' | 'post' | 'custom'
object_id    pk of the Page/Post (only for page/post items)
label        explicit title ('' = fall back to the target's title)
url          only for custom links
title_attr, new_tab, css_classes, link_classes, element_id, rel,
visibility, is_active    1:1 with the same-named MenuItem fields
depth        nesting level, 0 = top level
(read-only, serialize only)  default_label, missing
"""
import re
from django.core.exceptions import ValidationError
from django.db import transaction

from pages.models import Page
from posts.models import Post
from .models import MenuItem

# Maximum nesting depth (0 = top level, so 5 means up to 6 levels). The JS
# builder receives the same number, so UI and server agree.
MAX_DEPTH = 5
# An HTML id may not contain whitespace.
ID_RE = re.compile(r'^\S+$')
# Custom URLs must START with one of these. This blocks dangerous schemes such
# as ``javascript:`` and ``data:`` (XSS) and bare relative paths.
ALLOWED_URL_PREFIXES = ('/', '#', '?', 'http://', 'https://', 'mailto:', 'tel:')
T = MenuItem.ItemType  # short alias used below


def serialize_items(menu):
    """Return the menu as a flat, ordered list of dicts with a ``depth`` per item.

    This is the shape the JavaScript builder works with.

    Depth is computed in one pass: items are sorted by ``order`` (depth-first
    order), so a parent always appears before its children and we can look up
    the parent's already-computed depth in ``depth_of``.

    Query cost: 1 query for items + page/post via ``select_related``.
    """
    items = list(menu.items.select_related('page', 'post').order_by('order', 'id'))
    depth_of = {}  # item pk -> depth
    out = []
    for it in items:
        depth = depth_of.get(it.parent_id, -1) + 1 if it.parent_id else 0
        depth_of[it.pk] = depth
        t = it.target()
        out.append({
            'id': it.pk,
            'type': it.item_type,
            'object_id': (it.page_id if it.item_type == T.PAGE else it.post_id if it.item_type == T.POST else None),
            'label': it.label,
            # Shown as placeholder in the builder when 'label' is empty.
            'default_label': t.title if t else '',
            'url': it.url,
            'title_attr': it.title_attr,
            'new_tab': it.new_tab,
            'css_classes': it.css_classes,
            'link_classes': it.link_classes,
            'element_id': it.element_id,
            'rel': it.rel,
            'visibility': it.visibility,
            'is_active': it.is_active,
            'depth': depth,
            # True => linked page/post was deleted; the builder shows a red badge.
            'missing': it.target_missing(),
        })
    return out


def available_objects():
    """Return ``(pages, posts)``: the lists shown in the builder's left column.

    Each entry has id, title, path (URL for display only) and ``published``
    (drafts are marked "(draft)" in the UI).
    """
    pages = [{'id': p.pk, 'title': p.title, 'path': '/' + p.full_path() + '/',
              'published': p.is_published}
             for p in Page.objects.select_related('parent').order_by('title')]
    posts = [{'id': p.pk, 'title': p.title, 'path': f'/posts/{p.slug}', 'published': True}
             for p in Post.objects.order_by('-date')]
    return pages, posts


def _clean_classes(value):
    """Collapse runs of whitespace: ``'btn   big '`` -> ``'btn big'``."""
    return ' '.join(str(value or '').split())


@transaction.atomic
def save_items(menu, payload):
    """Replace the menu's items with ``payload`` (flat list with depth).

    Raises ``django.core.exceptions.ValidationError`` with a readable message
    on the first invalid row. The function is wrapped in a database
    transaction, so on ANY error nothing is changed (all-or-nothing).

    Algorithm
    ---------
    1. Pre-load existing items / pages / posts into dicts (avoids per-row queries).
    2. For each row (``pos`` = position, becomes ``order``):
         a. validate type and target (page/post exists, or custom URL is safe);
         b. validate label / element id / visibility;
         c. turn ``depth`` into a ``parent`` using ``stack`` (explained below);
         d. update the existing item (matched by ``id``) or create a new one.
    3. Delete every existing item that was NOT in the payload (the editor
       removed it in the builder).

    The ``stack`` trick
    -------------------
    ``stack[d]`` holds the most recently saved item at depth ``d``. For a row
    with depth ``n`` the parent is ``stack[n-1]``. Rows are processed top to
    bottom, so that is always "the closest previous item one level up".
    After choosing the parent we cut the stack back to ``n`` entries (items
    deeper than this row are no longer candidates) and push the row itself.
    ``depth`` is also clamped to ``len(stack)`` so a row can never skip a level
    (e.g. depth 3 directly after depth 0 becomes depth 1).
    """
    if not isinstance(payload, list):
        raise ValidationError('Invalid data.')

    existing = {i.pk: i for i in menu.items.all()}
    pages = {p.pk: p for p in Page.objects.all()}
    posts = {p.pk: p for p in Post.objects.all()}
    valid_types = {c for c, _ in T.choices}
    valid_vis = {c for c, _ in MenuItem.Visibility.choices}

    keep_ids = set()
    stack = []  # stack[d] = saved item that is the current parent at depth d
    for pos, row in enumerate(payload):
        if not isinstance(row, dict):
            raise ValidationError('Invalid data.')
        # `name` is only used to make error messages understandable.
        name = (row.get('label') or '').strip() or f'item {pos + 1}'
        itype = row.get('type')
        if itype not in valid_types:
            raise ValidationError(f'"{name}": unknown type.')

        # Start from a clean slate so switching an item's type never leaves a
        # stale page/post/url behind.
        data = dict(item_type=itype, page=None, post=None, url='')
        if itype == T.PAGE:
            data['page'] = pages.get(row.get('object_id'))
            if data['page'] is None:
                raise ValidationError(f'"{name}": the page no longer exists - remove the item.')
        elif itype == T.POST:
            data['post'] = posts.get(row.get('object_id'))
            if data['post'] is None:
                raise ValidationError(f'"{name}": the post no longer exists - remove the item.')
        else:
            url = (row.get('url') or '').strip()
            if not url:
                raise ValidationError(f'"{name}": the URL is missing.')
            if not url.lower().startswith(ALLOWED_URL_PREFIXES):
                raise ValidationError(
                    f'"{name}": the URL must start with /, #, ?, http://, https://, mailto: or tel:')
            data['url'] = url[:500]

        label = (row.get('label') or '').strip()
        # Page/post items may leave the label empty (their title is used);
        # custom links have nothing to fall back to.
        if itype == T.CUSTOM and not label:
            raise ValidationError(f'Custom link ({data["url"]}) has no title.')
        element_id = (row.get('element_id') or '').strip()
        if element_id and not ID_RE.match(element_id):
            raise ValidationError(f'"{name}": the ID cannot contain spaces.')
        visibility = row.get('visibility')
        if visibility not in valid_vis:
            visibility = MenuItem.Visibility.ALL

        try:
            depth = int(row.get('depth', 0))
        except (TypeError, ValueError):
            depth = 0
        depth = max(0, min(depth, MAX_DEPTH, len(stack)))  # can't skip a level
        parent = stack[depth - 1] if depth else None
        del stack[depth:]

        # [:N] truncations mirror the max_length of the model fields.
        data.update(
            label=label[:200],
            title_attr=(row.get('title_attr') or '').strip()[:200],
            new_tab=bool(row.get('new_tab')),
            css_classes=_clean_classes(row.get('css_classes'))[:200],
            link_classes=_clean_classes(row.get('link_classes'))[:200],
            element_id=element_id[:100],
            rel=_clean_classes(row.get('rel'))[:100],
            visibility=visibility,
            is_active=bool(row.get('is_active', True)),
            order=pos, parent=parent, menu=menu,
        )

        # Only items that already belong to THIS menu are updated; an unknown
        # or foreign id simply creates a new item (cannot hijack other menus).
        obj = existing.get(row.get('id'))
        if obj is None:
            obj = MenuItem(**data)
        else:
            for k, v in data.items():
                setattr(obj, k, v)
        obj.save()
        keep_ids.add(obj.pk)
        stack.append(obj)

    # Anything the editor removed in the UI disappears (with its descendants,
    # via the CASCADE on `parent`).
    menu.items.exclude(pk__in=keep_ids).delete()
