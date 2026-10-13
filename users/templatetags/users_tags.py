"""
users.templatetags.users_tags - show the author of a post.

Usage::

    {% load users_tags %}
    {% author_box post %}                          {# author box: photo, name, about, links #}
    {{ post.author|author_name }}                  {# display name of a user #}

``author_box`` renders nothing when the post has no author, the author account is inactive, or
Settings -> Users -> "Show the post author" is off. It never writes to the database.
"""
from django import template

from posts.models import Post
from siteconfig.models import SiteSettings

from ..models import Profile

register = template.Library()


@register.filter
def author_name(user):
    """Display name of ``user`` (profile display name -> full name -> username)."""
    return Profile.of(user).name if user else ''


@register.inclusion_tag('users/_author_box.html', takes_context=True)
def author_box(context, post):
    site = context.get('site') or SiteSettings.load()
    author = post.author
    if not (site.show_author_box and author and author.is_active):
        return {'author': None}
    return {
        'author': author,
        'profile': Profile.of(author),
        'post_count': Post.objects.filter(author=author).count(),
    }
