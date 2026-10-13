"""
comments.admin - moderation of comments.

Filter by status (default view = all; use the "Pending" filter for the queue). Bulk actions:
Approve / Mark as pending / Mark as spam. Delete = real delete (no Trash for comments).
"""
from django.contrib import admin, messages

from .models import Comment


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('short_body', 'author_name', 'author_email', 'post', 'status', 'created')
    list_filter = ('status', 'created')
    search_fields = ('author_name', 'author_email', 'body', 'post__title')
    date_hierarchy = 'created'
    raw_id_fields = ('post', 'parent', 'user')
    readonly_fields = ('ip_address', 'created')
    actions = ['approve', 'mark_pending', 'mark_spam']

    @admin.display(description='Comment')
    def short_body(self, obj):
        return obj.short_body()

    def _set(self, request, queryset, status, label):
        n = queryset.update(status=status)
        self.message_user(request, '%d comment(s) %s.' % (n, label), messages.SUCCESS)

    @admin.action(description='Approve selected comments')
    def approve(self, request, queryset):
        self._set(request, queryset, Comment.APPROVED, 'approved')

    @admin.action(description='Mark selected comments as pending')
    def mark_pending(self, request, queryset):
        self._set(request, queryset, Comment.PENDING, 'set to pending')

    @admin.action(description='Mark selected comments as spam')
    def mark_spam(self, request, queryset):
        self._set(request, queryset, Comment.SPAM, 'marked as spam')
