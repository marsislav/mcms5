"""
menus.admin - admin integration for menus + the custom builder screen.

Screens
-------
* Changelist / change form  -> normal Django admin for ``Menu`` (name, slug,
  ``<ul>`` classes). Menu ITEMS are not edited here.
* Builder (custom)          -> ``/admin/menus/menu/<id>/builder/``
  Drag-and-drop editor; template ``admin/menus/menu/builder.html``.
* Builder save (custom AJAX)-> ``/admin/menus/menu/<id>/builder/save/``
  Receives JSON, validates and stores it via ``menus.builder.save_items``.

Security
--------
Both custom URLs are wrapped in ``admin_site.admin_view`` (so the user must be
a logged-in staff member) and additionally checked with
``has_change_permission`` (see ``_menu``).  CSRF is enforced: the JavaScript
sends the ``X-CSRFToken`` header.
"""
import json

from django.contrib import admin
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import path, reverse
from django.utils.html import format_html

from . import builder
from .models import Menu


@admin.register(Menu)
class MenuAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'item_count', 'builder_link')
    prepopulated_fields = {'slug': ('name',)}
    # Adds an "Edit structure" button to the change form (see that template).
    change_form_template = 'admin/menus/menu/change_form.html'

    @admin.display(description='Items')
    def item_count(self, obj):
        """Changelist column: number of items in the menu (one COUNT query per row)."""
        return obj.items.count()

    @admin.display(description='')
    def builder_link(self, obj):
        """Changelist column: link to the drag-and-drop builder."""
        return format_html('<a href="{}">Edit structure →</a>',
                           reverse('admin:menus_menu_builder', args=[obj.pk]))

    def response_add(self, request, obj, post_url_continue=None):
        """After creating a NEW menu, go straight to the builder.

        Skipped when the editor pressed "Save and continue editing" or
        "Save and add another" (their normal behaviour is kept).
        """
        if '_continue' not in request.POST and '_addanother' not in request.POST:
            return redirect('admin:menus_menu_builder', obj.pk)
        return super().response_add(request, obj, post_url_continue)

    def get_urls(self):
        """Register the two custom URLs.

        Ours are placed BEFORE the default admin URLs: otherwise the generic
        ``<path:object_id>/`` pattern would capture ``5/builder/``.
        """
        wrap = self.admin_site.admin_view  # enforces "logged-in staff"
        return [
            path('<int:menu_id>/builder/', wrap(self.builder_view), name='menus_menu_builder'),
            path('<int:menu_id>/builder/save/', wrap(self.builder_save), name='menus_menu_builder_save'),
        ] + super().get_urls()

    def _menu(self, request, menu_id):
        """Fetch the menu (404 if missing) and require the 'change menu' permission."""
        menu = get_object_or_404(Menu, pk=menu_id)
        if not self.has_change_permission(request, menu):
            raise PermissionDenied
        return menu

    def builder_view(self, request, menu_id):
        """Render the builder page (GET).

        All data the JavaScript needs is passed as one JSON blob
        (``builder_data``) which the template embeds with ``json_script``:

        items    current menu items, flat list with ``depth`` (builder.serialize_items)
        pages    all pages the editor can add (builder.available_objects)
        posts    all posts the editor can add
        saveUrl  endpoint for saving (``builder_save`` below)
        maxDepth maximum nesting level (builder.MAX_DEPTH)
        """
        menu = self._menu(request, menu_id)
        pages, posts = builder.available_objects()
        ctx = {
            # Standard admin context: site header, navigation, user info...
            **self.admin_site.each_context(request),
            'title': f'Menu: {menu.name}',
            'menu': menu,
            'opts': self.model._meta,
            'builder_data': {
                'items': builder.serialize_items(menu),
                'pages': pages,
                'posts': posts,
                'saveUrl': reverse('admin:menus_menu_builder_save', args=[menu.pk]),
                'maxDepth': builder.MAX_DEPTH,
            },
        }
        return render(request, 'admin/menus/menu/builder.html', ctx)

    def builder_save(self, request, menu_id):
        """Save the builder state (AJAX POST, JSON in / JSON out).

        Request body: ``{"items": [ {row}, ... ]}`` (a bare list is accepted too).
        Success:      ``{"ok": true,  "items": [...]}`` - the freshly stored,
                      normalised items (with their new database ids).
        Failure:      HTTP 400 ``{"ok": false, "error": "message"}`` - nothing
                      is saved (the save is atomic, see builder.save_items).
        """
        if request.method != 'POST':
            return JsonResponse({'ok': False, 'error': 'POST only'}, status=405)
        menu = self._menu(request, menu_id)
        try:
            payload = json.loads(request.body or b'[]')
            builder.save_items(menu, payload.get('items') if isinstance(payload, dict) else payload)
        except (ValueError, ValidationError) as e:
            # ValidationError -> readable validation message; other ValueError
            # (json.JSONDecodeError is a subclass) -> "Invalid JSON.".
            msg = ' '.join(e.messages) if isinstance(e, ValidationError) else 'Invalid JSON.'
            return JsonResponse({'ok': False, 'error': msg}, status=400)
        return JsonResponse({'ok': True, 'items': builder.serialize_items(menu)})
