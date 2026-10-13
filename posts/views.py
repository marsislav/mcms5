"""
posts.views - public views for the blog.

URL map (see ``posts/urls.py``, mounted under ``/posts/`` in ``mcms5/urls.py``)::

    /posts/         -> posts_list   (name 'posts:list')
    /posts/<slug>   -> post_page    (name 'posts:page')
    /posts/category/<slug> -> category_posts (name 'posts:category')

Both views feed ``templates/layout.html`` with two extra context variables:

page_title   text of the hero heading
breadcrumbs  ``[(label, url), ...]`` - the trail AFTER "Home"; the last item is
             rendered as the current page (its url is ignored, so '' is fine).
"""
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404, render
from django.urls import reverse

from .models import Category, Post


def _live_categories():
    """Prefetch that skips categories in the Trash."""
    return Prefetch('categories', queryset=Category.objects.all())


def posts_list(request):
    """List all posts, oldest first (``order_by('date')``).

    Change to ``'-date'`` for newest first.
    Template: ``posts/templates/posts/posts_list.html``.
    Breadcrumbs: Home > Blog.
    """
    posts = Post.objects.prefetch_related(_live_categories()).order_by('date')
    return render(request, 'posts/posts_list.html', {
        'posts': posts,
        'page_title': 'Blog',
        'breadcrumbs': [('Blog', reverse('posts:list'))],
    })


def category_posts(request, slug):
    """List the posts of one category (same template as the blog index). Unknown slug -> 404.

    Breadcrumbs: Home > Blog > <category name>.
    """
    category = get_object_or_404(Category.objects, slug=slug)
    return render(request, 'posts/posts_list.html', {
        'posts': category.posts.alive().prefetch_related(_live_categories()).order_by('date'),
        'category': category,
        'page_title': category.name,
        'breadcrumbs': [('Blog', reverse('posts:list')), (category.name, '')],
    })


def post_page(request, slug):
    """Show one post. Unknown slug -> HTTP 404.

    Template: ``posts/templates/posts/post_page.html``.
    Breadcrumbs: Home > Blog > <post title>.
    """
    post = get_object_or_404(Post.objects.prefetch_related(_live_categories()), slug=slug)
    return render(request, 'posts/post_page.html', {
        'post': post,
        'related_posts': post.related_posts(),
        'page_title': post.title,
        # The last crumb is the current page, so it has no link target.
        'breadcrumbs': [('Blog', reverse('posts:list')), (post.title, '')],
    })
