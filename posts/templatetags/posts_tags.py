"""
posts.templatetags.posts_tags - sidebar widgets for the blog (used by ``templates/layout.html``).

Usage::

    {% load posts_tags %}
    {% categories_widget %}        -> "Categories" box (only categories that have posts, with counts)
    {% recent_posts_widget 5 %}    -> "Recent Posts" box with the 5 newest posts (default 5)
"""
from django import template
from django.db.models import Count, Q

from ..models import Category, Post

register = template.Library()


@register.inclusion_tag('posts/_categories_widget.html')
def categories_widget():
    categories = Category.objects.annotate(post_count=Count('posts', filter=Q(posts__deleted_at__isnull=True))).filter(post_count__gt=0)
    return {'categories': categories}


@register.inclusion_tag('posts/_recent_posts_widget.html')
def recent_posts_widget(count=5):
    return {'recent_posts': Post.objects.order_by('-date')[:count]}
