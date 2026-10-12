"""
posts.urls - routes for the blog, mounted at ``/posts/`` by ``mcms5/urls.py``.

Namespace ``posts``:
    posts:list  -> /posts/
    posts:page  -> /posts/<slug>   (no trailing slash; ``menus.models.MenuItem.get_url``
                                    builds this URL with reverse())
"""
from django.urls import path
from . import views

app_name = 'posts'
urlpatterns = [
    path('', views.posts_list, name='list'),
    path('<slug:slug>', views.post_page, name='page'),
]
