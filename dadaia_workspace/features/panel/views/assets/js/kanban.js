// kanban.js — Kanban board tab UI (lifecycle-truth board, kanban-v2)
//
// Depends on: window.authedFetch() and window.escHtml() defined in core.js (loaded before this).
//
// API contract (kanban-v2 — normative; see views/kanban.py docstring):
//   GET /api/kanban
//     → { schema: "kanban-v2", generated_at: "<ISO>", swimlanes: [ SwimLane, ... ] }
//   SwimLane: { context, columns: { release_def, impl_review, closure }, observers: [Card] }
//   Card (release): { card_kind: "release", release, phase }
//   Card (session): { card_kind: "session", session_id, mode, release, started_at,
//                     last_seen_at, age_seconds }
//
// Column label map (canonical §7 SDD lifecycle):
//   release_def  → "Release Definition"      (release card in DEFINITION/SPEC/PLAN; SPEC sessions)
//   impl_review  → "Implementation + Review" (release card in TASKS/IMPLEMENTATION/REVIEW;
//                                              BOUND_IMPLEMENTATION + BOUND_REVIEW sessions)
//   closure      → "Closure"                 (release card in CLOSURE)
//   observers    → "Observers" strip         (live READ sessions — NOT backlog work)
//
// kanban-v2 behaviour:
//   - The Backlog column is RETIRED. The old board dumped every (often dead) READ bind
//     into Backlog as `sess_xxxx / unknown / unknown · 9h ago`. v2 shows only LIVE
//     sessions, routes READ binds to an Observers strip, and makes the primary card per
//     lane the context's real release + phase from ACTIVE.md.
//   - Release cards render the release id + phase; session cards render mode, release
//     (if bound) and relative age — never the literal string "unknown". Absent fields
//     are omitted, not stubbed.
//   - Per-card stale indicator preserved on session cards via data-stale.
//   - Poll every 10 s (checks document.hidden). window.Kanban: isLoaded(), load(), reload().

(function () {
  'use strict';

  // ── Constants ──────────────────────────────────────────────────────────────
  var AUTO_REFRESH_MS = 10000;

  var COLUMN_LABELS = {
    release_def: 'Release Definition',
    impl_review: 'Implementation + Review',
    closure:     'Closure',
  };

  // Concurrency badges per column (undefined = no badge).
  var COLUMN_BADGES = {
    release_def: '≤2',  // ≤2 concurrent spec sessions
    impl_review: '×2',  // ×2 (impl + review combined)
  };

  var COLUMN_ORDER = ['release_def', 'impl_review', 'closure'];

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

  // ── Relative age formatter (from age_seconds or ISO) ────────────────────────
  function fmtAgeFromSeconds(sec) {
    if (sec == null || isNaN(sec)) { return null; }
    sec = Math.floor(sec);
    if (sec < 60) { return 'just now'; }
    var min = Math.floor(sec / 60);
    if (min < 60) { return min + 'm ago'; }
    var h = Math.floor(min / 60);
    if (h < 24) { return h + 'h ago'; }
    return Math.floor(h / 24) + 'd ago';
  }

  // ── Update "last updated" badge ────────────────────────────────────────────
  function updateLastUpdated() {
    var el = document.getElementById('kanban-last-updated');
    if (!el) { return; }
    el.textContent = 'Updated: ' + new Date().toLocaleTimeString();
  }

  // ── Build a release card's HTML ──────────────────────────────────────────────
  function buildReleaseCardHtml(card, ctx) {
    var release = card.release || '';
    var phase = card.phase || '';
    var ariaLabel = 'Active release ' + esc(release) + ', phase ' + esc(phase);

    var html = '<div class="kanban-card kanban-card--release"'
      + ' role="article"'
      + ' tabindex="0"'
      + ' data-card-kind="release"'
      + ' aria-label="' + ariaLabel + '"'
      + ' data-context="' + esc(ctx) + '"'
      + '>'
      + '<div class="kanban-card-title-row">'
        + '<span class="kanban-card-session-id">' + esc(release) + '</span>'
        + '<span class="kanban-release-badge">release</span>'
      + '</div>';
    if (phase) {
      html += '<div class="kanban-card-meta">' + esc(phase) + '</div>';
    }
    html += '</div>';
    return html;
  }

  // ── Build a live-session card's HTML ─────────────────────────────────────────
  // Renders only the fields that are present — never the literal "unknown".
  function buildSessionCardHtml(card, ctx) {
    var id = card.session_id || '';
    var mode = card.mode || '';
    var isStale = card.is_stale === true; // v2 only emits live sessions; flag retained.
    var staleAttr = isStale ? 'true' : 'false';
    var age = fmtAgeFromSeconds(card.age_seconds);
    var statusText = isStale ? 'stale' : 'active';

    var labelParts = ['Session ' + esc(id)];
    if (mode) { labelParts.push(esc(mode)); }
    if (card.release) { labelParts.push(esc(card.release)); }
    if (age) { labelParts.push(esc(age)); }
    labelParts.push(esc(statusText));

    var html = '<div class="kanban-card kanban-card--session"'
      + ' role="article"'
      + ' tabindex="0"'
      + ' data-card-kind="session"'
      + ' aria-label="' + labelParts.join(', ') + '"'
      + ' data-context="' + esc(ctx) + '"'
      + ' data-stale="' + esc(staleAttr) + '"'
      + '>'
      + '<div class="kanban-card-title-row">'
        + '<span class="kanban-card-session-id">' + esc(id) + '</span>'
        + '<span class="kanban-status-dot" role="img" data-stale="' + esc(staleAttr) + '"'
          + ' aria-label="' + esc(statusText) + '"></span>'
      + '</div>';

    // Meta line 1: mode (always present on a session card).
    if (mode) {
      html += '<div class="kanban-card-meta">' + esc(mode) + '</div>';
    }
    // Meta line 2: release · age — only the present pieces, joined by " · ".
    var detail = [];
    if (card.release) { detail.push(esc(card.release)); }
    if (age) { detail.push(esc(age)); }
    if (detail.length) {
      html += '<div class="kanban-card-meta-detail">' + detail.join(' · ') + '</div>';
    }

    html += '</div>';
    return html;
  }

  function buildCardHtml(card, ctx) {
    if (card && card.card_kind === 'release') {
      return buildReleaseCardHtml(card, ctx);
    }
    return buildSessionCardHtml(card, ctx);
  }

  // ── Build a swimlane's HTML ─────────────────────────────────────────────────
  function buildLaneHtml(lane) {
    var ctx = lane.context || '';
    var ctxSlug = ctx.replace(/[^a-z0-9]+/gi, '-').toLowerCase();
    var columns = lane.columns || {};
    var observers = lane.observers || [];

    // Detect a fully idle lane (no release card, no session cards, no observers).
    var totalCards = observers.length;
    COLUMN_ORDER.forEach(function (col) {
      totalCards += (columns[col] || []).length;
    });

    var html = '<section class="kanban-lane" aria-labelledby="lane-' + esc(ctxSlug) + '-heading">';

    html += '<div class="kanban-lane-header">'
      + '<h3 class="kanban-lane-title" id="lane-' + esc(ctxSlug) + '-heading">'
        + esc(ctx)
      + '</h3>'
      + '</div>';

    if (totalCards === 0) {
      html += '<div class="kanban-lane-empty" role="status" aria-live="polite">No active release or live sessions</div>';
    }

    html += '<div class="kanban-lane-columns">';

      COLUMN_ORDER.forEach(function (colKey) {
        var label = COLUMN_LABELS[colKey] || colKey;
        var cards = columns[colKey] || [];
        var headingId = 'col-' + esc(colKey) + '-' + esc(ctxSlug) + '-heading';

        html += '<div class="kanban-column"'
          + ' role="group"'
          + ' aria-labelledby="' + headingId + '"'
          + '>';

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

        if (cards.length === 0) {
          html += '<div class="kanban-empty-placeholder"'
            + ' data-testid="kanban-empty-placeholder"'
            + ' aria-hidden="true">'
            + '</div>';
        } else {
          cards.forEach(function (card) {
            html += buildCardHtml(card, ctx);
          });
        }

        html += '</div>'; // .kanban-column
      });

      html += '</div>'; // .kanban-lane-columns

    // Observers strip — live READ sessions only (never rendered when empty).
    if (observers.length) {
      html += '<div class="kanban-observers" role="group" aria-label="Observers — live read-only sessions">'
        + '<span class="kanban-observers-label">Observers</span>'
        + '<div class="kanban-observers-cards">';
      observers.forEach(function (card) {
        html += buildCardHtml(card, ctx);
      });
      html += '</div></div>';
    }

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
          renderError('Failed to load Kanban board (HTTP ' + r.status + ').');
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
    var section = document.getElementById('ops-subsection-kanban')
      || document.getElementById('section-kanban');
    if (!section) { return; } // No kanban section in the DOM — no-op

    document.addEventListener('visibilitychange', function () {
      if (!document.hidden) {
        fetchKanban();
      }
    });

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
