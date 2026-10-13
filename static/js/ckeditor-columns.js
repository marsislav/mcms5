/* ============================================================================
 * ckeditor-columns.js - "Columns" dropdown for the CKEditor 5 toolbar (admin)
 * ============================================================================
 * Adds a "Колони / Columns" button at the end of every CKEditor toolbar.
 * Choosing 1, 2, 3, 4, 5, 6 or 12 inserts a responsive column block:
 *
 *     <div class="mcms-cols mcms-cols-N"> N x <div class="mcms-col"><p></p></div> </div>
 *
 * The look/responsiveness comes from static/css/mcms-columns.css (loaded in the
 * editor via CKEDITOR_5_CUSTOM_CSS and on the site via layout.html).
 *
 * Why not a real CKEditor plugin? django-ckeditor-5 ships a PRE-BUILT bundle;
 * custom plugins cannot be added without rebuilding it. Instead we use the
 * bundle's public hook ``ckeditorRegisterCallback(id, fn)`` that gives us each
 * editor instance, and use its normal API (``editor.model`` / ``editor.data``).
 * The HTML survives because "htmlSupport" in settings.py allows div + classes.
 *
 * Loaded by ``Media.js`` of PageAdmin and PostAdmin (after the editor bundle).
 * ========================================================================== */
(function () {
  'use strict';

  var COUNTS = [1, 2, 3, 4, 5, 6, 12];
  var LABEL = {1: '1 колона', 2: '2 колони', 3: '3 колони', 4: '4 колони', 5: '5 колони', 6: '6 колони', 12: '12 колони'};

  /** Static HTML for a block with n columns (one empty paragraph per column). */
  function columnsHtml(n) {
    var cell = '<div class="mcms-col"><p>&nbsp;</p></div>';
    return '<div class="mcms-cols mcms-cols-' + n + '">' + new Array(n + 1).join(cell) + '</div>';
  }

  /** Insert the block after the current paragraph (or in place of an empty one). */
  function insertColumns(editor, n) {
    var model = editor.model;
    var html = columnsHtml(n);
    var fragment = editor.data.toModel(editor.data.processor.toView(html));
    model.change(function (writer) {
      var sel = model.document.selection;
      var block = sel.getFirstPosition().parent;
      var isEmptyPara = block.is('element', 'paragraph') && block.isEmpty;
      var range;
      if (block.is('element') && !block.is('rootElement') && !isEmptyPara) {
        range = model.insertContent(fragment, writer.createPositionAfter(block));
      } else {
        range = model.insertContent(fragment);
      }
      // put the cursor into the first column so the user can start typing at once
      var items = range.getItems();
      for (var it = items.next(); !it.done; it = items.next()) {
        if (it.value.is('element', 'paragraph')) { writer.setSelection(it.value, 'in'); break; }
      }
    });
    editor.editing.view.focus();
  }

  var openMenu = null;                       // the currently open dropdown (only one at a time)
  function closeMenu() {
    if (openMenu) { openMenu.remove(); openMenu = null; }
  }
  document.addEventListener('mousedown', function (e) {
    if (openMenu && !openMenu.contains(e.target) && !e.target.closest('.mcms-cols-btn')) closeMenu();
  });
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape') closeMenu(); });
  window.addEventListener('resize', closeMenu);

  function openDropdown(editor, button) {
    closeMenu();
    var menu = document.createElement('div');
    menu.className = 'mcms-cols-menu';
    COUNTS.forEach(function (n) {
      var item = document.createElement('button');
      item.type = 'button';
      item.className = 'mcms-cols-item';
      var preview = '<span class="mcms-cols-preview">' + new Array(n + 1).join('<i></i>') + '</span>';
      item.innerHTML = preview + '<span>' + LABEL[n] + '</span>';
      item.addEventListener('click', function () { closeMenu(); insertColumns(editor, n); });
      menu.appendChild(item);
    });
    document.body.appendChild(menu);
    var r = button.getBoundingClientRect();
    menu.style.top = (r.bottom + 4) + 'px';
    menu.style.left = Math.min(r.left, window.innerWidth - menu.offsetWidth - 8) + 'px';
    openMenu = menu;
  }

  /** Add the button to one editor's toolbar. */
  function addButton(editor) {
    var toolbar = editor.ui.view.toolbar.element;
    var items = toolbar && toolbar.querySelector('.ck-toolbar__items');
    if (!items || items.querySelector('.mcms-cols-btn')) return;

    var sep = document.createElement('span');
    sep.className = 'ck ck-toolbar__separator';
    var btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'ck ck-button ck-off ck-button_with-text mcms-cols-btn';
    btn.title = 'Вмъкни колони (адаптивни)';
    btn.innerHTML = '<span class="ck ck-button__label">&#9707; Колони &#9662;</span>';
    // mousedown keeps the editor selection (a click would blur the editable first)
    btn.addEventListener('mousedown', function (e) { e.preventDefault(); });
    btn.addEventListener('click', function () {
      if (openMenu) { closeMenu(); } else { openDropdown(editor, btn); }
    });
    items.appendChild(sep);
    items.appendChild(btn);
  }

  /** Hook into every editor on the page (also editors that are created later). */
  function init() {
    Array.prototype.forEach.call(document.querySelectorAll('textarea.django_ckeditor_5'), function (ta) {
      if (ta.id.indexOf('__prefix__') !== -1) return;
      if (window.editors && window.editors[ta.id]) { addButton(window.editors[ta.id]); return; }
      if (window.ckeditorRegisterCallback) window.ckeditorRegisterCallback(ta.id, addButton);
    });
  }
  // The editor bundle also starts on DOMContentLoaded (registered earlier), but creates
  // editors asynchronously, so registering the callback here is still in time.
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init); else init();

  // Dropdown styles (kept here so this single file is all the admin needs).
  var css = document.createElement('style');
  css.textContent =
    '.mcms-cols-btn{font-weight:600}' +
    '.mcms-cols-menu{position:fixed;z-index:100000;background:#fff;border:1px solid #c4c4c4;border-radius:4px;' +
    'box-shadow:0 4px 14px rgba(0,0,0,.2);padding:4px;min-width:200px}' +
    '.mcms-cols-item{display:flex;align-items:center;gap:10px;width:100%;background:none;border:0;padding:6px 8px;' +
    'cursor:pointer;font-size:13px;text-align:left;border-radius:3px;color:#222}' +
    '.mcms-cols-item:hover{background:#e6f1fb}' +
    '.mcms-cols-preview{display:flex;gap:2px;width:72px;height:16px;flex:none}' +
    '.mcms-cols-preview i{flex:1;background:#7aa7d6;border-radius:1px;min-width:2px}';
  document.head.appendChild(css);
})();
