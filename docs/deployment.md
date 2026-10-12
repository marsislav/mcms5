# Deployment checklist

Current `mcms5/settings.py` is a **development** configuration.

| Setting | Now | For production |
|---|---|---|
| `DEBUG` | `True` | `False` |
| `SECRET_KEY` | placeholder in the file | read from an environment variable; rotate the committed one |
| `ALLOWED_HOSTS` | `[]` | your domain(s) |
| `DATABASES` | SQLite file | fine for small sites; back up `db.sqlite3` (or switch to PostgreSQL/MySQL) |
| Static files | `STATICFILES_DIRS` only | add `STATIC_ROOT`, run `python manage.py collectstatic`, serve `/static/` with the web server |
| Media files | served by Django only when `DEBUG=True` | serve `/media/` with nginx/Apache |
| HTTPS | - | enable `SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE` |
| `TEMPLATES['DIRS']` | relative `'templates'` | use `[BASE_DIR / 'templates']` so it does not depend on the working directory |

Then:

```bash
python manage.py check --deploy
python manage.py migrate
python manage.py collectstatic
```

Entry points: `mcms5.wsgi.application` (WSGI) / `mcms5.asgi.application` (ASGI).

## Upgrading an existing database

Pull the new code and run `python manage.py migrate`. Migrations
`menus.0003_english_labels` and `posts.0004_english_labels` only change labels;
`menus.0003` also renames the default Bulgarian menu names ("Главно меню",
"Начало") to English if they were never customised. No data is lost.
