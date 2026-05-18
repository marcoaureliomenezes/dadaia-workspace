// Hash navigation grammar (normative, per SPEC §7.1):
//   #<tab-section-id>[?key=val&...]
//   #memories | #agents | #workflows | #servers  — bare tab activation
//   #agents?filter=<agent-name>                  — agent filter (existing pattern)
//   #workflows?detail=<workflow-name>            — workflow detail view (PR3-17 FE)
// This module-level comment documents the grammar; the hash router below parses both.
// PR3-17 (FE) will extend the router to handle #workflows?detail= in js/workflows.js.

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

  // ── Tab activation hook — lazy fetch for agents/workflows ─────────────
  // Agents module: window.Agents (agents.js, loaded after this script).
  // Workflows module: window.Workflows (workflows.js, loaded after this script).
  // Agents module is loaded by agents.js (separate script tag); accessed via
  // window.Agents. Workflows module remains inline (PR3-16/17 will extract it).
  tabs.forEach(function (tab) {
    tab.addEventListener('click', function () {
      var target = tab.getAttribute('data-section');
      if (target === 'agents' && window.Agents && !window.Agents.isLoaded()) {
        window.Agents.load();
      }
      if (target === 'workflows' && window.Workflows && !window.Workflows.isLoaded()) {
        window.Workflows.load();
      }
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
        setTimeout(function () {
          if (window.Agents) { window.Agents.applyHashFilter(); }
        }, 300);
      }
    } else if (hash.startsWith('#workflows')) {
      var workflowsTab = document.getElementById('tab-workflows');
      if (workflowsTab) { workflowsTab.click(); }
    }
  })();

})();
