from django.http import Http404
from django.shortcuts import render

from .models import Page


def page_detail(request, path):
    """Resolve '/services/web/' by walking the slug chain from the top level down."""
    page = None
    for slug in path.strip('/').split('/'):
        try:
            page = Page.objects.get(slug=slug, parent=page)
        except Page.DoesNotExist:
            raise Http404('Page not found')
    # Drafts are visible only to staff, so you can preview before publishing.
    if not page.is_published and not request.user.is_staff:
        raise Http404('Page not found')
    return render(request, 'pages/page.html', {'page': page})
