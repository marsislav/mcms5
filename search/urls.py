"""search.urls - ``/search/`` (name ``search``). Included in ``mcms5/urls.py`` BEFORE the pages catch-all."""
from django.urls import path
from . import views

urlpatterns = [
    path('', views.search, name='search'),
]
