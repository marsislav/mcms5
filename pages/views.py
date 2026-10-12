"""
pages.views - the public view that renders a CMS ``Page``.

Request flow
------------
1. ``mcms5/urls.py`` includes ``pages.urls`` LAST (catch-all).
2. ``pages/urls.py`` matches ``<path:path>/`` and calls ``page_detail``.
3. ``page_detail`` finds the page, checks publication state and renders
   ``pages/templates/pages/page.html`` (which extends ``templates/layout.html``).

Template context provided
-------------------------
page         the ``Page`` instance
page_title   shown in the hero banner heading in ``layout.html``
breadcrumbs  ``[(label, url), ...]`` for the breadcrumb bar in ``layout.html``
             (see ``Page.get_breadcrumbs``)
"""
from django.http import Http404
from django.shortcuts import render

from .models import Page


def page_detail(request, path):
    """Resolve e.g. ``/services/web/`` by walking the slug chain top-down.

    ``path`` is the URL without the leading and trailing slash
    (``'services/web'``). For every segment we look up the page whose slug
    equals the segment AND whose parent is the page found in the previous
    step (``None`` for the first segment). If any step fails -> 404.

    Draft pages (``is_published=False``) are only visible to staff users, so
    editors can preview before publishing. Everyone else gets a 404 (the
    page's existence is not revealed).
    """
    page = None
    for slug in path.strip('/').split('/'):
        try:
            page = Page.objects.get(slug=slug, parent=page)
        except Page.DoesNotExist:
            raise Http404('Page not found')
    # Drafts are visible only to staff, so you can preview before publishing.
    if not page.is_published and not request.user.is_staff:
        raise Http404('Page not found')
    return render(request, 'pages/page.html', {
        'page': page,
        # Hero heading in layout.html.
        'page_title': page.title,
        # Breadcrumb bar in layout.html ("Home" is added by the template).
        'breadcrumbs': page.get_breadcrumbs(),
    })
