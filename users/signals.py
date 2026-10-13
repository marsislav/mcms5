"""users.signals - keep one ``Profile`` per user (connected in ``users/apps.py``)."""
from django.contrib.auth import get_user_model
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import Profile


@receiver(post_save, sender=get_user_model(), dispatch_uid='users_create_profile')
def create_profile(sender, instance, created, raw=False, **kwargs):
    """New user -> empty profile (skipped while loading fixtures: ``raw``)."""
    if created and not raw:
        Profile.objects.get_or_create(user=instance)


@receiver(post_delete, sender=Profile, dispatch_uid='users_delete_avatar')
def delete_avatar_file(sender, instance, **kwargs):
    """Cascade-deleting a user removes the row without calling ``Profile.delete()``: remove the file here."""
    if instance.avatar:
        instance.avatar.storage.delete(instance.avatar.name)
