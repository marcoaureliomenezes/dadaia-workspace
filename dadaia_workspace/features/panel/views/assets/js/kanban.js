// kanban.js — Kanban board tab UI (swimlanes, phase columns, XOR lock visual, auto-refresh)
// panel-kanban-v1 K-2 (FE)
//
// Depends on: window.authedFetch() and window.escHtml() defined in core.js (loaded before this).
//
// API contract (SPEC §3 K-1 response schema — normative):
//   GET /api/kanban
//     → { generated_at: "<ISO>", swimlanes: [ SwimLane, ... ] }
//   SwimLane: { context: "<name>", columns: { research: [...], spec: [...],
//               implementation: [...], review: [...] } }
//   SessionCard: { session_id, mode, release, runtime, pid, last_seen_at, is_stale }
//
// Column label map:
//   research        → "Research"
//   spec            → "Definition"   (UI label per SPEC §3 K-2)
//   implementation  → "Implementation"
//   review          → "Review"
//
// Behaviour summary:
//   - On DOMContentLoaded: locate #section-kanban; if absent, exit (no-op).
//   - fetchKanban() calls GET /api/kanban via authedFetch.
//   - renderBoard(data): renders lanes and columns into #kanban-board.
//   - XOR lock visual: if a lane has ≥1 card in review → dim implementation column
//     of that lane (kanban-column--locked, data-locked="true", lock badge U+1F512,
//     aria supplement). Vice versa when implementation is active and review is empty.
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
    research:       'Research',
    spec:           'Definition',
    implementation: 'Implementation',
    review:         'Review',
  };

  // Concurrency badges per column (undefined = no badge).
  var COLUMN_BADGES = {
    spec:           '≤2',  // ≤2
    implementation: '×1',  // ×1
    review:         '×1',  // ×1
  };

  var COLUMN_ORDER = ['research', 'spec', 'implementation', 'review'];

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

    // Check XOR lock: review cards present → lock implementation; implementation cards present → lock review.
    var hasReview = (columns.review || []).length > 0;
    var hasImpl   = (columns.implementation || []).length > 0;

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

        // Determine lock state for this column
        var isLocked = false;
        var lockReason = '';
        if (colKey === 'implementation' && hasReview) {
          isLocked = true;
          lockReason = 'Implementation column, locked — context is in review';
        } else if (colKey === 'review' && hasImpl) {
          isLocked = true;
          lockReason = 'Review column, locked — context is in implementation';
        }

        var lockedClass = isLocked ? ' kanban-column--locked' : '';
        var lockedAttr = isLocked ? ' data-locked="true"' : '';

        html += '<div class="kanban-column' + lockedClass + '"'
          + lockedAttr
          + ' role="group"'
          + ' aria-labelledby="' + headingId + '"'
          + '>';

        // Column header
        var badge = COLUMN_BADGES[colKey];
        html += '<div class="kanban-col-header">'
          + '<span class="kanban-col-title" id="' + headingId + '">'
            + esc(label);

        if (isLocked) {
          // Lock icon supplement — not sole conveyance of locked state (WCAG 1.4.1)
          html += ' <span class="kanban-lock-badge" aria-hidden="true">🔒</span>';
        }

        html += '</span>'
          + '<div class="kanban-col-header-right">';

        if (badge) {
          html += '<span class="kanban-concurrency-badge" title="Max concurrency: ' + esc(badge) + '">'
            + esc(badge)
            + '</span>';
        }

        html += '</div>';

        // ARIA supplement for locked headers (screen-reader only)
        if (isLocked) {
          html += '<span class="sr-only">' + esc(lockReason) + '</span>';
        }

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
