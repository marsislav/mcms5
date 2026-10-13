# Templates and front end

## Template inheritance

```
templates/layout.html            <- base: header, hero + breadcrumbs, content card, sidebar, footer
   ^ {% extends "layout.html" %}
   |- templates/home.html
   |- templates/about.html
   |- pages/templates/pages/page.html
   |- posts/templates/posts/posts_list.html
   |- posts/templates/posts/post_page.html
   '- users/templates/users/register.html
```

A child template must start with `{% extends "layout.html" %}` (this must be
the first tag - put documentation comments after it).

### Blocks provided by `layout.html`

| Block | Where | Default |
|---|---|---|
| `title` | `<title>` | `mCMS 5` |
| `image` | thumbnail column of the content card | empty |
| `content` | body of the content card | empty |

### Context variables read by `layout.html`

| Variable | Source | Effect |
|---|---|---|
| `page_title` | view | hero heading (default `mCMS 5`) |
| `breadcrumbs` | view | breadcrumb trail, see [breadcrumbs.md](breadcrumbs.md) |
| `request` | `request` context processor | used by `{% render_menu %}` |

Template tags: `{% load static menu_tags %}`.

## Template lookup

`TEMPLATES['DIRS'] = ['templates']` (project-wide) and `APP_DIRS = True`
(each app's `templates/`). Namespacing convention: `<app>/templates/<app>/file.html`.

## Static files (`static/`)

| File | Role |
|---|---|
| `css/style.css` | theme main CSS (breadcrumb styles in section 16) |
| `css/style.oth.css` | **your** project overrides |
| `css/bootstrap.min.css`, `animate.css`, `classy-nav.css`, `owl.carousel.min.css`, `magnific-popup.css`, `font-awesome.min.css` | vendor / theme CSS |
| `js/jquery.min.js`, `popper.min.js`, `bootstrap.min.js` | vendor JS (load order matters) |
| `js/mcms.bundle.js` | bundled theme plugins |
| `js/default-assets/active.js` | theme initialisation (menu, preloader...) |
| `js/main.js` | **your** custom JS (stub) |

Scripts are loaded with `defer` at the end of `<body>`.

## Placeholders still in `layout.html`

These are static demo content from the theme: top bar contact/social links,
"Booking Now" button, second blog card, pagination, sidebar widgets, footer
text/hours/newsletter. Several `./img/...` URLs point to files that are not in
`static/`, so those images are broken. Replace them gradually with dynamic data
or `{% static %}` references.

## Escaping

Django escapes `{{ variables }}` automatically. Exceptions (`|safe`) are only
`page.body` and `post.body`, which contain editor HTML.


## Site settings in templates

`layout.html` / `full-page.html` read the variable `site` (admin → Settings): title, meta description, favicon, logo, e-mail, location. Date filters: `{% load site_tags %}` then `|site_date`, `|site_time`, `|site_datetime`. Details: [settings.md](settings.md).


## Search box

`layout.html` (sidebar) and `full-page.html` (top of content) contain a GET form to `{% url 'search' %}` with the field `q`. Results: `search/templates/search/results.html`. See [search.md](search.md).
