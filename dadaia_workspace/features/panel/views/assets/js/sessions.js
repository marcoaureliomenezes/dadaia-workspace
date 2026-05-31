// sessions.js — Sessions tab UI (sortable table, detail drawer, filter, auto-refresh)
// PR5-C3 (FE): Claude-only path live.
// PR5-E3 (FE): Codex banner + Cost column override.
//
// Depends on: window.authedFetch() defined in core.js (loaded before this script)
//
// API contracts (SPEC §FR3, §FR4 — normative):
//   GET /api/sessions?runtime=<runtime>[&project=<slug>][&limit=<n>]
//     → { sessions: [ SessionRow... ], runtime, project, limit, generated_at, total_count }
//   GET /api/sessions/<runtime>/<session_id>
//     → SessionDetail (SessionRow + event_timestamps)
//
// SessionRow fields:
//   session_id, runtime, project, cwd, model, started_at, last_activity_at,
//   message_count, context_size_tokens, cumulative_cost_usd, cost_known,
//   status ("active"|"idle"|"ended"), agent_name, ai_title
//
// Behaviour summary:
//   - On DOMContentLoaded: locate #section-sessions; if absent, exit (no-op).
//   - fetchSessions() appends ?runtime= from Runtime.get() (Phase C: fallback "claude").
//   - renderTable(rows): builds tbody rows with row-click → openDrawer(sessionId).
//   - openDrawer(sessionId): fetches detail, populates #session-drawer, focuses first
//     focusable element (a11y focus management), adds .open class.
//   - Close: close button click + Escape key.
//   - Sort: clicking th[data-sort-key] toggles asc/desc on that column.
//   - Filter: #sessions-filter debounced 200ms; client-side substring filter.
//   - Auto-refresh: setInterval 10s; checks document.hidden before each tick.
//   - Listens for 'dadaia:runtime-change' CustomEvent; calls updateBanner() then
//     refetches (Phase E: banner and Cost column override for Codex).
//   - Updates #sessions-last-updated badge via updateStatusLabel pattern.
//
// Phase E: Codex banner — when runtime === 'codex':
//   - #sessions-banner shows "Cost not tracked for Codex" (aria-live="polite").
//   - Cost column renders '—' for every row regardless of row.cost_known.
//   When runtime flips back to 'claude', banner is hidden and Cost re-populates.

(function () {
  'use strict';

  // ── Constants ─────────────────────────────────────────────────────────────────
  var AUTO_REFRESH_MS = 10000;
  var FILTER_DEBOUNCE_MS = 200;
  var DEFAULT_RUNTIME = 'claude';
  var CODEX_BANNER_TEXT = 'Cost not tracked for Codex';

  // ── Module state ─────────────────────────────────────────────────────────────
  var _allRows = [];           // last fetched SessionRow array (full set, pre-filter)
  var _sortKey = null;         // current sort column key (string | null)
  var _sortDir = 'none';       // 'asc' | 'desc' | 'none'
  var _filterText = '';        // current filter string (lowercased)
  var _refreshTimer = null;    // interval handle for auto-refresh
  var _filterTimer = null;     // debounce handle for filter input
  var _loaded = false;         // has at least one successful fetch completed?

  // ── HTML escape helper ────────────────────────────────────────────────────────
  // TODO: replace with window.escHtml when touching this file
  function escHtml(s) {
    return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
    });
  }

  // ── Runtime resolution ────────────────────────────────────────────────────────
  // Phase D ships window.Runtime; in Phase C we fall back to 'claude'.
  function getRuntime() {
    if (window.Runtime && typeof window.Runtime.get === 'function') {
      return window.Runtime.get();
    }
    return DEFAULT_RUNTIME;
  }

  // ── Banner: show/hide the "Cost not tracked for Codex" notice ────────────────
  // Called after each fetchSessions() resolution and on every dadaia:runtime-change.
  // The #sessions-banner element starts with the HTML [hidden] attribute (set in the
  // scaffold); JS shows it only when runtime === 'codex'.
  function updateBanner() {
    var banner = document.getElementById('sessions-banner');
    if (!banner) { return; }
    var runtime = getRuntime();
    if (runtime === 'codex') {
      banner.textContent = CODEX_BANNER_TEXT;
      banner.removeAttribute('hidden');
    } else {
      banner.textContent = '';
      banner.setAttribute('hidden', '');
    }
  }

  // ── Dashboard ─────────────────────────────────────────────────────────────────
  function computeStats(rows, runtime) {
    var totalSessions = rows.length;
    var activeSessions = 0;
    var totalCostUsd = 0;
    var anyCostKnown = false;
    var totalTurns = 0;
    var agentCounts = {};
    for (var i = 0; i < rows.length; i++) {
      var r = rows[i];
      if (r.status === 'active') { activeSessions++; }
      if (r.cost_known && r.cumulative_cost_usd != null) {
        totalCostUsd += r.cumulative_cost_usd;
        anyCostKnown = true;
      }
      if (r.message_count) { totalTurns += r.message_count; }
      var ag = r.agent_name || 'operator';
      agentCounts[ag] = (agentCounts[ag] || 0) + 1;
    }
    var topAgent = null;
    var topCount = 0;
    Object.keys(agentCounts).forEach(function (k) {
      if (agentCounts[k] > topCount) { topAgent = k; topCount = agentCounts[k]; }
    });
    return {
      totalSessions: totalSessions,
      activeSessions: activeSessions,
      totalCostUsd: anyCostKnown ? totalCostUsd : null,
      totalTurns: totalTurns,
      topAgent: topAgent,
      topAgentCount: topCount,
      runtime: runtime,
    };
  }

  function renderDashboard(stats) {
    var dash = document.getElementById('sessions-dashboard');
    if (!dash) { return; }
    var isCodex = stats.runtime === 'codex';
    var costVal = isCodex ? 'N/A'
      : (stats.totalCostUsd == null ? '—' : '$' + stats.totalCostUsd.toFixed(2));
    var costClass = (!isCodex && stats.totalCostUsd != null)
      ? 'sessions-stat-value sessions-stat-value--cost'
      : 'sessions-stat-value';
    var turnsStr = stats.totalTurns >= 1000000
      ? (stats.totalTurns / 1000000).toFixed(1) + 'M'
      : stats.totalTurns >= 1000
      ? (stats.totalTurns / 1000).toFixed(1) + 'k'
      : String(stats.totalTurns);
    var agentLabel = stats.topAgent ? escHtml(stats.topAgent) : '—';
    var agentSub = (stats.topAgent && stats.topAgentCount > 0)
      ? escHtml(String(stats.topAgentCount)) + ' session' + (stats.topAgentCount !== 1 ? 's' : '')
      : '&nbsp;';
    dash.innerHTML =
      '<div class="sessions-stat-card">'
        + '<span class="sessions-stat-label">Total Sessions</span>'
        + '<span class="sessions-stat-value">' + escHtml(String(stats.totalSessions)) + '</span>'
        + '<span class="sessions-stat-sub">' + escHtml(stats.activeSessions > 0 ? String(stats.activeSessions) + ' active' : 'none active') + '</span>'
      + '</div>'
      + '<div class="sessions-stat-card">'
        + '<span class="sessions-stat-label">Total Cost</span>'
        + '<span class="' + costClass + '">' + escHtml(costVal) + '</span>'
        + '<span class="sessions-stat-sub">' + (isCodex ? 'not tracked for Codex' : '&nbsp;') + '</span>'
      + '</div>'
      + '<div class="sessions-stat-card">'
        + '<span class="sessions-stat-label">AI Turns</span>'
        + '<span class="sessions-stat-value">' + escHtml(turnsStr) + '</span>'
        + '<span class="sessions-stat-sub">&nbsp;</span>'
      + '</div>'
      + '<div class="sessions-stat-card">'
        + '<span class="sessions-stat-label">Top Agent</span>'
        + '<span class="sessions-stat-value" style="font-size:1.05rem;line-height:1.3;">' + agentLabel + '</span>'
        + '<span class="sessions-stat-sub">' + agentSub + '</span>'
      + '</div>';
  }

  // ── Relative date formatter ────────────────────────────────────────────────────
  function fmtRelativeDate(iso) {
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
    if (diffD < 30) { return diffD + 'd ago'; }
    var diffMo = Math.floor(diffD / 30);
    if (diffMo < 12) { return diffMo + 'mo ago'; }
    return Math.floor(diffMo / 12) + 'y ago';
  }

  // ── Cost formatter ────────────────────────────────────────────────────────────
  function fmtCost(v, costKnown) {
    if (!costKnown || v == null) { return '—'; }
    return '$' + Number(v).toFixed(2);
  }

  // ── Context size formatter (compact) ─────────────────────────────────────────
  function fmtTokens(n) {
    if (n == null) { return '—'; }
    if (n >= 1000000) { return (n / 1000000).toFixed(1) + 'M'; }
    if (n >= 1000) { return (n / 1000).toFixed(1) + 'k'; }
    return String(n);
  }

  // ── Update "Last updated" badge ────────────────────────────────────────────────
  function updateLastUpdatedBadge() {
    var badge = document.getElementById('sessions-last-updated');
    if (!badge) { return; }
    badge.textContent = 'Updated: ' + new Date().toLocaleTimeString();
  }

  // ── Skeleton rows (while fetching) ────────────────────────────────────────────
  function renderSkeletonRows(count) {
    var rows = '';
    for (var i = 0; i < count; i++) {
      rows += '<tr class="session-row session-row--skeleton" aria-hidden="true">'
        + '<td><span class="skeleton-cell skeleton-pulse" style="width:80px"></span></td>'
        + '<td><span class="skeleton-cell skeleton-pulse" style="width:100px"></span></td>'
        + '<td><span class="skeleton-cell skeleton-pulse" style="width:140px"></span></td>'
        + '<td><span class="skeleton-cell skeleton-pulse" style="width:40px"></span></td>'
        + '<td><span class="skeleton-cell skeleton-pulse" style="width:60px"></span></td>'
        + '<td><span class="skeleton-cell skeleton-pulse" style="width:60px"></span></td>'
        + '<td><span class="skeleton-cell skeleton-pulse" style="width:70px"></span></td>'
        + '<td><span class="skeleton-cell skeleton-pulse" style="width:55px"></span></td>'
        + '</tr>';
    }
    return rows;
  }

  // ── Row HTML builder ──────────────────────────────────────────────────────────
  function buildRowHtml(session) {
    var slug = session.session_id ? session.session_id.substring(0, 8) : '—';
    var titleAttr = session.ai_title
      ? ' title="' + escHtml(session.ai_title) + '"'
      : '';
    // For Codex sessions project is always absent/em-dash; render a muted
    // placeholder span so the PROJECT column shows '—' with .cell-placeholder
    // styling rather than a blank cell (SPEC F2 AC, T-PUX-01).
    var projectRaw = session.project;
    var project = (projectRaw && projectRaw !== '—')
      ? escHtml(projectRaw)
      : '<span class="cell-placeholder" title="Project context not applicable for Codex sessions">&mdash;</span>';
    var model = session.model ? escHtml(session.model) : '—';
    var turns = session.message_count != null ? escHtml(String(session.message_count)) : '—';
    var ctx = fmtTokens(session.context_size_tokens);
    // Phase E: when runtime is 'codex', Cost column always renders '—' because
    // cost tracking is not available for Codex sessions (SPEC §FR6, §4 out-of-scope).
    var runtime = getRuntime();
    var cost = (runtime === 'codex') ? '—' : fmtCost(session.cumulative_cost_usd, session.cost_known);
    var lastActivity = fmtRelativeDate(session.last_activity_at);
    var status = session.status || 'ended';

    return '<tr class="session-row"'
      + ' data-session-id="' + escHtml(session.session_id) + '"'
      + ' tabindex="0"'
      + ' role="row"'
      + ' aria-label="Session ' + escHtml(slug) + ', ' + escHtml(project) + ', ' + escHtml(status) + '"'
      + '>'
      + '<td class="cell-session"' + titleAttr + '>'
        + '<span class="session-slug">' + escHtml(slug) + '</span>'
      + '</td>'
      + '<td class="cell-project">' + project + '</td>'
      + '<td class="cell-model">' + model + '</td>'
      + '<td class="cell-turns">' + turns + '</td>'
      + '<td class="cell-context">' + escHtml(ctx) + '</td>'
      + '<td class="cell-cost">' + escHtml(cost) + '</td>'
      + '<td class="cell-last-activity">' + escHtml(lastActivity) + '</td>'
      + '<td class="cell-status">'
        + '<span class="status-dot" data-status="' + escHtml(status) + '">'
          + escHtml(status)
        + '</span>'
      + '</td>'
      + '</tr>';
  }

  // ── Apply filter ──────────────────────────────────────────────────────────────
  function applyFilter(rows) {
    if (!_filterText) { return rows; }
    return rows.filter(function (s) {
      var project = (s.project || '').toLowerCase();
      var sessionId = (s.session_id || '').toLowerCase();
      return project.indexOf(_filterText) !== -1
        || sessionId.indexOf(_filterText) !== -1;
    });
  }

  // ── Apply sort ────────────────────────────────────────────────────────────────
  function applySort(rows) {
    if (!_sortKey || _sortDir === 'none') { return rows; }
    var key = _sortKey;
    var dir = _sortDir;
    return rows.slice().sort(function (a, b) {
      var av = a[key];
      var bv = b[key];
      // Numeric sort for numeric fields; string sort for others
      if (typeof av === 'number' || typeof bv === 'number') {
        av = av == null ? -Infinity : Number(av);
        bv = bv == null ? -Infinity : Number(bv);
      } else {
        av = String(av == null ? '' : av).toLowerCase();
        bv = String(bv == null ? '' : bv).toLowerCase();
      }
      if (av < bv) { return dir === 'asc' ? -1 : 1; }
      if (av > bv) { return dir === 'asc' ? 1 : -1; }
      return 0;
    });
  }

  // ── Render table rows ─────────────────────────────────────────────────────────
  function renderTable(rows) {
    var tbody = document.getElementById('sessions-tbody');
    if (!tbody) { return; }

    var filtered = applyFilter(rows);
    var sorted = applySort(filtered);

    if (sorted.length === 0) {
      var noRows = rows.length === 0
        ? '<tr><td colspan="8" class="empty-state" style="padding:1rem;text-align:center;">'
          + 'No sessions found.</td></tr>'
        : '<tr><td colspan="8" class="empty-state" style="padding:1rem;text-align:center;">'
          + 'No sessions match the filter.</td></tr>';
      tbody.innerHTML = noRows;
      return;
    }

    tbody.innerHTML = sorted.map(buildRowHtml).join('');

    // Wire click and keyboard interactions on each row
    var rowEls = tbody.querySelectorAll('tr.session-row');
    rowEls.forEach(function (tr) {
      var sessionId = tr.getAttribute('data-session-id');
      tr.addEventListener('click', function () {
        openDrawer(sessionId);
      });
      // Keyboard: Enter/Space activates row (a11y — row is tabindex="0")
      tr.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          openDrawer(sessionId);
        }
      });
    });
  }

  // ── Drawer: render detail content ─────────────────────────────────────────────
  function renderDrawerContent(detail) {
    if (!detail) { return '<div class="drawer-error" role="alert">Session detail not available.</div>'; }

    var events = detail.event_timestamps || [];
    var eventsHtml = events.length > 0
      ? '<ul class="drawer-events">'
        + events.map(function (ts) {
            return '<li>' + escHtml(ts) + '</li>';
          }).join('')
        + '</ul>'
      : '<p style="font-size:0.82rem;color:var(--color-muted,#666)">No events recorded.</p>';

    return '<div class="drawer-field">'
        + '<span class="drawer-field-label">Session ID</span>'
        + '<span class="drawer-field-value drawer-field-value--mono drawer-session-id">'
          + escHtml((detail.session_id || '').substring(0, 8))
        + '</span>'
      + '</div>'
      + '<div class="drawer-field">'
        + '<span class="drawer-field-label">Project</span>'
        + '<span class="drawer-field-value">' + escHtml(detail.project || '—') + '</span>'
      + '</div>'
      + '<div class="drawer-field">'
        + '<span class="drawer-field-label">Model</span>'
        + '<span class="drawer-field-value drawer-model">' + escHtml(detail.model || '—') + '</span>'
      + '</div>'
      + '<div class="drawer-field">'
        + '<span class="drawer-field-label">Agent</span>'
        + '<span class="drawer-field-value drawer-agent">' + escHtml(detail.agent_name || '—') + '</span>'
      + '</div>'
      + (detail.ai_title
        ? '<div class="drawer-field">'
            + '<span class="drawer-field-label">AI Title</span>'
            + '<span class="drawer-field-value">' + escHtml(detail.ai_title) + '</span>'
          + '</div>'
        : '')
      + '<div class="drawer-field">'
        + '<span class="drawer-field-label">Status</span>'
        + '<span class="drawer-field-value">'
          + '<span class="status-dot drawer-status" data-status="' + escHtml(detail.status || 'ended') + '">'
            + escHtml(detail.status || 'ended')
          + '</span>'
        + '</span>'
      + '</div>'
      + '<div class="drawer-field">'
        + '<span class="drawer-field-label">Cost</span>'
        + '<span class="drawer-field-value drawer-field-value--cost drawer-cost">'
          + escHtml(fmtCost(detail.cumulative_cost_usd, detail.cost_known))
        + '</span>'
      + '</div>'
      + '<div class="drawer-field">'
        + '<span class="drawer-field-label">AI Turns</span>'
        + '<span class="drawer-field-value drawer-field-value--mono">'
          + escHtml(detail.message_count != null ? String(detail.message_count) : '—')
        + '</span>'
      + '</div>'
      + '<div class="drawer-field">'
        + '<span class="drawer-field-label">Context (tokens)</span>'
        + '<span class="drawer-field-value drawer-field-value--mono">'
          + escHtml(fmtTokens(detail.context_size_tokens))
        + '</span>'
      + '</div>'
      + '<div class="drawer-field">'
        + '<span class="drawer-field-label">Started</span>'
        + '<span class="drawer-field-value drawer-field-value--mono">'
          + escHtml(detail.started_at || '—')
        + '</span>'
      + '</div>'
      + '<div class="drawer-field">'
        + '<span class="drawer-field-label">Last Activity</span>'
        + '<span class="drawer-field-value drawer-field-value--mono">'
          + escHtml(fmtRelativeDate(detail.last_activity_at))
        + '</span>'
      + '</div>'
      + '<div class="drawer-field">'
        + '<span class="drawer-field-label">Event Timeline</span>'
        + eventsHtml
      + '</div>';
  }

  // ── Drawer: open ─────────────────────────────────────────────────────────────
  function openDrawer(sessionId) {
    var drawer = document.getElementById('session-drawer');
    if (!drawer) { return; }

    var runtime = getRuntime();
    var contentEl = drawer.querySelector('.session-drawer__content');
    if (!contentEl) { return; }

    // Show drawer with loading state
    drawer.removeAttribute('hidden');
    drawer.classList.add('open');
    drawer.setAttribute('aria-hidden', 'false');
    contentEl.innerHTML = '<div class="drawer-loading" aria-busy="true" aria-label="Loading session detail">'
      + '<span class="skeleton-cell skeleton-pulse" style="width:70%;height:0.85em;display:block;margin-bottom:0.5rem"></span>'
      + '<span class="skeleton-cell skeleton-pulse" style="width:50%;height:0.85em;display:block;margin-bottom:0.5rem"></span>'
      + '<span class="skeleton-cell skeleton-pulse" style="width:60%;height:0.85em;display:block"></span>'
      + '</div>';

    // Focus the close button as the first focusable element (a11y)
    var closeBtn = document.getElementById('drawer-close');
    if (closeBtn) {
      closeBtn.focus();
    }

    // Fetch session detail
    window.authedFetch('/api/sessions/' + encodeURIComponent(runtime) + '/' + encodeURIComponent(sessionId))
      .then(function (r) {
        if (!r.ok) {
          if (r.status === 404) {
            contentEl.innerHTML = '<div class="drawer-error" role="alert">Session not found.</div>';
          } else if (r.status === 401) {
            contentEl.innerHTML = '<div class="drawer-error" role="alert">'
              + '<strong>Authentication required.</strong> '
              + 'Re-open the panel via <code>dadaia panel start</code>.'
              + '</div>';
          } else {
            contentEl.innerHTML = '<div class="drawer-error" role="alert">'
              + 'Failed to load session detail (HTTP ' + escHtml(String(r.status)) + ').'
              + '</div>';
          }
          return null;
        }
        return r.json();
      })
      .then(function (detail) {
        if (!detail) { return; }
        contentEl.innerHTML = renderDrawerContent(detail);
      })
      .catch(function (err) {
        contentEl.innerHTML = '<div class="drawer-error" role="alert">'
          + 'Failed to load session detail: '
          + escHtml(err && err.message ? err.message : String(err))
          + '</div>';
      });
  }

  // ── Drawer: close ─────────────────────────────────────────────────────────────
  function closeDrawer() {
    var drawer = document.getElementById('session-drawer');
    if (!drawer) { return; }
    drawer.classList.remove('open');
    drawer.setAttribute('aria-hidden', 'true');
    // After transition completes (180ms), set hidden attribute
    setTimeout(function () {
      if (!drawer.classList.contains('open')) {
        drawer.setAttribute('hidden', '');
      }
    }, 200);
  }

  // ── Sort handler ──────────────────────────────────────────────────────────────
  function handleSortClick(th) {
    var key = th.getAttribute('data-sort-key');
    if (!key) { return; }

    // Reset all other header sort indicators
    var allTh = document.querySelectorAll('.sessions-table th[data-sort-key]');
    allTh.forEach(function (t) {
      if (t !== th) {
        t.setAttribute('data-sort-dir', 'none');
        t.removeAttribute('aria-sort');
      }
    });

    // Toggle direction on clicked header
    if (_sortKey === key) {
      _sortDir = _sortDir === 'asc' ? 'desc' : _sortDir === 'desc' ? 'none' : 'asc';
    } else {
      _sortKey = key;
      _sortDir = 'asc';
    }

    if (_sortDir === 'none') {
      _sortKey = null;
      th.setAttribute('data-sort-dir', 'none');
      th.removeAttribute('aria-sort');
    } else {
      th.setAttribute('data-sort-dir', _sortDir);
      th.setAttribute('aria-sort', _sortDir === 'asc' ? 'ascending' : 'descending');
    }

    renderTable(_allRows);
  }

  // ── Wire sort headers ─────────────────────────────────────────────────────────
  function wireSortHeaders() {
    var headers = document.querySelectorAll('.sessions-table th[data-sort-key]');
    headers.forEach(function (th) {
      th.setAttribute('tabindex', '0');
      th.setAttribute('role', 'columnheader');
      th.addEventListener('click', function () { handleSortClick(th); });
      th.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          handleSortClick(th);
        }
      });
    });
  }

  // ── Update meta line ──────────────────────────────────────────────────────────
  function updateMeta(total, filtered) {
    var meta = document.getElementById('sessions-meta');
    if (!meta) { return; }
    if (_filterText && filtered !== total) {
      meta.textContent = filtered + ' of ' + total + ' sessions';
    } else {
      meta.textContent = total + ' session' + (total === 1 ? '' : 's');
    }
  }

  // ── Fetch sessions ────────────────────────────────────────────────────────────
  function fetchSessions() {
    if (document.hidden) { return; }

    var runtime = getRuntime();
    var container = document.getElementById('sessions-table-container');

    window.authedFetch('/api/sessions?runtime=' + encodeURIComponent(runtime))
      .then(function (r) {
        if (!r.ok) {
          var tbody = document.getElementById('sessions-tbody');
          if (tbody) {
            if (r.status === 401) {
              tbody.innerHTML = '<tr><td colspan="8">'
                + '<div class="sessions-error-container" role="alert">'
                + '<h4 class="sessions-error-heading">Authentication required</h4>'
                + '<p class="sessions-error-body">Re-open the panel via <code>dadaia panel start</code>.</p>'
                + '</div></td></tr>';
            } else {
              tbody.innerHTML = '<tr><td colspan="8">'
                + '<div class="sessions-error-container" role="alert">'
                + '<h4 class="sessions-error-heading">Failed to load sessions</h4>'
                + '<p class="sessions-error-body">HTTP ' + escHtml(String(r.status)) + '.</p>'
                + '<button type="button" class="sessions-retry-btn" aria-label="Retry loading sessions">Retry</button>'
                + '</div></td></tr>';
              if (container) { container.setAttribute('aria-busy', 'false'); }
              var retryBtnEl = tbody.querySelector('.sessions-retry-btn');
              if (retryBtnEl) { retryBtnEl.addEventListener('click', function() { fetchSessions(); }); }
            }
            if (container) { container.setAttribute('aria-busy', 'false'); }
          }
          return null;
        }
        return r.json();
      })
      .then(function (data) {
        if (!data) { return; }

        _allRows = data.sessions || [];
        _loaded = true;

        updateBanner();
        renderTable(_allRows);
        renderDashboard(computeStats(_allRows, runtime));

        var filtered = applyFilter(_allRows);
        updateMeta(_allRows.length, filtered.length);
        updateLastUpdatedBadge();

        if (container) { container.setAttribute('aria-busy', 'false'); }
      })
      .catch(function (err) {
        var tbody = document.getElementById('sessions-tbody');
        if (tbody) {
          tbody.innerHTML = '<tr><td colspan="8">'
            + '<div class="sessions-error-container" role="alert">'
            + '<h4 class="sessions-error-heading">Failed to load sessions</h4>'
            + '<p class="sessions-error-body">'
            + escHtml(err && err.message ? err.message : String(err))
            + '</p>'
            + '<button type="button" class="sessions-retry-btn" aria-label="Retry loading sessions">Retry</button>'
            + '</div></td></tr>';
          var retryBtnEl = tbody.querySelector('.sessions-retry-btn');
          if (retryBtnEl) { retryBtnEl.addEventListener('click', function() { fetchSessions(); }); }
        }
        if (container) { container.setAttribute('aria-busy', 'false'); }
      });
  }

  // ── Auto-refresh ──────────────────────────────────────────────────────────────
  function startAutoRefresh() {
    if (_refreshTimer !== null) { clearInterval(_refreshTimer); }
    _refreshTimer = setInterval(function () {
      if (!document.hidden) { fetchSessions(); }
    }, AUTO_REFRESH_MS);
  }

  // ── Filter input handler ──────────────────────────────────────────────────────
  function onFilterInput(e) {
    var value = e.target.value;
    if (_filterTimer !== null) { clearTimeout(_filterTimer); }
    _filterTimer = setTimeout(function () {
      _filterText = value.trim().toLowerCase();
      renderTable(_allRows);
      var filtered = applyFilter(_allRows);
      updateMeta(_allRows.length, filtered.length);
    }, FILTER_DEBOUNCE_MS);
  }

  // ── Initialise ────────────────────────────────────────────────────────────────
  document.addEventListener('DOMContentLoaded', function () {
    var section = document.getElementById('section-sessions');
    if (!section) { return; } // No sessions section in the DOM — no-op

    // Wire sort headers
    wireSortHeaders();

    // Wire filter input
    var filterInput = document.getElementById('sessions-filter');
    if (filterInput) {
      filterInput.addEventListener('input', onFilterInput);
    }

    // Wire close button
    var closeBtn = document.getElementById('drawer-close');
    if (closeBtn) {
      closeBtn.addEventListener('click', function () { closeDrawer(); });
    }

    // Escape key closes the drawer when it's open
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') {
        var drawer = document.getElementById('session-drawer');
        if (drawer && drawer.classList.contains('open')) {
          closeDrawer();
        }
      }
    });

    // Visibility change: resume refresh when tab is foregrounded
    document.addEventListener('visibilitychange', function () {
      if (!document.hidden) {
        fetchSessions();
      }
    });

    // Render skeleton rows while initial fetch is in flight
    var tbody = document.getElementById('sessions-tbody');
    if (tbody) { tbody.innerHTML = renderSkeletonRows(8); }

    // Phase E: set banner state before first fetch so it's immediately visible
    // if the persisted runtime is 'codex'.
    updateBanner();

    // Subscribe to runtime changes. Phase E: call updateBanner() immediately so
    // the banner (or its absence) is visible before the fetch round-trip completes.
    // Then drop cached rows and refetch with the new runtime.
    document.addEventListener('dadaia:runtime-change', function () {
      updateBanner();
      _allRows = [];
      _sortKey = null;
      _sortDir = 'none';
      renderDashboard(computeStats([], getRuntime()));
      fetchSessions();
    });

    // Render cleared dashboard immediately on init (data loads asynchronously)
    renderDashboard(computeStats([], getRuntime()));

    // Initial fetch
    fetchSessions();

    // Start auto-refresh loop
    startAutoRefresh();
  });

  // ── Public API ────────────────────────────────────────────────────────────────
  window.Sessions = {
    isLoaded: function () { return _loaded; },
    reload: function () {
      _allRows = [];
      fetchSessions();
    },
  };

})();
