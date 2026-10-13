"""
posts.models - the ``Post`` model: dated blog articles.

Where this fits
---------------
* ``Post`` = blog article (listed at ``/posts/``, detail at ``/posts/<slug>``).
  Static, hierarchical pages are ``pages.models.Page`` instead.
* Referenced by ``menus.models.MenuItem.post`` so a post can be placed in a
  navigation menu.

Posts and categories use the Trash (``mcms5/softdelete.py``): deleting them only hides
them; restore from the admin ("Trash: Posts" / "Trash: Categories").

Depends on
----------
* ``django_ckeditor_5`` (rich-text ``body``; config in ``mcms5/settings.py``).
* Pillow + ``MEDIA_ROOT`` for the ``banner`` image.
* ``media/fallback.png`` must exist: it is the default banner. If you delete
  that file, posts without their own banner will render a broken image.
"""
from django.conf import settings
from django.db import models
from django.urls import reverse
from django_ckeditor_5.fields import CKEditor5Field

from mcms5.softdelete import SoftDeleteModel


class Category(SoftDeleteModel):
    """A blog category. A post can belong to several categories.

    name   Label shown in the sidebar, on posts and in the admin.
    slug   Unique URL segment: the category lives at ``/posts/category/<slug>``.
    """

    name = models.CharField(max_length=75, unique=True)
    slug = models.SlugField(max_length=75, unique=True)

    class Meta(SoftDeleteModel.Meta):
        ordering = ['name']
        verbose_name_plural = 'categories'

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('posts:category', kwargs={'slug': self.slug})


class Post(SoftDeleteModel):
    """A blog post.

    title   Heading; also the breadcrumb label and hero heading.
    body    Rich-text HTML (CKEditor 5). Rendered with ``|safe`` in
            ``post_page.html`` - this is safe only because just trusted staff
            can edit posts in the admin.
    slug    Unique URL segment: the post lives at ``/posts/<slug>``.
    date    Creation timestamp, set once automatically (``auto_now_add``);
            it cannot be edited in the admin. Used for list ordering.
    banner  Image stored under ``MEDIA_ROOT``; defaults to ``fallback.png``.
    categories  Zero or more ``Category`` objects.
    author  The user shown as the author (name under the title + author box after the post, see
            ``users`` app). Filled with the logged-in admin user when a post is created in the admin;
            posts without an author show no author info. Deleting the user keeps the post
            (``SET_NULL``). ``user.posts`` also lists Trash items - use ``Post.objects.filter(author=user)``.
    comments_open  Per-post switch for comments (the global switch is Settings -> Discussion).
    related     Hand-picked related posts. Symmetrical: linking A to B also links B to A.
    """

    title = models.CharField(max_length=75)
    body = CKEditor5Field('Content', config_name='default')
    slug = models.SlugField(max_length=75, unique=True)
    date = models.DateTimeField(auto_now_add=True)
    banner = models.ImageField(default='fallback.png', blank=True)
    categories = models.ManyToManyField(Category, blank=True, related_name='posts')
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='posts',
        help_text='Shown as the author of the post. Filled with you when you create a post.')
    related = models.ManyToManyField('self', blank=True, symmetrical=True)
    comments_open = models.BooleanField(
        'Allow comments', default=True,
        help_text='Turn off to close comments on this post (Settings -> Discussion must also be on).')

    def __str__(self):
        """Shown in the admin lists and in the menu builder."""
        return self.title

    def get_absolute_url(self):
        return reverse('posts:page', kwargs={'slug': self.slug})

    def related_posts(self, limit=4):
        """Hand-picked related posts; if there are none, posts sharing a category (newest first)."""
        manual = list(self.related.alive().order_by('-date')[:limit])
        if manual:
            return manual
        return list(
            Post.objects.filter(categories__in=self.categories.alive())
            .exclude(pk=self.pk).distinct().order_by('-date')[:limit]
        )


class TrashedPost(Post):
    """Proxy used only to show the Trash of posts in the admin."""

    class Meta:
        proxy = True
        verbose_name = 'Trash: post'
        verbose_name_plural = 'Trash: Posts'


class TrashedCategory(Category):
    """Proxy used only to show the Trash of categories in the admin."""

    class Meta:
        proxy = True
        verbose_name = 'Trash: category'
        verbose_name_plural = 'Trash: Categories'
