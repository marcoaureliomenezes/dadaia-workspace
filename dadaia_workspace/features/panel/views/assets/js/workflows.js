// workflows.js — Workflows tab UI (card grid, skeleton, error/empty states)
// PR3-16 (card grid) — PR3-17 will extend with detail view + hash routing
//
// Depends on: authedFetch() defined in core.js (loaded before this script)
//
// API contract (SPEC §5.3 — normative):
//   GET /api/workflows → {
//     source_hint: string,
//     workflows: [
//       {
//         name: string,
//         display_name: string,
//         description: string | null,
//         agent_ids: string[],
//         stage_count: number,
//         source_path: string
//       }, ...
//     ]
//   }
//
// Card layout (per design report, SPEC §7.5, Surface D3):
//   - Full-width card grid (NOT 2-pane list/detail — that is the discarded pattern)
//   - 2-col ≥768px, 1-col below
//   - Each card: name heading, description (1-2 lines clamped), agent chips, stage_count badge
//   - "View DAG →" CTA button with data-workflow-name for PR3-17 to wire
//
// Keyboard accessibility:
//   - CTA button is keyboard reachable (native <button>)
//   - Enter/Space trigger the affordance (native button behaviour)

(function () {
  'use strict';

  // ── Utilities ─────────────────────────────────────────────────────────────────

  function escHtml(s) {
    return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
    });
  }

  function escAttr(s) {
    return escHtml(s);
  }

  // ── Skeleton rendering ─────────────────────────────────────────────────────────

  function renderSkeletons(count) {
    var cards = '';
    for (var i = 0; i < count; i++) {
      cards += '<div class="workflow-card workflow-card--skeleton" aria-hidden="true">'
        + '<div class="workflow-card__header">'
        + '<span class="skeleton-line skeleton-pulse" style="width:60%"></span>'
        + '<span class="workflow-stage-badge skeleton-pulse" style="width:60px"></span>'
        + '</div>'
        + '<div class="skeleton-line skeleton-pulse" style="width:90%;margin-top:0.5rem"></div>'
        + '<div class="skeleton-line skeleton-pulse" style="width:70%;margin-top:0.3rem"></div>'
        + '<div class="workflow-card__chips">'
        + '<span class="workflow-agent-chip skeleton-pulse" style="width:80px"></span>'
        + '<span class="workflow-agent-chip skeleton-pulse" style="width:90px"></span>'
        + '</div>'
        + '<div class="workflow-card__footer">'
        + '<span class="skeleton-line skeleton-pulse" style="width:80px"></span>'
        + '</div>'
        + '</div>';
    }
    return cards;
  }

  // ── Card rendering ─────────────────────────────────────────────────────────────

  // Render a single workflow card.
  // The "View DAG →" button carries data-workflow-name so PR3-17 can wire the click.
  function renderCard(w) {
    var name = w.name || '';
    var displayName = w.display_name || name;
    var description = w.description || '';
    var agentIds = w.agent_ids || [];
    var stageCount = w.stage_count != null ? w.stage_count : 0;
    var stagesLabel = stageCount === 1 ? '1 stage' : stageCount + ' stages';

    var chipsHtml = agentIds.map(function (id) {
      return '<span class="workflow-agent-chip" title="' + escAttr(id) + '">'
        + escHtml(id)
        + '</span>';
    }).join('');
    if (agentIds.length === 0) {
      chipsHtml = '<span class="workflow-agent-chip workflow-agent-chip--none">no agents</span>';
    }

    var descHtml = description
      ? '<p class="workflow-card__description">' + escHtml(description) + '</p>'
      : '<p class="workflow-card__description workflow-card__description--empty">No description.</p>';

    return '<article class="workflow-card" aria-label="' + escAttr(displayName) + '">'
      + '<div class="workflow-card__header">'
      + '<h3 class="workflow-card__name">' + escHtml(displayName) + '</h3>'
      + '<span class="workflow-stage-badge" aria-label="' + escAttr(stagesLabel) + '">'
      + escHtml(stagesLabel)
      + '</span>'
      + '</div>'
      + descHtml
      + '<div class="workflow-card__chips" aria-label="Participating agents">'
      + chipsHtml
      + '</div>'
      + '<div class="workflow-card__footer">'
      + '<button type="button"'
      + ' class="workflow-dag-cta"'
      + ' data-workflow-name="' + escAttr(name) + '"'
      + ' aria-label="View DAG for ' + escAttr(displayName) + '">'
      + 'View DAG &#8594;'
      + '</button>'
      + '</div>'
      + '</article>';
  }

  // ── Render response ────────────────────────────────────────────────────────────

  function render(data) {
    var grid = document.getElementById('workflows-grid');
    var empty = document.getElementById('workflows-empty');
    var meta = document.getElementById('workflows-meta');

    if (!grid) { return; }

    var workflows = data.workflows || [];

    if (meta) {
      meta.textContent = workflows.length + ' workflow' + (workflows.length === 1 ? '' : 's')
        + (data.source_hint ? ' (' + data.source_hint + ')' : '');
    }

    grid.setAttribute('aria-busy', 'false');

    if (workflows.length === 0) {
      grid.innerHTML = '';
      if (empty) { empty.hidden = false; }
      return;
    }

    if (empty) { empty.hidden = true; }
    grid.innerHTML = workflows.map(renderCard).join('');

    // Wire CTA buttons — placeholder for PR3-17 which adds the detail view.
    // For now, each button announces via aria-label; click handler is a no-op
    // that PR3-17 will replace with hash routing (#workflows?detail=<name>).
    grid.querySelectorAll('.workflow-dag-cta[data-workflow-name]').forEach(function (btn) {
      btn.addEventListener('click', function (e) {
        // PR3-17: replace this handler with hash navigation + detail render.
        // The data-workflow-name attribute is the stable target for that PR.
        e.preventDefault();
      });

      // Keyboard: Enter/Space are natively handled by <button> — no explicit keydown needed.
      // Focus-visible styles are defined in workflows.css.
    });
  }

  // ── Error state ────────────────────────────────────────────────────────────────

  function renderError(status) {
    var grid = document.getElementById('workflows-grid');
    if (!grid) { return; }
    grid.setAttribute('aria-busy', 'false');
    if (status === 401) {
      grid.innerHTML = '<div class="error-state" role="alert">'
        + '<strong>Authentication required.</strong> '
        + 'Re-authenticate by opening the panel with '
        + '<code>dadaia panel start</code> and using the token URL provided.'
        + '</div>';
    } else {
      grid.innerHTML = '<div class="error-state" role="alert">'
        + 'Failed to load workflows (HTTP ' + escHtml(String(status)) + '). '
        + '<button type="button" id="workflows-retry-btn" class="retry-link">Retry</button>'
        + '</div>';
      var retryBtn = document.getElementById('workflows-retry-btn');
      if (retryBtn) {
        retryBtn.addEventListener('click', function () { load(); });
      }
    }
  }

  // ── Load ───────────────────────────────────────────────────────────────────────

  var loaded = false;

  function load() {
    var grid = document.getElementById('workflows-grid');
    if (!grid) { return; }
    grid.setAttribute('aria-busy', 'true');
    grid.innerHTML = renderSkeletons(6);

    authedFetch('/api/workflows')
      .then(function (r) {
        if (!r.ok) {
          renderError(r.status);
          return null;
        }
        return r.json();
      })
      .then(function (data) {
        if (!data) { return; }
        render(data);
        loaded = true;
      })
      .catch(function (err) {
        var grid2 = document.getElementById('workflows-grid');
        if (grid2) {
          grid2.setAttribute('aria-busy', 'false');
          grid2.innerHTML = '<div class="error-state" role="alert">'
            + 'Failed to load workflows: '
            + escHtml(err && err.message ? err.message : String(err))
            + '</div>';
        }
      });
  }

  // ── Public API ─────────────────────────────────────────────────────────────────

  window.Workflows = {
    load: load,
    isLoaded: function () { return loaded; },
  };

})();
