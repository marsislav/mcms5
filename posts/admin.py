"""posts.admin - registers ``Post`` in the Django admin with default options."""
from django.contrib import admin
from .models import Post

admin.site.register(Post)
