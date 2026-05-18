(function () {
  'use strict';

  // ── Constants ─────────────────────────────────────────────────────────────
  var STORAGE_KEY = 'dadaia-panel-theme';
  var THEMES = ['mint', 'sage', 'warm'];
  var THEME_LABELS = { mint: 'Mint', sage: 'Sage', warm: 'Warm' };

  // ── Apply theme ───────────────────────────────────────────────────────────
  // Sets data-theme on <html> and persists to localStorage.
  function applyTheme(theme) {
    if (THEMES.indexOf(theme) === -1) { return; }
    document.documentElement.dataset.theme = theme;
    localStorage.setItem(STORAGE_KEY, theme);
    // Update aria-checked on menu items
    var items = document.querySelectorAll('[data-theme-value]');
    items.forEach(function (item) {
      var isChecked = item.getAttribute('data-theme-value') === theme;
      item.setAttribute('aria-checked', isChecked ? 'true' : 'false');
    });
  }

  // ── Close dropdown ────────────────────────────────────────────────────────
  function closeMenu(btn, menu) {
    menu.hidden = true;
    btn.setAttribute('aria-expanded', 'false');
  }

  // ── Open dropdown ─────────────────────────────────────────────────────────
  function openMenu(btn, menu) {
    menu.hidden = false;
    btn.setAttribute('aria-expanded', 'true');
    // Focus the currently checked item, or the first item
    var checked = menu.querySelector('[aria-checked="true"]');
    var first = menu.querySelector('[role="menuitemradio"]');
    var toFocus = checked || first;
    if (toFocus) { toFocus.focus(); }
  }

  // ── Init ──────────────────────────────────────────────────────────────────
  function init() {
    var btn = document.getElementById('theme-btn');
    var menu = document.getElementById('theme-menu');
    if (!btn || !menu) { return; }

    // Reflect the current theme in aria-checked on initial load
    var current = document.documentElement.dataset.theme || 'mint';
    var items = menu.querySelectorAll('[role="menuitemradio"]');
    items.forEach(function (item) {
      var isChecked = item.getAttribute('data-theme-value') === current;
      item.setAttribute('aria-checked', isChecked ? 'true' : 'false');
    });

    // ── Button click: toggle dropdown ───────────────────────────────────────
    btn.addEventListener('click', function (e) {
      e.stopPropagation();
      if (!menu.hidden) {
        closeMenu(btn, menu);
      } else {
        openMenu(btn, menu);
      }
    });

    // ── Button keyboard: Enter/Space open; Escape close ─────────────────────
    btn.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        if (!menu.hidden) {
          closeMenu(btn, menu);
        } else {
          openMenu(btn, menu);
        }
      } else if (e.key === 'Escape') {
        e.preventDefault();
        closeMenu(btn, menu);
        btn.focus();
      } else if (e.key === 'ArrowDown') {
        e.preventDefault();
        if (menu.hidden) { openMenu(btn, menu); }
        var first = menu.querySelector('[role="menuitemradio"]');
        if (first) { first.focus(); }
      }
    });

    // ── Menu item click: select theme ────────────────────────────────────────
    items.forEach(function (item) {
      item.addEventListener('click', function () {
        var theme = item.getAttribute('data-theme-value');
        applyTheme(theme);
        closeMenu(btn, menu);
        btn.focus();
      });
    });

    // ── Menu item keyboard: Enter/Space select; Escape close; arrows cycle ───
    var itemList = Array.prototype.slice.call(items);
    itemList.forEach(function (item, idx) {
      item.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          var theme = item.getAttribute('data-theme-value');
          applyTheme(theme);
          closeMenu(btn, menu);
          btn.focus();
        } else if (e.key === 'Escape') {
          e.preventDefault();
          closeMenu(btn, menu);
          btn.focus();
        } else if (e.key === 'ArrowDown') {
          e.preventDefault();
          var next = itemList[(idx + 1) % itemList.length];
          if (next) { next.focus(); }
        } else if (e.key === 'ArrowUp') {
          e.preventDefault();
          var prev = itemList[(idx - 1 + itemList.length) % itemList.length];
          if (prev) { prev.focus(); }
        } else if (e.key === 'Home') {
          e.preventDefault();
          itemList[0].focus();
        } else if (e.key === 'End') {
          e.preventDefault();
          itemList[itemList.length - 1].focus();
        }
      });
    });

    // ── Click outside: close dropdown ────────────────────────────────────────
    document.addEventListener('click', function (e) {
      if (!btn.contains(e.target) && !menu.contains(e.target)) {
        if (!menu.hidden) { closeMenu(btn, menu); }
      }
    });

    // ── Escape from anywhere closes the menu ────────────────────────────────
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && !menu.hidden) {
        closeMenu(btn, menu);
        btn.focus();
      }
    });
  }

  // Run after DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
