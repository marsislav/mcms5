from django.contrib import admin
from .models import Page


@admin.register(Page)
class PageAdmin(admin.ModelAdmin):
    list_display = ('title', 'full_path', 'is_published', 'show_in_menu', 'menu_order', 'updated')
    list_editable = ('is_published', 'show_in_menu', 'menu_order')
    list_filter = ('is_published', 'show_in_menu')
    search_fields = ('title', 'slug', 'body')
    prepopulated_fields = {'slug': ('title',)}  # slug is filled in while typing the title
    autocomplete_fields = ('parent',)
