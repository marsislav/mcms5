"""
posts.views - public views for the blog.

URL map (see ``posts/urls.py``, mounted under ``/posts/`` in ``mcms5/urls.py``)::

    /posts/         -> posts_list   (name 'posts:list')
    /posts/<slug>   -> post_page    (name 'posts:page')

Both views feed ``templates/layout.html`` with two extra context variables:

page_title   text of the hero heading
breadcrumbs  ``[(label, url), ...]`` - the trail AFTER "Home"; the last item is
             rendered as the current page (its url is ignored, so '' is fine).
"""
from django.shortcuts import get_object_or_404, render
from django.urls import reverse

from .models import Post


def posts_list(request):
    """List all posts, oldest first (``order_by('date')``).

    Change to ``'-date'`` for newest first.
    Template: ``posts/templates/posts/posts_list.html``.
    Breadcrumbs: Home > Blog.
    """
    posts = Post.objects.all().order_by('date')
    return render(request, 'posts/posts_list.html', {
        'posts': posts,
        'page_title': 'Blog',
        'breadcrumbs': [('Blog', reverse('posts:list'))],
    })


def post_page(request, slug):
    """Show one post. Unknown slug -> HTTP 404.

    Template: ``posts/templates/posts/post_page.html``.
    Breadcrumbs: Home > Blog > <post title>.
    """
    post = get_object_or_404(Post, slug=slug)
    return render(request, 'posts/post_page.html', {
        'post': post,
        'page_title': post.title,
        # The last crumb is the current page, so it has no link target.
        'breadcrumbs': [('Blog', reverse('posts:list')), (post.title, '')],
    })
