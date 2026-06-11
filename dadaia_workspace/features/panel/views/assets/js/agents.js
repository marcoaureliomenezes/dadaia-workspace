// agents.js — Agents tab UI (card grid, modal detail, skeleton, error/empty states)
// PR3-10 (collapsed layout) / P5-D (modal redesign: T-P5-18 to T-P5-21)
//
// Depends on: window.authedFetch() defined in core.js (loaded before this script)
//
// API contracts (SPEC §5.1, §5.2 — normative):
//   GET /api/agents → { agents: [ { agent_id, display_name, description, status,
//                                    skills, tools, model, telemetry: {
//                                      session_count, total_cost_usd, total_cost_30d_usd,
//                                      cost_known, last_activity_at, context_breakdown,
//                                      ... } } ], ... }
//   GET /api/agents/<id>/prompt → { agent_id, system_prompt, source_path }
//
// Card lifecycle:
//   1. Tab activation → Agents.load() called once
//   2. fetch in-flight → skeleton cards rendered with aria-busy="true"
//   3. fetch resolves → real cards rendered (collapsed button with aria-haspopup="dialog")
//   4. click (or Enter/Space) → openModal(): fetch prompt if not cached, render in dialog
//   5. Escape or close button → native <dialog>.close(); focus returns to triggering card
//
// Prompt cache: per-session in-memory Map keyed by agent_id.
//   Re-opening a card's modal within the same session does NOT re-fetch.
//
// Cost format: total_cost_usd from telemetry → "$N.NN" (2 decimal places).
//   $0.00 if zero; "—" if cost_known is false or field is null.

(function () {
  'use strict';

  // ── Prompt cache (in-memory, keyed by agent_id) ──────────────────────────────
  // Cache size bounded by the canonical agent count (10 today, ≤50 realistic).
  var promptCache = new Map();

  // ── Utilities ────────────────────────────────────────────────────────────────

  // TODO: replace with window.escHtml when touching this file
  function escHtml(s) {
    return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
    });
  }

  function escAttr(s) {
    return escHtml(s);
  }

  // Format cost: null/undefined or !costKnown → "—"; otherwise "$N.NN"
  // Cost example: $12.34 for total_cost_usd = 12.3456
  function fmtCost(v, costKnown) {
    if (!costKnown || v == null) { return '—'; }
    return '$' + Number(v).toFixed(2);
  }

  // ── Tier label helper ────────────────────────────────────────────────────────

  // Maps a tier number to its human-readable label text.
  // Default (missing / null / unexpected value): "T3 Leaf" (neutral, harmless fallback).
  function tierLabel(tier) {
    if (tier === 1) { return 'T1 Orchestrator'; }
    if (tier === 2) { return 'T2 Curator'; }
    return 'T3 Leaf';
  }

  // ── Skeleton rendering ───────────────────────────────────────────────────────

  function renderSkeletons(count) {
    var cards = '';
    for (var i = 0; i < count; i++) {
      cards += '<div class="agent-card agent-card--minimal agent-card--skeleton" aria-hidden="true">'
        + '<div class="agent-card__header">'
        + '<span class="skeleton-name skeleton-pulse"></span>'
        + '</div>'
        + '<div class="agent-card__facts">'
        + '<div class="skeleton-line skeleton-pulse" style="width:70%"></div>'
        + '<div class="skeleton-line skeleton-pulse" style="width:85%"></div>'
        + '<div class="skeleton-line skeleton-pulse" style="width:60%"></div>'
        + '</div>'
        + '</div>';
    }
    return cards;
  }

  // ── Minimalist card rendering (operator demand — Agentic tab redesign) ───────

  // Render the model line: configured model id, or the inherited harness default
  // with an explicit marker when the agent declares no model: frontmatter.
  // NEVER fabricate a model id.
  function renderModelValue(agent) {
    if (agent.model) {
      return '<code class="agent-card__model-id">' + escHtml(agent.model) + '</code>';
    }
    // model_inherited is true (or model is null) → inherited default, marked.
    return '<span class="agent-card__model-inherited" title="No model: in frontmatter; '
      + 'uses the harness-inherited default">inherited default</span>';
  }

  // Render the lifecycle phase chips (§7-derived). Neutral "—" when none.
  function renderPhases(phases) {
    var list = phases || [];
    if (list.length === 0) {
      return '<span class="agent-meta-none">&mdash;</span>';
    }
    return list.map(function (p) {
      return '<span class="phase-chip">' + escHtml(p) + '</span>';
    }).join('');
  }

  // Render the workflow membership chips. Neutral "—" when the agent is in none.
  function renderWorkflows(workflows) {
    var list = workflows || [];
    if (list.length === 0) {
      return '<span class="agent-meta-none">&mdash;</span>';
    }
    return list.map(function (w) {
      return '<span class="workflow-chip">' + escHtml(w) + '</span>';
    }).join('');
  }

  // Render a single MINIMALIST collapsed agent card.
  // Card root is a <button aria-haspopup="dialog"> — clicking opens the agent modal.
  // Exactly four data points (no review counts / last-seen / token-cost noise):
  //   1. agent name (+ tier label, retained as a low-key subtitle)
  //   2. agent MODEL (configured model id, or "inherited default" marker)
  //   3. development-lifecycle phase(s) it owns/gates (§7-derived)
  //   4. workflows it takes part in (workflow-definition-derived)
  function renderCard(agent) {
    // data-tier drives the CSS left-accent colour per the tier-aware design spec (PR4-18).
    // Defensive fallback: if agent.tier is absent/null/undefined, default to 3 (T3 Leaf).
    var tierNum = (agent.tier === 1 || agent.tier === 2 || agent.tier === 3)
      ? agent.tier
      : 3;

    return '<button type="button"'
      + ' class="agent-card agent-card--minimal"'
      + ' data-agent-id="' + escAttr(agent.agent_id) + '"'
      + ' data-tier="' + tierNum + '"'
      + ' aria-haspopup="dialog"'
      + ' aria-label="View details for ' + escAttr(agent.display_name || agent.agent_id) + '"'
      + '>'
      + '<div class="agent-card__header">'
      + '<span class="agent-card__name-block">'
      + '<span class="agent-card__name">' + escHtml(agent.display_name || agent.agent_id) + '</span>'
      + '<span class="agent-card__tier-label">' + escHtml(tierLabel(tierNum)) + '</span>'
      + '</span>'
      + '</div>'
      + '<dl class="agent-card__facts">'
      + '<div class="agent-fact">'
      + '<dt class="agent-fact__label">Model</dt>'
      + '<dd class="agent-fact__value">' + renderModelValue(agent) + '</dd>'
      + '</div>'
      + '<div class="agent-fact">'
      + '<dt class="agent-fact__label">Lifecycle</dt>'
      + '<dd class="agent-fact__value agent-fact__chips">' + renderPhases(agent.phases) + '</dd>'
      + '</div>'
      + '<div class="agent-fact">'
      + '<dt class="agent-fact__label">Workflows</dt>'
      + '<dd class="agent-fact__value agent-fact__chips">' + renderWorkflows(agent.workflows) + '</dd>'
      + '</div>'
      + '</dl>'
      + '</button>';
  }

  // ── Modal management (T-P5-18) ──────────────────────────────────────────────

  // Module-level reference to the card button that triggered the modal open.
  // Used to return focus when the modal closes.
  var _triggerCard = null;

  // Render the full skills list (all skills, not truncated) for the modal.
  function renderExpandedSkills(skills) {
    if (!skills || skills.length === 0) {
      return '<span class="agent-detail__no-skills">No skills declared.</span>';
    }
    return skills.map(function (s) {
      return '<span class="skill-chip skill-chip--expanded">' + escHtml(s) + '</span>';
    }).join('');
  }

  // Render context breakdown cost bars for the modal.
  // tel.context_breakdown is an array of { context_name, cost_usd, cost_known }.
  function renderContextBreakdown(tel) {
    var breakdown = tel.context_breakdown || [];
    if (breakdown.length === 0) { return ''; }

    var totalCost = tel.total_cost_usd || 0;
    var rows = breakdown.map(function (entry) {
      var pct = totalCost > 0 ? Math.min(100, (entry.cost_usd / totalCost) * 100) : 0;
      var costStr = fmtCost(entry.cost_usd, tel.cost_known);
      return '<div class="context-breakdown-row">'
        + '<span class="context-breakdown-row__name">' + escHtml(entry.context_name || 'unknown') + '</span>'
        + '<div class="context-bar" role="presentation">'
        + '<div class="context-bar-fill" style="width:' + pct.toFixed(1) + '%"></div>'
        + '</div>'
        + '<span class="context-breakdown-row__cost">' + escHtml(costStr) + '</span>'
        + '</div>';
    }).join('');

    return '<div class="context-breakdown">'
      + '<div class="agent-detail__section-label">Cost by context</div>'
      + rows
      + '</div>';
  }

  // Wire clipboard copy for the system prompt in the modal.
  // Must be called after the modal content is injected into the DOM.
  function wireCopyButton(agentId, promptText) {
    var btn = document.getElementById('copy-prompt-' + agentId);
    if (!btn) { return; }
    btn.addEventListener('click', function () {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(promptText || '').then(function () {
          btn.textContent = 'Copied';
          setTimeout(function () { btn.textContent = 'Copy'; }, 2000);
        }).catch(function () {
          btn.textContent = 'Failed';
          setTimeout(function () { btn.textContent = 'Copy'; }, 2000);
        });
      } else {
        // Fallback: create a transient textarea
        var ta = document.createElement('textarea');
        ta.value = promptText || '';
        ta.style.position = 'fixed';
        ta.style.opacity = '0';
        document.body.appendChild(ta);
        ta.select();
        try {
          document.execCommand('copy');
          btn.textContent = 'Copied';
        } catch (_) {
          btn.textContent = 'Failed';
        }
        document.body.removeChild(ta);
        setTimeout(function () { btn.textContent = 'Copy'; }, 2000);
      }
    });
  }

  // Render the full detail content for the modal body.
  // agent: the agent data object from /api/agents
  // promptText: the system_prompt string from /api/agents/<id>/prompt
  function renderModalContent(agent, promptText) {
    var tel = agent.telemetry || {};
    var skills = agent.skills || [];
    var totalCostStr = fmtCost(tel.total_cost_usd, tel.cost_known);
    var copyBtnId = 'copy-prompt-' + escAttr(agent.agent_id);

    return '<div class="agent-detail">'

      // Full skills section
      + '<div class="agent-detail__section">'
      + '<div class="agent-detail__section-label">Skills</div>'
      + '<div class="agent-detail__skills">'
      + renderExpandedSkills(skills)
      + '</div>'
      + '</div>'

      // Total cost highlight
      + '<div class="agent-detail__section agent-detail__cost-row">'
      + '<span class="agent-detail__section-label">Total cost</span>'
      + '<span class="agent-detail__cost-value">' + escHtml(totalCostStr) + '</span>'
      + '</div>'

      // Context breakdown bars (if available)
      + renderContextBreakdown(tel)

      // System prompt
      + '<div class="agent-detail__section">'
      + '<div class="agent-detail__prompt-header">'
      + '<span class="agent-detail__section-label">System prompt</span>'
      + '<button type="button" class="agent-detail__copy-btn" id="' + escAttr(copyBtnId) + '"'
      + ' aria-label="Copy system prompt to clipboard">'
      + 'Copy'
      + '</button>'
      + '</div>'
      + '<pre class="agent-prompt"><code>' + escHtml(promptText || '') + '</code></pre>'
      + '</div>'

      + '</div>';
  }

  // Render loading skeleton for the modal body while prompt is fetching.
  function renderModalLoading() {
    return '<div class="agent-detail agent-detail--loading" aria-busy="true" aria-label="Loading system prompt">'
      + '<div class="agent-detail__loading-row">'
      + '<span class="skeleton-line skeleton-pulse" style="width:60%"></span>'
      + '</div>'
      + '<div class="agent-detail__loading-row">'
      + '<span class="skeleton-line skeleton-pulse" style="width:40%"></span>'
      + '</div>'
      + '</div>';
  }

  // Render error state in the modal body.
  function renderModalError(status) {
    return '<div class="agent-detail agent-detail--error" role="alert">'
      + 'Failed to load system prompt (HTTP ' + escHtml(String(status)) + ').'
      + '</div>';
  }

  // Open the agent modal for a given agent data object.
  // Shows loading skeleton immediately, then lazy-fetches the system prompt.
  function openModal(agentData) {
    var modal = document.getElementById('agent-modal');
    var titleEl = document.getElementById('agent-modal-title');
    var bodyEl = document.getElementById('agent-modal-body');
    if (!modal || !bodyEl) { return; }

    var agentId = agentData.agent_id;

    // Update modal title
    if (titleEl) {
      titleEl.textContent = agentData.display_name || agentId;
    }

    // Check prompt cache first — render full content immediately if available
    if (promptCache.has(agentId)) {
      var cachedPrompt = promptCache.get(agentId);
      bodyEl.innerHTML = renderModalContent(agentData, cachedPrompt);
      modal.showModal();
      wireCopyButton(agentId, cachedPrompt);
      return;
    }

    // Show loading skeleton, then open modal
    bodyEl.innerHTML = renderModalLoading();
    modal.showModal();

    // Fetch system prompt (lazy, on first open)
    window.authedFetch('/api/agents/' + encodeURIComponent(agentId) + '/prompt')
      .then(function (r) {
        if (!r.ok) {
          bodyEl.innerHTML = renderModalError(r.status);
          return null;
        }
        return r.json();
      })
      .then(function (data) {
        if (!data) { return; }
        var promptText = data.system_prompt || '';
        // Cache for subsequent opens within this session
        promptCache.set(agentId, promptText);
        // Only update DOM if the modal is still open
        if (modal.open) {
          bodyEl.innerHTML = renderModalContent(agentData, promptText);
          wireCopyButton(agentId, promptText);
        }
      })
      .catch(function (err) {
        if (modal.open) {
          bodyEl.innerHTML = '<div class="agent-detail agent-detail--error" role="alert">'
            + 'Failed to load system prompt: ' + escHtml(err && err.message ? err.message : String(err))
            + '</div>';
        }
      });
  }

  // Close the agent modal.
  function closeModal() {
    var modal = document.getElementById('agent-modal');
    if (modal) { modal.close(); }
  }

  // ── Modal wiring (called once at module load) ────────────────────────────────

  (function wireModal() {
    var modal = document.getElementById('agent-modal');
    var closeBtn = document.getElementById('agent-modal-close');
    if (!modal) { return; }

    // Focus returns to the card that opened the modal when it closes (Escape or close btn)
    modal.addEventListener('close', function () {
      if (_triggerCard) {
        _triggerCard.focus();
        _triggerCard = null;
      }
    });

    if (closeBtn) {
      closeBtn.addEventListener('click', function () { closeModal(); });
    }
  }());

  // ── Apply hash filter ────────────────────────────────────────────────────────

  function applyHashFilter() {
    var m = location.hash.match(/^#agents[?]filter=(.+)$/);
    if (!m) { return; }
    var want = decodeURIComponent(m[1]);
    document.querySelectorAll('.agent-card[data-agent-id]').forEach(function (card) {
      card.style.display = card.dataset.agentId === want ? '' : 'none';
    });
  }

  // ── Render response ──────────────────────────────────────────────────────────

  function render(data) {
    var grid = document.getElementById('agents-grid');
    var empty = document.getElementById('agents-empty');
    var meta = document.getElementById('agents-meta');
    var banner = document.getElementById('agents-staleness-banner');

    if (!grid) { return; }

    // Update meta line (minimalist: agent count only — no window/cost noise)
    if (meta) {
      var count = (data.agents || []).length;
      meta.textContent = count + ' agent' + (count === 1 ? '' : 's');
    }

    // Staleness banner
    if (banner) {
      if (data.pricing_age_days != null && data.pricing_age_days > 90) {
        banner.hidden = false;
        banner.textContent = 'Pricing data is ' + data.pricing_age_days
          + ' days old — costs may be stale.';
      } else {
        banner.hidden = true;
      }
    }

    var agents = data.agents || [];

    if (agents.length === 0) {
      grid.innerHTML = '';
      grid.setAttribute('aria-busy', 'false');
      if (empty) { empty.hidden = false; }
      return;
    }

    if (empty) { empty.hidden = true; }
    grid.innerHTML = agents.map(renderCard).join('');
    grid.setAttribute('aria-busy', 'false');

    // Wire each card button to open the agent modal on click.
    // Escape is handled natively by the <dialog> element.
    grid.querySelectorAll('.agent-card[aria-haspopup="dialog"]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var agentId = btn.dataset.agentId;
        var agentData = null;
        if (data.agents) {
          for (var i = 0; i < data.agents.length; i++) {
            if (data.agents[i].agent_id === agentId) {
              agentData = data.agents[i];
              break;
            }
          }
        }
        if (!agentData) { return; }
        _triggerCard = btn;
        openModal(agentData);
      });
    });

    applyHashFilter();
  }

  // ── Error state ──────────────────────────────────────────────────────────────

  function renderError(status) {
    var grid = document.getElementById('agents-grid');
    if (!grid) { return; }
    grid.setAttribute('aria-busy', 'false');
    grid.innerHTML = '<div class="error-state" role="alert">'
      + 'Failed to load agents (HTTP ' + escHtml(String(status)) + '). '
      + '<button type="button" id="agents-retry-btn" class="retry-link">Retry</button>'
      + '</div>';
    var retryBtn = document.getElementById('agents-retry-btn');
    if (retryBtn) {
      retryBtn.addEventListener('click', function () { load(); });
    }
  }

  // ── Load ─────────────────────────────────────────────────────────────────────

  // ── Runtime helper ────────────────────────────────────────────────────────────
  // Phase D ships window.Runtime; fall back to 'claude' if not yet available.
  function getRuntime() {
    if (window.Runtime && typeof window.Runtime.get === 'function') {
      return window.Runtime.get();
    }
    return 'claude';
  }

  var loaded = false;

  function load() {
    var grid = document.getElementById('agents-grid');
    if (!grid) { return; }
    grid.setAttribute('aria-busy', 'true');
    grid.innerHTML = renderSkeletons(10);

    window.authedFetch('/api/agents?runtime=' + encodeURIComponent(getRuntime()))
      .then(function (r) {
        if (!r.ok) {
          renderError(r.status);
          return null;
        }
        return r.json();
      })
      .then(function (data) {
        if (!data) { return; }
        render(data);
        loaded = true;
      })
      .catch(function (err) {
        var grid2 = document.getElementById('agents-grid');
        if (grid2) {
          grid2.setAttribute('aria-busy', 'false');
          grid2.innerHTML = '<div class="error-state" role="alert">'
            + 'Failed to load agents: ' + escHtml(err && err.message ? err.message : String(err))
            + '</div>';
        }
      });
  }

  // ── Runtime-change subscription (PR5-D5) ─────────────────────────────────────
  // When the operator switches runtimes, drop the prompt cache and refetch so the
  // Agents tab reflects the newly selected runtime's agents.
  // data-tier wiring (PR4-18) is preserved in renderCard() above — both coexist.

  document.addEventListener('dadaia:runtime-change', function () {
    promptCache.clear();
    loaded = false;
    // Only refetch if the Ops section (parent) is currently active (avoid background load)
    var section = document.getElementById('section-ops');
    if (section && section.classList.contains('active')) {
      load();
    }
  });

  // ── Public API ───────────────────────────────────────────────────────────────

  window.Agents = {
    load: load,
    applyHashFilter: applyHashFilter,
    isLoaded: function () { return loaded; },
  };

})();
