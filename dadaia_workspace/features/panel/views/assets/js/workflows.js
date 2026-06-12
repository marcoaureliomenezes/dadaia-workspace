// workflows.js — Workflows tab UI (card grid + detail view + hash routing)
// PR3-16: card grid (skeleton, render, error/empty states)
// PR3-17: detail view, hash routing (#workflows?detail=<name>), DAG skeleton,
//         back affordance (button + Escape), inline error + retry,
//         direct deep-link support.
//
// Hash grammar (SPEC §7.1 — normative, documented here per TASKS.md PR3-17):
//   #workflows               — activate Workflows tab, show card grid
//   #workflows?detail=<name> — activate Workflows tab, fetch + show detail view
//
// Depends on: window.authedFetch() defined in core.js (loaded before this script)
//
// API contracts (SPEC §5.3 / §5.4 — normative):
//   GET /api/workflows → {
//     source_hint: string,
//     workflows: [{ name, display_name, description, agent_ids, stage_count,
//                   version, schema_version, has_parallel, has_gates,
//                   lifecycle_phase, source_path }]
//   }
//
// Workflows are grouped in the grid by development-lifecycle phase
// (lifecycle_phase, sourced from public/workflows/*.md frontmatter). The Run
// affordance was removed (operator decision 2026-06-11): DAG cards do not run.
//   GET /api/workflows/<name> → {
//     name, description, version, schema_version, inputs, stages, diagram_svg,
//     source_path
//   }
//
// Security (OWASP A03):
//   diagram_svg is injected as innerHTML only for the /api/workflows/<name>
//   endpoint whose content is entirely server-controlled SVG. The server is the
//   trust boundary (per constraint in TASKS.md PR3-17). No other raw HTML is
//   injected from external sources.

(function () {
  'use strict';

  // ── Utilities ─────────────────────────────────────────────────────────────────

  // TODO: replace with window.escHtml when touching this file
  function escHtml(s) {
    return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
    });
  }

  function escAttr(s) {
    return escHtml(s);
  }

  // ── Hash grammar ───────────────────────────────────────────────────────────────
  // Parse the #workflows?detail=<name> pattern.
  // Returns { section: string, params: URLSearchParams } or null if not workflows.

  function parseWorkflowHash(hash) {
    if (!hash || !hash.startsWith('#workflows')) { return null; }
    var raw = hash.slice(1); // strip '#'
    var qIdx = raw.indexOf('?');
    var section = qIdx >= 0 ? raw.slice(0, qIdx) : raw;
    var params = new URLSearchParams(qIdx >= 0 ? raw.slice(qIdx + 1) : '');
    return { section: section, params: params };
  }

  function buildDetailHash(workflowName) {
    return '#workflows?detail=' + encodeURIComponent(workflowName);
  }

  // ── Skeleton rendering (grid) ──────────────────────────────────────────────────

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

  // ── Detail loading skeleton ────────────────────────────────────────────────────
  // 3 placeholder nodes in a horizontal row inside aria-busy container.
  // The back button is operative throughout (SPEC §7.5 normative).

  function renderDetailSkeleton(workflowName) {
    return '<div class="workflow-detail-skeleton" aria-busy="true" aria-label="Loading workflow detail">'
      + '<button type="button" class="workflow-back-btn" id="detail-back-btn-skeleton"'
      + ' aria-label="Back to workflows">'
      + '&#8592; Back to Workflows'
      + '</button>'
      + '<div class="workflow-detail-header">'
      + '<div class="skeleton-line skeleton-pulse" style="width:45%;height:1.2em"></div>'
      + '<div class="skeleton-line skeleton-pulse" style="width:70%;margin-top:0.4rem"></div>'
      + '</div>'
      + '<div class="workflow-dag-section">'
      + '<div class="workflow-dag-label">DAG</div>'
      + '<div class="workflow-dag-skeleton" aria-busy="true" aria-label="Loading DAG diagram">'
      + '<div class="dag-node-placeholder skeleton-pulse"></div>'
      + '<div class="dag-edge-placeholder skeleton-pulse"></div>'
      + '<div class="dag-node-placeholder skeleton-pulse"></div>'
      + '<div class="dag-edge-placeholder skeleton-pulse"></div>'
      + '<div class="dag-node-placeholder skeleton-pulse"></div>'
      + '</div>'
      + '</div>'
      + '</div>';
  }

  // ── Card rendering ─────────────────────────────────────────────────────────────

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

  // ── Detail view rendering ──────────────────────────────────────────────────────

  function renderAgentChips(agentIds) {
    if (!agentIds || agentIds.length === 0) {
      return '<span class="workflow-detail-chip">no agents</span>';
    }
    return agentIds.map(function (id) {
      return '<span class="workflow-detail-chip" title="' + escAttr(id) + '">'
        + escHtml(id)
        + '</span>';
    }).join('');
  }

  function renderStagesTable(stages) {
    if (!stages || stages.length === 0) {
      return '<p class="workflow-detail-description">No stages.</p>';
    }
    var rows = stages.map(function (s) {
      var needs = (s.needs && s.needs.length > 0) ? s.needs.join(', ') : '—';
      var gate = s.gate ? escHtml(s.gate) : '—';
      var out = s.expected_output_path ? escHtml(s.expected_output_path) : '—';
      return '<tr>'
        + '<td>' + escHtml(s.id) + '</td>'
        + '<td>' + escHtml(s.agent || '') + '</td>'
        + '<td>' + escHtml(needs) + '</td>'
        + '<td>' + gate + '</td>'
        + '<td>' + out + '</td>'
        + '</tr>';
    }).join('');
    return '<table class="workflow-stages-table" aria-label="Workflow stages">'
      + '<thead><tr>'
      + '<th scope="col">Stage</th>'
      + '<th scope="col">Agent</th>'
      + '<th scope="col">Depends on</th>'
      + '<th scope="col">Gate</th>'
      + '<th scope="col">Expected output</th>'
      + '</tr></thead>'
      + '<tbody>' + rows + '</tbody>'
      + '</table>';
  }

  function renderDetailView(data, workflowName) {
    var name = data.name || workflowName || '';
    var version = data.version ? escHtml(data.version) : '';
    var description = data.description || '';
    var agentIds = [];

    // Collect unique agent IDs from stages
    if (data.stages && data.stages.length > 0) {
      var seen = {};
      data.stages.forEach(function (s) {
        if (s.agent && !seen[s.agent]) {
          seen[s.agent] = true;
          agentIds.push(s.agent);
        }
      });
    }

    var versionPill = version
      ? '<span class="workflow-detail-version">' + version + '</span>'
      : '';

    var dagHtml = '';
    if (data.diagram_svg) {
      // Security: diagram_svg is server-rendered SVG from a trusted backend endpoint.
      // The backend is the trust boundary per TASKS.md PR3-17 constraint.
      // No client-supplied HTML is ever injected via this path.
      dagHtml = data.diagram_svg;
    } else {
      dagHtml = '<p class="workflow-detail-description">No diagram available.</p>';
    }

    // Stages table is collapsed under an affordance (design decision):
    // The DAG already communicates the topology visually. The table provides
    // machine-readable depth (depends-on, gate, expected_output_path) for operators
    // who want to inspect precise stage metadata. Starting collapsed keeps the
    // primary DAG visually dominant; the operator reveals the table on demand.
    var stagesTableHtml = renderStagesTable(data.stages);

    return '<div class="workflow-detail-view" id="workflow-detail-view" role="region" aria-label="Workflow detail: ' + escAttr(name) + '">'
      + '<button type="button" class="workflow-back-btn" id="detail-back-btn"'
      + ' aria-label="Back to workflows list">'
      + '&#8592; Back to Workflows'
      + '</button>'
      + '<div class="workflow-detail-header">'
      + '<h3>' + escHtml(name) + (versionPill ? ' ' + versionPill : '') + '</h3>'
      + (description ? '<p class="workflow-detail-description">' + escHtml(description) + '</p>' : '')
      + '</div>'
      + '<div class="workflow-detail-agents" aria-label="Participating agents">'
      + '<div class="workflow-detail-agents-label">Agents</div>'
      + '<div class="workflow-detail-chips">' + renderAgentChips(agentIds) + '</div>'
      + '</div>'
      + '<div class="workflow-dag-section">'
      + '<div class="workflow-dag-label">DAG Diagram</div>'
      + '<div class="dag-toolbar" id="dag-toolbar">'
      + '<button type="button" class="dag-zoom-btn" id="dag-zoom-out" aria-label="Zoom out">&#8722;</button>'
      + '<span class="dag-zoom-display" id="dag-zoom-display" aria-live="polite">100%</span>'
      + '<button type="button" class="dag-zoom-btn" id="dag-zoom-in" aria-label="Zoom in">&#43;</button>'
      + '<button type="button" class="dag-zoom-btn dag-zoom-fit" id="dag-zoom-fit" aria-label="Fit to view">Fit</button>'
      + '</div>'
      + '<div class="workflow-dag-viewport" id="workflow-dag-viewport">'
      + '<div class="workflow-dag" role="img" aria-label="Workflow DAG for ' + escAttr(name) + '">'
      + dagHtml
      + '</div>'
      + '</div>'
      + '</div>'
      + '<div class="workflow-stages-section">'
      + '<button type="button" class="workflow-stages-toggle" id="stages-toggle-btn"'
      + ' aria-expanded="false" aria-controls="stages-table-wrap">'
      + '&#9656; Show stages table'
      + '</button>'
      + '<div class="workflow-stages-table-wrap" id="stages-table-wrap" hidden>'
      + stagesTableHtml
      + '</div>'
      + '</div>'
      + '</div>';
  }

  // ── Detail error state ─────────────────────────────────────────────────────────

  function renderDetailError(workflowName, statusOrMsg) {
    return '<div class="workflow-detail-view">'
      + '<button type="button" class="workflow-back-btn" id="detail-back-btn-error"'
      + ' aria-label="Back to workflows list">'
      + '&#8592; Back to Workflows'
      + '</button>'
      + '<div class="workflow-detail-error" role="alert">'
      + '<strong>Failed to load workflow detail.</strong> '
      + escHtml(String(statusOrMsg || ''))
      + ' <button type="button" id="detail-retry-btn" class="retry-link"'
      + ' aria-label="Retry loading workflow ' + escAttr(workflowName) + '">Retry</button>'
      + '</div>'
      + '</div>';
  }

  // ── State ──────────────────────────────────────────────────────────────────────

  var loaded = false;        // card grid has been loaded
  var inDetailView = false;  // currently showing detail view
  var _cachedGrid = '';      // serialized card grid HTML for back navigation
  var _zoomLevel = 100;      // current zoom percentage (50-300)

  // ── DAG zoom ───────────────────────────────────────────────────────────────────

  function applyZoom(level) {
    var STEP = 25, MIN = 50, MAX = 300;
    level = Math.max(MIN, Math.min(MAX, Math.round(level / STEP) * STEP));
    _zoomLevel = level;
    var dagEl = document.querySelector('.workflow-dag-viewport .workflow-dag');
    var display = document.getElementById('dag-zoom-display');
    var viewport = document.getElementById('workflow-dag-viewport');
    if (dagEl) { dagEl.style.transform = 'scale(' + (level / 100) + ')'; }
    if (display) { display.textContent = level + '%'; }
    if (viewport) {
      if (level !== 100) { viewport.classList.add('dag-zoomed'); }
      else { viewport.classList.remove('dag-zoomed'); }
    }
  }

  // ── Grid container helpers ─────────────────────────────────────────────────────

  function getGrid() {
    return document.getElementById('workflows-grid');
  }

  function showGrid() {
    var grid = getGrid();
    if (!grid) { return; }
    inDetailView = false;
    grid.className = 'workflows-card-grid';
    if (_cachedGrid) {
      grid.innerHTML = _cachedGrid;
      grid.setAttribute('aria-busy', 'false');
      // Re-wire CTA buttons
      wireCTAButtons(grid);
    } else {
      load();
    }
    // Hide empty-state when returning (it will be controlled by render())
    var empty = document.getElementById('workflows-empty');
    if (empty) { empty.hidden = true; }
  }

  // ── Back navigation ────────────────────────────────────────────────────────────

  function navigateBack() {
    history.pushState(null, '', location.pathname + location.search + '#workflows');
    showGrid();
  }

  // ── Escape key handler (when detail is focused/visible) ───────────────────────

  function onEscapeKey(e) {
    if (e.key === 'Escape' && inDetailView) {
      navigateBack();
    }
  }

  // ── Wire back button(s) in the detail container ───────────────────────────────

  function wireDetailControls(container) {
    // Back buttons (there may be several: header, skeleton, error)
    var backBtns = container.querySelectorAll(
      '#detail-back-btn, #detail-back-btn-skeleton, #detail-back-btn-error'
    );
    backBtns.forEach(function (btn) {
      btn.addEventListener('click', function () { navigateBack(); });
    });

    // Retry button (error state)
    var retryBtn = container.querySelector('#detail-retry-btn');
    if (retryBtn) {
      var name = retryBtn.getAttribute('aria-label') || '';
      // Extract workflow name from aria-label "Retry loading workflow <name>"
      var match = name.match(/Retry loading workflow (.+)$/);
      var wfName = match ? match[1] : '';
      retryBtn.addEventListener('click', function () {
        if (wfName) { loadDetail(wfName); }
      });
    }

    // Stages toggle
    var toggleBtn = container.querySelector('#stages-toggle-btn');
    var tableWrap = container.querySelector('#stages-table-wrap');
    if (toggleBtn && tableWrap) {
      toggleBtn.addEventListener('click', function () {
        var expanded = toggleBtn.getAttribute('aria-expanded') === 'true';
        toggleBtn.setAttribute('aria-expanded', String(!expanded));
        tableWrap.hidden = expanded;
        toggleBtn.innerHTML = expanded
          ? '&#9656; Show stages table'
          : '&#9662; Hide stages table';
      });
    }

    // Zoom controls
    var zoomIn = container.querySelector('#dag-zoom-in');
    var zoomOut = container.querySelector('#dag-zoom-out');
    var zoomFit = container.querySelector('#dag-zoom-fit');
    if (zoomIn)  { zoomIn.addEventListener('click',  function() { applyZoom(_zoomLevel + 25); }); }
    if (zoomOut) { zoomOut.addEventListener('click', function() { applyZoom(_zoomLevel - 25); }); }
    if (zoomFit) { zoomFit.addEventListener('click', function() { applyZoom(100); }); }

    // Keyboard zoom bindings when focus is within the DAG section
    var dagSection = container.querySelector('.workflow-dag-section');
    if (dagSection) {
      dagSection.addEventListener('keydown', function(e) {
        if (e.key === '+' || e.key === '=') { e.preventDefault(); applyZoom(_zoomLevel + 25); }
        else if (e.key === '-' || e.key === '_') { e.preventDefault(); applyZoom(_zoomLevel - 25); }
        else if (e.key === '0') { e.preventDefault(); applyZoom(100); }
      });
      dagSection.setAttribute('tabindex', '0');
    }
  }

  // ── CTA button wiring (card grid) ─────────────────────────────────────────────

  function wireCTAButtons(grid) {
    grid.querySelectorAll('.workflow-dag-cta[data-workflow-name]').forEach(function (btn) {
      btn.addEventListener('click', function (e) {
        e.preventDefault();
        var name = btn.getAttribute('data-workflow-name');
        if (!name) { return; }
        history.pushState(null, '', location.pathname + location.search + buildDetailHash(name));
        loadDetail(name);
      });
    });
  }

  // ── Load detail view ───────────────────────────────────────────────────────────

  function loadDetail(workflowName) {
    var grid = getGrid();
    if (!grid) { return; }

    _zoomLevel = 100;
    inDetailView = true;
    grid.className = 'workflow-detail-view-container';

    // Show loading skeleton immediately
    grid.innerHTML = renderDetailSkeleton(workflowName);
    grid.setAttribute('aria-busy', 'true');
    // Wire back button in skeleton
    wireDetailControls(grid);

    // Focus the detail region for keyboard users
    grid.setAttribute('tabindex', '-1');
    grid.focus({ preventScroll: true });

    window.authedFetch('/api/workflows/' + encodeURIComponent(workflowName))
      .then(function (r) {
        if (!r.ok) {
          grid.setAttribute('aria-busy', 'false');
          grid.innerHTML = renderDetailError(workflowName, 'HTTP ' + r.status);
          wireDetailControls(grid);
          return null;
        }
        return r.json();
      })
      .then(function (data) {
        if (!data) { return; }
        grid.setAttribute('aria-busy', 'false');
        grid.innerHTML = renderDetailView(data, workflowName);
        wireDetailControls(grid);
      })
      .catch(function (err) {
        grid.setAttribute('aria-busy', 'false');
        grid.innerHTML = renderDetailError(
          workflowName,
          err && err.message ? err.message : String(err)
        );
        wireDetailControls(grid);
      });
  }

  // ── Lifecycle-phase grouping ────────────────────────────────────────────────
  // Canonical group order mirrors the dadaia-workspace development lifecycle.
  // Any workflow whose lifecycle_phase is absent/unrecognised lands in
  // "Unmapped" so the grouping is honest (never a fabricated phase).

  var PHASE_ORDER = [
    'Backlog Definition',
    'Research',
    'Release Definition',
    'Implementation + Review',
    'Audits',
    'Closure',
    'Unmapped'
  ];

  function phaseOf(w) {
    var p = w && w.lifecycle_phase ? String(w.lifecycle_phase) : 'Unmapped';
    return PHASE_ORDER.indexOf(p) >= 0 ? p : 'Unmapped';
  }

  // Build the grouped grid HTML: one <section> per non-empty phase, in the
  // canonical order above, each containing its workflow cards.
  function renderGroupedGrid(workflows) {
    var buckets = {};
    workflows.forEach(function (w) {
      var p = phaseOf(w);
      (buckets[p] || (buckets[p] = [])).push(w);
    });
    var html = '';
    PHASE_ORDER.forEach(function (phase) {
      var items = buckets[phase];
      if (!items || items.length === 0) { return; }
      var countLabel = items.length + ' workflow' + (items.length === 1 ? '' : 's');
      html += '<section class="workflow-phase-group" aria-label="' + escAttr(phase) + '">'
        + '<h4 class="workflow-phase-heading">'
        + escHtml(phase)
        + '<span class="workflow-phase-count">' + escHtml(countLabel) + '</span>'
        + '</h4>'
        + '<div class="workflow-phase-cards">'
        + items.map(renderCard).join('')
        + '</div>'
        + '</section>';
    });
    return html;
  }

  // ── Grid render ────────────────────────────────────────────────────────────────

  function render(data) {
    var grid = getGrid();
    var empty = document.getElementById('workflows-empty');
    var meta = document.getElementById('workflows-meta');

    if (!grid) { return; }

    var workflows = data.workflows || [];

    if (meta) {
      meta.textContent = workflows.length + ' workflow' + (workflows.length === 1 ? '' : 's')
        + (data.source_hint ? ' (' + data.source_hint + ')' : '');
    }

    grid.setAttribute('aria-busy', 'false');
    grid.className = 'workflows-card-grid';

    if (workflows.length === 0) {
      grid.innerHTML = '';
      _cachedGrid = '';
      if (empty) { empty.hidden = false; }
      return;
    }

    if (empty) { empty.hidden = true; }
    var gridHtml = renderGroupedGrid(workflows);
    grid.innerHTML = gridHtml;
    _cachedGrid = gridHtml;

    wireCTAButtons(grid);
  }

  // ── Error state (grid) ─────────────────────────────────────────────────────────

  function renderError(status) {
    var grid = getGrid();
    if (!grid) { return; }
    grid.setAttribute('aria-busy', 'false');
    grid.innerHTML = '<div class="error-state" role="alert">'
      + 'Failed to load workflows (HTTP ' + escHtml(String(status)) + '). '
      + '<button type="button" id="workflows-retry-btn" class="retry-link">Retry</button>'
      + '</div>';
    var retryBtn = document.getElementById('workflows-retry-btn');
    if (retryBtn) {
      retryBtn.addEventListener('click', function () { load(); });
    }
  }

  // ── Runtime helper ─────────────────────────────────────────────────────────────
  // Phase D ships window.Runtime; fall back to 'claude' if not yet available.
  function getRuntime() {
    if (window.Runtime && typeof window.Runtime.get === 'function') {
      return window.Runtime.get();
    }
    return 'claude';
  }

  // ── Load (card grid) ───────────────────────────────────────────────────────────

  function load() {
    var grid = getGrid();
    if (!grid) { return; }
    inDetailView = false;
    grid.className = 'workflows-card-grid';
    grid.setAttribute('aria-busy', 'true');
    grid.innerHTML = renderSkeletons(6);

    window.authedFetch('/api/workflows?runtime=' + encodeURIComponent(getRuntime()))
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
        var grid2 = getGrid();
        if (grid2) {
          grid2.setAttribute('aria-busy', 'false');
          grid2.innerHTML = '<div class="error-state" role="alert">'
            + 'Failed to load workflows: '
            + escHtml(err && err.message ? err.message : String(err))
            + '</div>';
        }
      });
  }

  // ── Hash-driven deep link (called from core.js on tab activation) ──────────────
  // If #workflows?detail=<name> is already in hash, fetch the detail immediately.

  function handleHashOnActivation() {
    var parsed = parseWorkflowHash(location.hash);
    if (!parsed) {
      load();
      return;
    }
    var detail = parsed.params.get('detail');
    if (detail) {
      loadDetail(detail);
    } else {
      load();
    }
  }

  // ── Popstate handler — back button or history.back() ─────────────────────────

  window.addEventListener('popstate', function () {
    var parsed = parseWorkflowHash(location.hash);
    // Only handle if the Ops section (parent) is active — workflows now lives inside Ops.
    var opsSection = document.getElementById('section-ops');
    if (!opsSection || !opsSection.classList.contains('active')) { return; }

    if (parsed && parsed.params.get('detail')) {
      loadDetail(parsed.params.get('detail'));
    } else if (parsed) {
      showGrid();
    }
  });

  // ── Escape key listener (document-level, guards inDetailView flag) ─────────────
  document.addEventListener('keydown', onEscapeKey);

  // ── Runtime-change subscription (PR5-D6) ─────────────────────────────────────
  // When the operator switches runtimes, drop cached grid HTML and refetch so the
  // Workflows tab reflects the newly selected runtime's workflows.

  document.addEventListener('dadaia:runtime-change', function () {
    loaded = false;
    _cachedGrid = '';
    inDetailView = false;
    // Only refetch if the Ops section (parent) is currently active
    var section = document.getElementById('section-ops');
    if (section && section.classList.contains('active')) {
      load();
    }
  });

  // ── Public API ─────────────────────────────────────────────────────────────────

  window.Workflows = {
    load: load,
    loadDetail: loadDetail,
    isLoaded: function () { return loaded; },
    parseWorkflowHash: parseWorkflowHash,
    buildDetailHash: buildDetailHash,
    handleHashOnActivation: handleHashOnActivation,
  };

})();
