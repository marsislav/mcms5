"""
mcms5.views - project-level views for the fixed URLs defined in ``mcms5/urls.py``.

Both views pass ``page_title`` and ``breadcrumbs`` to ``templates/layout.html``:

* ``page_title``  - text of the hero heading.
* ``breadcrumbs`` - trail AFTER "Home" as ``[(label, url), ...]``. An empty list
  means "we are on the home page" (the template then shows "Home" as the
  active item).
"""
from django.shortcuts import render


def homepage(request):
    """``/`` - home page. No breadcrumb trail (we ARE the root)."""
    return render(request, 'home.html', {'page_title': 'Home', 'breadcrumbs': []})


def about(request):
    """``/about/`` - static About page. Breadcrumbs: Home > About."""
    return render(request, 'about.html', {
        'page_title': 'About',
        'breadcrumbs': [('About', '/about/')],
    })
