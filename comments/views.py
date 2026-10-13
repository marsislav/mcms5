"""
comments.views - receiving a new comment (``POST /comments/post/<post_id>/``).

Flow: check that commenting is allowed -> validate the form -> pick the status
(``services.decide_status``) -> save -> redirect back to the post with
``?commented=approved|pending`` (the post page shows a message). On a validation
error the post page is re-rendered with the form errors.
"""
from django.http import HttpResponseForbidden
from django.shortcuts import redirect
from django.views.decorators.http import require_POST

from posts.views import get_post_or_404, render_post
from siteconfig.models import SiteSettings

from . import services
from .forms import CommentForm
from .models import Comment


@require_POST
def submit(request, post_id):
    post = get_post_or_404(pk=post_id)
    site = SiteSettings.load()
    if not services.comments_open_for(post, site):
        return HttpResponseForbidden('Comments are closed.')
    if site.comments_registered_only and not request.user.is_authenticated:
        return HttpResponseForbidden('Please log in to comment.')

    form = CommentForm(request.POST, site=site, post=post, user=request.user)
    if not form.is_valid():
        return render_post(request, post, {'comment_form': form}, status=400)

    back = post.get_absolute_url()
    if form.cleaned_data.get('website'):          # honeypot: pretend it worked, store nothing
        return redirect('%s?commented=pending#comments' % back)

    data = form.cleaned_data
    status = services.decide_status(site, user=request.user, name=data['author_name'],
                                    email=data['author_email'], body=data['body'])
    comment = Comment.objects.create(
        post=post, parent=data['parent_obj'], author_name=data['author_name'],
        author_email=data['author_email'], body=data['body'], status=status,
        user=request.user if request.user.is_authenticated else None,
        ip_address=request.META.get('REMOTE_ADDR') or None,
    )
    services.notify_admin(site, comment, request)
    if status == Comment.APPROVED:
        return redirect('%s?commented=approved#comment-%d' % (back, comment.pk))
    # pending and spam look the same to the visitor (so spammers learn nothing)
    return redirect('%s?commented=pending#comments' % back)
