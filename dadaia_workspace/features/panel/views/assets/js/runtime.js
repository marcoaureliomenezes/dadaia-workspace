// runtime.js — Global runtime selector for the Dadaia Workspace Panel.
// PR5-D2 (FE): implements window.Runtime with get() / set() backed by localStorage.
//
// localStorage key: dadaia-panel-runtime  (per SPEC §NFR3)
// Valid values:      'claude' | 'codex' | 'pi'    (default: 'claude')
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
  var VALID_VALUES = ['claude', 'codex', 'pi'];
  var DEFAULT_VALUE = 'claude';

  // ── Internal helpers ──────────────────────────────────────────────────────────

  function isValid(v) {
    return VALID_VALUES.indexOf(v) !== -1;
  }

  // ── Core API ──────────────────────────────────────────────────────────────────

  /**
   * Runtime.get() → 'claude' | 'codex' | 'pi'
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

  // ── Wire topbar buttons after DOM is ready ────────────────────────────────────
  // Accessible keyboard nav: Arrow keys move focus between Claude / Codex buttons
  // within the radiogroup (ARIA pattern for radio groups).

  function _updateButtonStates(activeValue) {
    var btns = document.querySelectorAll('.runtime-switcher [data-runtime-value]');
    btns.forEach(function (btn) {
      var isActive = btn.getAttribute('data-runtime-value') === activeValue;
      btn.setAttribute('aria-checked', isActive ? 'true' : 'false');
      btn.setAttribute('tabindex', isActive ? '0' : '-1');
    });
  }

  function _wireRuntimeSwitcher() {
    var switchers = document.querySelectorAll('.runtime-switcher');
    if (!switchers.length) { return; }

    switchers.forEach(function (switcher) {
      var btns = switcher.querySelectorAll('[data-runtime-value]');
      if (!btns.length) { return; }

      // Set initial state reflecting current runtime
      _updateButtonStates(get());

      btns.forEach(function (btn) {
        // Click handler
        btn.addEventListener('click', function () {
          var value = btn.getAttribute('data-runtime-value');
          if (value) {
            set(value);
            _updateButtonStates(value);
          }
        });

        // Arrow key navigation within the radiogroup (ARIA radio group pattern)
        btn.addEventListener('keydown', function (e) {
          var allBtns = Array.prototype.slice.call(
            switcher.querySelectorAll('[data-runtime-value]')
          );
          var idx = allBtns.indexOf(btn);
          if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
            e.preventDefault();
            var next = allBtns[(idx + 1) % allBtns.length];
            if (next) {
              var nextValue = next.getAttribute('data-runtime-value');
              set(nextValue);
              _updateButtonStates(nextValue);
              next.focus();
            }
          } else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
            e.preventDefault();
            var prev = allBtns[(idx - 1 + allBtns.length) % allBtns.length];
            if (prev) {
              var prevValue = prev.getAttribute('data-runtime-value');
              set(prevValue);
              _updateButtonStates(prevValue);
              prev.focus();
            }
          }
        });
      });
    });

    // Keep ALL button states in sync when runtime changes via any mechanism.
    // Registered once (outside the per-switcher loop) to avoid duplicate listeners.
    document.addEventListener('dadaia:runtime-change', function (e) {
      var runtime = e.detail && e.detail.runtime ? e.detail.runtime : get();
      _updateButtonStates(runtime);
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', _wireRuntimeSwitcher);
  } else {
    _wireRuntimeSwitcher();
  }

})();
