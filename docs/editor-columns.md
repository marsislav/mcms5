# Responsive columns in the editor (CKEditor 5)

The editor toolbar has a **„Колони“ (Columns)** dropdown (last button of the
toolbar). It inserts a layout block with **1, 2, 3, 4, 5, 6 or 12 columns**.
The columns are visible in the editor (dashed frames), can be filled with any
content (text, images, lists, tables…) and are **responsive** on the site.

## How to use

1. Put the cursor where the block should go (an empty paragraph, or after a paragraph).
2. Toolbar → **Колони ▾** → choose the number of columns.
3. The block is inserted after the current paragraph and the cursor lands in the
   first column. Click into any column to type.
4. A block inserted while the cursor is **inside a column** becomes a **nested** block.
5. To remove a block: select it (drag across it) and press Delete, or remove the
   `<div class="mcms-cols …">` in **Източник (Source)**.
6. Changing the number of columns of an existing block: insert a new block, move
   the content, delete the old one (or edit `mcms-cols-N` in Source and add/remove
   `<div class="mcms-col">` cells).

## Responsive behaviour (columns per row)

| Block | Desktop ≥1200px | Laptop 992–1199px | Tablet 576–991px | Mobile <576px |
|---|---|---|---|---|
| 1 column | 1 | 1 | 1 | 1 |
| 2 columns | 2 | 2 | 2 | 1 |
| 3 columns | 3 | 3 | 3 | 1 |
| 4 columns | 4 | 4 | 2 | 1 |
| 5 columns | 5 | 5 | 3 | 1 |
| 6 columns | 6 | 6 | 3 | 1 |
| 12 columns | 12 | 6 | 4 | 2 |

Columns have equal width (CSS grid) and a 24 px gap (12 px for 12 columns).
Cells that do not fit wrap onto the next row.

## HTML produced

```html
<div class="mcms-cols mcms-cols-3">
  <div class="mcms-col"><p>First</p></div>
  <div class="mcms-col"><p>Second</p></div>
  <div class="mcms-col"><p>Third</p></div>
</div>
```

It is stored as normal HTML in the page/post body. You can also write it by
hand in Source mode; the class `mcms-cols-N` must be one of 1, 2, 3, 4, 5, 6, 12.

## Files

| File | Role |
|---|---|
| `static/js/ckeditor-columns.js` | Adds the dropdown to the toolbar and inserts the block (documented in the file). Loaded in the admin by `Media.js` of `PageAdmin` (`pages/admin.py`) and `PostAdmin` (`posts/admin.py`). |
| `static/css/mcms-columns.css` | Grid + breakpoints (editable variables at the top). Used **both** in the editor (`CKEDITOR_5_CUSTOM_CSS` in `mcms5/settings.py`; adds the dashed frames only inside `.ck-content`) **and** on the site (`<link>` in `templates/layout.html` and `full-page.html`). |
| `mcms5/settings.py` | `CKEDITOR_5_CUSTOM_CSS = "css/mcms-columns.css"`; `htmlSupport` (already present) lets `div` + classes survive in the editor. |
| `templates/layout.html`, `full-page.html` | CSS `<link>`; the content card got `flex-grow-1` so the columns get the full width of the card (before, the card shrank to its content). |
| `pages/test_editor_columns.py` | Tests that assets are wired in. |

## How it works / limits

* `django-ckeditor-5` ships a **pre-built** bundle, so custom CKEditor plugins
  cannot be added. The script instead uses the bundle's public hook
  `ckeditorRegisterCallback(id, fn)` to receive each editor instance, adds a
  button to its toolbar and inserts HTML through the normal editor API
  (`editor.data.toModel(...)` + `model.insertContent`).
* Columns are normal `div`s, not a CKEditor "widget": there is no drag handle
  for the whole block (see step 5 above for removing it).
* To use the dropdown in another model's editor, add
  `class Media: js = ('js/ckeditor-columns.js',)` to its `ModelAdmin`.
* Different breakpoints / counts: edit the media queries in `mcms-columns.css`.
  A new count (e.g. 8) needs a `.mcms-cols-8` rule there **and** the number in
  `COUNTS`/`LABEL` in `ckeditor-columns.js`.
