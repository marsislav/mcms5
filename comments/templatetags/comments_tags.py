"""
comments.templatetags.comments_tags - the comments block of the post page.

    {% load comments_tags %}
    {% comments_section post %}

Renders nothing when comments are disabled (Settings -> Discussion). Otherwise: the
approved comments as a tree (replies under their parent), the "closed"/"log in"
notices and the comment form. "Reply" links are plain GET links
(``?replytocom=<id>#respond``) so no JavaScript is needed.
"""
from collections import defaultdict

from django import template

from siteconfig.models import SiteSettings

from ..forms import CommentForm
from ..models import Comment
from ..services import comments_open_for

register = template.Library()


def _tree(comments, max_depth, can_reply):
    """Nest the approved comments. A reply whose parent is not approved is left out."""
    children = defaultdict(list)
    for c in comments:
        children[c.parent_id].append(c)

    def build(parent_id, depth):
        return [{'comment': c, 'depth': depth, 'can_reply': can_reply and depth < max_depth,
                 'children': build(c.pk, depth + 1)} for c in children.get(parent_id, [])]
    return build(None, 1)


@register.inclusion_tag('comments/_section.html', takes_context=True)
def comments_section(context, post):
    request = context['request']
    site = context.get('site') or SiteSettings.load()
    if not site.comments_enabled:
        return {'enabled': False}

    is_open = comments_open_for(post, site)
    needs_login = is_open and site.comments_registered_only and not request.user.is_authenticated
    can_reply = is_open and site.comments_threaded and not needs_login
    approved = list(Comment.objects.filter(post=post, status=Comment.APPROVED))

    form = context.get('comment_form')
    reply_to = None
    if is_open and not needs_login:
        if form is None:
            initial = {}
            wanted = request.GET.get('replytocom', '')
            if can_reply and wanted.isdigit():
                reply_to = next((c for c in approved if c.pk == int(wanted)
                                 and c.depth() < site.comments_max_depth), None)
                if reply_to:
                    initial['parent'] = reply_to.pk
            form = CommentForm(site=site, post=post, user=request.user, initial=initial)
        elif form.is_bound and form.data.get('parent', '').isdigit():
            reply_to = next((c for c in approved if c.pk == int(form.data['parent'])), None)

    return {
        'enabled': True, 'post': post, 'site': site, 'open': is_open, 'needs_login': needs_login,
        'nodes': _tree(approved, site.comments_max_depth, can_reply), 'count': len(approved),
        'form': form, 'reply_to': reply_to, 'csrf_token': context.get('csrf_token'),
        'commented': request.GET.get('commented') if request.GET.get('commented') in ('approved', 'pending') else '',
        'user': request.user,
    }
