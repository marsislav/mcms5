"""
mcms5.softdelete - "Trash" (soft delete) for content models.

Deleting a ``Post``, ``Page`` or ``Category`` does NOT remove the row: it only sets
``deleted_at``. The item disappears from the site, search, menus and the normal admin
lists, and can be restored from the admin ("Trash: ..." entries).

Managers (on every ``SoftDeleteModel``)
---------------------------------------
``Model.objects``      only items that are NOT deleted   <- use this everywhere on the site
``Model.all_objects``  everything, deleted or not        <- admin Trash, uniqueness checks

``all_objects`` is the model's *default manager* (``Meta.default_manager_name``). That is
deliberate: Django's unique-slug validation uses the default manager, so a new item can't
steal the slug of an item sitting in the Trash (restoring would otherwise fail).
Consequence: reverse relations (``category.posts``, ``post.related``) include deleted
rows - call ``.alive()`` on them, and use ``Model.objects`` with ``get_object_or_404``.

API
---
``obj.delete()``        -> move to Trash (soft)
``obj.restore()``       -> bring it back; raises ``ValidationError`` if it can't
                           (slug now used by another item / parent page still in Trash)
``obj.hard_delete()``   -> really delete from the database
``qs.delete()``, ``qs.restore()``, ``qs.hard_delete()``, ``qs.alive()``, ``qs.dead()``
"""
from django.core.exceptions import ValidationError
from django.db import IntegrityError, models, transaction
from django.utils import timezone


class SoftDeleteQuerySet(models.QuerySet):
    def alive(self):
        return self.filter(deleted_at__isnull=True)

    def dead(self):
        return self.filter(deleted_at__isnull=False)

    def delete(self):
        """Soft delete every not-yet-deleted object (one by one, so Page can cascade to children)."""
        count = 0
        for obj in list(self.alive()):
            obj.delete()
            count += 1
        return count, {self.model._meta.label: count}

    delete.alters_data = True
    delete.queryset_only = True

    def hard_delete(self):
        """Really delete from the database (irreversible)."""
        return super().delete()

    hard_delete.alters_data = True

    def restore(self):
        for obj in list(self.dead()):
            obj.restore()

    restore.alters_data = True


class AliveManager(models.Manager.from_queryset(SoftDeleteQuerySet)):
    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)


class AllManager(models.Manager.from_queryset(SoftDeleteQuerySet)):
    pass


class SoftDeleteModel(models.Model):
    deleted_at = models.DateTimeField(null=True, blank=True, editable=False, db_index=True)

    objects = AliveManager()
    all_objects = AllManager()

    class Meta:
        abstract = True
        default_manager_name = 'all_objects'

    @property
    def is_deleted(self):
        return self.deleted_at is not None

    # -- soft delete / restore ------------------------------------------------
    def delete(self, using=None, keep_parents=False):
        """Move to Trash. Deleting an already deleted object does nothing."""
        if self.deleted_at is None:
            with transaction.atomic():
                self._soft_delete(timezone.now())
        return 1, {self._meta.label: 1}

    delete.alters_data = True

    def _soft_delete(self, ts):
        """Mark deleted with timestamp ``ts``. Subclasses extend this to cascade."""
        self.deleted_at = ts
        # update() on purpose: no save() side effects (auto_now fields, validation).
        type(self).all_objects.filter(pk=self.pk).update(deleted_at=ts)

    def restore(self):
        """Take the object out of the Trash. Raises ``ValidationError`` if that is impossible."""
        if self.deleted_at is None:
            return
        ts = self.deleted_at
        try:
            with transaction.atomic():
                self._restore(ts)
        except IntegrityError:
            raise ValidationError(
                'Cannot restore: its slug is now used by another item. '
                'Change the slug of the other item first.')
        self.deleted_at = None

    restore.alters_data = True

    def _restore(self, ts):
        """Clear ``deleted_at``. Subclasses extend this (checks, cascade)."""
        type(self).all_objects.filter(pk=self.pk).update(deleted_at=None)

    def hard_delete(self, using=None, keep_parents=False):
        """Really delete from the database (irreversible)."""
        return super().delete(using=using, keep_parents=keep_parents)

    hard_delete.alters_data = True
