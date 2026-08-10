// agent_policy.js — Sub-agents tab: L1 agent model governance (v0.1.65 FR8).
//
// Renders the roster table (the 9 core agents) with a per-agent
// model picker (registry models) + effort picker (low|medium|high|xhigh|max), a
// template selector, and an explicit Apply button (validate-before-save — G-2 Apply
// semantics: PUT persists the overlay AND re-renders BOTH L1 projections). After a
// successful Apply, a pop-up shows the per-harness pickup instructions returned by the
// server plus what was re-rendered.
//
// Data sources (loopback, no credential — same posture as every panel route):
//   GET /api/agent-model-policy      → { exists, policy, resolved }
//   GET /api/agent-model-templates   → { templates, models, efforts }
// Mutations:
//   POST /api/agent-model-policy/validate   (dry-run)
//   PUT  /api/agent-model-policy            (persist + re-render both projections)
//
// Security: every value rendered into the DOM goes through escHtml. Agent names,
// model ids, and effort values are server-controlled vocabularies, never free text.

(function () {
  'use strict';

  function escHtml(s) {
    return (window.escHtml || function (x) {
      return String(x == null ? '' : x).replace(/[&<>"]/g, function (c) {
        return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
      });
    })(s);
  }

  function fetchJson(url, opts) {
    return window.fetch(url, opts || {}).then(function (r) {
      return r.json().then(function (body) { return { status: r.status, body: body }; });
    });
  }

  var templates = [];        // [{id, label, default, assignments}]
  var models = [];           // registry claude ids (canonical storage vocabulary)
  var modelsByHarness = {};  // harness -> {claudeId: harness-native display id}
  var efforts = [];          // low..max
  var policy = null;         // last GET policy document
  var resolved = {};         // last GET resolved roster {agent: {model, effort, source}}
  var selectedTemplate = null;   // template id driving the pickers
  var pendingOverrides = {};     // {agent: {model?, effort?}} — the edit state

  function templateById(id) {
    for (var i = 0; i < templates.length; i++) {
      if (templates[i].id === id) { return templates[i]; }
    }
    return null;
  }

  function defaultTemplateId() {
    for (var i = 0; i < templates.length; i++) {
      if (templates[i].default) { return templates[i].id; }
    }
    return templates.length ? templates[0].id : null;
  }

  function isCoreAgent(agent) {
    var t = templateById(selectedTemplate) || templateById(defaultTemplateId());
    return !!(t && t.assignments[agent]);
  }

  // The template baseline for one agent: {model, effort} from the active template.
  function baselineFor(agent) {
    var t = templateById(selectedTemplate);
    if (t && t.assignments[agent]) { return t.assignments[agent]; }
    return null;
  }

  function effectiveFor(agent) {
    var base = baselineFor(agent) || { model: null, effort: null };
    var ov = pendingOverrides[agent] || {};
    return {
      model: ov.model != null ? ov.model : base.model,
      effort: ov.effort !== undefined ? ov.effort : base.effort
    };
  }

  function setPendingField(agent, field, value) {
    var base = baselineFor(agent) || {};
    var ov = pendingOverrides[agent] || {};
    var baseValue = field === 'model' ? base.model : base.effort;
    if (value === baseValue || (value === '' && baseValue == null)) {
      delete ov[field];
    } else {
      ov[field] = value === '' ? null : value;
    }
    if (ov.model === undefined && ov.effort === undefined) {
      delete pendingOverrides[agent];
    } else {
      pendingOverrides[agent] = ov;
    }
  }

  function setBanner(kind, message) {
    var banner = document.getElementById('ap-banner');
    if (!banner) { return; }
    banner.className = 'ap-banner ap-banner--' + kind;
    banner.textContent = message;
    banner.hidden = !message;
  }

  // ── Render ─────────────────────────────────────────────────────────────────

  function renderTemplateOptions() {
    var sel = document.getElementById('ap-template-select');
    if (!sel) { return; }
    var out = '';
    for (var i = 0; i < templates.length; i++) {
      var t = templates[i];
      var selAttr = t.id === selectedTemplate ? ' selected' : '';
      out += '<option value="' + escHtml(t.id) + '"' + selAttr + '>' +
        escHtml(t.label || t.id) + (t.default ? ' — default' : '') + '</option>';
    }
    sel.innerHTML = out;
  }

  // --- Harness-native model view (bug agents-tab-model-picker-ignores-harness-runtime).
  // The overlay stores canonical claude ids; the picker DISPLAYS the toggled
  // harness's native vocabulary (codex -> gpt-*, kimi -> moonshotai/*). Values
  // submitted stay canonical: a native pick maps back to the first canonical id
  // that projects to it.
  function activeRuntime() {
    return (window.Runtime && window.Runtime.get && window.Runtime.get()) || 'claude';
  }

  function nativeMap() {
    return modelsByHarness[activeRuntime()] || null;
  }

  function renderModelOptions(selectedCanonical) {
    var map = nativeMap();
    if (!map || activeRuntime() === 'claude') {
      return renderSelectOptions(models, selectedCanonical, null);
    }
    // Distinct native ids, each carrying a representative canonical value.
    var seen = {};
    var out = '';
    var selectedNative = map[selectedCanonical] || selectedCanonical;
    for (var i = 0; i < models.length; i++) {
      var nat = map[models[i]] || models[i];
      if (seen[nat]) { continue; }
      seen[nat] = models[i];
      out += '<option value="' + escHtml(seen[nat]) + '"' +
        (nat === selectedNative ? ' selected' : '') + '>' + escHtml(nat) + '</option>';
    }
    return out;
  }

  function renderSelectOptions(values, selected, emptyLabel) {
    var out = '';
    if (emptyLabel != null) {
      out += '<option value=""' + (selected == null ? ' selected' : '') + '>' +
        escHtml(emptyLabel) + '</option>';
    }
    for (var i = 0; i < values.length; i++) {
      var v = values[i];
      out += '<option value="' + escHtml(v) + '"' + (v === selected ? ' selected' : '') + '>' +
        escHtml(v) + '</option>';
    }
    return out;
  }

  function sourceFor(agent) {
    if (pendingOverrides[agent]) { return 'override (pending)'; }
    var entry = resolved[agent];
    return entry ? entry.source : '';
  }

  function renderRoster() {
    var mount = document.getElementById('ap-roster');
    if (!mount) { return; }
    var agents = Object.keys(resolved);
    if (!agents.length) {
      mount.innerHTML = '<div class="empty-state">No agents resolved.</div>';
      return;
    }
    var core = agents.filter(isCoreAgent).sort();
    var rows = '';
    core.forEach(function (agent) {
      var eff = effectiveFor(agent);
      var source = sourceFor(agent);
      var isOverride = source.indexOf('override') === 0;
      var effortSelect = renderSelectOptions(efforts, eff.effort, null);
      rows += '<tr>' +
        '<td class="ap-agent-name">' + escHtml(agent) + '</td>' +
        '<td><select class="ap-model-select" aria-label="Model for ' + escHtml(agent) + '" ' +
          'data-ap-agent="' + escHtml(agent) + '">' +
          renderModelOptions(eff.model) + '</select></td>' +
        '<td><select class="ap-effort-select" aria-label="Effort for ' + escHtml(agent) + '" ' +
          'data-ap-agent="' + escHtml(agent) + '">' + effortSelect + '</select></td>' +
        '<td><span class="ap-source-badge' + (isOverride ? ' ap-source-badge--override' : '') +
          '">' + escHtml(source) + '</span></td>' +
        '</tr>';
    });
    mount.innerHTML =
      '<table class="ap-roster-table">' +
      '<thead><tr><th scope="col">Agent</th><th scope="col">Model</th>' +
      '<th scope="col">Effort</th><th scope="col">Source</th></tr></thead>' +
      '<tbody>' + rows + '</tbody></table>';
    bindRosterEvents();
  }

  function bindRosterEvents() {
    document.querySelectorAll('#ap-roster .ap-model-select').forEach(function (sel) {
      sel.addEventListener('change', function () {
        setPendingField(sel.getAttribute('data-ap-agent'), 'model', sel.value);
        renderRoster();
      });
    });
    document.querySelectorAll('#ap-roster .ap-effort-select').forEach(function (sel) {
      sel.addEventListener('change', function () {
        setPendingField(sel.getAttribute('data-ap-agent'), 'effort', sel.value);
        renderRoster();
      });
    });
  }

  // ── Policy payload ───────────────────────────────────────────────────────────

  function buildPolicyDoc() {
    var doc = { schema_version: 'agent-model-policy-v1' };
    if (selectedTemplate) { doc.applied_template = selectedTemplate; }
    var overrides = {};
    var any = false;
    for (var agent in pendingOverrides) {
      var ov = pendingOverrides[agent];
      var entry = {};
      if (ov.model != null) { entry.model = ov.model; }
      if (ov.effort != null) { entry.effort = ov.effort; }
      if (Object.keys(entry).length) { overrides[agent] = entry; any = true; }
    }
    if (any) { doc.overrides = overrides; }
    return doc;
  }

  function jsonOpts(method, payload) {
    return {
      method: method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    };
  }

  // ── Post-apply pop-up (G-2) ──────────────────────────────────────────────────

  function showPopup(result) {
    var popup = document.getElementById('ap-popup');
    var body = document.getElementById('ap-popup-body');
    if (!popup || !body) { return; }
    var instructions = result.instructions || {};
    var items = '';
    for (var harness in instructions) {
      items += '<li><strong>' + escHtml(harness) + '</strong>: ' +
        escHtml(instructions[harness]) + '</li>';
    }
    var rerendered = result.rerendered || [];
    var lines = rerendered.length
      ? rerendered.map(function (l) { return escHtml(l); }).join('<br>')
      : 'Projections already up to date (no files changed).';
    body.innerHTML =
      '<p>Policy applied — both L1 projections were re-rendered.</p>' +
      '<ul class="ap-popup-instructions">' + items + '</ul>' +
      '<div class="ap-popup-rerendered" data-testid="ap-rerendered">' + lines + '</div>';
    popup.hidden = false;
    var closeBtn = document.getElementById('ap-popup-close');
    if (closeBtn) { closeBtn.focus(); }
  }

  function hidePopup() {
    var popup = document.getElementById('ap-popup');
    if (popup) { popup.hidden = true; }
  }

  // ── Apply (validate-before-save) ─────────────────────────────────────────────

  function errorMessage(body) {
    return (body.errors && body.errors.map(function (e) {
      return e.path + ': ' + e.message;
    }).join('; ')) || body.message || body.error || 'Invalid policy.';
  }

  function apply() {
    var payload = buildPolicyDoc();
    setBanner('info', 'Validating…');
    return fetchJson('/api/agent-model-policy/validate', jsonOpts('POST', payload))
      .then(function (res) {
        if (!(res.status === 200 && res.body.valid)) {
          setBanner('error', 'Validation failed — ' + errorMessage(res.body));
          return null;
        }
        setBanner('info', 'Applying…');
        return fetchJson('/api/agent-model-policy', jsonOpts('PUT', payload));
      })
      .then(function (res) {
        if (!res) { return; }
        if (res.status === 200 && res.body.saved) {
          setBanner('ok', 'Applied.');
          pendingOverrides = {};
          showPopup(res.body);
          return loadPolicy();
        }
        setBanner('error', 'Apply failed — ' + errorMessage(res.body));
      })
      .catch(function () { setBanner('error', 'Apply request failed.'); });
  }

  // ── Load ─────────────────────────────────────────────────────────────────────

  function loadTemplates() {
    return fetchJson('/api/agent-model-templates').then(function (res) {
      templates = (res.body && res.body.templates) || [];
      models = (res.body && res.body.models) || [];
      modelsByHarness = (res.body && res.body.models_by_harness) || {};
      efforts = (res.body && res.body.efforts) || [];
    });
  }

  function loadPolicy() {
    return fetchJson('/api/agent-model-policy').then(function (res) {
      if (res.status !== 200) {
        setBanner('error', 'Could not load the agent model policy — ' +
          errorMessage(res.body || {}));
        return;
      }
      policy = res.body.policy || {};
      resolved = res.body.resolved || {};
      selectedTemplate = policy.applied_template || defaultTemplateId();
      // Seed the edit state from the persisted overrides so Apply round-trips them.
      pendingOverrides = {};
      var persisted = policy.overrides || {};
      for (var a in persisted) {
        pendingOverrides[a] = {};
        if (persisted[a].model != null) { pendingOverrides[a].model = persisted[a].model; }
        if (persisted[a].effort != null) { pendingOverrides[a].effort = persisted[a].effort; }
      }
      renderTemplateOptions();
      renderRoster();
    });
  }

  var loaded = false;

  function load() {
    if (loaded) { return; }
    loaded = true;
    var applyBtn = document.getElementById('ap-apply-btn');
    if (applyBtn) { applyBtn.addEventListener('click', apply); }
    var templateSel = document.getElementById('ap-template-select');
    if (templateSel) {
      templateSel.addEventListener('change', function () {
        selectedTemplate = templateSel.value;
        // A template switch resets per-agent edits to the new baseline.
        pendingOverrides = {};
        renderRoster();
      });
    }
    var closeBtn = document.getElementById('ap-popup-close');
    if (closeBtn) { closeBtn.addEventListener('click', hidePopup); }
    var popup = document.getElementById('ap-popup');
    if (popup) {
      popup.addEventListener('keydown', function (e) {
        if (e.key === 'Escape') { hidePopup(); }
      });
    }
    loadTemplates().then(loadPolicy).catch(function () {
      setBanner('error', 'Could not load the agent model governance data.');
    });
    // The model pickers show the toggled harness's native vocabulary — re-render
    // on every runtime switch so codex/kimi never display claude-* ids.
    document.addEventListener('dadaia:runtime-change', function () {
      if (loaded) { renderRoster(); }
    });
  }

  // Lazy activation on the Sub-agents tab (self-contained — no core.js change).
  document.addEventListener('DOMContentLoaded', function () {
    var tab = document.querySelector('.nav-tab[data-section="subagents"]');
    if (tab) { tab.addEventListener('click', load); }
    if (window.location.hash.indexOf('#subagents') === 0) { load(); }
  });

  window.AgentPolicy = {
    load: load,
    isLoaded: function () { return loaded; }
  };
  if (window.Panel && window.Panel.register) {
    window.Panel.register('agent_policy', { load: load });
  }
})();
