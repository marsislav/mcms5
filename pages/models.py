from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from django_ckeditor_5.fields import CKEditor5Field


class Page(models.Model):
    """A static page (About, Contact, Services...) as opposed to a dated blog Post.

    Pages can be nested: a page with parent "services" and slug "web" is served
    at /services/web/.
    """

    title = models.CharField(max_length=150)
    # Slug is only ONE URL segment; the full URL is built from the parent chain.
    slug = models.SlugField(max_length=75)
    parent = models.ForeignKey(
        'self', null=True, blank=True, on_delete=models.CASCADE,
        related_name='children',
        help_text='Optional. Makes this page a sub-page: /parent-slug/this-slug/',
    )
    body = CKEditor5Field('Content', config_name='default', blank=True)
    banner = models.ImageField(upload_to='pages/', blank=True)
    meta_description = models.CharField(
        max_length=160, blank=True, help_text='SEO description (max 160 chars).')
    is_published = models.BooleanField(
        default=True, help_text='Unpublished pages return 404 for visitors (staff can still preview).')
    show_in_menu = models.BooleanField(default=False, help_text='List this page in the site menu.')
    menu_order = models.PositiveIntegerField(default=0, help_text='Lower numbers appear first in the menu.')
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['menu_order', 'title']
        constraints = [
            # Same slug is allowed under different parents, but not twice under one parent.
            models.UniqueConstraint(fields=['parent', 'slug'], name='unique_slug_per_parent'),
            # SQL treats NULLs as distinct, so top-level pages need their own constraint.
            models.UniqueConstraint(fields=['slug'], condition=models.Q(parent__isnull=True),
                                    name='unique_top_level_slug'),
        ]

    def __str__(self):
        return self.full_path()

    def full_path(self):
        """'services/web' - slugs of all ancestors joined with '/'."""
        parts, node, seen = [], self, set()
        while node is not None and node.pk not in seen:
            seen.add(node.pk)
            parts.append(node.slug)
            node = node.parent
        return '/'.join(reversed(parts))

    def get_absolute_url(self):
        return reverse('pages:detail', kwargs={'path': self.full_path()})

    def clean(self):
        # Stop a page from becoming its own ancestor (would loop forever).
        node = self.parent
        while node is not None:
            if node.pk is not None and node.pk == self.pk:
                raise ValidationError({'parent': 'A page cannot be a child of itself or its own descendant.'})
            node = node.parent
