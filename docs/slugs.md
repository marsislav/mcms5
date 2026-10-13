# Slugs (URL names) of pages and posts

The **Slug** is the URL part of a page/post: page `services` → `/services/`,
post `first-post` → `/posts/first-post`.

## Behaviour in the admin (Pages and Posts)

| Situation | What happens |
|---|---|
| New page/post: you type the **Title** | The slug is filled live from the title (`Уеб дизайн` → `ueb-dizayn`). |
| You want a different slug | Just edit the slug field. From then on the title no longer changes it. |
| You clear the slug field | Automatic filling is switched on again. |
| You save with an **empty** slug | The server builds it from the title and makes it unique: `about`, `about-2`, `about-3`… (for pages: unique among pages with the same parent). |
| You type a slug that is already taken | Normal error "already exists" – your value is never changed silently. |
| Editing an **existing** page/post | The slug is **not** changed automatically (that would break links). Change it by hand if needed. |

Slugs contain only `a-z`, `0-9` and `-`, max 75 characters.

## Transliteration

Cyrillic is converted with the official Bulgarian "Streamlined System"
(Закон за транслитерацията, 2009):

| | | | | | | | |
|---|---|---|---|---|---|---|---|
| а a | б b | в v | г g | д d | е e | ж zh | з z |
| и i | й y | к k | л l | м m | н n | о o | п p |
| р r | с s | т t | у u | ф f | х h | ц ts | ч ch |
| ш sh | щ sht | ъ a | ь y | ю yu | я ya | | |

Example: `Щастие и Ъгъл 2026!` → `shtastie-i-agal-2026`. Latin accents are
removed, other characters become `-`. A title with no usable character gives
`page` / `post` (then `-2`, … if taken).

## Files

| File | Role |
|---|---|
| `static/js/admin-slug.js` | live filling while typing; stops on manual edit (loaded by `Media.js` of `PageAdmin` and `PostAdmin`) |
| `mcms5/slugs.py` | `slugify_bg()` and `unique_slug()` – the same table as the JS (**keep both in sync**) |
| `pages/admin.py` → `PageAdminForm` | slug not required; empty → generated, unique per parent |
| `posts/admin.py` → `PostAdminForm` | slug not required; empty → generated, unique |
| `mcms5/tests_slugs.py` | tests |

No migration. To use it for another model add a form like `PostAdminForm` and
`class Media: js = ('js/admin-slug.js',)` (the page needs fields with ids `id_title` and `id_slug`).
