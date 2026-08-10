// sessions.js — Sessions tab UI (aggregated-cost dashboard only).
// panel-plumbing v0.1.52 FR2: the client list/table/drawer/sort/filter and the
// 10s auto-refresh were removed. The cost aggregate is computed server-side and
// served by GET /api/sessions; this module renders the 4-card summary + the
// cost-unknown banner from that envelope.
//
// Depends on: window.authedFetch() defined in core.js (loaded before this script)
//             window.Runtime (runtime.js) — get() + the dadaia:runtime-change event.
//
// API contract (SPEC §FR1 — normative):
//   GET /api/sessions?runtime=<runtime>
//     → {
//         runtime, total_sessions, active_sessions,
//         total_cost_usd (float | null), cost_known (bool),
//         total_messages, top_agent: {name, session_count} | null, generated_at
//       }
//
// Cost render mapping (SPEC §FR1 matrix, preserved client-side):
//   - cost-unknown runtime (codex/kimi)  → 'N/A'
//   - claude, total_cost_usd === null  → '—'
//   - otherwise                        → '$X.XX' (incl. '$0.00' for 0.0)
//
// Behaviour summary:
//   - On DOMContentLoaded: locate #section-sessions; if absent, exit (no-op).
//   - fetchAggregate() appends ?runtime= from Runtime.get() (fallback 'claude').
//   - renderDashboard(agg): renders the 4 stat cards from the aggregate envelope.
//   - updateBanner(): shows #sessions-banner for cost-unknown runtimes only.
//   - Re-fetch on the 'dadaia:runtime-change' CustomEvent (updateBanner first).
//   - Updates the #sessions-last-updated badge after each aggregate fetch.

(function () {
  'use strict';

  // ── Constants ─────────────────────────────────────────────────────────────────
  var DEFAULT_RUNTIME = 'claude';
  var CODEX_BANNER_TEXT = 'Cost not tracked for Codex';
  var KIMI_BANNER_TEXT = 'Cost not tracked for Kimi';

  // Runtimes with no per-event pricing — cost is unknown and never fabricated.
  // Codex and Kimi share this posture; the Cost card renders 'N/A' and the banner
  // appears for both.
  function isCostUnknownRuntime(runtime) {
    return runtime === 'codex' || runtime === 'kimi-code';
  }

  // ── Module state ─────────────────────────────────────────────────────────────
  var _loaded = false;         // has at least one successful aggregate fetch completed?

  // ── HTML escape helper ────────────────────────────────────────────────────────
  function escHtml(s) {
    return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
    });
  }

  // ── Runtime resolution ────────────────────────────────────────────────────────
  function getRuntime() {
    if (window.Runtime && typeof window.Runtime.get === 'function') {
      return window.Runtime.get();
    }
    return DEFAULT_RUNTIME;
  }

  // ── Compact integer formatter (k / M) ─────────────────────────────────────────
  function fmtCompact(n) {
    n = Number(n) || 0;
    if (n >= 1000000) { return (n / 1000000).toFixed(1) + 'M'; }
    if (n >= 1000) { return (n / 1000).toFixed(1) + 'k'; }
    return String(n);
  }

  // ── Banner: show/hide the "Cost not tracked for …" notice ────────────────────
  // Called before each fetchAggregate() and on every dadaia:runtime-change. The
  // #sessions-banner element starts with the HTML [hidden] attribute (set in the
  // scaffold); JS shows it only when the runtime is cost-unknown (codex/kimi).
  function updateBanner() {
    var banner = document.getElementById('sessions-banner');
    if (!banner) { return; }
    var runtime = getRuntime();
    if (isCostUnknownRuntime(runtime)) {
      banner.textContent = (runtime === 'kimi-code') ? KIMI_BANNER_TEXT : CODEX_BANNER_TEXT;
      banner.removeAttribute('hidden');
    } else {
      banner.textContent = '';
      banner.setAttribute('hidden', '');
    }
  }

  // ── Dashboard: render the 4 stat cards from the server aggregate ─────────────
  // `agg` is the /api/sessions envelope, or null before the first fetch resolves
  // (in which case placeholder zeros/dashes are rendered).
  function renderDashboard(agg) {
    var dash = document.getElementById('sessions-dashboard');
    if (!dash) { return; }

    var runtime = getRuntime();
    var isCostUnknown = isCostUnknownRuntime(runtime);

    var totalSessions = agg ? agg.total_sessions : 0;
    var activeSessions = agg ? agg.active_sessions : 0;
    var totalCostUsd = agg ? agg.total_cost_usd : null;
    var totalMessages = agg ? agg.total_messages : 0;
    var topAgent = agg ? agg.top_agent : null;

    // Cost render mapping (SPEC §FR1): 'N/A' for cost-unknown runtimes, '—' when
    // claude cost is null, '$X.XX' otherwise (incl. '$0.00' for a known 0.0).
    var costVal = isCostUnknown ? 'N/A'
      : (totalCostUsd == null ? '—' : '$' + Number(totalCostUsd).toFixed(2));
    var costClass = (!isCostUnknown && totalCostUsd != null)
      ? 'sessions-stat-value sessions-stat-value--cost'
      : 'sessions-stat-value';
    var costSub = isCostUnknown
      ? ('not tracked for ' + (runtime === 'kimi-code' ? 'Kimi' : 'Codex'))
      : '&nbsp;';

    var activeSub = activeSessions > 0
      ? (escHtml(String(activeSessions)) + ' active')
      : 'none active';

    var turnsStr = fmtCompact(totalMessages);

    var agentName = (topAgent && topAgent.name) ? escHtml(topAgent.name) : '—';
    var agentCount = (topAgent && topAgent.session_count) ? topAgent.session_count : 0;
    var agentSub = (topAgent && agentCount > 0)
      ? escHtml(String(agentCount)) + ' session' + (agentCount !== 1 ? 's' : '')
      : '&nbsp;';

    dash.innerHTML =
      '<div class="sessions-stat-card">'
        + '<span class="sessions-stat-label">Total Sessions</span>'
        + '<span class="sessions-stat-value">' + escHtml(String(totalSessions)) + '</span>'
        + '<span class="sessions-stat-sub">' + activeSub + '</span>'
      + '</div>'
      + '<div class="sessions-stat-card">'
        + '<span class="sessions-stat-label">Total Cost</span>'
        + '<span class="' + costClass + '">' + escHtml(costVal) + '</span>'
        + '<span class="sessions-stat-sub">' + costSub + '</span>'
      + '</div>'
      + '<div class="sessions-stat-card">'
        + '<span class="sessions-stat-label">AI Turns</span>'
        + '<span class="sessions-stat-value">' + escHtml(turnsStr) + '</span>'
        + '<span class="sessions-stat-sub">&nbsp;</span>'
      + '</div>'
      + '<div class="sessions-stat-card">'
        + '<span class="sessions-stat-label">Top Agent</span>'
        + '<span class="sessions-stat-value" style="font-size:1.05rem;line-height:1.3;">' + agentName + '</span>'
        + '<span class="sessions-stat-sub">' + agentSub + '</span>'
      + '</div>';
  }

  // ── Update the "Last updated" badge ────────────────────────────────────────────
  function updateLastUpdatedBadge() {
    var badge = document.getElementById('sessions-last-updated');
    if (!badge) { return; }
    badge.textContent = 'Updated: ' + new Date().toLocaleTimeString();
  }

  // ── Fetch the server-side aggregate and render the dashboard ─────────────────
  function fetchAggregate() {
    var runtime = getRuntime();

    window.authedFetch('/api/sessions?runtime=' + encodeURIComponent(runtime))
      .then(function (r) {
        if (!r.ok) { return null; }
        return r.json();
      })
      .then(function (agg) {
        if (!agg) {
          renderDashboard(null);
          updateLastUpdatedBadge();
          return;
        }
        _loaded = true;
        updateBanner();
        renderDashboard(agg);
        updateLastUpdatedBadge();
      })
      .catch(function () {
        renderDashboard(null);
      });
  }

  // ── Initialise ────────────────────────────────────────────────────────────────
  document.addEventListener('DOMContentLoaded', function () {
    var section = document.getElementById('section-sessions');
    if (!section) { return; } // No sessions section in the DOM — no-op

    // Set banner state and a cleared dashboard before the first fetch resolves.
    updateBanner();
    renderDashboard(null);

    // Re-fetch when the global runtime changes (runtime.js dispatches the event).
    // updateBanner() runs first so the banner (or its absence) is visible before
    // the fetch round-trip completes.
    document.addEventListener('dadaia:runtime-change', function () {
      updateBanner();
      renderDashboard(null);
      fetchAggregate();
    });

    // Initial fetch.
    fetchAggregate();
  });

  // ── Public API ────────────────────────────────────────────────────────────────
  window.Sessions = {
    isLoaded: function () { return _loaded; },
    reload: function () { fetchAggregate(); },
  };

})();
