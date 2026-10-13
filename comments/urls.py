"""
comments.urls - mounted at ``/comments/`` by ``mcms5/urls.py``.

Namespace ``comments``:
    comments:submit -> /comments/post/<post_id>/   (POST only)
"""
from django.urls import path

from . import views

app_name = 'comments'
urlpatterns = [
    path('post/<int:post_id>/', views.submit, name='submit'),
]
