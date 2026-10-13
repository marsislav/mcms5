# Site search

Visitors search pages and posts at **`/search/?q=<words>`**. The search box is in
the sidebar of `templates/layout.html` and at the top of
`templates/full-page.html` (CMS pages have no sidebar). App: `search`.

## What is searched

| Content | Fields | Notes |
|---|---|---|
| Pages (`pages.Page`) | title, body, meta description | **published only** (drafts never appear, even for staff) |
| Posts (`posts.Post`) | title, body | all posts |

## How matching works

* The query is split into words: `web design` → `web`, `design`. A result must
  contain **all** words (AND), in any order and any field.
* **Case-insensitive in every language**, Cyrillic included
  (`софтуер` finds `Софтуер`). See *SQLite note* below.
* The body's HTML is stripped before matching, so markup (`<div>`, `class="mcms-col"`,
  link URLs…) never matches – only visible text.
* **Ranking:** per word: in the title +5, in the meta description +2, in the
  body +1 per occurrence (max 5). Best score first, ties → newest first.
* Every result shows the title (link), type (Page/Post) and a snippet around the
  first match with the words highlighted (`<mark>`). Snippet text is HTML-escaped.
* 10 results per page (`?page=2`). Words shorter than 2 characters are ignored;
  at most 5 words are used; at most 500 candidate rows per model are examined.

## Files

| File | Role |
|---|---|
| `search/views.py` | `search` view, query parsing, matching, ranking, snippets (constants at the top: `MIN_LENGTH`, `MAX_TERMS`, `PER_PAGE`, `SNIPPET`) |
| `search/urls.py` | route `/search/` (name `search`), included in `mcms5/urls.py` **before** the pages catch-all |
| `search/templates/search/results.html` | results page (extends `layout.html`) |
| `search/sqlite.py`, `search/apps.py` | Unicode-aware `LIKE` for SQLite (below) |
| `search/tests.py` | tests (Cyrillic, ranking, AND, drafts, markup, escaping, pagination) |

No migration and no new dependency.

## SQLite note

SQLite's `LIKE` ignores case only for ASCII, so Django's `icontains` would not
find "Софтуер" with "софтуер". On every new SQLite connection `search/sqlite.py`
replaces SQLite's `like()` with a Unicode-aware Python version. This also fixes the
admin's own search boxes. Other databases (PostgreSQL, MySQL) need nothing.

## Search from your own template

```django
<form action="{% url 'search' %}" method="get" role="search">
  <input type="search" name="q" value="{{ request.GET.q }}" placeholder="Search...">
  <button type="submit">Search</button>
</form>
```

## Scaling

This is a simple database search (SQL pre-filter + Python ranking), fine for
thousands of pages/posts. For much larger sites use database full-text search
(PostgreSQL `SearchVector`) or an external engine; the view's
`run_search(terms)` is the only function to replace.
