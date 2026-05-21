// academy.js — Academy tab module for window.Panel
//
// Depends on: window.authedFetch() defined in core.js (loaded before this script)
//
// API contracts:
//   GET /api/academy → { courses: [ { slug, name, module_number, module_name, created_at } ] }
//
// Module lifecycle:
//   1. Tab activation → Academy.load() called
//   2. fetch in-flight → loading state rendered (aria-busy)
//   3. fetch resolves → course card grid rendered, or empty state
//   4. "Open →" click → renderDetail(course) shows content view
//   5. "← Back to Academy" click → load() called again to return to list

(function () {
  'use strict';

  // ── Utilities ────────────────────────────────────────────────────────────────

  // TODO: replace with window.escHtml when touching this file
  function escHtml(s) {
    var safe = window.escHtml;
    if (typeof safe === 'function') { return safe(s); }
    return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
    });
  }

  // ── Container reference ───────────────────────────────────────────────────────

  function getContainer() {
    return document.getElementById('academy-content');
  }

  // ── Card grid rendering ───────────────────────────────────────────────────────

  function renderList(courses) {
    var container = getContainer();
    if (!container) { return; }

    if (!courses || courses.length === 0) {
      container.innerHTML = '<div class="empty-state">No academy modules available.</div>';
      return;
    }

    var html = '<div class="academy-grid">';
    courses.forEach(function (course) {
      html += '<article class="academy-card">';
      html += '<div class="academy-card__header">';
      html += '<span class="academy-type-chip">Module ' + escHtml(String(course.module_number)) + '</span>';
      html += '</div>';
      html += '<h3 class="academy-card__title">' + escHtml(course.name) + '</h3>';
      html += '<p class="academy-card__meta">' + escHtml(course.module_name) + '</p>';
      html += '<button class="academy-card__cta" type="button" data-slug="' + escHtml(course.slug) + '">';
      html += 'Open &#8594;';
      html += '</button>';
      html += '</article>';
    });
    html += '</div>';
    container.innerHTML = html;

    // Wire CTA buttons
    container.querySelectorAll('.academy-card__cta').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var slug = btn.dataset.slug;
        var course = null;
        for (var i = 0; i < courses.length; i++) {
          if (courses[i].slug === slug) {
            course = courses[i];
            break;
          }
        }
        if (course) { renderDetail(course); }
      });
    });
  }

  // ── Detail view rendering ─────────────────────────────────────────────────────

  function renderDetail(course) {
    var container = getContainer();
    if (!container) { return; }

    container.innerHTML =
      '<div class="academy-detail">' +
      '<button class="academy-back-btn" type="button" aria-label="Back to Academy list">&#8592; Back to Academy</button>' +
      '<h3 class="academy-detail__title">' + escHtml(course.name) + '</h3>' +
      '<p class="academy-detail__meta">Module ' + escHtml(String(course.module_number)) + ' &mdash; ' + escHtml(course.module_name) + '</p>' +
      '<p class="academy-detail__date">' + escHtml(course.created_at || '') + '</p>' +
      '</div>';

    container.querySelector('.academy-back-btn').addEventListener('click', function () {
      load();
    });
  }

  // ── Load (fetches course list) ────────────────────────────────────────────────

  function load() {
    var container = getContainer();
    if (!container) { return; }

    container.innerHTML = '<div class="empty-state" aria-busy="true">Loading academy modules&hellip;</div>';

    window.authedFetch('/api/academy')
      .then(function (r) {
        if (!r.ok) { throw new Error('HTTP ' + r.status); }
        return r.json();
      })
      .then(function (data) {
        renderList(data.courses || []);
      })
      .catch(function (err) {
        var container2 = getContainer();
        if (container2) {
          container2.innerHTML =
            '<div class="empty-state error-state" role="alert">Failed to load academy modules: ' +
            escHtml(err && err.message ? err.message : String(err)) +
            '</div>';
        }
      });
  }

  // ── Public API ────────────────────────────────────────────────────────────────

  var Academy = {
    load: load,
    renderList: renderList,
    renderDetail: renderDetail,
  };

  window.Academy = Academy;
  if (window.Panel && window.Panel.register) {
    window.Panel.register('academy', Academy);
  }

})();
