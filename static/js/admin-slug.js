/* ============================================================================
 * admin-slug.js - fills the "Slug" field from the "Title" while you type
 * ============================================================================
 * Loaded by the admin of Page, Post and Category (title field: id_title or id_name) (``Media.js``).
 *
 *  - Works on the "add" form: the slug follows the title live.
 *  - The slug stays EDITABLE: as soon as you type in the slug field yourself the
 *    automatic filling stops (so your own value is never overwritten).
 *  - Clear the slug field to switch automatic filling back on.
 *  - On the "change" form of an existing object (slug already saved) nothing is
 *    changed automatically - changing a slug would break existing links.
 *
 * Transliteration = official Bulgarian "Streamlined System", identical to
 * ``mcms5/slugs.py`` (keep both tables in sync).
 * ========================================================================== */
(function () {
  'use strict';
  var MAP = {
    'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ж': 'zh', 'з': 'z',
    'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm', 'н': 'n', 'о': 'o', 'п': 'p',
    'р': 'r', 'с': 's', 'т': 't', 'у': 'u', 'ф': 'f', 'х': 'h', 'ц': 'ts', 'ч': 'ch',
    'ш': 'sh', 'щ': 'sht', 'ъ': 'a', 'ь': 'y', 'ю': 'yu', 'я': 'ya',
    'ы': 'y', 'э': 'e', 'ё': 'yo'
  };

  function slugify(text, max) {
    var s = String(text || '').toLowerCase().split('').map(function (c) { return MAP[c] !== undefined ? MAP[c] : c; }).join('');
    s = s.normalize('NFKD').replace(/[̀-ͯ]/g, '').replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '');
    return s.slice(0, max || 75).replace(/-+$/, '');
  }

  document.addEventListener('DOMContentLoaded', function () {
    var title = document.getElementById('id_title') || document.getElementById('id_name');
    var slug = document.getElementById('id_slug');
    if (!title || !slug) return;
    var max = parseInt(slug.getAttribute('maxlength'), 10) || 75;

    var auto = slug.value === '';            // only auto-fill when the slug is empty (new object)
    title.addEventListener('input', function () { if (auto) slug.value = slugify(title.value, max); });
    slug.addEventListener('input', function () { auto = slug.value === ''; });  // manual edit stops it; empty = on again
  });
})();
