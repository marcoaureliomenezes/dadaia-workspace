// workflow_policy.js — Workflows tab: inline per-step model pickers (v0.1.45 redesign).
//
// The per-step model governance is MERGED into the workflow diagram cards: each
// model-driven step card in a workflow's <details> expand carries a picker mount
//   <div class="wf-step-picker" data-wfp-workflow="<id>" data-wfp-step="<label>">
// which this module hydrates with a real editor:
//   - segmented codex/pi harness control
//   - profile dropdown filtered by the selected harness (options incl. the labelled
//     OpenRouter kimi option, e.g. pi-openrouter-kimi-high / "OpenRouter — kimi-2.7 (high)")
//   - concrete model + effort readout
//   - default-vs-effective diff + reset-to-default
// A single visible toolbar (Validate / Save) in the section header commits the pending
// overrides: validate-before-save (POST …/validate) then persist (PUT …).
//
// Data sources (Wave C GET routes, all loopback, no credential):
//   GET /api/workflow-catalog            → { workflows: [{ workflow_id, steps:[...] }] }
//   GET /api/workflow-model-profiles     → { profiles: [...], model_choices: {...} }
//   GET /api/workflow-model-policy       → { exists, policy }
// Mutations:
//   POST /api/workflow-model-policy/validate   (dry-run)
//   PUT  /api/workflow-model-policy            (persist)
//
// Security: every value rendered into the DOM goes through escHtml. Workflow ids / step
// labels are catalog-controlled (the governed catalog projects [A-Za-z0-9_] identifiers),
// never operator free-text. The server-rendered SVG fluxogram (already on the page) is the
// canonical diagram — no browser-Mermaid is an execution dependency.

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

  // Escape a value for use inside an attribute-selector string ("...").
  function cssAttr(s) {
    return String(s).replace(/["\\]/g, '\\$&');
  }

  function fetchJson(url, opts) {
    var f = window.authedFetch || window.fetch;
    return f(url, opts || {}).then(function (r) {
      return r.json().then(function (body) { return { status: r.status, body: body }; });
    });
  }

  // In-memory edit state: { workflow_id: { step: profile_id } } — pending profile overrides.
  var pending = {};
  // Pending harness overrides: { workflow_id: { step: harness } }.
  var pendingHarness = {};
  var profilesByHarness = {}; // harness -> [profile]
  var modelChoicesByHarness = {}; // harness -> [{value, label}] (full allowed set)
  var catalog = null;         // last catalog payload

  function profilesFor(harness) {
    return profilesByHarness[harness] || [];
  }

  // ── Effective-state helpers ──────────────────────────────────────────────────

  // The step's effective harness: a pending toggle wins, else the catalog row's
  // resolved harness (which already folds the persisted overlay).
  function effectiveHarness(workflowId, step) {
    var h = pendingHarness[workflowId] && pendingHarness[workflowId][step.step];
    return h != null ? h : step.harness;
  }

  function effectiveProfile(workflowId, step) {
    var p = pending[workflowId] && pending[workflowId][step.step];
    if (p != null) { return p; }
    var ph = pendingHarness[workflowId] && pendingHarness[workflowId][step.step];
    if (ph != null && ph !== step.harness) {
      return defaultProfileForStep(ph, step);
    }
    return step.effective_profile;
  }

  // The harness's default profile for this step comes straight off the catalog row's
  // ``default_profiles`` map — the SAME map the resolver uses for auto-profile.
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

  // ── Picker markup ─────────────────────────────────────────────────────────────

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

  // The inner control injected into one step's picker mount: harness segment + profile
  // dropdown + concrete-model readout + default-vs-effective diff + reset.
  function renderPickerControl(workflowId, step) {
    var eff = effectiveProfile(workflowId, step);
    var harness = effectiveHarness(workflowId, step);
    var defaultHarness = step.default_harness || harnessForProfile(step.default_profile, harness);
    var harnessOverridden = harness !== defaultHarness;
    var isOverridden = eff !== step.default_profile || harnessOverridden;

    var harnessFlag = harnessOverridden
      ? '<span class="wfp-diff-harness" data-testid="wfp-diff-harness">harness: ' +
        escHtml(defaultHarness) + ' → ' + escHtml(harness) + '</span>'
      : '';
    var diff = isOverridden
      ? '<span class="wfp-diff" data-testid="wfp-diff">default: ' +
        escHtml(step.default_profile) + ' → ' + escHtml(eff) + '</span>' + harnessFlag
      : '<span class="wfp-diff wfp-diff--none">default</span>';

    var model = escHtml(step.model || '—') +
      (step.reasoning ? ' <span class="wfp-effort">(' + escHtml(step.reasoning) + ')</span>' : '');

    return '<div class="wfp-picker' + (isOverridden ? ' wfp-picker--overridden' : '') + '">' +
      '<div class="wfp-picker-controls">' +
        renderHarnessSegment(workflowId, step, harness) +
        '<select class="wfp-profile-select" aria-label="Model profile for ' + escHtml(step.step) + '" ' +
          'data-wfp-workflow="' + escHtml(workflowId) + '" data-wfp-step="' + escHtml(step.step) + '">' +
          renderProfileOptions(harness, eff) + '</select>' +
      '</div>' +
      '<div class="wfp-picker-meta">' +
        '<span class="wfp-picker-model">' + model + '</span>' +
        diff +
        '<button type="button" class="wfp-reset-btn" data-wfp-reset ' +
          'data-wfp-workflow="' + escHtml(workflowId) + '" data-wfp-step="' + escHtml(step.step) + '"' +
          (isOverridden ? '' : ' disabled') + '>reset</button>' +
      '</div>' +
    '</div>';
  }

  function findMount(workflowId, stepLabel) {
    return document.querySelector(
      '.wf-step-picker[data-wfp-workflow="' + cssAttr(workflowId) + '"]' +
      '[data-wfp-step="' + cssAttr(stepLabel) + '"]');
  }

  // Hydrate every step picker mount from the catalog + pending state, then (re)bind.
  function render() {
    if (!catalog) { return; }
    (catalog.workflows || []).forEach(function (wf) {
      (wf.steps || []).forEach(function (step) {
        var mount = findMount(wf.workflow_id, step.step);
        if (mount) { mount.innerHTML = renderPickerControl(wf.workflow_id, step); }
      });
    });
    bindPickerEvents();
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

  function bindPickerEvents() {
    document.querySelectorAll('.wf-step-picker .wfp-profile-select').forEach(function (sel) {
      sel.addEventListener('change', function () {
        var wfId = sel.getAttribute('data-wfp-workflow');
        var stepLabel = sel.getAttribute('data-wfp-step');
        var step = stepByLabel(wfId, stepLabel);
        if (!step) { return; }
        setPending(wfId, stepLabel, sel.value, step.default_profile);
        render();
      });
    });

    document.querySelectorAll('.wf-step-picker .wfp-seg-btn').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var wfId = btn.getAttribute('data-wfp-workflow');
        var stepLabel = btn.getAttribute('data-wfp-step');
        var harness = btn.getAttribute('data-wfp-harness');
        var step = stepByLabel(wfId, stepLabel);
        if (!step) { return; }
        setPendingHarness(wfId, stepLabel, harness, step);
        // When the harness flips to one that doesn't carry the current profile, auto-select
        // that harness's default profile for the step purpose (mirrors the resolver).
        var currentProfile = effectiveProfile(wfId, step);
        if (harnessForProfile(currentProfile, null) !== harness) {
          setPending(wfId, stepLabel, defaultProfileForStep(harness, step), step.default_profile);
        }
        render();
      });
    });

    document.querySelectorAll('.wf-step-picker [data-wfp-reset]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var wfId = btn.getAttribute('data-wfp-workflow');
        var stepLabel = btn.getAttribute('data-wfp-step');
        if (pending[wfId]) { delete pending[wfId][stepLabel]; }
        if (pendingHarness[wfId]) { delete pendingHarness[wfId][stepLabel]; }
        render();
      });
    });
  }

  // ── Policy payload ───────────────────────────────────────────────────────────

  function buildPolicyPayload() {
    var workflows = {};
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

  // ── Load ──────────────────────────────────────────────────────────────────────

  function loadProfiles() {
    return fetchJson('/api/workflow-model-profiles').then(function (res) {
      profilesByHarness = {};
      ((res.body && res.body.profiles) || []).forEach(function (p) {
        if (!profilesByHarness[p.harness]) { profilesByHarness[p.harness] = []; }
        profilesByHarness[p.harness].push(p);
      });
      // The full per-harness allowed concrete-model catalog (incl. curated OpenRouter ids
      // like kimi-2.7:high, each labelled). Retained for reference/tooltips.
      modelChoicesByHarness = (res.body && res.body.model_choices) || {};
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
      setBanner('error', 'Could not load the workflow model catalog.');
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
