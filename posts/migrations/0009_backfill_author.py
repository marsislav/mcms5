"""Data migration: posts written before ``Post.author`` existed get the site owner (the first active
superuser) as author, so the author box shows on them. Posts that already have an author are untouched.
Change the author of any post later in admin -> Posts."""
from django.conf import settings
from django.db import migrations


def backfill(apps, schema_editor):
    app_label, model_name = settings.AUTH_USER_MODEL.split('.')
    User = apps.get_model(app_label, model_name)
    Post = apps.get_model('posts', 'Post')
    owner = User.objects.filter(is_superuser=True, is_active=True).order_by('pk').first()
    if owner:
        Post._default_manager.filter(author__isnull=True).update(author=owner)


class Migration(migrations.Migration):

    dependencies = [
        ('posts', '0008_post_author'),
    ]

    operations = [
        migrations.RunPython(backfill, migrations.RunPython.noop),
    ]
