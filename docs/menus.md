# Menus

Navigation menus are data, edited in the admin with a drag-and-drop builder and
rendered in templates with one tag.

## Concepts

* **Menu** - a named container. Default menus (created by migration 0002):
  `primary` (site header) and `footer`.
* **MenuItem** - one entry. Types: **Page**, **Post**, **Custom link**.
  Items are nested through `parent`; `order` is the position in the whole
  depth-first list.

```
Menu 'primary'
 |- Home            custom '/'
 |- Services        page
 |   '- Web          page (child of Services)
 '- Blog            post
```

## Using a menu in a template

```django
{% load menu_tags %}
{% render_menu 'primary' %}
```

* Needs the `request` context processor (enabled in settings).
* Unknown slug -> renders nothing (no error).
* Output (simplified):

```html
<ul id="nav">                                  <!-- Menu.ul_id / Menu.ul_class -->
  <li class="menu-item current-menu-item active"><a href="/" aria-current="page">Home</a></li>
  <li class="menu-item menu-item-has-children"><a href="/services/">Services</a>
    <ul class="dropdown">                      <!-- Menu.submenu_class -->
      <li class="menu-item"><a href="/services/web/">Web</a></li>
    </ul>
  </li>
</ul>
```

### CSS classes added to each `<li>`

| Class | When |
|---|---|
| `menu-item` | always |
| `menu-item-has-children` | the item has visible sub-items |
| `current-menu-item` + `active` | its URL equals the page being viewed |
| `current-menu-ancestor` + `active` | one of its descendants is the current page |
| custom classes | whatever the editor typed in "CSS classes (on `<li>`)" |

URL matching ignores `?query`, `#fragment` and the trailing slash; only
internal links (starting with `/`) can be "current".

### When an item is NOT rendered

1. "Show" (`is_active`) is off.
2. It points to a page/post that was deleted ("missing").
3. Its **visibility** does not allow the visitor: Everyone / Logged-out only /
   Logged-in only / Staff only.
4. It links to an **unpublished page** and the visitor is not staff.
5. Its parent was hidden for any reason above (the whole branch disappears).

## The builder (admin)

Open *Admin -> Menus -> (menu) -> Edit structure* or
`/admin/menus/menu/<id>/builder/`.

* Left column: add Pages, Posts, or a Custom link.
* Right column: the tree. Drag a row; drop on the **top/bottom edge** to place
  before/after, on the **middle** to make it a sub-item. Or use the arrow
  buttons. `▾` opens the item's settings (title, URL, classes, id, title
  attribute, rel, visibility, new window, show).
* Nothing is saved until **Save menu**. Max nesting: `menus.builder.MAX_DEPTH` (5).

### Data flow

```
DB (MenuItem rows)
   | builder.serialize_items(menu)            flat list + depth
   v
builder_view -> template: {{ builder_data|json_script:"mb-data" }}
   v
JavaScript `items` array (user edits)
   | fetch POST {items:[...]}  + X-CSRFToken   (Save)
   v
MenuAdmin.builder_save -> builder.save_items(menu, rows)   (atomic transaction)
   | success: JSON {ok:true, items:[...]}  (new ids)   | error: 400 {ok:false, error:"..."}
   v
DB updated (rows updated/created, missing ones deleted)
```

### JSON row format

```json
{"id": 12, "type": "page", "object_id": 3, "label": "", "url": "",
 "title_attr": "", "new_tab": false, "css_classes": "btn", "link_classes": "",
 "element_id": "menu-services", "rel": "", "visibility": "all",
 "is_active": true, "depth": 1}
```

`id` = existing item (null for new). `depth` = nesting level (0 = top).

### Validation (server side, `menus/builder.py`) - nothing is saved if any row fails

* `type` must be page / post / custom.
* page/post: the target must still exist.
* custom: URL required and must start with `/`, `#`, `?`, `http://`, `https://`,
  `mailto:` or `tel:` (blocks `javascript:` etc.); a title is required.
* element id: no whitespace.
* `depth` is clamped: cannot be negative, deeper than `MAX_DEPTH`, or skip a level.
* An `id` that does not belong to this menu creates a new item instead.
* Items not in the payload are deleted (with their children).
* Text fields are cut to the model's `max_length`.

### Permissions

The builder URLs are staff-only (`admin_view`) and also require the Django
permission *change menu*. CSRF protection is active.

## Page/post deleted?

`MenuItem.page` / `.post` use `on_delete=SET_NULL`: the menu item survives, is
hidden on the site, and shows a red "target missing" badge in the builder so you can remove it.

## Legacy: `Page.show_in_menu` / `menu_order`

Used only once by migration 0002 to seed the first menu. Changing them later
does **not** change the menu.

## Adding another menu

1. Admin -> Menus -> Add menu (name + slug, optional classes). You are taken to the builder.
2. Add `{% render_menu 'your-slug' %}` where it should appear.
