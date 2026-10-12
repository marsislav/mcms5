"""
pages.urls - URL routing for CMS pages.

There is a single catch-all route. Because ``<path:path>`` matches anything,
this module MUST be included LAST in ``mcms5/urls.py``; otherwise it would
swallow URLs such as ``/admin/``, ``/posts/`` or ``/about/``.

The ``app_name`` creates the ``pages:`` namespace, so ``reverse('pages:detail',
kwargs={'path': 'services/web'})`` -> ``/services/web/`` (used by
``Page.get_absolute_url``).
"""
from django.urls import path
from . import views

app_name = 'pages'
urlpatterns = [
    # Catch-all: MUST stay the LAST include in the project urls.py,
    # so /admin/, /posts/, /about/ etc. keep working.
    path('<path:path>/', views.page_detail, name='detail'),
]
