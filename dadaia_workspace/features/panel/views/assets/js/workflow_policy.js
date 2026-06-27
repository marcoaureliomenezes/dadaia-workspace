// workflow_policy.js — Workflows first-class nav: model-governance control plane (Wave C, D-5).
//
// Renders, per governed workflow, a step matrix
//   (Step | Role | Harness | Effective profile | Concrete model | Fragments | Gate)
// with a per-step model editor:
//   - segmented codex/pi harness control
//   - profile dropdown filtered by the selected harness
//   - reset-to-default per step
//   - default-vs-effective diff (a step whose effective != default is flagged)
//   - validate-before-save banner (POST /api/workflow-model-policy/validate)
//   - save (PUT /api/workflow-model-policy)
// plus a run-snapshot evidence view per workflow that reads the persisted snapshot
//   (GET /api/lifecycle-runs) — it shows the model actually used, never re-resolving.
//
// Data sources (Wave C GET routes, all loopback, no credential):
//   GET /api/workflow-catalog            → { workflows: [{ workflow_id, steps:[...] }] }
//   GET /api/workflow-model-profiles     → { profiles: [{ id, harness, label, ... }] }
//   GET /api/workflow-model-policy       → { exists, policy }
//   GET /api/lifecycle-runs?workflow=&context=
// Mutations:
//   POST /api/workflow-model-policy/validate   (dry-run)
//   PUT  /api/workflow-model-policy            (persist)
//
// Security: every value rendered into the DOM goes through escHtml; the only innerHTML
// injected from the server is the diagram SVG (server-controlled). No browser-Mermaid is
// an execution dependency — the server-rendered SVG (already on the page) is canonical.

(function () {
  'use strict';

  var CONTEXT = 'default'; // D-2: only the default overlay is honored this release.

  function escHtml(s) {
    return (window.escHtml || function (x) {
      return String(x == null ? '' : x).replace(/[&<>"]/g, function (c) {
        return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
      });
    })(s);
  }

  function fetchJson(url, opts) {
    var f = window.authedFetch || window.fetch;
    return f(url, opts || {}).then(function (r) {
      return r.json().then(function (body) { return { status: r.status, body: body }; });
    });
  }

  // In-memory edit state: { workflow_id: { step: profile_id } } — pending profile overrides.
  var pending = {};
  // Pending harness overrides: { workflow_id: { step: harness } } (D-3, T-29-C-02).
  var pendingHarness = {};
  var profilesByHarness = {}; // harness -> [profile]
  var catalog = null;         // last catalog payload

  function profilesFor(harness) {
    return profilesByHarness[harness] || [];
  }

  // ── Rendering ──────────────────────────────────────────────────────────────

  // The step's effective harness: a pending toggle wins, else the catalog row's
  // resolved harness (which already folds the persisted overlay, D-1 precedence).
  function effectiveHarness(workflowId, step) {
    var h = pendingHarness[workflowId] && pendingHarness[workflowId][step.step];
    return h != null ? h : step.harness;
  }

  function effectiveProfile(workflowId, step) {
    var p = pending[workflowId] && pending[workflowId][step.step];
    if (p != null) { return p; }
    // No pending profile: if the harness was toggled away from the row's resolved
    // harness, the row's effective_profile no longer matches — auto-select the toggled
    // harness's default profile for the step purpose (D-1 auto-profile in the browser).
    var ph = pendingHarness[workflowId] && pendingHarness[workflowId][step.step];
    if (ph != null && ph !== step.harness) {
      return defaultProfileForStep(ph, step);
    }
    return step.effective_profile;
  }

  // The harness's default profile for this step comes straight off the catalog row's
  // ``default_profiles`` map — the SAME map the resolver uses for D-1 auto-profile, so the
  // panel and the server never disagree on which profile a harness flip selects (no second
  // JS table). Falls back to the harness's first profile only if the map is absent.
  function defaultProfileForStep(harness, step) {
    var byHarness = step.default_profiles || {};
    if (byHarness[harness] != null) { return byHarness[harness]; }
    var list = profilesFor(harness);
    return list.length ? list[0].id : step.effective_profile;
  }

  function harnessForProfile(profileId, fallback) {
    for (var h in profilesByHarness) {
      var list = profilesByHarness[h];
      for (var i = 0; i < list.length; i++) {
        if (list[i].id === profileId) { return h; }
      }
    }
    return fallback;
  }

  function renderProfileOptions(harness, selectedId) {
    var list = profilesFor(harness);
    var out = '';
    for (var i = 0; i < list.length; i++) {
      var p = list[i];
      var sel = p.id === selectedId ? ' selected' : '';
      out += '<option value="' + escHtml(p.id) + '"' + sel + '>' +
        escHtml(p.label || p.id) + '</option>';
    }
    return out;
  }

  function renderHarnessSegment(workflowId, step, harness) {
    // Only harnesses that actually carry profiles are selectable (codex/pi).
    var harnesses = Object.keys(profilesByHarness).sort();
    var out = '<span class="wfp-seg" role="radiogroup" aria-label="Harness">';
    for (var i = 0; i < harnesses.length; i++) {
      var h = harnesses[i];
      var active = h === harness ? ' wfp-seg-btn--active' : '';
      var checked = h === harness ? 'true' : 'false';
      out += '<button type="button" class="wfp-seg-btn' + active + '" role="radio" ' +
        'aria-checked="' + checked + '" data-wfp-harness="' + escHtml(h) + '" ' +
        'data-wfp-workflow="' + escHtml(workflowId) + '" data-wfp-step="' + escHtml(step.step) + '">' +
        escHtml(h) + '</button>';
    }
    out += '</span>';
    return out;
  }

  function renderStepRow(workflowId, step) {
    var eff = effectiveProfile(workflowId, step);
    // The effective harness drives the segmented control AND the dropdown filter; with a
    // pending toggle this is the toggled harness, else the catalog row's resolved harness.
    var harness = effectiveHarness(workflowId, step);
    var defaultHarness = step.default_harness || harnessForProfile(step.default_profile, harness);
    var harnessOverridden = harness !== defaultHarness;
    var isOverridden = eff !== step.default_profile || harnessOverridden;
    var rowCls = 'wfp-step-row' + (isOverridden ? ' wfp-step-row--overridden' : '');
    var harnessFlag = harnessOverridden
      ? ' <span class="wfp-diff-harness" data-testid="wfp-diff-harness">harness: ' +
        escHtml(defaultHarness) + ' → ' + escHtml(harness) + '</span>'
      : '';
    var diff = isOverridden
      ? '<span class="wfp-diff" data-testid="wfp-diff">default: ' +
        escHtml(step.default_profile) + ' → ' + escHtml(eff) + '</span>' + harnessFlag
      : '<span class="wfp-diff wfp-diff--none">default</span>';
    var gate = step.is_gate || step.gate
      ? '<span class="wfp-gate" title="gate step">◉</span>' : '';
    // Read-only fragment inspector (T-28-D-01): each fragment id is a button that opens
    // the resolved fragment body + dynamic inputs + output schema. No edit affordance.
    var fragList = step.fragments || [];
    var fragments = fragList.length
      ? fragList.map(function (fid) {
          return '<button type="button" class="wfp-frag-btn" data-wfp-fragment="' +
            escHtml(fid) + '">' + escHtml(fid) + '</button>';
        }).join(' ')
      : '—';

    return '<tr class="' + rowCls + '" data-wfp-step-row="' + escHtml(step.step) + '">' +
      '<td class="wfp-c-step">' + escHtml(step.step) + '</td>' +
      '<td class="wfp-c-role">' + escHtml(step.role || '') + '</td>' +
      '<td class="wfp-c-harness">' + renderHarnessSegment(workflowId, step, harness) + '</td>' +
      '<td class="wfp-c-profile">' +
        '<select class="wfp-profile-select" aria-label="Model profile for ' + escHtml(step.step) + '" ' +
        'data-wfp-workflow="' + escHtml(workflowId) + '" data-wfp-step="' + escHtml(step.step) + '">' +
        renderProfileOptions(harness, eff) + '</select>' +
      '</td>' +
      '<td class="wfp-c-model">' + escHtml(step.model || '—') +
        (step.reasoning ? ' <span class="wfp-effort">(' + escHtml(step.reasoning) + ')</span>' : '') + '</td>' +
      '<td class="wfp-c-frag">' + fragments + '</td>' +
      '<td class="wfp-c-gate">' + gate + '</td>' +
      '<td class="wfp-c-diff">' + diff +
        ' <button type="button" class="wfp-reset-btn" data-wfp-reset ' +
        'data-wfp-workflow="' + escHtml(workflowId) + '" data-wfp-step="' + escHtml(step.step) + '" ' +
        (isOverridden ? '' : 'disabled ') + '>reset</button></td>' +
      '</tr>';
  }

  function renderWorkflow(wf) {
    var rows = (wf.steps || []).map(function (s) { return renderStepRow(wf.workflow_id, s); }).join('');
    return '<section class="wfp-workflow" data-wfp-workflow-card="' + escHtml(wf.workflow_id) + '">' +
      '<header class="wfp-workflow-head"><h3 class="wfp-workflow-title">' +
        escHtml(wf.workflow_id) + '</h3>' +
        '<button type="button" class="wfp-runs-btn" data-wfp-runs="' + escHtml(wf.workflow_id) + '">' +
        'Run snapshots</button></header>' +
      (wf.error ? '<p class="wfp-error" data-testid="wfp-workflow-error">' + escHtml(wf.error) + '</p>' : '') +
      '<table class="wfp-matrix"><thead><tr>' +
        '<th>Step</th><th>Role</th><th>Harness</th><th>Model profile</th>' +
        '<th>Concrete model</th><th>Fragments</th><th>Gate</th><th>Default vs effective</th>' +
      '</tr></thead><tbody>' + rows + '</tbody></table>' +
      '<div class="wfp-inspector" data-wfp-inspector-panel="' + escHtml(wf.workflow_id) + '" hidden></div>' +
      '<div class="wfp-runs" data-wfp-runs-panel="' + escHtml(wf.workflow_id) + '" hidden></div>' +
      '</section>';
  }

  function render() {
    var root = document.getElementById('wfp-root');
    if (!root || !catalog) { return; }
    var html = (catalog.workflows || []).map(renderWorkflow).join('');
    root.innerHTML = html ||
      '<p class="empty-state" data-testid="wfp-empty">No governed workflows.</p>';
    bindRowEvents();
  }

  function setBanner(kind, message) {
    var banner = document.getElementById('wfp-banner');
    if (!banner) { return; }
    banner.className = 'wfp-banner wfp-banner--' + kind;
    banner.textContent = message;
    banner.hidden = !message;
  }

  // ── Events ──────────────────────────────────────────────────────────────────

  function setPending(workflowId, step, profileId, defaultProfile) {
    if (!pending[workflowId]) { pending[workflowId] = {}; }
    if (profileId === defaultProfile) {
      delete pending[workflowId][step];
      if (Object.keys(pending[workflowId]).length === 0) { delete pending[workflowId]; }
    } else {
      pending[workflowId][step] = profileId;
    }
  }

  // Record a pending harness override (T-29-C-02). A harness equal to the catalog default
  // harness is NOT a pending override — it is cleared so the PUT body omits it (back-compat).
  function setPendingHarness(workflowId, step, harness, catStep) {
    if (!pendingHarness[workflowId]) { pendingHarness[workflowId] = {}; }
    var defaultHarness = catStep.default_harness;
    if (harness === defaultHarness) {
      delete pendingHarness[workflowId][step];
      if (Object.keys(pendingHarness[workflowId]).length === 0) { delete pendingHarness[workflowId]; }
    } else {
      pendingHarness[workflowId][step] = harness;
    }
  }

  function stepByLabel(workflowId, label) {
    var wf = (catalog.workflows || []).find(function (w) { return w.workflow_id === workflowId; });
    if (!wf) { return null; }
    return (wf.steps || []).find(function (s) { return s.step === label; }) || null;
  }

  function bindRowEvents() {
    var root = document.getElementById('wfp-root');
    if (!root) { return; }

    root.querySelectorAll('.wfp-profile-select').forEach(function (sel) {
      sel.addEventListener('change', function () {
        var wfId = sel.getAttribute('data-wfp-workflow');
        var stepLabel = sel.getAttribute('data-wfp-step');
        var step = stepByLabel(wfId, stepLabel);
        if (!step) { return; }
        setPending(wfId, stepLabel, sel.value, step.default_profile);
        render();
      });
    });

    root.querySelectorAll('.wfp-seg-btn').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var wfId = btn.getAttribute('data-wfp-workflow');
        var stepLabel = btn.getAttribute('data-wfp-step');
        var harness = btn.getAttribute('data-wfp-harness');
        var step = stepByLabel(wfId, stepLabel);
        if (!step) { return; }
        setPendingHarness(wfId, stepLabel, harness, step);
        // When the harness flips to one that doesn't carry the current profile, auto-select
        // that harness's default profile for the step purpose (mirrors the resolver, D-1).
        // A pending profile that already belongs to the toggled harness is preserved.
        var currentProfile = effectiveProfile(wfId, step);
        if (harnessForProfile(currentProfile, null) !== harness) {
          setPending(wfId, stepLabel, defaultProfileForStep(harness, step), step.default_profile);
        }
        render();
      });
    });

    root.querySelectorAll('[data-wfp-reset]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var wfId = btn.getAttribute('data-wfp-workflow');
        var stepLabel = btn.getAttribute('data-wfp-step');
        if (pending[wfId]) { delete pending[wfId][stepLabel]; }
        if (pendingHarness[wfId]) { delete pendingHarness[wfId][stepLabel]; }
        render();
      });
    });

    root.querySelectorAll('[data-wfp-runs]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        loadRuns(btn.getAttribute('data-wfp-runs'));
      });
    });

    // Read-only fragment inspector buttons (T-28-D-01).
    root.querySelectorAll('[data-wfp-fragment]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var workflowSection = btn.closest('[data-wfp-workflow-card]');
        if (!workflowSection) { return; }
        var workflowId = workflowSection.getAttribute('data-wfp-workflow-card');
        loadFragment(workflowId, btn.getAttribute('data-wfp-fragment'));
      });
    });
  }

  // ── Read-only fragment inspector (T-28-D-01) ──────────────────────────────────

  function loadFragment(workflowId, fragmentId) {
    var panel = document.querySelector(
      '[data-wfp-inspector-panel="' + cssEsc(workflowId) + '"]');
    if (!panel) { return; }
    panel.hidden = false;
    panel.innerHTML = '<p class="wfp-loading">Loading fragment…</p>';
    fetchJson('/api/workflow-fragments/' + encodeURIComponent(fragmentId))
      .then(function (res) {
        if (res.status !== 200 || !res.body) {
          var msg = (res.body && res.body.message) || 'Fragment could not be loaded.';
          panel.innerHTML = '<p class="wfp-error" data-testid="wfp-fragment-error">' +
            escHtml(msg) + '</p>';
          return;
        }
        panel.innerHTML = renderFragment(res.body);
      })
      .catch(function () {
        panel.innerHTML = '<p class="wfp-error">Could not load fragment.</p>';
      });
  }

  function renderInputList(items) {
    if (!items || !items.length) { return '<span class="wfp-frag-none">—</span>'; }
    return items.map(function (x) {
      return '<code class="wfp-frag-input">' + escHtml(x) + '</code>';
    }).join(' ');
  }

  function renderFragment(frag) {
    // Read-only: body is rendered as escaped <pre> text (NEVER as markup) so a fragment
    // body can never inject script into the panel (A03/A07). No edit affordance.
    return '<div class="wfp-fragment" data-testid="wfp-fragment-detail">' +
      '<header class="wfp-fragment-head"><code class="wfp-fragment-id">' +
        escHtml(frag.id) + '</code>' +
        '<span class="wfp-fragment-meta">' + escHtml(frag.role || '') + ' · ' +
        escHtml(frag.workflow || '') + '.' + escHtml(frag.step || '') + '</span>' +
        '<span class="wfp-fragment-readonly" title="Fragments are source-controlled; ' +
        'edit them in a release, not the panel">read-only</span></header>' +
      '<dl class="wfp-fragment-fields">' +
        '<dt>Dynamic inputs</dt><dd data-testid="wfp-fragment-dynamic">' +
          renderInputList(frag.dynamic_inputs) + '</dd>' +
        '<dt>Static inputs</dt><dd>' + renderInputList(frag.static_inputs) + '</dd>' +
        '<dt>Output schema</dt><dd data-testid="wfp-fragment-schema"><code>' +
          escHtml(frag.output_schema || '—') + '</code></dd>' +
        '<dt>Max context</dt><dd><code>' +
          escHtml(frag.max_context_policy || '—') + '</code></dd>' +
      '</dl>' +
      '<pre class="wfp-fragment-body" data-testid="wfp-fragment-body">' +
        escHtml(frag.body || '') + '</pre>' +
      '</div>';
  }

  // ── Policy payload ───────────────────────────────────────────────────────────

  function buildPolicyPayload() {
    var workflows = {};
    // Profile overrides → workflow.steps. Harness overrides → workflow.harnesses (D-3).
    var wfId;
    for (wfId in pending) {
      var steps = {};
      for (var step in pending[wfId]) { steps[step] = pending[wfId][step]; }
      if (Object.keys(steps).length) { workflows[wfId] = { steps: steps }; }
    }
    for (wfId in pendingHarness) {
      var harnesses = {};
      for (var hstep in pendingHarness[wfId]) { harnesses[hstep] = pendingHarness[wfId][hstep]; }
      if (Object.keys(harnesses).length) {
        if (!workflows[wfId]) { workflows[wfId] = { steps: {} }; }
        workflows[wfId].harnesses = harnesses;
      }
    }
    return {
      schema_version: 'workflow-model-policy-v1',
      policy_id: 'default',
      contexts: { default: { workflows: workflows } }
    };
  }

  function jsonBody(payload) {
    return {
      method: '',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    };
  }

  function validate() {
    var opts = jsonBody(buildPolicyPayload());
    opts.method = 'POST';
    setBanner('info', 'Validating…');
    return fetchJson('/api/workflow-model-policy/validate?context=' + CONTEXT, opts)
      .then(function (res) {
        if (res.status === 200 && res.body.valid) {
          setBanner('ok', 'Valid — ready to save.');
          return true;
        }
        var msg = (res.body.errors && res.body.errors.map(function (e) {
          return e.path + ': ' + e.message;
        }).join('; ')) || res.body.message || 'Invalid policy.';
        setBanner('error', 'Validation failed — ' + msg);
        return false;
      })
      .catch(function () { setBanner('error', 'Validation request failed.'); return false; });
  }

  function save() {
    // Validate-before-save: never PUT without a green validate first.
    return validate().then(function (ok) {
      if (!ok) { return; }
      var opts = jsonBody(buildPolicyPayload());
      opts.method = 'PUT';
      return fetchJson('/api/workflow-model-policy?context=' + CONTEXT, opts).then(function (res) {
        if (res.status === 200 && res.body.saved) {
          setBanner('ok', 'Saved.');
          pending = {};
          pendingHarness = {};
          return loadCatalog();
        }
        var msg = (res.body.errors && res.body.errors.map(function (e) {
          return e.path + ': ' + e.message;
        }).join('; ')) || res.body.message || res.body.error || 'Save failed.';
        setBanner('error', 'Save failed — ' + msg);
      });
    });
  }

  // ── Run-snapshot evidence (AC-7) ──────────────────────────────────────────────

  function loadRuns(workflowId) {
    var panel = document.querySelector('[data-wfp-runs-panel="' + cssEsc(workflowId) + '"]');
    if (!panel) { return; }
    panel.hidden = false;
    panel.innerHTML = '<p class="wfp-loading">Loading run snapshots…</p>';
    fetchJson('/api/lifecycle-runs?workflow=' + encodeURIComponent(workflowId) +
      '&context=' + CONTEXT).then(function (res) {
      var runs = (res.body && res.body.runs) || [];
      if (!runs.length) {
        panel.innerHTML = '<p class="wfp-runs-empty">No runs recorded for this workflow.</p>';
        return;
      }
      panel.innerHTML = runs.map(renderRunSnapshot).join('');
    }).catch(function () {
      panel.innerHTML = '<p class="wfp-error">Could not load run snapshots.</p>';
    });
  }

  function renderRunSnapshot(run) {
    var snap = run.workflow_policy;
    var steps = (snap && snap.steps) || [];
    var rows = steps.map(function (s) {
      return '<tr><td>' + escHtml(s.step) + '</td><td>' + escHtml(s.harness) +
        '</td><td>' + escHtml(s.model_profile) + '</td><td>' + escHtml(s.model) +
        ' (' + escHtml(s.reasoning) + ')</td><td>' + escHtml(s.source) + '</td></tr>';
    }).join('');
    return '<div class="wfp-run" data-testid="wfp-run-snapshot">' +
      '<div class="wfp-run-head"><code>' + escHtml(run.run_id) + '</code> · ' +
      escHtml(run.status) + ' · prefix ' +
      escHtml((snap && snap.prefix_hash) || '—') + '</div>' +
      '<table class="wfp-run-table"><thead><tr><th>Step</th><th>Harness</th>' +
      '<th>Profile</th><th>Model used</th><th>Source</th></tr></thead><tbody>' +
      rows + '</tbody></table></div>';
  }

  function cssEsc(s) {
    return String(s).replace(/["\\]/g, '\\$&');
  }

  // ── Load ──────────────────────────────────────────────────────────────────────

  function loadProfiles() {
    return fetchJson('/api/workflow-model-profiles').then(function (res) {
      profilesByHarness = {};
      ((res.body && res.body.profiles) || []).forEach(function (p) {
        if (!profilesByHarness[p.harness]) { profilesByHarness[p.harness] = []; }
        profilesByHarness[p.harness].push(p);
      });
    });
  }

  function loadCatalog() {
    return fetchJson('/api/workflow-catalog?context=' + CONTEXT).then(function (res) {
      catalog = res.body;
      render();
    });
  }

  var loaded = false;

  function load() {
    if (loaded) { return; }
    loaded = true;
    var saveBtn = document.getElementById('wfp-save-btn');
    var validateBtn = document.getElementById('wfp-validate-btn');
    if (saveBtn) { saveBtn.addEventListener('click', save); }
    if (validateBtn) { validateBtn.addEventListener('click', validate); }
    loadProfiles().then(loadCatalog).catch(function () {
      var root = document.getElementById('wfp-root');
      if (root) { root.innerHTML = '<p class="wfp-error">Could not load the workflow catalog.</p>'; }
    });
  }

  window.WorkflowPolicy = {
    load: load,
    isLoaded: function () { return loaded; }
  };
  if (window.Panel && window.Panel.register) {
    window.Panel.register('workflow_policy', { load: load });
  }
})();
