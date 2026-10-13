"""
mcms5.softdelete_admin - admin helpers for ``mcms5.softdelete``.

``SoftDeleteAdminMixin``  put FIRST in the bases of the normal ModelAdmin:
                          lists only items that are not in the Trash; "delete" (single or
                          bulk) moves to the Trash; relation pickers skip trashed items.
``TrashAdmin``            admin of a PROXY model: lists only trashed items, with the bulk
                          actions "Restore" and "Delete permanently" (with confirmation).
"""
from django.contrib import admin, messages
from django.core.exceptions import ObjectDoesNotExist, ValidationError


class SoftDeleteAdminMixin:
    def get_queryset(self, request):
        return super().get_queryset(request).filter(deleted_at__isnull=True)

    def _alive_queryset(self, db_field, kwargs):
        model = db_field.remote_field.model
        if 'queryset' not in kwargs and hasattr(model, 'all_objects'):
            kwargs['queryset'] = model.objects.all()
        return kwargs

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        return super().formfield_for_foreignkey(db_field, request, **self._alive_queryset(db_field, kwargs))

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        return super().formfield_for_manytomany(db_field, request, **self._alive_queryset(db_field, kwargs))


class AliveRelatedFieldListFilter(admin.RelatedFieldListFilter):
    """Sidebar filter on a relation that does not offer trashed objects."""

    def field_choices(self, field, request, model_admin):
        return field.get_choices(include_blank=False, limit_choices_to={'deleted_at__isnull': True})


class TrashAdmin(admin.ModelAdmin):
    """Register for a proxy model (``class TrashedPost(Post): Meta: proxy = True``)."""

    ordering = ('-deleted_at',)
    list_display_links = None          # nothing to edit in the Trash
    actions = ['restore_selected']

    def get_queryset(self, request):
        return self.model.all_objects.filter(deleted_at__isnull=False).order_by('-deleted_at')

    # Nothing can be added or edited here; restoring/deleting go through the actions.
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def _orig_perm(self, request, action):
        opts = self.model._meta.proxy_for_model._meta
        return request.user.has_perm(f'{opts.app_label}.{action}_{opts.model_name}')

    def has_restore_permission(self, request):
        return self._orig_perm(request, 'change')

    def has_delete_permission(self, request, obj=None):
        return self._orig_perm(request, 'delete')

    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'delete_selected' in actions:
            func, name, _ = actions['delete_selected']
            actions['delete_selected'] = (func, name, 'Delete permanently selected %(verbose_name_plural)s')
        return actions

    # The built-in "delete selected" action (with its confirmation page) ends in these two
    # methods; in the Trash they must really delete.
    def delete_queryset(self, request, queryset):
        queryset.hard_delete()

    def delete_model(self, request, obj):
        obj.hard_delete()

    @admin.action(description='Restore selected %(verbose_name_plural)s', permissions=['restore'])
    def restore_selected(self, request, queryset):
        restored = 0
        for obj in list(queryset):
            try:
                obj.refresh_from_db()           # a parent page's restore may already have restored it
                if obj.deleted_at is not None:
                    obj.restore()
                restored += 1
            except ObjectDoesNotExist:
                continue
            except ValidationError as e:
                self.message_user(request, f'{obj}: {" ".join(e.messages)}', messages.ERROR)
        if restored:
            self.message_user(request, f'Restored: {restored}.', messages.SUCCESS)
