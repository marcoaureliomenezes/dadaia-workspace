"""Static frontend assets for the Dadaia Workspace Panel.

PANEL_CSS  — design tokens from specs/memory/architecture.html + structural rules from
             the frontend mockup (index.html, memories.html, memory-view.html).
             Body-text links use --color-accent-dark (#2d7d9a, WCAG AA ~5:1 on #fafafa).
             #7ec8e3 is decorative accent only (left-border on primary card, hover glow).

PANEL_JS   — auto-refresh /api/servers every 5s; tab switching; TTL relative formatter.
             Vanilla JS, no frameworks, no eval().

LOGO_RHINO_24 / LOGO_RHINO_16 — inline SVG for the rhino logomark, loaded at import
             time from assets/. currentColor only; zero hardcoded hex.
             (spec: dadaia-workspace-brand-identity-v1 T-BR-03/04/05)
"""

from pathlib import Path

_ASSETS_DIR = Path(__file__).parent / "assets"
LOGO_RHINO_24: str = (_ASSETS_DIR / "logo-rhino-24.svg").read_text(encoding="utf-8")
LOGO_RHINO_16: str = (_ASSETS_DIR / "logo-rhino-16.svg").read_text(encoding="utf-8")

PALETTE: dict[str, str] = {
    "accent": "#9cddc8",
    "accent_secondary": "#bfd8ad",
    "warning_bg": "#ddd9ab",
    "alert": "#f7af63",
    "cost": "#633d2e",
}
"""Canonical brand palette (spec: dadaia-workspace-brand-identity-v1 SPEC.md)."""

PANEL_CSS: str = """
:root {
  --color-bg:            #fafafa;
  --color-surface:       #ffffff;
  --color-text:          #222222;
  --color-heading:       #111111;
  --color-muted:         #666666;
  --color-border:        #dddddd;
  --color-border-strong: #333333;
  --color-accent:        #9cddc8; /* was #7ec8e3 — brand-identity-v1 */
  --color-accent-dark:   #2d7d9a;
  --color-code-bg:       #f0f0f0;
  --color-th-bg:         #eeeeee;
  --color-primary-ring:  #9cddc8; /* was #7ec8e3 — brand-identity-v1 */
  --color-primary-bg:    #f0fbf7; /* was #f0faff — brand-identity-v1 */
  --color-accent-secondary: #bfd8ad; /* brand-identity-v1 */
  --color-warning-bg:    #ddd9ab; /* brand-identity-v1 */
  --color-alert:         #f7af63; /* brand-identity-v1 */
  --color-cost:          #633d2e; /* brand-identity-v1 */
  --color-active-dot:    #3aaa6e;
  --color-stale-dot:     #cc7700;
  --color-row-hover:     #f5f5f5;
  --color-placeholder-bg: #f7f7f7;
  --color-card-hover:    #f8feff;

  --font-stack: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
  --font-mono:  ui-monospace, "SFMono-Regular", Consolas, monospace;

  --radius:      4px;
  --radius-card: 6px;
  --space-xs:    0.3rem;
  --space-sm:    0.6rem;
  --space-md:    1rem;
  --space-lg:    1.5rem;
  --space-xl:    2rem;
  --topbar-h:    52px;
  --nav-h:       44px;
}

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

body {
  font-family: var(--font-stack);
  background: var(--color-bg);
  color: var(--color-text);
  line-height: 1.55;
  min-height: 100vh;
}

a { color: var(--color-accent-dark); text-decoration: none; }
a:hover, a:focus { text-decoration: underline; }
a:focus-visible { outline: 2px solid var(--color-accent, #9cddc8); outline-offset: 2px; border-radius: 2px; }

code {
  font-family: var(--font-mono);
  background: var(--color-code-bg);
  padding: 0.1em 0.3em;
  border-radius: var(--radius);
  font-size: 0.88em;
}

/* ── Top bar ─────────────────────────────────────── */
.topbar {
  position: sticky;
  top: 0;
  z-index: 100;
  height: var(--topbar-h);
  background: var(--color-surface);
  border-bottom: 2px solid var(--color-border-strong);
  display: flex;
  align-items: center;
  padding: 0 var(--space-lg);
  gap: var(--space-md);
}

.topbar-logo { color: var(--color-cost, #633d2e); display: inline-flex; align-items: center; margin-right: 0.5rem; }
.topbar-logo svg { width: 24px; height: 24px; display: block; }

.topbar-wordmark {
  font-size: 1.1rem;
  font-weight: 700;
  color: var(--color-cost, #633d2e); /* brand-identity-v1 T-BR-07: high-contrast brown (AAA on white) */
  letter-spacing: -0.01em;
}
.topbar-wordmark span { color: var(--color-accent-dark); }
.topbar-divider { width: 1px; height: 24px; background: var(--color-border); }
.topbar-subtitle { color: var(--color-muted); font-size: 0.9rem; }
.topbar-badge {
  margin-left: auto;
  background: var(--color-accent, #9cddc8);
  color: var(--color-heading);
  font-size: 0.78rem;
  font-weight: 600;
  padding: 0.2rem 0.6rem;
  border-radius: 20px;
  white-space: nowrap;
}

/* ── Navigation tabs ─────────────────────────────── */
.nav-tabs {
  background: var(--color-surface);
  border-bottom: 1px solid var(--color-border);
  display: flex;
  padding: 0 var(--space-lg);
  gap: 0;
}

.nav-tab {
  display: inline-block;
  padding: 0.65rem 1.1rem;
  font-size: 0.92rem;
  color: var(--color-muted);
  border-bottom: 3px solid transparent;
  cursor: pointer;
  background: none;
  border-top: none;
  border-left: none;
  border-right: none;
  font-family: inherit;
  transition: color 0.15s, border-color 0.15s;
  white-space: nowrap;
}
.nav-tab:hover { color: var(--color-text); }
.nav-tab:focus-visible { outline: 2px solid var(--color-accent, #9cddc8); outline-offset: -2px; }
.nav-tab.active {
  color: var(--color-heading);
  font-weight: 600;
  border-bottom-color: var(--color-accent, #9cddc8);
}

/* ── Main content ───────────────────────────────── */
.main {
  max-width: 1024px;
  margin: 0 auto;
  padding: var(--space-xl) var(--space-lg);
}

.section { display: none; }
.section.active { display: block; }

.section-header {
  margin-bottom: var(--space-lg);
  padding-bottom: var(--space-sm);
  border-bottom: 1px solid var(--color-border);
}
.section-header h2 { font-size: 1.15rem; color: var(--color-heading); }
.section-header p { font-size: 0.88rem; color: var(--color-muted); margin-top: 0.25rem; }

/* ── Servers section ─────────────────────────────── */
.refresh-notice {
  font-size: 0.8rem;
  color: var(--color-muted);
  text-align: right;
  margin-bottom: var(--space-sm);
}

#refresh-status {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--color-active-dot);
  margin-right: 4px;
  vertical-align: middle;
  transition: opacity 0.3s;
}
#refresh-status.updating { opacity: 0.3; }

.group-label {
  font-size: 0.8rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--color-muted);
  margin: var(--space-lg) 0 var(--space-xs) 0;
}
.group-label:first-of-type { margin-top: 0; }

table.servers-table {
  border-collapse: collapse;
  width: 100%;
  margin-bottom: var(--space-md);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  overflow: hidden;
  font-size: 0.92rem;
}
table.servers-table th,
table.servers-table td {
  padding: 0.5rem 0.75rem;
  border-bottom: 1px solid var(--color-border);
  text-align: left;
  vertical-align: middle;
}
table.servers-table th {
  background: var(--color-th-bg);
  font-size: 0.78rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--color-muted);
}
table.servers-table tr:last-child td { border-bottom: none; }
table.servers-table tbody tr:hover { background: var(--color-row-hover); }

.status-active { color: var(--color-active-dot); font-weight: 600; }
.status-stale  { color: var(--color-stale-dot); }

.port-badge {
  font-family: var(--font-mono);
  font-size: 0.88em;
  background: var(--color-code-bg);
  padding: 0.15em 0.4em;
  border-radius: var(--radius);
  border: 1px solid var(--color-border);
}

.empty-state {
  padding: var(--space-xl);
  text-align: center;
  background: var(--color-surface);
  border: 1px dashed var(--color-border);
  border-radius: var(--radius-card);
  color: var(--color-muted);
}
.empty-state code { display: inline-block; margin-top: var(--space-sm); font-size: 0.85em; }

/* ── Memory cards grid ───────────────────────────── */
.context-count {
  font-size: 0.85rem;
  color: var(--color-muted);
  margin-bottom: var(--space-md);
}
.context-count strong { color: var(--color-text); }

.cards-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: var(--space-md);
}

.context-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  overflow: hidden;
  transition: box-shadow 0.15s;
}
.context-card:hover { box-shadow: 0 2px 8px rgba(0,0,0,0.08); }
.context-card.primary {
  border-left: 4px solid var(--color-primary-ring, #9cddc8);
  background: var(--color-primary-bg, #f0fbf7);
}

.card-header {
  padding: var(--space-md) var(--space-md) var(--space-sm);
  display: flex;
  align-items: flex-start;
  gap: var(--space-sm);
}
.card-name { font-size: 0.97rem; font-weight: 700; color: var(--color-heading); flex: 1; }
.card-primary-badge {
  flex-shrink: 0;
  font-size: 0.7rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  background: var(--color-accent, #9cddc8);
  color: var(--color-heading);
  padding: 0.2em 0.5em;
  border-radius: 20px;
}
.card-meta {
  padding: 0 var(--space-md) var(--space-sm);
  font-size: 0.83rem;
  color: var(--color-muted);
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-sm);
}

.card-links { border-top: 1px solid var(--color-border); }
.memory-link {
  display: flex;
  align-items: center;
  padding: 0.5rem var(--space-md);
  font-size: 0.87rem;
  color: var(--color-accent-dark);
  border-bottom: 1px solid var(--color-border);
  gap: var(--space-sm);
  transition: background 0.1s;
}
.memory-link:last-child { border-bottom: none; }
.memory-link:hover, .memory-link:focus { background: var(--color-card-hover); text-decoration: none; }
.memory-link:focus-visible { outline: 2px solid var(--color-accent, #9cddc8); outline-offset: -2px; }
.memory-link-icon { font-size: 0.9em; color: var(--color-muted); flex-shrink: 0; width: 1.2em; text-align: center; }
.memory-link-label { flex: 1; }
.memory-link-arrow { color: var(--color-border); font-size: 0.9em; flex-shrink: 0; }

/* ── Agents placeholder card ─────────────────────── */
.placeholder-card {
  background: var(--color-placeholder-bg);
  border: 1px dashed var(--color-border);
  border-radius: var(--radius-card);
  padding: var(--space-xl);
  text-align: center;
  color: var(--color-muted);
  max-width: 480px;
}
.placeholder-card .placeholder-title {
  font-size: 1rem;
  font-weight: 600;
  color: var(--color-muted);
  margin-bottom: var(--space-sm);
}
.placeholder-card .placeholder-body { font-size: 0.88rem; }

/* ── panel-section base ──────────────────────────── */
.panel-section { display: none; }
.panel-section.active { display: block; }

/* ── agents-grid ─────────────────────────────────── */
.card-grid.agents-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
  gap: 1rem;
}
.agent-card {
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: 1rem;
  background: var(--color-surface);
}
.agent-card-header {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 0.5rem;
}
.agent-card-header h3 { margin: 0; font-size: 1rem; color: var(--color-cost, #633d2e); }
.agent-model { font-size: 0.85rem; color: #666; font-family: ui-monospace, monospace; }
.agent-metrics {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.5rem;
  margin: 0.75rem 0;
  font-size: 0.9rem;
}
.agent-metric .label { display: block; font-size: 0.7rem; text-transform: uppercase; color: #666; }
.agent-metric .value { display: block; font-weight: 600; }
.agent-cost-unknown { color: #999; font-style: italic; }
.agent-suspect-badge {
  background: var(--color-alert, #f7af63);
  color: #3d2a00; /* dark on amber — WCAG AA contrast ~6.3:1 */
  padding: 0.15rem 0.5rem;
  border-radius: 4px;
  font-size: 0.75rem;
}
.context-breakdown { margin: 0.5rem 0; }
.context-breakdown-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.85rem;
  margin: 0.25rem 0;
}
.context-bar { flex: 1; height: 0.5rem; background: #eee; border-radius: 4px; overflow: hidden; }
.context-bar-fill { height: 100%; background: var(--color-accent, #9cddc8); }
.warning-banner {
  padding: 0.75rem 1rem;
  background: var(--color-warning-bg, #ddd9ab);
  color: #3d3600;
  border-radius: 6px;
  margin-bottom: 1rem;
}
.sessions-drilldown { margin-top: 0.5rem; }
.sessions-drilldown table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
.sessions-drilldown th,
.sessions-drilldown td { padding: 0.25rem 0.5rem; text-align: left; border-bottom: 1px solid #eee; }
.sessions-drilldown button[aria-expanded] {
  background: none;
  border: none;
  color: var(--color-accent-dark, #2d7d9a);
  cursor: pointer;
  font-size: 0.85rem;
  padding: 0.25rem 0;
  font-family: inherit;
  text-decoration: underline;
}
.sessions-drilldown button[aria-expanded]:hover { color: var(--color-cost, #633d2e); }
.sessions-drilldown button[aria-expanded]:focus-visible {
  outline: 2px solid var(--color-accent, #9cddc8);
  outline-offset: 2px;
}
.error-state { color: #c0392b; font-size: 0.9rem; }

/* ── Workflows 2-pane layout ─────────────────────── */
.workflows-pane {
  display: grid;
  grid-template-columns: 260px 1fr;
  gap: var(--space-md);
  align-items: start;
}
@media (max-width: 640px) {
  .workflows-pane { grid-template-columns: 1fr; }
  .workflows-detail { display: none; }
  .workflows-detail.visible { display: block; }
}

/* Left list */
.workflows-list {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  background: var(--color-surface);
  overflow: hidden;
}
.workflow-list-item {
  display: block;
  width: 100%;
  text-align: left;
  padding: 0.65rem var(--space-md);
  font-size: 0.9rem;
  font-family: inherit;
  background: none;
  border: none;
  border-bottom: 1px solid var(--color-border);
  cursor: pointer;
  color: var(--color-text);
  transition: background 0.1s;
}
.workflow-list-item:last-child { border-bottom: none; }
.workflow-list-item:hover { background: var(--color-row-hover); }
.workflow-list-item.selected {
  background: var(--color-primary-bg, #f0fbf7);
  border-left: 3px solid var(--color-accent, #9cddc8);
  color: var(--color-heading);
  font-weight: 600;
}
.workflow-list-item:focus-visible {
  outline: 2px solid var(--color-accent, #9cddc8);
  outline-offset: -2px;
}
.workflow-item-name { display: block; font-size: 0.88rem; font-weight: 600; }
.workflow-item-source { display: block; font-size: 0.75rem; color: var(--color-muted); font-family: var(--font-mono); margin-top: 0.1rem; }

/* Right detail panel */
.workflows-detail {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  background: var(--color-surface);
  padding: var(--space-md);
  min-height: 240px;
}
.workflows-detail-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 200px;
  color: var(--color-muted);
  font-size: 0.9rem;
  text-align: center;
}
.workflow-detail-name {
  font-size: 1.05rem;
  font-weight: 700;
  color: var(--color-cost, #633d2e);
  margin-bottom: var(--space-xs);
}
.workflow-detail-source {
  font-size: 0.78rem;
  color: var(--color-muted);
  font-family: var(--font-mono);
  margin-bottom: var(--space-sm);
}
.workflow-detail-description {
  font-size: 0.9rem;
  color: var(--color-text);
  margin-bottom: var(--space-md);
  padding-bottom: var(--space-sm);
  border-bottom: 1px solid var(--color-border);
}
.workflow-detail-description.no-desc { color: var(--color-muted); font-style: italic; }

/* SVG stepper diagram */
.workflow-diagram {
  margin-top: var(--space-md);
  overflow-x: auto;
}
.workflow-diagram svg { display: block; }

/* Agent chips (detail pane) */
.workflow-agent-chips { display: flex; flex-wrap: wrap; gap: 0.25rem; margin-top: var(--space-sm); }
.workflow-agent-chip {
  background: var(--color-accent, #9cddc8);
  color: #222;
  border: none;
  padding: 0.2rem 0.6rem;
  border-radius: 12px;
  font-size: 0.75rem;
  cursor: pointer;
  font-family: inherit;
}
.workflow-agent-chip:hover { background: var(--color-accent-secondary, #bfd8ad); }
.workflow-agent-chip:focus { outline: 2px solid var(--color-cost, #633d2e); outline-offset: 2px; }
"""

PANEL_JS: str = """
(function () {
  'use strict';

  // ── Token bootstrap ───────────────────────────────────────────────
  // On first load the panel URL carries ?token=<value>.
  // Persist it to sessionStorage so auth survives tab navigation,
  // then strip from the URL bar so it is not accidentally shared.
  (function bootstrapToken() {
    var params = new URLSearchParams(location.search);
    var urlToken = params.get('token');
    if (urlToken) {
      sessionStorage.setItem('panel_token', urlToken);
      params.delete('token');
      var newSearch = params.toString();
      var newUrl = location.pathname + (newSearch ? '?' + newSearch : '') + location.hash;
      history.replaceState(null, '', newUrl);
    }
  })();

  // ── Authenticated fetch wrapper ────────────────────────────────────
  // All /api/* calls must carry Authorization: Bearer <token>.
  // If the token is absent the call is still made so callers see the 401.
  function authedFetch(url, opts) {
    opts = opts || {};
    var token = sessionStorage.getItem('panel_token') || '';
    var headers = opts.headers ? Object.assign({}, opts.headers) : {};
    if (token) {
      headers['Authorization'] = 'Bearer ' + token;
    }
    return fetch(url, Object.assign({}, opts, { headers: headers }));
  }

  // ── Tab switching ──────────────────────────────────────────────────
  var tabs = document.querySelectorAll('.nav-tab');
  var sections = document.querySelectorAll('.section');

  tabs.forEach(function (tab) {
    tab.addEventListener('click', function () {
      var target = tab.getAttribute('data-section');
      tabs.forEach(function (t) {
        t.classList.remove('active');
        t.setAttribute('aria-selected', 'false');
      });
      sections.forEach(function (s) { s.classList.remove('active'); });
      tab.classList.add('active');
      tab.setAttribute('aria-selected', 'true');
      var sec = document.getElementById('section-' + target);
      if (sec) { sec.classList.add('active'); }
    });
  });

  // ── Tab keyboard navigation (ARIA APG: tabs pattern) ──────────────
  // ArrowRight/ArrowLeft cycle; Home/End jump; Enter/Space activate.
  var tabList = Array.prototype.slice.call(tabs);
  tabList.forEach(function (tab, idx) {
    tab.addEventListener('keydown', function (e) {
      var key = e.key;
      var total = tabList.length;
      var targetIdx = -1;

      if (key === 'ArrowRight') {
        targetIdx = (idx + 1) % total;
      } else if (key === 'ArrowLeft') {
        targetIdx = (idx - 1 + total) % total;
      } else if (key === 'Home') {
        targetIdx = 0;
      } else if (key === 'End') {
        targetIdx = total - 1;
      } else if (key === 'Enter' || key === ' ') {
        tab.click();
        e.preventDefault();
        return;
      }

      if (targetIdx >= 0) {
        e.preventDefault();
        tabList[targetIdx].focus();
        tabList[targetIdx].click();
      }
    });
  });

  // ── TTL formatter ──────────────────────────────────────────────────
  // Given an ISO-8601 expiry string (e.g. "2026-05-16T18:00:00+00:00"),
  // returns a relative duration like "6h 42m" or "expired".
  function formatTTL(expiresAt) {
    if (!expiresAt) { return '—'; }
    var expiry = new Date(expiresAt);
    var now = new Date();
    var diffMs = expiry - now;
    if (diffMs <= 0) { return 'expired'; }
    var diffSec = Math.floor(diffMs / 1000);
    var h = Math.floor(diffSec / 3600);
    var m = Math.floor((diffSec % 3600) / 60);
    if (h > 0) { return h + 'h ' + m + 'm'; }
    if (m > 0) { return m + 'm'; }
    return diffSec + 's';
  }

  // ── Auto-refresh status indicator ─────────────────────────────────
  var statusDot = document.getElementById('refresh-status');
  var statusLabel = document.getElementById('refresh-label');
  var lastUpdated = new Date();

  function formatAge() {
    var seconds = Math.round((new Date() - lastUpdated) / 1000);
    if (seconds < 5) { return 'Last updated just now'; }
    if (seconds < 60) { return 'Last updated ' + seconds + 's ago'; }
    return 'Last updated ' + Math.floor(seconds / 60) + 'm ago';
  }

  function updateStatusLabel() {
    if (statusLabel) { statusLabel.textContent = formatAge(); }
  }

  // ── Server table renderer ──────────────────────────────────────────
  function escHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function buildServersHTML(data) {
    var groups = data.groups;
    if (!groups || groups.length === 0) {
      return '<div class="empty-state">'
        + 'Nenhum servidor rodando. Rode '
        + '<code>dadaia server register --port X --project Y</code>.'
        + '</div>';
    }
    var html = '';
    groups.forEach(function (group) {
      html += '<div class="group-label">' + escHtml(group.group_label) + '</div>';
      if (!group.rows || group.rows.length === 0) { return; }
      html += '<table class="servers-table"><thead><tr>'
        + '<th>Port</th><th>Project</th><th>URL</th>'
        + '<th>Status</th><th>TTL restante</th><th>PID</th>'
        + '</tr></thead><tbody>';
      group.rows.forEach(function (row) {
        var statusClass = row.status === 'active' ? 'status-active' : 'status-stale';
        var statusSymbol = row.status === 'active' ? '&#9679;' : '&#9675;';
        var urlCell = row.url
          ? '<a href="' + escHtml(row.url) + '" target="_blank" rel="noopener noreferrer">'
            + escHtml(row.url) + '</a>'
          : '—';
        var pid = row.pid != null ? '<code>' + escHtml(String(row.pid)) + '</code>' : '—';
        var ttl = formatTTL(row.expires_at);
        html += '<tr>'
          + '<td><span class="port-badge">' + escHtml(String(row.port)) + '</span></td>'
          + '<td>' + escHtml(row.project) + '</td>'
          + '<td>' + urlCell + '</td>'
          + '<td><span class="' + statusClass + '">' + statusSymbol + ' ' + escHtml(row.status) + '</span></td>'
          + '<td>' + escHtml(ttl) + '</td>'
          + '<td>' + pid + '</td>'
          + '</tr>';
      });
      html += '</tbody></table>';
    });
    return html;
  }

  // ── Fetch and refresh servers ──────────────────────────────────────
  function fetchServers() {
    if (statusDot) { statusDot.classList.add('updating'); }
    fetch('/api/servers')
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var container = document.getElementById('servers-content');
        if (container) { container.innerHTML = buildServersHTML(data); }
        lastUpdated = new Date();
        if (statusDot) { statusDot.classList.remove('updating'); }
        updateStatusLabel();
      })
      .catch(function () {
        if (statusDot) { statusDot.classList.remove('updating'); }
        lastUpdated = new Date();
        updateStatusLabel();
      });
  }

  setInterval(fetchServers, 5000);
  setInterval(updateStatusLabel, 5000);

  // ── agents tab ────────────────────────────────────────────────────────
  var Agents = (function () {
    var loaded = false;
    var fmtUsd = function (v) { return v == null ? '—' : '$' + v.toFixed(2); };
    function escHtmlA(s) {
      return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) {
        return {'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c];
      });
    }
    function escAttrA(s) { return escHtmlA(s); }
    function fmtDate(iso) {
      if (!iso) { return '—'; }
      return iso.slice(0, 16).replace('T', ' ');
    }
    function renderCard(a) {
      var costHtml = a.cost_known
        ? escHtmlA(fmtUsd(a.total_cost_usd))
        : '<span class="agent-cost-unknown">custo indisponível</span>';
      var suspect = a.suspect_count > 0
        ? '<span class="agent-suspect-badge" title="Eventos com tokens fora dos limites">' + a.suspect_count + ' suspeitos</span>'
        : '';
      var breakdown = (a.context_breakdown || []).map(function (cb) {
        var pct = cb.cost_fraction != null ? (cb.cost_fraction * 100).toFixed(1) : '—';
        var fillW = cb.cost_fraction != null ? (cb.cost_fraction * 100) : 0;
        return '<div class="context-breakdown-row" aria-label="' + escAttrA(cb.context_name) + ': ' + pct + '% do custo total">'
          + '<span>' + escHtmlA(cb.context_name) + '</span>'
          + '<span class="context-bar"><span class="context-bar-fill" style="width: ' + fillW + '%"></span></span>'
          + '<span>' + pct + '%</span>'
          + '</div>';
      }).join('');
      return '<article class="agent-card" data-agent-id="' + escAttrA(a.agent_id) + '">'
        + '<div class="agent-card-header">'
        + '<h3>' + escHtmlA(a.display_name) + ' ' + suspect + '</h3>'
        + '<span class="agent-model">' + escHtmlA(a.dominant_model || '—') + '</span>'
        + '</div>'
        + '<div class="agent-metrics">'
        + '<div class="agent-metric"><span class="label">Sessões</span><span class="value">' + a.session_count + '</span></div>'
        + '<div class="agent-metric"><span class="label">Custo total</span><span class="value">' + costHtml + '</span></div>'
        + '<div class="agent-metric"><span class="label">Última atividade</span><span class="value">' + escHtmlA(fmtDate(a.last_activity_at)) + '</span></div>'
        + '</div>'
        + '<div class="context-breakdown">' + breakdown + '</div>'
        + '<div class="sessions-drilldown">'
        + '<button type="button" data-action="toggle-sessions" aria-expanded="false" aria-controls="sessions-' + escAttrA(a.agent_id) + '">'
        + 'Mostrar sessões recentes'
        + '</button>'
        + '<div id="sessions-' + escAttrA(a.agent_id) + '" hidden></div>'
        + '</div>'
        + '</article>';
    }
    function renderSessionsTable(rows) {
      if (rows.length === 0) { return '<p>Nenhuma sessão recente.</p>'; }
      var head = '<thead><tr><th>Sessão</th><th>Data</th><th>Custo</th><th>Branch</th><th>Contexto</th></tr></thead>';
      var body = rows.map(function (s) {
        return '<tr>'
          + '<td><code>' + escHtmlA(s.session_id_prefix) + '…</code></td>'
          + '<td>' + escHtmlA(s.date) + '</td>'
          + '<td>' + (s.cost_usd != null ? '$' + s.cost_usd.toFixed(2) : '—') + '</td>'
          + '<td>' + escHtmlA(s.git_branch || '—') + '</td>'
          + '<td>' + escHtmlA(s.context_slug || 'unassigned') + '</td>'
          + '</tr>';
      }).join('');
      return '<table>' + head + '<tbody>' + body + '</tbody></table>';
    }
    function applyHashFilter() {
      var m = location.hash.match(/^#agents[?]filter=(.+)$/);
      if (!m) { return; }
      var want = decodeURIComponent(m[1]);
      document.querySelectorAll('.agent-card').forEach(function (card) {
        card.style.display = card.dataset.agentId === want ? '' : 'none';
      });
    }
    function toggleSessions(btn) {
      var expanded = btn.getAttribute('aria-expanded') === 'true';
      var targetEl = document.getElementById(btn.getAttribute('aria-controls'));
      if (expanded) {
        btn.setAttribute('aria-expanded', 'false');
        targetEl.hidden = true;
        return;
      }
      btn.setAttribute('aria-expanded', 'true');
      targetEl.hidden = false;
      if (targetEl.dataset.loaded === '1') { return; }
      var agentId = btn.closest('.agent-card').dataset.agentId;
      targetEl.innerHTML = '<p>Carregando…</p>';
      authedFetch('/api/agents/' + encodeURIComponent(agentId) + '/sessions?limit=10')
        .then(function (r) { return r.json(); })
        .then(function (data) {
          targetEl.innerHTML = renderSessionsTable(data.sessions || []);
          targetEl.dataset.loaded = '1';
          btn.textContent = 'Ocultar sessões recentes';
        })
        .catch(function (e) {
          targetEl.innerHTML = '<p class="error-state">Falha: ' + escHtmlA(e.message) + '</p>';
        });
    }
    function render(data) {
      var meta = document.getElementById('agents-meta');
      if (meta) {
        meta.textContent = data.agents.length + ' agente' + (data.agents.length === 1 ? '' : 's')
          + ' · janela ' + data.window_days + 'd';
      }
      var banner = document.getElementById('agents-staleness-banner');
      if (banner) {
        if (data.pricing_age_days != null && data.pricing_age_days > 90) {
          banner.hidden = false;
          banner.textContent = 'Preços com ' + data.pricing_age_days + ' dias sem revisão — custos podem estar defasados.';
        } else {
          banner.hidden = true;
        }
      }
      var grid = document.getElementById('agents-grid');
      var empty = document.getElementById('agents-empty');
      if (!grid) { return; }
      if (data.agents.length === 0) {
        grid.innerHTML = '';
        if (empty) { empty.hidden = false; }
        return;
      }
      if (empty) { empty.hidden = true; }
      grid.innerHTML = data.agents.map(renderCard).join('');
      grid.querySelectorAll('[data-action=toggle-sessions]').forEach(function (btn) {
        btn.addEventListener('click', function () { toggleSessions(btn); });
      });
      applyHashFilter();
    }
    function load() {
      var grid = document.getElementById('agents-grid');
      if (!grid) { return; }
      grid.setAttribute('aria-busy', 'true');
      authedFetch('/api/agents?window_days=180&limit=50')
        .then(function (r) {
          if (!r.ok) { throw new Error('HTTP ' + r.status); }
          return r.json();
        })
        .then(function (data) {
          render(data);
          loaded = true;
          grid.setAttribute('aria-busy', 'false');
        })
        .catch(function (e) {
          grid.innerHTML = '<p class="error-state" role="alert">Falha ao carregar dados: ' + escHtmlA(e.message) + '</p>';
          grid.setAttribute('aria-busy', 'false');
        });
    }
    return { load: load, applyHashFilter: applyHashFilter, isLoaded: function () { return loaded; } };
  })();

  // ── workflows tab ─────────────────────────────────────────────────────
  var Workflows = (function () {
    var loaded = false;
    var _workflows = [];
    function escHtmlW(s) {
      return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) {
        return {'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c];
      });
    }
    function escAttrW(s) { return escHtmlW(s); }

    // ── Agent cross-link ────────────────────────────────────────────────
    function filterAgent(agentId) {
      location.hash = '#agents?filter=' + encodeURIComponent(agentId);
      var agentsTab = document.getElementById('tab-agents');
      if (agentsTab) { agentsTab.click(); }
    }

    // ── Inline SVG stepper diagram ───────────────────────────────────────
    // Renders agent_ids as a horizontal stepper (left-to-right DAG).
    // Vanilla SVG, no CDN, no Mermaid — CSP-safe.
    function buildStepperSVG(agentIds) {
      if (!agentIds || agentIds.length === 0) {
        return '<svg width="120" height="40" aria-label="No steps" role="img">'
          + '<text x="8" y="24" font-size="12" fill="#666">No agents</text>'
          + '</svg>';
      }
      var nodeW = 120;
      var nodeH = 36;
      var arrowW = 28;
      var padX = 12;
      var padY = 12;
      var totalW = padX * 2 + agentIds.length * nodeW + (agentIds.length - 1) * arrowW;
      var totalH = nodeH + padY * 2;
      var rects = '';
      var labels = '';
      var arrows = '';
      for (var i = 0; i < agentIds.length; i++) {
        var x = padX + i * (nodeW + arrowW);
        var y = padY;
        // Node box
        rects += '<rect x="' + x + '" y="' + y + '" width="' + nodeW + '" height="' + nodeH + '"'
          + ' rx="4" ry="4" fill="#f0fbf7" stroke="#9cddc8" stroke-width="1.5"/>';
        // Label (truncate to fit)
        var label = agentIds[i];
        if (label.length > 14) { label = label.slice(0, 13) + '…'; }
        labels += '<text x="' + (x + nodeW / 2) + '" y="' + (y + nodeH / 2 + 5) + '"'
          + ' text-anchor="middle" font-size="11" fill="#222" font-family="ui-monospace,monospace"'
          + ' aria-hidden="true">' + escHtmlW(label) + '</text>';
        // Arrow (not after last node)
        if (i < agentIds.length - 1) {
          var ax = x + nodeW;
          var ay = padY + nodeH / 2;
          arrows += '<line x1="' + ax + '" y1="' + ay + '" x2="' + (ax + arrowW - 6) + '" y2="' + ay + '"'
            + ' stroke="#9cddc8" stroke-width="2"/>'
            + '<polygon points="'
            + (ax + arrowW - 6) + ',' + (ay - 5) + ' '
            + (ax + arrowW) + ',' + ay + ' '
            + (ax + arrowW - 6) + ',' + (ay + 5)
            + '" fill="#9cddc8"/>';
        }
      }
      var ariaLabel = 'Workflow steps: ' + agentIds.join(' → ');
      return '<svg width="' + totalW + '" height="' + totalH + '"'
        + ' viewBox="0 0 ' + totalW + ' ' + totalH + '"'
        + ' role="img" aria-label="' + escAttrW(ariaLabel) + '">'
        + '<title>' + escHtmlW(ariaLabel) + '</title>'
        + rects + labels + arrows
        + '</svg>';
    }

    // ── Detail panel renderer ────────────────────────────────────────────
    function showDetail(w) {
      var detail = document.getElementById('workflows-detail');
      if (!detail) { return; }
      var descClass = w.description ? 'workflow-detail-description' : 'workflow-detail-description no-desc';
      var descText = w.description || 'No description';
      var chips = (w.agent_ids || []).map(function (id) {
        return '<button class="workflow-agent-chip" type="button" data-action="filter-agent"'
          + ' data-agent-id="' + escAttrW(id) + '"'
          + ' aria-label="Filter Agents by: ' + escAttrW(id) + '">'
          + escHtmlW(id)
          + '</button>';
      }).join('');
      detail.innerHTML =
        '<div class="workflow-detail-name">' + escHtmlW(w.display_name) + '</div>'
        + '<div class="workflow-detail-source">' + escHtmlW(w.source || '') + '</div>'
        + '<p class="' + descClass + '">' + escHtmlW(descText) + '</p>'
        + '<div class="workflow-diagram" aria-label="Workflow step diagram">'
        + buildStepperSVG(w.agent_ids || [])
        + '</div>'
        + '<div class="workflow-agent-chips">' + chips + '</div>';
      detail.querySelectorAll('[data-action=filter-agent]').forEach(function (btn) {
        btn.addEventListener('click', function () { filterAgent(btn.dataset.agentId); });
      });
      detail.classList.add('visible');
    }

    // ── Left list renderer ────────────────────────────────────────────────
    function renderList(workflows) {
      var list = document.getElementById('workflows-list');
      if (!list) { return; }
      if (workflows.length === 0) {
        list.innerHTML = '';
        return;
      }
      list.innerHTML = workflows.map(function (w, idx) {
        return '<button class="workflow-list-item" type="button"'
          + ' data-workflow-idx="' + idx + '"'
          + ' aria-pressed="false"'
          + ' aria-label="Workflow: ' + escAttrW(w.display_name) + '">'
          + '<span class="workflow-item-name">' + escHtmlW(w.display_name) + '</span>'
          + '<span class="workflow-item-source">' + escHtmlW(w.source || '') + '</span>'
          + '</button>';
      }).join('');
      list.querySelectorAll('.workflow-list-item').forEach(function (btn) {
        btn.addEventListener('click', function () {
          list.querySelectorAll('.workflow-list-item').forEach(function (b) {
            b.classList.remove('selected');
            b.setAttribute('aria-pressed', 'false');
          });
          btn.classList.add('selected');
          btn.setAttribute('aria-pressed', 'true');
          var idx = parseInt(btn.dataset.workflowIdx, 10);
          if (_workflows[idx]) { showDetail(_workflows[idx]); }
        });
      });
      // Auto-select first item
      var first = list.querySelector('.workflow-list-item');
      if (first) { first.click(); }
    }

    function render(data) {
      _workflows = data.workflows || [];
      var meta = document.getElementById('workflows-meta');
      if (meta) {
        meta.textContent = _workflows.length + ' workflow' + (_workflows.length === 1 ? '' : 's')
          + ' (' + (data.source_hint || '') + ')';
      }
      var grid = document.getElementById('workflows-grid');
      var empty = document.getElementById('workflows-empty');
      if (!grid) { return; }
      grid.setAttribute('aria-busy', 'false');
      if (_workflows.length === 0) {
        grid.style.display = 'none';
        if (empty) { empty.hidden = false; }
        return;
      }
      if (empty) { empty.hidden = true; }
      grid.style.display = '';
      renderList(_workflows);
    }

    function load() {
      var grid = document.getElementById('workflows-grid');
      if (!grid) { return; }
      grid.setAttribute('aria-busy', 'true');
      authedFetch('/api/workflows')
        .then(function (r) {
          if (!r.ok) { throw new Error('HTTP ' + r.status); }
          return r.json();
        })
        .then(function (data) {
          render(data);
          loaded = true;
        })
        .catch(function (e) {
          var detail = document.getElementById('workflows-detail');
          if (detail) {
            detail.innerHTML = '<p class="error-state" role="alert">Falha: ' + escHtmlW(e.message) + '</p>';
          }
          if (grid) { grid.setAttribute('aria-busy', 'false'); }
        });
    }
    return { load: load, isLoaded: function () { return loaded; } };
  })();

  // ── Tab activation hook — lazy fetch for agents/workflows ─────────────
  tabs.forEach(function (tab) {
    tab.addEventListener('click', function () {
      var target = tab.getAttribute('data-section');
      if (target === 'agents' && !Agents.isLoaded()) { Agents.load(); }
      if (target === 'workflows' && !Workflows.isLoaded()) { Workflows.load(); }
    });
  });

  // ── Hash-fragment routing on initial load ─────────────────────────────
  (function () {
    var hash = location.hash;
    if (!hash) { return; }
    if (hash.startsWith('#agents')) {
      var agentsTab = document.getElementById('tab-agents');
      if (agentsTab) {
        agentsTab.click();
        // applyHashFilter is called inside Agents.load() -> render() already,
        // but call it again after a tick in case load finishes asynchronously.
        setTimeout(function () { Agents.applyHashFilter(); }, 300);
      }
    } else if (hash.startsWith('#workflows')) {
      var workflowsTab = document.getElementById('tab-workflows');
      if (workflowsTab) { workflowsTab.click(); }
    }
  })();

})();
"""
