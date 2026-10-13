# Site settings (admin → Settings)

Site-wide options edited by an administrator, without touching code.
App: `siteconfig` · model: `SiteSettings` · admin: **Settings → Settings**
(`/admin/siteconfig/sitesettings/`).

The screen is split into **sections** shown as tabs. Currently there is one:
**General** and **Discussion** (comments - see [comments.md](comments.md)).

## General section – options

| Field | Type | Required | What it does / where it is used |
|---|---|---|---|
| **Site title** | text, max 120 | yes (default `mCMS 5`) | `<title>` of pages that don't set their own title, default hero heading (`page_title`), alt text of the logo, and the **text logo** when no logo is uploaded. |
| **Site description** | text, max 300 | no | `<meta name="description">` (shown by search engines). Falls back to the site title when empty. |
| **Logo** | image upload | no | Shown in the header (`.nav-brand`) and in the footer. Any image Pillow can read (JPG, PNG, GIF, WebP…), max **2 MB**. If empty, the site title is shown as text. |
| **Favicon** | file upload | no | `<link rel="icon">` (browser tab icon). Allowed: `.ico .png .svg .gif .jpg`, max **512 KB**. Recommended: square, ≥ 32×32 px. If empty, no icon tag is output. |
| **Admin e-mail** | e-mail | no | Main contact / administrator address. Shown (as a `mailto:` link) in the top bar and the footer; hidden when empty. Also available to code as `SiteSettings.load().admin_email` for notifications. |
| **Location** | text, max 255 | no | Address/place, e.g. `Str 28, Plovdiv, 4000, Bulgaria`. Shown in the top bar and the footer; hidden when empty. |
| **Date format** | choice | yes (default `j F Y`) | How dates are displayed (see below). |
| **Custom date format** | text | only if "Custom…" | Your own format string; the field is visible only when *Date format* = "Custom…". |
| **Time format** | choice | yes (default `H:i`) | How times are displayed (see below). |
| **Custom time format** | text | only if "Custom…" | Your own format string; visible only when *Time format* = "Custom…". |

Uploaded files are stored in `media/site/logo/` and `media/site/favicon/`.
When you **replace or clear** an image the old file is deleted from disk.
(Like all uploads, `/media/` is served by Django only when `DEBUG=True`; in
production the web server must serve it – see `deployment.md`.)

### Date and time formats

Formats use Django's `date` syntax (same as the `|date` template filter).

| Preset | Example |
|---|---|
| `j F Y` | 12 October 2026 |
| `d.m.Y` | 12.10.2026 |
| `d/m/Y` | 12/10/2026 |
| `m/d/Y` | 10/12/2026 |
| `Y-m-d` | 2026-10-12 |
| `F j, Y` | October 12, 2026 |
| `H:i` | 14:05 |
| `H:i:s` | 14:05:09 |
| `g:i A` / `g:i a` | 2:05 PM / 2:05 pm |

Common characters for **Custom…**: `d` day 01-31 · `j` day 1-31 · `m` month 01-12 ·
`n` month 1-12 · `M` Oct · `F` October · `y` 26 · `Y` 2026 · `H` hour 00-23 ·
`g` hour 1-12 · `i` minutes · `s` seconds · `A` AM/PM · `D` Mon · `l` Monday.
Full list: <https://docs.djangoproject.com/en/6.1/ref/templates/builtins/#date>.
A custom format is validated on save (it must not be empty).

Datetimes are converted to the project time zone (`TIME_ZONE` in `settings.py`)
before formatting.

## Using the settings in templates

The context processor `siteconfig.context_processors.site_settings` (enabled in
`settings.py`) adds the variable **`site`** to every template:

```django
{{ site.site_title }}
{{ site.site_description }}
{% if site.logo %}<img src="{{ site.logo.url }}" alt="{{ site.site_title }}">{% endif %}
{% if site.favicon %}<link rel="icon" href="{{ site.favicon.url }}">{% endif %}
{{ site.admin_email }}   {{ site.location }}
```

Format dates/times with the chosen formats via the filters in `site_tags`:

```django
{% load site_tags %}
{{ post.date|site_date }}       {# 12.10.2026 #}
{{ post.date|site_time }}       {# 14:05 #}
{{ post.date|site_datetime }}   {# 12.10.2026 14:05 #}
```

Already wired: `templates/layout.html` and `templates/full-page.html` (title,
meta description, favicon, logo, top-bar/footer e-mail and location) and the
post date in `posts/post_page.html` and `posts/posts_list.html`.

## Using the settings in Python

```python
from siteconfig.models import SiteSettings

s = SiteSettings.load()                 # always returns the single row (creates it with defaults)
s.site_title, s.admin_email, s.logo
s.format_date(dt); s.format_time(dt); s.format_datetime(dt)
s.date_format_string                    # effective format string, e.g. 'd.m.Y'
```

## How it works (files)

| File | Role |
|---|---|
| `siteconfig/models.py` | `SiteSettings` singleton model (always `pk=1`; `load()` creates it). Validation, old-file cleanup, format helpers. |
| `siteconfig/admin.py` | Admin integration: sections = `fieldsets`; the list screen redirects to the form; no second row / delete; stays on the form after Save. |
| `siteconfig/templates/admin/siteconfig/sitesettings/change_form.html` | Turns fieldsets into tabs; opens the tab that has an error; shows the *custom format* input only for "Custom…". |
| `siteconfig/context_processors.py` | Provides `site` to all templates (one query per request). |
| `siteconfig/templatetags/site_tags.py` | `site_date`, `site_time`, `site_datetime` filters. |
| `siteconfig/migrations/0001_initial.py` | Creates the table. The row is created on first use. |
| `siteconfig/tests.py` | Singleton, formats, validation, uploads, file cleanup, permissions, front-end output. |

Access: only logged-in **staff** users with the change permission for
*Settings* (superusers always). Nobody can delete the settings row.

## Adding a new section (e.g. "SEO", "Social")

1. Add the fields to `SiteSettings` (with a default or `blank=True`) and run
   `python manage.py makemigrations siteconfig && python manage.py migrate`.
2. In `siteconfig/admin.py` append a fieldset – it becomes a new tab automatically:

   ```python
   ('Social', {'description': 'Links to social networks.',
               'fields': ('facebook_url', 'linkedin_url')}),
   ```
3. Use the values in templates as `{{ site.facebook_url }}` and document them in
   the table above.

## Upgrading an existing site

Copy the `siteconfig/` folder and the changed templates, then run
`python manage.py migrate`. Until you save the form the defaults are used
(title `mCMS 5`, no logo/favicon/e-mail/location), so the previously
hard-coded address (`Str 28, Plovdiv…`) and e-mail (`me@gmail.bg`) in the
layout are **no longer shown** – enter them under *Settings → General*.

## Troubleshooting: `no such table: siteconfig_sitesettings`

The database does not have the new table yet. Run (from the folder with `manage.py`,
with the same settings/database the site uses):

```bash
python manage.py migrate
```

Until then the public site still works with default settings (the context processor
and the date filters fall back to defaults); only the admin *Settings* page needs the table.
