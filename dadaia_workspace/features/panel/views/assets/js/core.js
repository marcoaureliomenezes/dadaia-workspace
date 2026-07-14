// Hash navigation grammar. The initial-load router (below) maps three hash routes to a
// bare tab activation on page load: #workflows | #reports | #academy | #games (prefix match, so a
// trailing ?key=val is tolerated but not parsed). The Sessions tab is click-activated,
// not an initial-load hash route. No other hash routes exist (the former
// #memories/#agents/#servers routes and the #agents?filter= / #workflows?detail= params
// were never wired — v0.1.48 F-truth fix).

(function () {
  'use strict';

  // ── Panel module registry ─────────────────────────────────────────
  // Central registry for named panel modules. Each module calls
  // window.Panel.register(name, mod) after defining itself.
  // Tab activation calls window.Panel.activate(name, opts) which
  // delegates to mod.load(opts).
  (function initPanelRegistry() {
    var _modules = {};
    window.Panel = {
      register: function (name, mod) {
        _modules[name] = mod;
      },
      activate: function (name, opts) {
        var mod = _modules[name];
        if (mod && typeof mod.load === 'function') {
          mod.load(opts);
        }
      },
    };
  })();

  // ── Stale credential purge ────────────────────────────────────────
  // The panel has no authentication (operator decision 2026-06-11): it is a
  // loopback-only local dev tool. Older builds persisted a Bearer token in
  // localStorage under 'panel_token'; remove it once so no stale credential
  // lingers in the browser.
  (function purgeStaleToken() {
    try {
      localStorage.removeItem('panel_token');
    } catch (e) {
      // localStorage may be unavailable (private mode); nothing to purge.
    }
  })();

  // ── Fetch alias ────────────────────────────────────────────────────
  // The panel sends no credentials. authedFetch is kept as a thin alias of
  // fetch so existing call sites do not churn; it adds no Authorization header.
  function authedFetch(url, opts) {
    return fetch(url, opts || {});
  }
  window.authedFetch = authedFetch;

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

  // ── HTML escape utility ────────────────────────────────────────────
  // Canonical implementation; promoted to window.escHtml so all modules
  // can share it without duplicating the function.
  function escHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }
  window.escHtml = escHtml;

  // ── Server table renderer ──────────────────────────────────────────

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
    fetch('/api/panel-status')
      .then(function (r) {
        if (!r.ok) { throw new Error('HTTP ' + r.status); }
        return r.json();
      })
      .then(function (data) {
        var container = document.getElementById('servers-content');
        if (container) { container.innerHTML = buildServersHTML(data); }
        lastUpdated = new Date();
        if (statusDot) { statusDot.classList.remove('updating'); }
        updateStatusLabel();
      })
      .catch(function (err) {
        if (statusDot) { statusDot.classList.remove('updating'); }
        lastUpdated = new Date();
        updateStatusLabel();
        var container = document.getElementById('servers-content');
        if (container && !container.dataset.errorNotice) {
          container.dataset.errorNotice = '1';
          var notice = document.createElement('p');
          notice.style.cssText = 'padding:0.5rem 1rem;color:var(--color-muted,#888);font-size:0.82rem;';
          notice.textContent = 'Server list unavailable: ' + (err && err.message ? err.message : String(err)) + '.';
          container.appendChild(notice);
        }
      });
  }

  setInterval(fetchServers, 5000);
  setInterval(updateStatusLabel, 5000);

  // ── Tab activation hook — lazy fetch for workflows/sessions/academy/reports ──
  // Sessions module: window.Sessions (sessions.js, loaded after this script).
  // Academy module: window.Academy (academy.js, loaded after this script).
  // Reports module: window.Reports (reports.js, loaded after this script).
  tabs.forEach(function (tab) {
    tab.addEventListener('click', function () {
      var target = tab.getAttribute('data-section');

      // ── Workflows tab (first-class): load the per-step model pickers ──────────
      if (target === 'workflows') {
        if (window.WorkflowPolicy && !window.WorkflowPolicy.isLoaded()) {
          window.WorkflowPolicy.load();
        }
      }

      if (target === 'sessions') {
        window.Panel.activate('sessions');
      }
      if (target === 'academy') {
        window.Panel.activate('academy');
      }
      if (target === 'reports') {
        window.Panel.activate('reports');
      }
    });
  });

  // ── Hash-fragment routing on initial load ─────────────────────────────
  // #workflows activates the first-class Workflows tab (Agentic tab removed).
  (function () {
    var hash = location.hash;
    if (!hash) { return; }
    if (hash.startsWith('#workflows')) {
      var workflowsTab = document.getElementById('tab-workflows');
      if (workflowsTab) { workflowsTab.click(); }
    } else if (hash.startsWith('#reports')) {
      var reportsTab = document.getElementById('tab-reports');
      if (reportsTab) { reportsTab.click(); }
    } else if (hash.startsWith('#academy')) {
      var academyTab = document.getElementById('tab-academy');
      if (academyTab) { academyTab.click(); }
    } else if (hash.startsWith('#games')) {
      var gamesTab = document.getElementById('tab-games');
      if (gamesTab) { gamesTab.click(); }
    }
  })();

  // ── Register modules into window.Panel ───────────────────────────────
  // Runs after all synchronous <script> tags have executed (DOMContentLoaded
  // fires after the parser has processed every script in the document head/body).
  document.addEventListener('DOMContentLoaded', function () {
    if (window.Sessions) { window.Panel.register('sessions', window.Sessions); }
    if (window.Academy) { window.Panel.register('academy', window.Academy); }
    if (window.Reports) { window.Panel.register('reports', window.Reports); }
  });

})();
