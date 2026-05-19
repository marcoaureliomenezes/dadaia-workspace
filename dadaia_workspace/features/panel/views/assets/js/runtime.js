// runtime.js — Global runtime selector for the Dadaia Workspace Panel.
// PR5-D2 (FE): implements window.Runtime with get() / set() backed by localStorage.
//
// localStorage key: dadaia-panel-runtime  (per SPEC §NFR3)
// Valid values:      'claude' | 'codex'    (default: 'claude')
//
// On set(value):
//   1. Persist to localStorage.
//   2. Set document.documentElement.dataset.runtime for CSS targeting.
//   3. Fire CustomEvent('dadaia:runtime-change', { detail: { runtime: value } })
//      on document — sessions.js, agents.js and workflows.js subscribe.
//
// The inline script in index.py <head> initialises data-theme equivalently for
// the theme switcher.  This script mirrors that pattern but is file-based and
// loaded synchronously as the first <script src="..."> so that data-runtime is
// set before any tab-specific JS runs.

(function () {
  'use strict';

  var LS_KEY = 'dadaia-panel-runtime';
  var VALID_VALUES = ['claude', 'codex'];
  var DEFAULT_VALUE = 'claude';

  // ── Internal helpers ──────────────────────────────────────────────────────────

  function isValid(v) {
    return VALID_VALUES.indexOf(v) !== -1;
  }

  // ── Core API ──────────────────────────────────────────────────────────────────

  /**
   * Runtime.get() → 'claude' | 'codex'
   * Returns the current runtime selection from localStorage, or 'claude' if
   * none is set or the stored value is invalid.
   */
  function get() {
    var stored = null;
    try {
      stored = localStorage.getItem(LS_KEY);
    } catch (_) {
      // localStorage unavailable (private browsing, quota exceeded, etc.)
    }
    return isValid(stored) ? stored : DEFAULT_VALUE;
  }

  /**
   * Runtime.set(value)
   * Persists `value` to localStorage, updates document.documentElement.dataset.runtime,
   * then fires the 'dadaia:runtime-change' CustomEvent with { detail: { runtime: value } }.
   * Silently ignores invalid values.
   */
  function set(value) {
    if (!isValid(value)) { return; }
    try {
      localStorage.setItem(LS_KEY, value);
    } catch (_) {
      // Proceed even if localStorage write fails; DOM + event are still updated.
    }
    document.documentElement.dataset.runtime = value;
    try {
      document.dispatchEvent(
        new CustomEvent('dadaia:runtime-change', { detail: { runtime: value } })
      );
    } catch (_) {
      // CustomEvent not supported (very old browser); fail silently.
    }
  }

  // ── Initialise on script load ─────────────────────────────────────────────────
  // Mirror the theme-switcher pattern from views/index.py:60 — set data-runtime
  // immediately so that CSS selectors targeting [data-runtime="..."] resolve
  // before the first paint.

  (function _init() {
    var current = get();
    document.documentElement.dataset.runtime = current;
  })();

  // ── Expose as window.Runtime ──────────────────────────────────────────────────

  window.Runtime = {
    get: get,
    set: set,
  };

})();
