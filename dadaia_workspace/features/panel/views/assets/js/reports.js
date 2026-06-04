// reports.js — Reports tab module for window.Panel
//
// Depends on: window.authedFetch() defined in core.js (loaded before this script)
//
// API contracts:
//   GET  /api/reports        → { reports: [ { title, agent, context, created_at, path, findings_summary } ] }
//   DELETE /api/reports/<path> → { deleted: true }   (bearer-only)
//   POST /api/reports-important/<path> → { important: true }
//   POST /api/reports-unimportant/<path> → { important: false }
//   GET  /reports/<path>     → HTML report content    (public route)
//
// Module lifecycle:
//   1. Tab activation → Reports.load() called
//   2. fetch in-flight → aria-busy loading state
//   3. fetch resolves → grouped <details>/<summary> list, or empty state
//   4. Trash click → inline confirm row shown; original row buttons hidden
//   5. Delete confirmed → DELETE /api/reports/<path>; <li> removed on 200
//   6. Cancel → original row buttons restored
//   7. Title click → fetch /reports/<path>; render HTML into #reports-content;
//      hide #reports-list; show breadcrumb + content
//   8. Back click → show #reports-list; hide #reports-content

(function () {
  'use strict';

  // ── Utilities ────────────────────────────────────────────────────────────────

  function escHtml(s) {
    var safe = window.escHtml;
    if (typeof safe === 'function') { return safe(s); }
    return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
    });
  }

  function encodeReportPath(path) {
    return String(path == null ? '' : path)
      .split('/')
      .map(function (segment) { return encodeURIComponent(segment); })
      .join('/');
  }

  // ── Container helpers ─────────────────────────────────────────────────────────

  function getList() {
    return document.getElementById('reports-list');
  }

  function getContent() {
    return document.getElementById('reports-content');
  }

  // ── Date formatter ────────────────────────────────────────────────────────────

  function fmtDate(iso) {
    if (!iso) { return '—'; }
    var d = new Date(iso);
    if (isNaN(d.getTime())) { return '—'; }
    return d.toLocaleString();
  }

  function retentionLabel(report) {
    if (report.important) { return 'Marked important'; }
    if (!report.expires_at) { return ''; }
    return 'Expires ' + fmtDate(report.expires_at);
  }

  // ── Group reports by context ──────────────────────────────────────────────────

  function groupByContext(reports) {
    var groups = {};
    reports.forEach(function (report) {
      var ctx = report.context || '(no context)';
      if (!groups[ctx]) { groups[ctx] = []; }
      groups[ctx].push(report);
    });
    return groups;
  }

  // ── Show content view with back button ────────────────────────────────────────

  function showContent(html) {
    var list = getList();
    var content = getContent();
    if (!list || !content) { return; }

    content.innerHTML =
      '<button class="reports-back-btn" type="button" aria-label="Back to Reports list">'
      + '&#8592; Back to Reports'
      + '</button>'
      + '<div class="reports-content-frame">'
      + html
      + '</div>';

    list.hidden = true;
    content.removeAttribute('hidden');

    var backBtn = content.querySelector('.reports-back-btn');
    if (backBtn) {
      backBtn.addEventListener('click', function () {
        content.setAttribute('hidden', '');
        content.innerHTML = '';
        list.hidden = false;
      });
      backBtn.focus();
    }
  }

  // ── Row: wire inline confirm (trash action) ───────────────────────────────────

  function wireTrashBtn(li, report) {
    var actions = li.querySelector('.reports-row__actions');
    var confirm = li.querySelector('.reports-row__confirm');
    var trashBtn = li.querySelector('.reports-row__trash');
    var deleteBtn = li.querySelector('.reports-confirm-delete');
    var cancelBtn = li.querySelector('.reports-confirm-cancel');

    if (!trashBtn || !confirm || !actions || !deleteBtn || !cancelBtn) { return; }

    trashBtn.addEventListener('click', function () {
      actions.hidden = true;
      confirm.removeAttribute('hidden');
      deleteBtn.focus();
    });

    cancelBtn.addEventListener('click', function () {
      confirm.setAttribute('hidden', '');
      actions.hidden = false;
      trashBtn.focus();
    });

    deleteBtn.addEventListener('click', function () {
      deleteBtn.disabled = true;
      deleteBtn.textContent = 'Deleting…';

      window.authedFetch('/api/reports/' + encodeReportPath(report.path), { method: 'DELETE' })
        .then(function (r) {
          if (r.ok) {
            // Remove the <li> from the DOM
            var ul = li.parentNode;
            li.remove();
            // If the group <ul> is now empty, remove the <details> group too
            if (ul && ul.querySelectorAll('.reports-row').length === 0) {
              var details = ul.closest('.reports-group');
              if (details) { details.remove(); }
            }
            // Check if all groups gone → show empty state
            var list = getList();
            if (list && list.querySelectorAll('.reports-group').length === 0) {
              list.innerHTML = '<div class="empty-state">No reports available.</div>';
            }
          } else {
            // Restore UI on failure
            deleteBtn.disabled = false;
            deleteBtn.textContent = 'Delete';
            var errMsg = li.querySelector('.reports-confirm-text');
            if (errMsg) {
              errMsg.textContent = 'Delete failed (HTTP ' + r.status + '). Try again.';
            }
          }
        })
        .catch(function (err) {
          deleteBtn.disabled = false;
          deleteBtn.textContent = 'Delete';
          var errMsg = li.querySelector('.reports-confirm-text');
          if (errMsg) {
            errMsg.textContent = 'Delete failed: ' + escHtml(err && err.message ? err.message : String(err));
          }
        });
    });
  }

  // ── Row: wire title (open report content) ────────────────────────────────────

  function wireTitleBtn(li, report) {
    var titleBtn = li.querySelector('.reports-row__title');
    if (!titleBtn) { return; }

    titleBtn.addEventListener('click', function () {
      titleBtn.disabled = true;
      titleBtn.setAttribute('aria-busy', 'true');

      // Public route — use plain fetch, not authedFetch
      fetch('/reports/' + encodeReportPath(report.path))
        .then(function (r) {
          if (!r.ok) {
            throw new Error('HTTP ' + r.status);
          }
          return r.text();
        })
        .then(function (html) {
          titleBtn.disabled = false;
          titleBtn.removeAttribute('aria-busy');
          showContent(html);
        })
        .catch(function (err) {
          titleBtn.disabled = false;
          titleBtn.removeAttribute('aria-busy');
          showContent(
            '<div class="empty-state error-state" role="alert">Failed to load report: '
            + escHtml(err && err.message ? err.message : String(err))
            + '</div>'
          );
        });
    });
  }

  function wireImportantBtn(li, report) {
    var btn = li.querySelector('.reports-row__important');
    if (!btn) { return; }
    btn.addEventListener('click', function () {
      btn.disabled = true;
      var route = report.important ? '/api/reports-unimportant/' : '/api/reports-important/';
      window.authedFetch(route + encodeReportPath(report.path), { method: 'POST' })
        .then(function (r) {
          if (!r.ok) { throw new Error('HTTP ' + r.status); }
          return r.json();
        })
        .then(function (data) {
          report.important = !!data.important;
          var meta = li.querySelector('.reports-row__retention');
          if (meta) { meta.textContent = retentionLabel(report); }
          btn.textContent = report.important ? 'Unmark important' : 'Important';
          btn.setAttribute('aria-pressed', report.important ? 'true' : 'false');
          btn.disabled = false;
        })
        .catch(function () {
          btn.disabled = false;
        });
    });
  }

  // ── Build a single report row (<li>) ─────────────────────────────────────────

  function buildRow(report) {
    var li = document.createElement('li');
    li.className = 'reports-row';
    li.setAttribute('data-path', escHtml(report.path || ''));

    var dateStr = fmtDate(report.created_at);

    li.innerHTML =
      '<div class="reports-row__actions">'
      + '<span class="report-tag-chip" aria-label="Agent: ' + escHtml(report.agent || '') + '">'
      + escHtml(report.agent || '—')
      + '</span>'
      + '<button class="reports-row__title" type="button"'
      + ' aria-label="Open report: ' + escHtml(report.title || '') + '">'
      + escHtml(report.title || '(untitled)')
      + '</button>'
      + '<span class="reports-row__date">' + escHtml(dateStr) + '</span>'
      + '<span class="reports-row__retention">' + escHtml(retentionLabel(report)) + '</span>'
      + '<button class="reports-row__important" type="button" aria-pressed="'
      + (report.important ? 'true' : 'false') + '">'
      + (report.important ? 'Unmark important' : 'Important')
      + '</button>'
      + '<button class="reports-row__trash" type="button"'
      + ' aria-label="Delete report: ' + escHtml(report.title || '') + '">'
      + '&#128465;'
      + '</button>'
      + '</div>'
      + '<div class="reports-row__confirm" hidden>'
      + '<span class="reports-confirm-text">Are you sure?</span>'
      + '<button class="reports-confirm-delete" type="button">Delete</button>'
      + '<button class="reports-confirm-cancel" type="button">Cancel</button>'
      + '</div>';

    wireTrashBtn(li, report);
    wireTitleBtn(li, report);
    wireImportantBtn(li, report);

    return li;
  }

  // ── Render grouped list ───────────────────────────────────────────────────────

  function renderList(reports) {
    var list = getList();
    if (!list) { return; }
    list.removeAttribute('aria-busy');

    if (!reports || reports.length === 0) {
      list.innerHTML = '<div class="empty-state">No reports available.</div>';
      return;
    }

    var groups = groupByContext(reports);
    var contextNames = Object.keys(groups).slice().sort();
    var totalGroups = contextNames.length;

    list.innerHTML = '';

    contextNames.forEach(function (ctx, idx) {
      var groupReports = groups[ctx];
      var count = groupReports.length;

      var details = document.createElement('details');
      details.className = 'reports-group';
      // Open by default when <= 3 groups
      if (totalGroups <= 3) {
        details.setAttribute('open', '');
      }

      var summary = document.createElement('summary');
      summary.className = 'reports-group-summary';
      summary.innerHTML =
        '<span class="reports-group-label">' + escHtml(ctx) + '</span>'
        + '<span class="reports-count-badge">' + escHtml(String(count)) + '</span>';
      details.appendChild(summary);

      var ul = document.createElement('ul');
      ul.className = 'reports-list';

      groupReports.forEach(function (report) {
        ul.appendChild(buildRow(report));
      });

      details.appendChild(ul);
      list.appendChild(details);
    });
  }

  // ── Load (fetches report list) ────────────────────────────────────────────────

  function load() {
    var list = getList();
    var content = getContent();
    if (!list) { return; }

    // Ensure content view is hidden and list is shown
    if (content) {
      content.setAttribute('hidden', '');
      content.innerHTML = '';
    }
    list.hidden = false;

    list.innerHTML = '<div class="empty-state" aria-busy="true">Loading reports&hellip;</div>';

    window.authedFetch('/api/reports')
      .then(function (r) {
        if (!r.ok) { throw new Error('HTTP ' + r.status); }
        return r.json();
      })
      .then(function (data) {
        renderList(data.reports || []);
      })
      .catch(function (err) {
        var list2 = getList();
        if (list2) {
          list2.removeAttribute('aria-busy');
          list2.innerHTML =
            '<div class="empty-state error-state" role="alert">Failed to load reports: '
            + escHtml(err && err.message ? err.message : String(err))
            + '</div>';
        }
      });
  }

  // ── Public API ────────────────────────────────────────────────────────────────

  var Reports = {
    load: load,
    renderList: renderList,
  };

  window.Reports = Reports;
  if (window.Panel && window.Panel.register) {
    window.Panel.register('reports', Reports);
  }

})();
