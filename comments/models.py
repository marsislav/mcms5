"""
comments.models - visitor comments on blog posts, with replies.

* ``Comment.post``    the post commented on (posts only; pages have no comments).
* ``Comment.parent``  the comment this one answers (``None`` = top level) -> threaded replies.
* ``Comment.status``  pending (waits for an admin) / approved (public) / spam (hidden).

Behaviour is controlled in admin -> Settings -> Discussion (``siteconfig.SiteSettings``)
and by ``Post.comments_open``; the rules live in ``comments/services.py``.
Only APPROVED comments are ever shown or counted publicly.
"""
from django.conf import settings
from django.db import models
from django.urls import reverse


class Comment(models.Model):
    PENDING, APPROVED, SPAM = 'pending', 'approved', 'spam'
    STATUS_CHOICES = [(PENDING, 'Pending'), (APPROVED, 'Approved'), (SPAM, 'Spam')]

    post = models.ForeignKey('posts.Post', on_delete=models.CASCADE, related_name='comments')
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='replies')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                             related_name='+')
    author_name = models.CharField('Name', max_length=80)
    author_email = models.EmailField('E-mail', blank=True)
    body = models.TextField('Comment', max_length=2000)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=PENDING, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created', 'id']

    def __str__(self):
        return '%s: %s' % (self.author_name, self.short_body())

    def short_body(self, n=60):
        text = ' '.join(self.body.split())
        return text if len(text) <= n else text[:n - 1] + '…'

    def depth(self):
        """1 for a top-level comment, 2 for a reply to it, ..."""
        depth, node, seen = 1, self, {self.pk}
        while node.parent_id and node.parent_id not in seen:
            seen.add(node.parent_id)
            node = node.parent
            depth += 1
        return depth

    def get_absolute_url(self):
        return '%s#comment-%d' % (reverse('posts:page', kwargs={'slug': self.post.slug}), self.pk)
