# Content models: Page and Post

## Page (`pages.models.Page`) - static, hierarchical

| Field | Meaning |
|---|---|
| `title` | heading, `<title>`, breadcrumb label, default menu label |
| `slug` | ONE URL segment (no `/`) |
| `parent` | optional parent page -> sub-page |
| `body` | rich text (CKEditor 5), stored as HTML |
| `banner` | optional image (`media/pages/`) |
| `meta_description` | SEO text (max 160) - not output by templates yet |
| `is_published` | drafts: 404 for visitors, visible to staff |
| `show_in_menu`, `menu_order` | **legacy**, see menus.md |
| `created`, `updated` | automatic timestamps |

### URLs
`parent=services, slug=web` -> `/services/web/`. `full_path()` joins the slugs
of the ancestor chain; `get_absolute_url()` reverses `pages:detail`.

Resolution (`pages.views.page_detail`): for each URL segment find the page with
that slug **and** the previous page as parent; any miss -> 404.

### Rules
* Slug unique **per parent** (and unique among top-level pages) - DB constraints.
* A page cannot be its own ancestor (`Page.clean()` validates it in the admin).
* Deleting a parent deletes its children (`CASCADE`).
* A top-level page may not use a slug of a fixed route (`admin`, `posts`,
  `users`, `ckeditor5`, `media`, `about`) - the fixed route wins and the page
  becomes unreachable.

## Post (`posts.models.Post`) - blog article

| Field | Meaning |
|---|---|
| `title` | max 75 chars |
| `slug` | unique; URL is `/posts/<slug>` |
| `body` | rich text HTML |
| `date` | set automatically at creation (`auto_now_add`); list is ordered by it, oldest first |
| `banner` | image; default `media/fallback.png` |

## Rich text and security

`body` is output with `|safe`. The editor allows ALL HTML
(`htmlSupport` in settings, incl. raw `HtmlEmbed`). This is fine only while
authors are trusted staff; never expose these fields to public forms.
Uploads go to `media/uploads/` (staff only: `CKEDITOR_5_FILE_UPLOAD_PERMISSION`).
