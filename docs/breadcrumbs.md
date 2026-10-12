# Breadcrumbs

Breadcrumbs are the trail under the hero banner:

```
 Home  >  Services  >  Web          (current page = last item, not a link)
```

## How it works (end to end)

Breadcrumbs are **not stored** anywhere and need **no setting**. A view
computes them for each request and hands them to the template as plain context
variables:

```
view  --render(request, 'x.html', {'page_title': ..., 'breadcrumbs': [...]})-->
      x.html  --{% extends "layout.html" %}-->
      layout.html  renders the hero heading and the <ol class="breadcrumb">
```

### The two context variables

| Variable | Type | Meaning | Used in |
|---|---|---|---|
| `page_title` | `str` | big heading in the hero banner. If missing: `mCMS 5` | `layout.html` (`<h2 class="title">`) |
| `breadcrumbs` | `list[(label, url)]` | the trail **after Home**. `[]` = home page | `layout.html` (`<ol class="breadcrumb">`) |

Rules implemented by `layout.html`:

1. **"Home"** (link to `/`) is always the first crumb - views never include it.
2. The **last** crumb is the current page: shown as text, `class="active"`,
   `aria-current="page"`. Its `url` is ignored, so `''` is fine.
3. All crumbs before the last one are links.
4. If `breadcrumbs` is empty/missing, only "Home" is shown, as the active item.
   (A view that forgets to pass the variable therefore shows "Home" only - not an error.)

## Where each page type gets its crumbs

| URL | View | `page_title` | `breadcrumbs` | Result |
|---|---|---|---|---|
| `/` | `mcms5.views.homepage` | `Home` | `[]` | Home |
| `/about/` | `mcms5.views.about` | `About` | `[('About','/about/')]` | Home > About |
| `/posts/` | `posts.views.posts_list` | `Blog` | `[('Blog', reverse('posts:list'))]` | Home > Blog |
| `/posts/<slug>` | `posts.views.post_page` | post title | `[('Blog','/posts/'), (post.title,'')]` | Home > Blog > Post |
| `/a/b/` (CMS page) | `pages.views.page_detail` | page title | `page.get_breadcrumbs()` | Home > A > B |

### CMS pages: `Page.get_breadcrumbs()` (`pages/models.py`)

Walks the `parent` chain from the page up to the top-level page, builds
`(title, get_absolute_url())` for each, and reverses the list so the top-most
ancestor comes first. Every ancestor is therefore a working link, e.g. for
`/services/web/`:

```python
[('Services', '/services/'), ('Web', '/services/web/')]
```

It depends on: `Page.parent` (the tree), `Page.title`, `Page.get_absolute_url()`
(which uses `Page.full_path()` and the `pages:detail` route). A cycle guard
(`seen` set) prevents infinite loops on bad data. Cost: one query per ancestor.

> Note: `/services/` is only a working link if a page with slug `services`
> exists - which it does, because it is the parent in the tree.

## Adding breadcrumbs to a NEW view

```python
from django.shortcuts import render
from django.urls import reverse

def product(request, slug):
    product = get_object_or_404(Product, slug=slug)
    return render(request, 'shop/product.html', {
        'product': product,
        'page_title': product.name,
        'breadcrumbs': [
            ('Shop', reverse('shop:list')),   # a link
            (product.name, ''),               # current page (url ignored)
        ],
    })
```

The template `shop/product.html` just has to start with
`{% extends "layout.html" %}` - nothing else is needed.

## Styling

* Markup is Bootstrap's breadcrumb: `<nav aria-label="breadcrumb"><ol class="breadcrumb"><li class="breadcrumb-item">`.
* Theme CSS: `static/css/style.css` -> section "16.0 Breadcrumb CSS", selectors
  `.breadcumb--con .breadcrumb ...` and `.breadcumb-area` (hero). The theme spells it
  "breadcumb" (missing "r"); keep that spelling when editing the CSS.
* Separator character between crumbs: `.breadcrumb-item + .breadcrumb-item::before`.
* Font Awesome icon `fa fa-home` is used for Home (`font-awesome.min.css`).

## Known limitation

The hero background image (`img/bg-img/12.jpg`) is referenced by a relative
path and the file is not in `static/`, so the banner currently has no picture.
Add the file under `static/img/bg-img/` and change the inline style in
`layout.html` to `url('{% static "img/bg-img/12.jpg" %}')`.

## Tests

`pages/tests.py::BreadcrumbTests` checks the model method and the rendered HTML
for home, about, blog, a post and a nested page.
