// kanban.js — Kanban board tab UI (swimlanes, 4-stage lifecycle columns, auto-refresh)
// panel-kanban-v1 K-2 (FE) — updated for §7 canonical lifecycle columns (T-016-P13)
//
// Depends on: window.authedFetch() and window.escHtml() defined in core.js (loaded before this).
//
// API contract (SPEC §3 K-1 response schema — normative):
//   GET /api/kanban
//     → { generated_at: "<ISO>", swimlanes: [ SwimLane, ... ] }
//   SwimLane: { context: "<name>", columns: { backlog: [...], release_def: [...],
//               impl_review: [...], closure: [...] } }
//   SessionCard: { session_id, mode, release, runtime, pid, last_seen_at, is_stale }
//
// Column label map (canonical §7 SDD lifecycle):
//   backlog      → "Backlog"                (READ sessions)
//   release_def  → "Release Definition"     (SPEC sessions)
//   impl_review  → "Implementation + Review" (BOUND_IMPLEMENTATION + BOUND_REVIEW sessions, combined)
//   closure      → "Closure"               (closure-phase sessions; present-but-empty until supported)
//
// Behaviour summary:
//   - On DOMContentLoaded: locate #section-kanban or #ops-subsection-kanban; if absent, exit (no-op).
//   - fetchKanban() calls GET /api/kanban via authedFetch.
//   - renderBoard(data): renders lanes and columns into #kanban-board.
//   - XOR lock dimming is RETIRED (impl and review share one combined column).
//   - Per-card stale indicator preserved: data-stale="true" on stale cards.
//   - Empty column → placeholder div with data-testid="kanban-empty-placeholder" + aria-hidden="true".
//   - Empty lane → visible italic "No active sessions" (announced by screen reader).
//   - Empty board → centred "No Spec Context Projects available".
//   - Poll for updates every 10 s (same interval as sessions.js); checks document.hidden.
//   - window.Kanban public API: isLoaded(), load(), reload().

(function () {
  'use strict';

  // ── Constants ──────────────────────────────────────────────────────────────
  var AUTO_REFRESH_MS = 10000;

  var COLUMN_LABELS = {
    backlog:     'Backlog',
    release_def: 'Release Definition',
    impl_review: 'Implementation + Review',
    closure:     'Closure',
  };

  // Concurrency badges per column (undefined = no badge).
  var COLUMN_BADGES = {
    release_def: '≤2',  // ≤2 concurrent spec sessions
    impl_review: '×2',  // ×2 (impl + review combined)
  };

  var COLUMN_ORDER = ['backlog', 'release_def', 'impl_review', 'closure'];

  // ── Module state ───────────────────────────────────────────────────────────
  var _loaded = false;
  var _refreshTimer = null;

  // ── HTML escape (prefer window.escHtml set by core.js; fallback inline) ───
  function esc(s) {
    if (window.escHtml) { return window.escHtml(String(s == null ? '' : s)); }
    return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
    });
  }

  // ── Relative age formatter ─────────────────────────────────────────────────
  function fmtAge(iso) {
    if (!iso) { return '—'; }
    var then = new Date(iso);
    if (isNaN(then.getTime())) { return '—'; }
    var diffMs = Date.now() - then.getTime();
    var diffSec = Math.floor(diffMs / 1000);
    if (diffSec < 60) { return 'just now'; }
    var diffMin = Math.floor(diffSec / 60);
    if (diffMin < 60) { return diffMin + 'm ago'; }
    var diffH = Math.floor(diffMin / 60);
    if (diffH < 24) { return diffH + 'h ago'; }
    var diffD = Math.floor(diffH / 24);
    return diffD + 'd ago';
  }

  // ── Update "last updated" badge ────────────────────────────────────────────
  function updateLastUpdated() {
    var el = document.getElementById('kanban-last-updated');
    if (!el) { return; }
    el.textContent = 'Updated: ' + new Date().toLocaleTimeString();
  }

  // ── Build a single card's HTML ─────────────────────────────────────────────
  function buildCardHtml(card) {
    var id = card.session_id || '';
    var runtime = card.runtime || '—';
    var isStale = card.is_stale === true;
    var staleAttr = isStale ? 'true' : 'false';
    var context = esc(card._context || '');
    var age = fmtAge(card.last_seen_at);
    var statusText = isStale ? 'stale' : 'active';

    // aria-label: "Session <id>, <runtime>, <age>, <status>"
    var ariaLabel = 'Session ' + esc(id) + ', ' + esc(runtime) + ', ' + esc(age) + ', ' + esc(statusText);

    return '<div class="kanban-card"'
      + ' role="article"'
      + ' tabindex="0"'
      + ' aria-label="' + ariaLabel + '"'
      + ' data-context="' + context + '"'
      + ' data-stale="' + esc(staleAttr) + '"'
      + '>'
      + '<div class="kanban-card-title-row">'
        + '<span class="kanban-card-session-id">' + esc(id) + '</span>'
        + '<span class="kanban-status-dot" role="img" data-stale="' + esc(staleAttr) + '"'
          + ' aria-label="' + esc(statusText) + '"></span>'
      + '</div>'
      + '<div class="kanban-card-meta">' + esc(runtime) + '</div>'
      + '<div class="kanban-card-meta-detail">' + esc(runtime) + ' · ' + esc(age) + '</div>'
      + '</div>';
  }

  // ── Build a swimlane's HTML ─────────────────────────────────────────────────
  function buildLaneHtml(lane) {
    var ctx = lane.context || '';
    var ctxSlug = ctx.replace(/[^a-z0-9]+/gi, '-').toLowerCase();
    var columns = lane.columns || {};

    // XOR lock dimming is retired: impl and review share one combined column (impl_review).
    // Count total cards in all columns to detect empty lane.
    var totalCards = 0;
    COLUMN_ORDER.forEach(function (col) {
      totalCards += (columns[col] || []).length;
    });

    var html = '<section class="kanban-lane" aria-labelledby="lane-' + esc(ctxSlug) + '-heading">';

    // Lane header
    html += '<div class="kanban-lane-header">'
      + '<h3 class="kanban-lane-title" id="lane-' + esc(ctxSlug) + '-heading">'
        + esc(ctx)
      + '</h3>'
      + '</div>';

    // Always render the 4-column grid (AC-2.4: empty columns show placeholders).
    // When all columns empty: also render a screen-reader-visible note for a11y.
    if (totalCards === 0) {
      // Screen-reader announcement for empty lane; sighted users see the placeholders.
      html += '<div class="kanban-lane-empty" role="status" aria-live="polite">No active sessions</div>';
    }

    html += '<div class="kanban-lane-columns">';

      COLUMN_ORDER.forEach(function (colKey) {
        var label = COLUMN_LABELS[colKey] || colKey;
        var cards = (columns[colKey] || []).map(function (c) {
          c._context = ctx;
          return c;
        });
        var headingId = 'col-' + esc(colKey) + '-' + esc(ctxSlug) + '-heading';

        html += '<div class="kanban-column"'
          + ' role="group"'
          + ' aria-labelledby="' + headingId + '"'
          + '>';

        // Column header
        var badge = COLUMN_BADGES[colKey];
        html += '<div class="kanban-col-header">'
          + '<span class="kanban-col-title" id="' + headingId + '">'
            + esc(label)
          + '</span>'
          + '<div class="kanban-col-header-right">';

        if (badge) {
          html += '<span class="kanban-concurrency-badge" title="Max concurrency: ' + esc(badge) + '">'
            + esc(badge)
            + '</span>';
        }

        html += '</div>';

        html += '</div>'; // .kanban-col-header

        // Cards or empty placeholder
        if (cards.length === 0) {
          html += '<div class="kanban-empty-placeholder"'
            + ' data-testid="kanban-empty-placeholder"'
            + ' aria-hidden="true">'
            + '</div>';
        } else {
          cards.forEach(function (card) {
            html += buildCardHtml(card);
          });
        }

        html += '</div>'; // .kanban-column
      });

      html += '</div>'; // .kanban-lane-columns

    html += '</section>'; // .kanban-lane
    return html;
  }

  // ── Render board ───────────────────────────────────────────────────────────
  function renderBoard(data) {
    var board = document.getElementById('kanban-board');
    if (!board) { return; }

    var swimlanes = (data && data.swimlanes) || [];

    if (swimlanes.length === 0) {
      board.innerHTML = '<div class="kanban-board-empty" role="status" aria-live="polite">'
        + 'No Spec Context Projects available.'
        + '</div>';
      return;
    }

    board.innerHTML = swimlanes.map(buildLaneHtml).join('');
    updateLastUpdated();
  }

  // ── Render error state ─────────────────────────────────────────────────────
  function renderError(msg) {
    var board = document.getElementById('kanban-board');
    if (!board) { return; }
    board.innerHTML = '<div class="kanban-error" role="alert">'
      + esc(msg)
      + '</div>';
  }

  // ── Fetch and render ───────────────────────────────────────────────────────
  function fetchKanban() {
    if (document.hidden) { return; }

    window.authedFetch('/api/kanban')
      .then(function (r) {
        if (!r.ok) {
          if (r.status === 401) {
            renderError('Authentication required. Re-open the panel via dadaia panel start.');
          } else {
            renderError('Failed to load Kanban board (HTTP ' + r.status + ').');
          }
          return null;
        }
        return r.json();
      })
      .then(function (data) {
        if (!data) { return; }
        _loaded = true;
        renderBoard(data);
      })
      .catch(function (err) {
        renderError('Failed to load Kanban board: ' + (err && err.message ? err.message : String(err)));
      });
  }

  // ── Auto-refresh ───────────────────────────────────────────────────────────
  function startAutoRefresh() {
    if (_refreshTimer !== null) { clearInterval(_refreshTimer); }
    _refreshTimer = setInterval(function () {
      if (!document.hidden) { fetchKanban(); }
    }, AUTO_REFRESH_MS);
  }

  // ── Initialise ─────────────────────────────────────────────────────────────
  document.addEventListener('DOMContentLoaded', function () {
    // Kanban lives inside the Ops section (#ops-subsection-kanban).
    // Fall back to #section-kanban for isolated test scaffolds that embed
    // only the kanban fragment (e.g. kanban-tab.spec.ts live-FE tests).
    var section = document.getElementById('ops-subsection-kanban')
      || document.getElementById('section-kanban');
    if (!section) { return; } // No kanban section in the DOM — no-op

    // Visibility change: resume refresh when tab is foregrounded
    document.addEventListener('visibilitychange', function () {
      if (!document.hidden) {
        fetchKanban();
      }
    });

    // Initial fetch + auto-refresh
    fetchKanban();
    startAutoRefresh();
  });

  // ── Public API ─────────────────────────────────────────────────────────────
  window.Kanban = {
    isLoaded: function () { return _loaded; },
    load: function () {
      if (!_loaded) { fetchKanban(); }
    },
    reload: function () {
      _loaded = false;
      fetchKanban();
    },
  };

})();
