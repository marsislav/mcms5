"""
comments.services - the rules: is commenting allowed, and what happens to a new comment.

All options come from ``siteconfig.SiteSettings`` (admin -> Settings -> Discussion).
"""
import re
from datetime import timedelta

from django.core.mail import send_mail
from django.utils import timezone

from siteconfig.models import MODERATION_AUTO, MODERATION_RETURNING

from .models import Comment

_LINK = re.compile(r'https?://|www\.', re.I)


def comments_open_for(post, site):
    """True if the comment form is available for ``post`` (global switch, post switch, age limit)."""
    if not site.comments_enabled or not post.comments_open:
        return False
    if site.comments_close_after_days and post.date < timezone.now() - timedelta(days=site.comments_close_after_days):
        return False
    return True


def blocked_words(site):
    return [w.strip().lower() for w in site.comments_blocked_words.splitlines() if w.strip()]


def contains_blocked(site, *texts):
    haystack = '\n'.join(t for t in texts if t).lower()
    return any(w in haystack for w in blocked_words(site))


def count_links(text):
    return len(_LINK.findall(text))


def decide_status(site, *, user, name, email, body):
    """Return the status a NEW comment gets.

    1. blocked word                        -> spam
    2. staff user                          -> approved
    3. more links than allowed             -> pending (even with automatic approval)
    4. approval mode: manual -> pending; automatic -> approved;
       returning commenters -> approved only if this e-mail already has an approved comment.
    """
    if contains_blocked(site, body, name, email):
        return Comment.SPAM
    if user is not None and user.is_authenticated and user.is_staff:
        return Comment.APPROVED
    if count_links(body) > site.comments_max_links:
        return Comment.PENDING
    mode = site.comments_moderation
    if mode == MODERATION_AUTO:
        return Comment.APPROVED
    if mode == MODERATION_RETURNING and email and \
            Comment.objects.filter(author_email__iexact=email, status=Comment.APPROVED).exists():
        return Comment.APPROVED
    return Comment.PENDING


def notify_admin(site, comment, request):
    """E-mail the site admin about a new comment (only if enabled and an admin e-mail is set)."""
    if not (site.comments_email_admin and site.admin_email) or comment.status == Comment.SPAM:
        return
    state = 'published' if comment.status == Comment.APPROVED else 'waiting for approval'
    send_mail(
        subject='[%s] New comment on "%s" (%s)' % (site.site_title, comment.post.title, state),
        message='%s <%s> wrote:\n\n%s\n\nView: %s' % (
            comment.author_name, comment.author_email or 'no e-mail', comment.body,
            request.build_absolute_uri(comment.get_absolute_url())),
        from_email=None, recipient_list=[site.admin_email], fail_silently=True,
    )
