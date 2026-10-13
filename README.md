# mCMS 5

A small Django content management system: static **pages** (hierarchical), a
**blog**, drag-and-drop **navigation menus**, automatic **breadcrumbs**, user
registration and a rich-text editor (CKEditor 5). The front end is the "Dento"
HTML theme (Bootstrap based) adapted into Django templates.

> Everything hand-written in this project (Python, templates, the menu-builder
> JavaScript) is documented in place with docstrings/comments, and the
> documents in [`docs/`](docs/) explain how the parts fit together.

## Documentation index

| Document | Read it to learn... |
|---|---|
| [docs/architecture.md](docs/architecture.md) | project layout, request flow, what depends on what, file-by-file reference |
| [docs/breadcrumbs.md](docs/breadcrumbs.md) | how breadcrumbs work, where data comes from, how to add them to a new page |
| [docs/menus.md](docs/menus.md) | the menu system: data model, builder screen, JSON format, rendering, CSS classes |
| [docs/content-models.md](docs/content-models.md) | `Page` and `Post`: fields, URLs, drafts, admin behaviour |
| [docs/templates-and-frontend.md](docs/templates-and-frontend.md) | `layout.html` blocks and context variables, static files, placeholders still to replace |
| [docs/slugs.md](docs/slugs.md) | slug auto-fill from the title (Bulgarian transliteration), editing, uniqueness |
| [docs/search.md](docs/search.md) | the site **search** (`/search/`): what is searched, ranking, Cyrillic/SQLite note, files |
| [docs/editor-columns.md](docs/editor-columns.md) | the editor **Columns** dropdown (1–6, 12 responsive columns): usage, HTML, breakpoints, files |
| [docs/accounts.md](docs/accounts.md) | registration, login, forgot password, **user profiles** (photo, description), post **authors** and author pages, e-mail delivery |
| [docs/settings.md](docs/settings.md) | the admin **Settings** pane (site title, logo, favicon, e-mail, location, date/time formats, **sending e-mail / local SMTP**, users): options, template/Python usage, adding sections |
| [docs/deployment.md](docs/deployment.md) | settings to change for production, static/media serving, checklist |

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt                         # Django, django-ckeditor-5, Pillow
python manage.py migrate                                # create / upgrade the database (also seeds the menus)
python manage.py createsuperuser                        # admin account
python manage.py runserver                              # http://127.0.0.1:8000/
python manage.py test                                   # run the test-suite (45 tests)
```

Run `manage.py` from the project root (the folder that contains `manage.py`):
`TEMPLATES['DIRS']` in `mcms5/settings.py` is the relative path `templates`.

## URLs at a glance

| URL | What | Code |
|---|---|---|
| `/` | home page | `mcms5/views.py::homepage` |
| `/about/` | About page | `mcms5/views.py::about` |
| `/posts/` | blog list | `posts/views.py::posts_list` |
| `/search/?q=...` | site search (pages + posts) | `search/views.py::search` |
| `/posts/<slug>` | one blog post | `posts/views.py::post_page` |
| `/users/register/` | sign-up form | `users/views.py::register_view` |
| `/admin/` | Django admin (pages, posts, menus, users, settings) | Django |
| `/admin/siteconfig/sitesettings/` | Settings pane (General section) | `siteconfig/admin.py` |
| `/admin/menus/menu/<id>/builder/` | drag-and-drop menu builder | `menus/admin.py` |
| `/<any/path>/` | CMS page (nested slugs) | `pages/views.py::page_detail` (**catch-all, must stay last**) |

## Requirements

Python 3.12+ (Django 6.1), Django >= 6.1, django-ckeditor-5 >= 0.2.20, Pillow.
(`requirements.txt`). The `*.whl` files in the project root are offline copies
of some dependencies and are not needed when you can use `pip install`.
