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
from django.db.models import Count, Prefetch, Q
from django.shortcuts import get_object_or_404, render
from django.urls import reverse

from .models import Category, Post


def _live_categories():
    """Prefetch that skips categories in the Trash."""
    return Prefetch('categories', queryset=Category.objects.all())


def _with_comment_count(qs):
    """Annotate ``comment_count`` = number of APPROVED comments (shown in the list)."""
    return qs.annotate(comment_count=Count('comments', filter=Q(comments__status='approved')))


def get_post_or_404(**lookup):
    """A post that is not in the Trash, with its live categories prefetched."""
    return get_object_or_404(Post.objects.prefetch_related(_live_categories()), **lookup)


def render_post(request, post, extra=None, status=200):
    """Render the single-post page. ``extra`` adds/overrides context (the comment form uses it)."""
    context = {
        'post': post,
        'related_posts': post.related_posts(),
        'page_title': post.title,
        # The last crumb is the current page, so it has no link target.
        'breadcrumbs': [('Blog', reverse('posts:list')), (post.title, '')],
    }
    context.update(extra or {})
    return render(request, 'posts/post_page.html', context, status=status)


def posts_list(request):
    """List all posts, oldest first (``order_by('date')``).

    Change to ``'-date'`` for newest first.
    Template: ``posts/templates/posts/posts_list.html``.
    Breadcrumbs: Home > Blog.
    """
    posts = _with_comment_count(Post.objects.prefetch_related(_live_categories())).order_by('date')
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
        'posts': _with_comment_count(category.posts.alive().prefetch_related(_live_categories())).order_by('date'),
        'category': category,
        'page_title': category.name,
        'breadcrumbs': [('Blog', reverse('posts:list')), (category.name, '')],
    })


def post_page(request, slug):
    """Show one post. Unknown slug -> HTTP 404.

    Template: ``posts/templates/posts/post_page.html``.
    Breadcrumbs: Home > Blog > <post title>.
    """
    return render_post(request, get_post_or_404(slug=slug))
