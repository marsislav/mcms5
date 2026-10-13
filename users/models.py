"""
users.models - the public ``Profile`` of a registered user.

The built-in ``django.contrib.auth.User`` is still used for accounts. ``Profile`` adds what a user may
show about themselves: a display name, a photo, a short description, a place and a website.

Where it is shown
-----------------
* the **author box** after every post that has an author (``{% author_box post %}``,
  ``users/templatetags/users_tags.py``) and the "by <name>" line under the post title;
* the public **author page** ``/users/author/<username>/`` with all posts of that author.
The e-mail address is never part of the profile and is never shown.

Lifecycle
---------
* A profile row is created automatically for every new user (``users/signals.py``); the migration
  ``0002_create_profiles`` created rows for the users that already existed.
* ``Profile.of(user)`` returns the profile for READING (an empty unsaved one if the row is missing);
  ``Profile.for_user(user)`` creates the row if needed (used by the edit page).
* Replacing or clearing the photo deletes the old file from ``MEDIA_ROOT/avatars/``; deleting the profile or
  the user deletes the photo too (``users/signals.py``).
"""
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator, URLValidator
from django.db import models
from django.urls import reverse

from siteconfig.models import MaxFileSize

MAX_AVATAR_SIZE = 2 * 1024 * 1024      # 2 MB
_web_url = URLValidator(schemes=['http', 'https'])   # no ftp:, javascript: ... in a public link


class Profile(models.Model):
    """Public information of one user. One row per user (``user.profile``)."""

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    display_name = models.CharField(
        'Display name', max_length=80, blank=True,
        help_text='Shown as the author name. Empty = your username.')
    avatar = models.ImageField(
        'Photo', upload_to='avatars/', blank=True,
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png', 'gif', 'webp']), MaxFileSize(MAX_AVATAR_SIZE)],
        help_text='JPG, PNG, GIF or WebP, up to 2 MB. A square picture looks best.')
    bio = models.TextField(
        'About me', max_length=500, blank=True,
        help_text='A few sentences about yourself (up to 500 characters). Plain text.')
    location = models.CharField('Location', max_length=100, blank=True, help_text='City / country (optional).')
    website = models.URLField(
        'Website', blank=True, validators=[_web_url],
        help_text='Your site or social profile, starting with http:// or https:// (optional).')

    class Meta:
        ordering = ['user__username']

    def __str__(self):
        return 'Profile of %s' % self.user.get_username()

    # ------------------------------------------------------------------ access
    @classmethod
    def of(cls, user):
        """The profile of ``user`` for reading; an unsaved empty one if there is no row yet."""
        try:
            return user.profile
        except cls.DoesNotExist:
            return cls(user=user)

    @classmethod
    def for_user(cls, user):
        """The profile of ``user``, created if it does not exist."""
        profile, _ = cls.objects.get_or_create(user=user)
        return profile

    # ----------------------------------------------------------------- display
    @property
    def name(self):
        """Display name -> full name -> username."""
        return self.display_name.strip() or self.user.get_full_name().strip() or self.user.get_username()

    @property
    def initial(self):
        """First letter of the name (shown in the circle when there is no photo)."""
        return self.name[:1].upper()

    def get_absolute_url(self):
        return reverse('users:author', kwargs={'username': self.user.get_username()})

    # ------------------------------------------------------------------- files
    def save(self, *args, **kwargs):
        """Delete the previous photo file when it is replaced or cleared."""
        old = type(self).objects.filter(pk=self.pk).first() if self.pk else None
        super().save(*args, **kwargs)
        if old and old.avatar and old.avatar.name != (self.avatar.name if self.avatar else None):
            old.avatar.storage.delete(old.avatar.name)
