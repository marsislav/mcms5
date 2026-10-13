# Architecture

## 1. Big picture

```
 Browser
    |  HTTP request
    v
 mcms5/urls.py  (ROOT_URLCONF)  ---- first matching pattern wins ---->
    |
    +-- /admin/            -> Django admin  (+ menus builder URLs from menus/admin.py)
    +-- /                  -> mcms5.views.homepage
    +-- /about/            -> mcms5.views.about
    +-- /posts/...         -> posts.urls   -> posts.views
    +-- /users/...         -> users.urls   -> users.views
    +-- /ckeditor5/...     -> django_ckeditor_5 (image upload endpoint)
    +-- /<path>/           -> pages.urls   -> pages.views.page_detail   (catch-all, LAST)
                                   |
                                   v
                       a view builds a context dict and calls render()
                                   |
                                   v
              app template (extends)  templates/layout.html
                 |  {% render_menu 'primary' %}  -> menus/templatetags/menu_tags.py
                 |  {{ page_title }}, {% for ... in breadcrumbs %}
                 v
                 HTML response
```

## 2. Apps (Django "applications")

| App | Purpose | Models | Depends on |
|---|---|---|---|
| `mcms5` | project package: settings, root URLs, fixed pages (`/`, `/about/`) | - | all apps |
| `pages` | hierarchical static pages | `Page` | `django_ckeditor_5` |
| `posts` | blog posts | `Post` | `django_ckeditor_5` |
| `menus` | navigation menus + admin builder | `Menu`, `MenuItem` | `pages`, `posts` |
| `users` | public registration | - (uses `auth.User`) | `django.contrib.auth` |
| `search` | public site search `/search/` (pages + posts), Unicode-aware on SQLite (see [search.md](search.md)) | - | `pages`, `posts` |
| `siteconfig` | admin **Settings** pane: site title/description, logo, favicon, e-mail, location, date/time formats (see [settings.md](settings.md)) | `SiteSettings` (singleton) | - |

Dependency direction (arrow = "imports / needs"):

```
menus ---> pages
menus ---> posts
pages ---> django_ckeditor_5
posts ---> django_ckeditor_5
templates/layout.html ---> menus (render_menu tag)
all views ---> templates/layout.html (via template inheritance)
```

`pages` and `posts` know nothing about `menus`; deleting a page/post only
sets the menu item's foreign key to NULL (item is then flagged "missing").

## 3. Where each piece of data comes from

| Thing on screen | Produced by | Stored in |
|---|---|---|
| Page title / body / banner | `Page` fields | DB table `pages_page` |
| Blog post | `Post` fields | DB table `posts_post`; images in `media/` |
| Main & footer navigation | `Menu` + `MenuItem` rows | DB tables `menus_menu`, `menus_menuitem` |
| Hero heading (`page_title`) | the **view** | not stored (computed per request) |
| Breadcrumb trail (`breadcrumbs`) | the **view** (`Page.get_breadcrumbs()` for pages) | not stored |
| Current-menu highlighting | `menu_tags.build_tree` compares `request.path` with each item URL | not stored |
| CSS/JS/fonts | `static/` folder | files |
| Uploaded images | `media/` folder (`MEDIA_ROOT`) | files |

## 4. File-by-file reference

Legend: **Uses** = what it needs; **Used by** = who needs it.

### Project package `mcms5/`

| File | What it does | Uses | Used by |
|---|---|---|---|
| `manage.py` | command line entry (`runserver`, `migrate`, `test`...) | settings | you |
| `mcms5/settings.py` | all configuration (apps, templates, DB, static, CKEditor toolbar) | - | everything |
| `mcms5/urls.py` | root URL map (order matters) | each app's `urls.py` | Django |
| `mcms5/views.py` | home + about views; pass `page_title`/`breadcrumbs` | `home.html`, `about.html` | `urls.py` |
| `mcms5/wsgi.py`, `asgi.py` | entry points for production servers | settings | web server |

### App `pages/`

| File | What it does |
|---|---|
| `models.py` | `Page` model; `full_path()`, `get_absolute_url()`, `get_breadcrumbs()`, `clean()` (cycle check) |
| `views.py` | `page_detail`: walks the slug chain, enforces draft rules, renders `pages/page.html` |
| `urls.py` | the catch-all route `<path:path>/` (named `pages:detail`) |
| `admin.py` | admin list/search/autocomplete configuration |
| `templates/pages/page.html` | page template (extends `layout.html`) |
| `context_processors.py` | legacy `menu_pages` processor (**not enabled**) |
| `tests.py` | breadcrumb + draft tests |
| `migrations/` | database history |

### App `posts/`

| File | What it does |
|---|---|
| `models.py` | `Post` model |
| `views.py` | `posts_list`, `post_page` (404 for unknown slug) |
| `urls.py` | `posts:list`, `posts:page` |
| `templates/posts/posts_list.html`, `post_page.html` | list and detail templates |
| `admin.py` | default admin registration |

### Editor columns (no app, static files only)

`static/js/ckeditor-columns.js` + `static/css/mcms-columns.css` - see [editor-columns.md](editor-columns.md).

### App `siteconfig/`

| File | What it does |
|---|---|
| `models.py` | `SiteSettings` singleton (`load()`, validation, format helpers) |
| `admin.py` | Settings pane; sections = `fieldsets` shown as tabs |
| `context_processors.py` | adds `site` to every template |
| `templatetags/site_tags.py` | `site_date`, `site_time`, `site_datetime` filters |
| `templates/admin/siteconfig/sitesettings/change_form.html` | tabs + custom-format toggle |
| `tests.py` | settings tests |

### App `menus/`

| File | What it does |
|---|---|
| `models.py` | `Menu`, `MenuItem` (+ choices, `get_url()`, `get_label()`) |
| `admin.py` | admin for `Menu` + two custom URLs (builder page, AJAX save) |
| `builder.py` | JSON <-> database conversion and **all validation** of the builder |
| `templatetags/menu_tags.py` | `{% render_menu 'slug' %}` tag and tree building |
| `templates/menus/menu.html`, `_items.html` | HTML output of a menu (recursive partial) |
| `templates/admin/menus/menu/builder.html` | builder UI (HTML + CSS + JavaScript) |
| `templates/admin/menus/menu/change_form.html` | adds the "Edit structure" button |
| `migrations/0002_seed_default_menus.py` | creates the default menus on a new database |
| `migrations/0003_english_labels.py` | English labels + renames the Bulgarian defaults |
| `tests.py` | builder + rendering tests |

### App `users/`

`views.py` (registration), `urls.py`, `templates/users/register.html`. `models.py`, `admin.py`, `tests.py` are intentionally empty.

### Shared `templates/`

`layout.html` (base template), `home.html`, `about.html`.

### `static/` and `media/`

`static/` = the theme (Bootstrap, jQuery, plugins, `style.css`, `style.oth.css`, `js/main.js`). These are third-party/theme files and are not documented line by line. Project-specific CSS goes into `static/css/style.oth.css`, project JS into `static/js/main.js`. `media/` holds uploads (`fallback.png` is required, see `Post.banner`).

## 5. Permissions model

* Anonymous visitors: published pages, posts, menu items with visibility "Everyone"/"Logged-out".
* Logged-in users (via `/users/register/`): same as anonymous plus menu items for "Logged-in users". They are **not staff**: no admin access.
* Staff: admin access (permission based), can preview draft pages, see "Staff only" menu items. Staff can edit HTML that is output without escaping (`|safe`), so only grant staff to trusted people.

## 6. Tests

`python manage.py test` runs `pages/tests.py` (breadcrumbs, drafts) and `menus/tests.py` (builder save/validation/rendering).
