"""
mcms5.urls - ROOT URL configuration (``ROOT_URLCONF`` in settings.py).

Order matters: Django uses the FIRST pattern that matches.

====================  ==============================  ============================
URL                   Handled by                      Notes
====================  ==============================  ============================
/admin/               django admin                    includes the menu builder
/                     mcms5.views.homepage            fixed home page
/about/               mcms5.views.about               fixed About page
/posts/...            posts.urls                      blog list + detail
/users/...            users.urls                      registration
/ckeditor5/...        django_ckeditor_5.urls          image upload endpoint
/media/...            static() helper                 uploaded files (DEBUG only)
/<any/path>/          pages.urls -> page_detail       CMS pages; MUST BE LAST
====================  ==============================  ============================

The ``pages`` catch-all matches ANY path ending in ``/``, so every new fixed URL
must be added ABOVE it.
"""
from django.contrib import admin
from django.urls import path, include
from . import views
from django.conf.urls.static import static
from django.conf import settings

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.homepage),
    path('about/', views.about),
    path('posts/', include('posts.urls')),
    path('users/', include('users.urls')),
    path('ckeditor5/', include('django_ckeditor_5.urls')),
    path('', include('pages.urls')),  # catch-all for CMS pages - keep LAST
]

# Serve user-uploaded files (MEDIA_URL -> MEDIA_ROOT). Django only does this
# when DEBUG=True; in production the web server (nginx/Apache) must serve
# /media/ itself.
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
