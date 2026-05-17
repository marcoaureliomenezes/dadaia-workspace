"""Static frontend assets for the Dadaia Workspace Panel.

Both constants are plain Python strings — no filesystem reads, no importlib.resources.
This is the R1 resolution from the software-engineer review: assets ship correctly in any
installed wheel without pyproject.toml package-data declarations.

PANEL_CSS  — design tokens from specs/memory/architecture.html + structural rules from
             the frontend mockup (index.html, memories.html, memory-view.html).
             Body-text links use --color-accent-dark (#2d7d9a, WCAG AA ~5:1 on #fafafa).
             #7ec8e3 is decorative accent only (left-border on primary card, hover glow).

PANEL_JS   — auto-refresh /api/servers every 5s; tab switching; TTL relative formatter.
             Vanilla JS, no frameworks, no eval().
"""

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
a:focus-visible { outline: 2px solid var(--color-accent); outline-offset: 2px; border-radius: 2px; }

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

.topbar-wordmark {
  font-size: 1.1rem;
  font-weight: 700;
  color: var(--color-heading);
  letter-spacing: -0.01em;
}
.topbar-wordmark span { color: var(--color-accent-dark); }
.topbar-divider { width: 1px; height: 24px; background: var(--color-border); }
.topbar-subtitle { color: var(--color-muted); font-size: 0.9rem; }
.topbar-badge {
  margin-left: auto;
  background: var(--color-accent);
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
.nav-tab:focus-visible { outline: 2px solid var(--color-accent); outline-offset: -2px; }
.nav-tab.active {
  color: var(--color-heading);
  font-weight: 600;
  border-bottom-color: var(--color-accent);
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
  border-left: 4px solid var(--color-primary-ring);
  background: var(--color-primary-bg);
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
  background: var(--color-accent);
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
.memory-link:focus-visible { outline: 2px solid var(--color-accent); outline-offset: -2px; }
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
"""

PANEL_JS: str = """
(function () {
  'use strict';

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

})();
"""
