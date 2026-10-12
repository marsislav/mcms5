"""
posts.models - the ``Post`` model: dated blog articles.

Where this fits
---------------
* ``Post`` = blog article (listed at ``/posts/``, detail at ``/posts/<slug>``).
  Static, hierarchical pages are ``pages.models.Page`` instead.
* Referenced by ``menus.models.MenuItem.post`` so a post can be placed in a
  navigation menu.

Depends on
----------
* ``django_ckeditor_5`` (rich-text ``body``; config in ``mcms5/settings.py``).
* Pillow + ``MEDIA_ROOT`` for the ``banner`` image.
* ``media/fallback.png`` must exist: it is the default banner. If you delete
  that file, posts without their own banner will render a broken image.
"""
from django.db import models
from django_ckeditor_5.fields import CKEditor5Field


class Post(models.Model):
    """A blog post.

    title   Heading; also the breadcrumb label and hero heading.
    body    Rich-text HTML (CKEditor 5). Rendered with ``|safe`` in
            ``post_page.html`` - this is safe only because just trusted staff
            can edit posts in the admin.
    slug    Unique URL segment: the post lives at ``/posts/<slug>``.
    date    Creation timestamp, set once automatically (``auto_now_add``);
            it cannot be edited in the admin. Used for list ordering.
    banner  Image stored under ``MEDIA_ROOT``; defaults to ``fallback.png``.
    """

    title = models.CharField(max_length=75)
    body = CKEditor5Field('Content', config_name='default')
    slug = models.SlugField(max_length=75, unique=True)
    date = models.DateTimeField(auto_now_add=True)
    banner = models.ImageField(default='fallback.png', blank=True)

    def __str__(self):
        """Shown in the admin lists and in the menu builder."""
        return self.title
