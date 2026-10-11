from .models import Page


def menu_pages(request):
    """Makes `menu_pages` (published top-level pages marked 'show in menu') available in every template."""
    return {'menu_pages': Page.objects.filter(is_published=True, show_in_menu=True, parent__isnull=True)}
