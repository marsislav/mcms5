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
| `categories` | many-to-many to `Category` (optional) |
| `related` | hand-picked related posts (many-to-many to itself, symmetrical) |

## Category (`posts.models.Category`)

| Field | Meaning |
|---|---|
| `name` | unique label |
| `slug` | unique; URL is `/posts/category/<slug>` (auto-filled from the name in the admin) |

* Sidebar box "Categories" (`{% categories_widget %}`) lists only categories that have posts, with counts.
* Post page: "Related posts" shows the hand-picked ones; if none are picked it falls back to posts sharing a category (max 4, newest first) - `Post.related_posts()`.
* Sidebar box "Recent Posts" (`{% recent_posts_widget 5 %}`) shows the newest posts; the number is the tag argument in `templates/layout.html`.
* Template tags: `posts/templatetags/posts_tags.py`.

## Rich text and security

`body` is output with `|safe`. The editor allows ALL HTML
(`htmlSupport` in settings, incl. raw `HtmlEmbed`). This is fine only while
authors are trusted staff; never expose these fields to public forms.
Uploads go to `media/uploads/` (staff only: `CKEDITOR_5_FILE_UPLOAD_PERMISSION`).


## Slug auto-fill

In the admin the slug is filled from the title and stays editable; an empty slug is generated on save and made unique. Details: [slugs.md](slugs.md).

## Trash (soft delete)

Deleting a **Post, Page or Category** (single delete or the bulk "Delete selected" action) moves it to the Trash instead of removing it. It disappears from the site, search, menus, sidebar widgets and the normal admin lists.

* Admin -> **Trash: Posts / Trash: Pages / Trash: Categories** list the deleted items (newest deletion first).
  Actions: **Restore selected** and **Delete permanently selected** (asks for confirmation; irreversible).
* Deleting a page also trashes its sub-pages; restoring the page restores exactly those sub-pages (ones trashed earlier on their own stay in the Trash). A sub-page can't be restored while its parent is still in the Trash.
* A menu item linking to a trashed page/post is hidden and shows as "missing" in the menu builder; it works again after the restore.
* The slug of a trashed item stays reserved, so a new item can't take it (restore would conflict). Delete it permanently to free the slug.
* Code: `mcms5/softdelete.py` (`Model.objects` = not deleted, `Model.all_objects` = everything, `obj.delete()/restore()/hard_delete()`), admin helpers in `mcms5/softdelete_admin.py`. Reverse relations (`category.posts`, `post.related`) include trashed rows - use `.alive()`.
