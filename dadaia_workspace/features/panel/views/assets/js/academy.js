// academy.js — Academy tab module for window.Panel
//
// Depends on: window.authedFetch() defined in core.js (loaded before this script)
//
// API contracts:
//   GET /api/academy → { modules: [ { module, module_number, title,
//                                      lesson_count, lessons: [ {lesson, title} ] } ] }
//   GET /academy/<module>/<lesson> → text/html (rendered lesson body)
//
// Module lifecycle:
//   1. Tab activation → Academy.load() called
//   2. fetch in-flight → loading state rendered (aria-busy)
//   3. fetch resolves → module card grid rendered (title + lesson count), or empty
//   4. "Open module" click → renderLessons(module) lists the module's lessons
//   5. lesson click → renderLesson() fetches and shows the rendered lesson HTML
//   6. "← Back" returns to the previous view (lessons → modules)

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

  // Encode a single path segment for use in the lesson URL.
  function encSeg(s) {
    return encodeURIComponent(String(s == null ? '' : s));
  }

  // ── Container reference ───────────────────────────────────────────────────────

  function getContainer() {
    return document.getElementById('academy-content');
  }

  // ── Module grid rendering ───────────────────────────────────────────────────

  function renderModules(modules) {
    var container = getContainer();
    if (!container) { return; }

    if (!modules || modules.length === 0) {
      container.innerHTML = '<div class="empty-state">No academy modules available.</div>';
      return;
    }

    var html = '<div class="academy-grid">';
    modules.forEach(function (mod) {
      var count = Number(mod.lesson_count || (mod.lessons ? mod.lessons.length : 0));
      var lessonWord = count === 1 ? 'lesson' : 'lessons';
      html += '<article class="academy-card">';
      html += '<div class="academy-card__header">';
      html += '<span class="academy-type-chip">Module ' + escHtml(String(mod.module_number)) + '</span>';
      html += '</div>';
      html += '<h3 class="academy-card__title">' + escHtml(mod.title) + '</h3>';
      html += '<p class="academy-card__meta">' + escHtml(String(count)) + ' ' + lessonWord + '</p>';
      html += '<button class="academy-card__cta" type="button" data-module="' + escHtml(mod.module) + '">';
      html += 'Open &#8594;';
      html += '</button>';
      html += '</article>';
    });
    html += '</div>';
    container.innerHTML = html;

    container.querySelectorAll('.academy-card__cta').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var name = btn.dataset.module;
        var mod = null;
        for (var i = 0; i < modules.length; i++) {
          if (modules[i].module === name) { mod = modules[i]; break; }
        }
        if (mod) { renderLessons(modules, mod); }
      });
    });
  }

  // ── Lesson list rendering ─────────────────────────────────────────────────────

  function renderLessons(modules, mod) {
    var container = getContainer();
    if (!container) { return; }

    var lessons = mod.lessons || [];
    var html = '<div class="academy-detail">';
    html += '<button class="academy-back-btn" type="button" aria-label="Back to module list">&#8592; Back to modules</button>';
    html += '<h3 class="academy-detail__title">' + escHtml(mod.title) + '</h3>';
    html += '<p class="academy-detail__meta">Module ' + escHtml(String(mod.module_number)) + '</p>';

    if (lessons.length === 0) {
      html += '<div class="empty-state">This module has no lessons.</div>';
    } else {
      html += '<ul class="academy-lesson-list">';
      lessons.forEach(function (lesson) {
        html += '<li class="academy-lesson-item">';
        html += '<button class="academy-lesson-link" type="button" data-lesson="' + escHtml(lesson.lesson) + '">';
        html += escHtml(lesson.title);
        html += '</button>';
        html += '</li>';
      });
      html += '</ul>';
    }
    html += '</div>';
    container.innerHTML = html;

    container.querySelector('.academy-back-btn').addEventListener('click', function () {
      renderModules(modules);
    });
    container.querySelectorAll('.academy-lesson-link').forEach(function (btn) {
      btn.addEventListener('click', function () {
        renderLesson(modules, mod, btn.dataset.lesson);
      });
    });
  }

  // ── Single lesson render ────────────────────────────────────────────────────

  function renderLesson(modules, mod, lessonFile) {
    var container = getContainer();
    if (!container) { return; }

    container.innerHTML = '<div class="empty-state" aria-busy="true">Loading lesson&hellip;</div>';

    var url = '/academy/' + encSeg(mod.module) + '/' + encSeg(lessonFile);
    window.authedFetch(url)
      .then(function (r) {
        if (!r.ok) { throw new Error('HTTP ' + r.status); }
        return r.text();
      })
      .then(function (htmlText) {
        var c = getContainer();
        if (!c) { return; }
        c.innerHTML =
          '<div class="academy-detail">' +
          '<button class="academy-back-btn" type="button" aria-label="Back to lesson list">&#8592; Back to lessons</button>' +
          '<div class="academy-lesson-body memory-doc">' + htmlText + '</div>' +
          '</div>';
        c.querySelector('.academy-back-btn').addEventListener('click', function () {
          renderLessons(modules, mod);
        });
      })
      .catch(function (err) {
        var c = getContainer();
        if (!c) { return; }
        c.innerHTML =
          '<div class="academy-detail">' +
          '<button class="academy-back-btn" type="button" aria-label="Back to lesson list">&#8592; Back to lessons</button>' +
          '<div class="empty-state error-state" role="alert">Failed to load lesson: ' +
          escHtml(err && err.message ? err.message : String(err)) +
          '</div></div>';
        c.querySelector('.academy-back-btn').addEventListener('click', function () {
          renderLessons(modules, mod);
        });
      });
  }

  // ── Load (fetches module catalog) ────────────────────────────────────────────

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
        renderModules(data.modules || []);
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
    renderModules: renderModules,
    renderLessons: renderLessons,
    renderLesson: renderLesson,
  };

  window.Academy = Academy;
  if (window.Panel && window.Panel.register) {
    window.Panel.register('academy', Academy);
  }

})();
