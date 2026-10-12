"""
pages.context_processors - template context available in EVERY template.

IMPORTANT - this processor is currently NOT ACTIVE. To activate it, add
``'pages.context_processors.menu_pages'`` to
``TEMPLATES[0]['OPTIONS']['context_processors']`` in ``mcms5/settings.py``.

It is also LEGACY: navigation is now rendered by the ``menus`` app
(``{% render_menu 'primary' %}`` in ``templates/layout.html``), which does not
use ``menu_pages``. Keep it only if some template still wants the raw list of
"show in menu" pages; otherwise it can be deleted.
"""
from .models import Page


def menu_pages(request):
    """Makes `menu_pages` (published top-level pages marked 'show in menu') available in every template."""
    return {'menu_pages': Page.objects.filter(is_published=True, show_in_menu=True, parent__isnull=True)}
