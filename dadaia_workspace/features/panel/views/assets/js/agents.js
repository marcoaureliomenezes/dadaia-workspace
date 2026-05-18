// agents.js — Agents tab UI (collapsed + expanded card grid, skeleton, error/empty states)
// PR3-10 (collapsed layout) / PR3-11 (expand interaction + lazy prompt fetch)
//
// Depends on: authedFetch() defined in core.js (loaded before this script)
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
//   3. fetch resolves → real cards rendered (collapsed)
//   4. click (or Enter/Space) → expand: fetch prompt if not cached, render detail
//   5. click again (or Escape with card focused) → collapse
//   6. Multi-open accordion: multiple cards may be expanded simultaneously (SPEC §7.4)
//
// Prompt cache: per-session in-memory Map keyed by agent_id.
//   Re-expanding a card within the same session does NOT re-fetch.
//
// Cost format: total_cost_usd from telemetry → "$N.NN" (2 decimal places).
//   $0.00 if zero; "—" if cost_known is false or field is null.

(function () {
  'use strict';

  // ── Prompt cache (in-memory, keyed by agent_id) ──────────────────────────────
  // Cache size bounded by the canonical agent count (10 today, ≤50 realistic).
  var promptCache = new Map();

  // ── Utilities ────────────────────────────────────────────────────────────────

  function escHtml(s) {
    return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
    });
  }

  function escAttr(s) {
    return escHtml(s);
  }

  // Format a UTC ISO-8601 timestamp as a relative human-readable string.
  // Returns "Never" if null/empty.
  function fmtRelativeDate(iso) {
    if (!iso) { return 'Never'; }
    var then = new Date(iso);
    if (isNaN(then.getTime())) { return 'Never'; }
    var nowMs = Date.now();
    var diffMs = nowMs - then.getTime();
    var diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
    if (diffDays < 0) { return 'just now'; }
    if (diffDays === 0) { return 'today'; }
    if (diffDays === 1) { return 'yesterday'; }
    if (diffDays < 30) { return diffDays + ' days ago'; }
    var diffMonths = Math.floor(diffDays / 30);
    if (diffMonths < 12) { return diffMonths + ' month' + (diffMonths === 1 ? '' : 's') + ' ago'; }
    var diffYears = Math.floor(diffMonths / 12);
    return diffYears + ' year' + (diffYears === 1 ? '' : 's') + ' ago';
  }

  // Format cost: null/undefined or !costKnown → "—"; otherwise "$N.NN"
  // Cost example: $12.34 for total_cost_usd = 12.3456
  function fmtCost(v, costKnown) {
    if (!costKnown || v == null) { return '—'; }
    return '$' + Number(v).toFixed(2);
  }

  // ── Skeleton rendering ───────────────────────────────────────────────────────

  function renderSkeletons(count) {
    var cards = '';
    for (var i = 0; i < count; i++) {
      cards += '<div class="agent-card agent-card--skeleton" aria-hidden="true">'
        + '<div class="agent-card__header">'
        + '<span class="skeleton-badge skeleton-pulse"></span>'
        + '<span class="skeleton-name skeleton-pulse"></span>'
        + '<span class="skeleton-chevron skeleton-pulse"></span>'
        + '</div>'
        + '<div class="skeleton-line skeleton-pulse" style="width:85%"></div>'
        + '<div class="skeleton-line skeleton-pulse" style="width:65%"></div>'
        + '<div class="agent-card__stats">'
        + '<div class="agent-stat skeleton-pulse"></div>'
        + '<div class="agent-stat skeleton-pulse"></div>'
        + '<div class="agent-stat skeleton-pulse"></div>'
        + '</div>'
        + '<div class="agent-card__skills">'
        + '<span class="skill-chip skeleton-pulse" style="width:90px"></span>'
        + '<span class="skill-chip skeleton-pulse" style="width:70px"></span>'
        + '</div>'
        + '</div>';
    }
    return cards;
  }

  // ── Collapsed card rendering ─────────────────────────────────────────────────

  // Render a single collapsed agent card.
  // Card root is a <button aria-expanded="false"> per SPEC §7.4.
  function renderCard(agent) {
    var tel = agent.telemetry || {};
    var isActive = agent.status === 'active';
    var statusClass = isActive ? 'agent-status-badge--active' : 'agent-status-badge--inactive';
    var statusLabel = isActive ? 'ACTIVE' : 'INACTIVE';
    var borderClass = isActive ? 'agent-card--active' : '';

    var sessions = tel.session_count != null ? String(tel.session_count) : '0';
    var cost = fmtCost(tel.total_cost_usd, tel.cost_known);
    var lastSeen = fmtRelativeDate(tel.last_activity_at);

    // Skills chips on the collapsed card: show first 2, then "+N more" if more exist
    var skills = agent.skills || [];
    var visibleSkills = skills.slice(0, 2);
    var hiddenCount = skills.length - visibleSkills.length;
    var skillsHtml = visibleSkills.map(function (s) {
      return '<span class="skill-chip">' + escHtml(s) + '</span>';
    }).join('');
    if (hiddenCount > 0) {
      skillsHtml += '<span class="skill-chip skill-chip--more">+' + hiddenCount + ' more</span>';
    }
    if (skills.length === 0) {
      skillsHtml = '<span class="skill-chip skill-chip--none">no skills</span>';
    }

    var description = agent.description || '';
    var detailId = 'agent-detail-' + escAttr(agent.agent_id);

    return '<button type="button"'
      + ' class="agent-card ' + escAttr(borderClass) + '"'
      + ' data-agent-id="' + escAttr(agent.agent_id) + '"'
      + ' aria-expanded="false"'
      + ' aria-controls="' + escAttr(detailId) + '"'
      + ' aria-label="' + escAttr(agent.display_name || agent.agent_id) + ', ' + statusLabel + '"'
      + '>'
      + '<div class="agent-card__header">'
      + '<span class="agent-status-badge ' + escAttr(statusClass) + '">'
      + '<span class="agent-status-badge__dot" aria-hidden="true"></span>'
      + escHtml(statusLabel)
      + '</span>'
      + '<span class="agent-card__name">' + escHtml(agent.display_name || agent.agent_id) + '</span>'
      + '<span class="agent-card__chevron" aria-hidden="true">&#9660;</span>'
      + '</div>'
      + '<p class="agent-card__description">' + escHtml(description) + '</p>'
      + '<div class="agent-card__stats">'
      + '<div class="agent-stat">'
      + '<span class="agent-stat__label">Sessions</span>'
      + '<span class="agent-stat__value">' + escHtml(sessions) + '</span>'
      + '</div>'
      + '<div class="agent-stat">'
      + '<span class="agent-stat__label">Cost (life)</span>'
      + '<span class="agent-stat__value">' + escHtml(cost) + '</span>'
      + '</div>'
      + '<div class="agent-stat">'
      + '<span class="agent-stat__label">Last seen</span>'
      + '<span class="agent-stat__value">' + escHtml(lastSeen) + '</span>'
      + '</div>'
      + '</div>'
      + '<div class="agent-card__skills">' + skillsHtml + '</div>'
      + '<div id="' + escAttr(detailId) + '" class="agent-card__detail" hidden>'
      + '</div>'
      + '</button>';
  }

  // ── Expanded detail rendering ────────────────────────────────────────────────

  // Render the full skills list (all skills, not truncated) for the expanded panel.
  function renderExpandedSkills(skills) {
    if (!skills || skills.length === 0) {
      return '<span class="agent-detail__no-skills">No skills declared.</span>';
    }
    return skills.map(function (s) {
      return '<span class="skill-chip skill-chip--expanded">' + escHtml(s) + '</span>';
    }).join('');
  }

  // Render context breakdown cost bars.
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

  // Render the expanded detail panel content for an agent.
  // Called once the prompt has been fetched (or after a cache hit).
  // agent: the agent data object from /api/agents
  // promptText: the system_prompt string from /api/agents/<id>/prompt
  function renderDetailContent(agent, promptText) {
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

  // Render an inline loading state for the detail panel (while prompt is fetching).
  function renderDetailLoading() {
    return '<div class="agent-detail agent-detail--loading" aria-busy="true" aria-label="Loading system prompt">'
      + '<div class="agent-detail__loading-row">'
      + '<span class="skeleton-line skeleton-pulse" style="width:60%"></span>'
      + '</div>'
      + '<div class="agent-detail__loading-row">'
      + '<span class="skeleton-line skeleton-pulse" style="width:40%"></span>'
      + '</div>'
      + '</div>';
  }

  // Render an error state in the detail panel.
  function renderDetailError(status) {
    if (status === 401) {
      return '<div class="agent-detail agent-detail--error" role="alert">'
        + '<strong>Authentication required.</strong> '
        + 'Re-authenticate via <code>dadaia panel start</code>.'
        + '</div>';
    }
    return '<div class="agent-detail agent-detail--error" role="alert">'
      + 'Failed to load system prompt (HTTP ' + escHtml(String(status)) + ').'
      + '</div>';
  }

  // ── Expand / collapse interaction ────────────────────────────────────────────

  // Wire clipboard copy for a rendered detail panel.
  // Must be called after the detail HTML is injected into the DOM.
  function wireCopyButton(agentId, promptText) {
    var btn = document.getElementById('copy-prompt-' + agentId);
    if (!btn) { return; }
    btn.addEventListener('click', function (e) {
      e.stopPropagation(); // Don't bubble to card button (would toggle expand)
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

  // Collapse a card: flip aria-expanded, hide detail, reset chevron.
  function collapseCard(btn) {
    btn.setAttribute('aria-expanded', 'false');
    var chevron = btn.querySelector('.agent-card__chevron');
    if (chevron) { chevron.style.transform = ''; }
    var detailEl = document.getElementById(btn.getAttribute('aria-controls'));
    if (detailEl) { detailEl.hidden = true; }
  }

  // Expand a card: flip aria-expanded, show detail, rotate chevron, fetch prompt.
  // The function is intentionally multi-open: it never collapses other cards.
  // (SPEC §7.4: "multi-open accordion — no single-open enforcement")
  function expandCard(btn, agentsData) {
    var agentId = btn.dataset.agentId;
    var detailEl = document.getElementById(btn.getAttribute('aria-controls'));
    if (!detailEl) { return; }

    btn.setAttribute('aria-expanded', 'true');
    var chevron = btn.querySelector('.agent-card__chevron');
    if (chevron) { chevron.style.transform = 'rotate(180deg)'; }
    detailEl.hidden = false;

    // Find the agent data for this card (to render the detail content)
    var agentData = null;
    if (agentsData && agentsData.agents) {
      for (var i = 0; i < agentsData.agents.length; i++) {
        if (agentsData.agents[i].agent_id === agentId) {
          agentData = agentsData.agents[i];
          break;
        }
      }
    }

    // Check prompt cache first
    if (promptCache.has(agentId)) {
      var cachedPrompt = promptCache.get(agentId);
      detailEl.innerHTML = renderDetailContent(agentData || { agent_id: agentId, skills: [], telemetry: {} }, cachedPrompt);
      wireCopyButton(agentId, cachedPrompt);
      return;
    }

    // Render loading state while fetching
    detailEl.innerHTML = renderDetailLoading();

    // Fetch system prompt (lazy, on first expand)
    authedFetch('/api/agents/' + encodeURIComponent(agentId) + '/prompt')
      .then(function (r) {
        if (!r.ok) {
          detailEl.innerHTML = renderDetailError(r.status);
          return null;
        }
        return r.json();
      })
      .then(function (data) {
        if (!data) { return; }
        var promptText = data.system_prompt || '';
        // Store in cache for subsequent expands within this session
        promptCache.set(agentId, promptText);
        // Only update the DOM if the card is still expanded
        if (btn.getAttribute('aria-expanded') === 'true') {
          detailEl.innerHTML = renderDetailContent(
            agentData || { agent_id: agentId, skills: [], telemetry: {} },
            promptText
          );
          wireCopyButton(agentId, promptText);
        }
      })
      .catch(function (err) {
        if (btn.getAttribute('aria-expanded') === 'true') {
          detailEl.innerHTML = '<div class="agent-detail agent-detail--error" role="alert">'
            + 'Failed to load system prompt: ' + escHtml(err && err.message ? err.message : String(err))
            + '</div>';
        }
      });
  }

  // Toggle a card between expanded and collapsed.
  function toggleCard(btn, agentsData) {
    var isExpanded = btn.getAttribute('aria-expanded') === 'true';
    if (isExpanded) {
      collapseCard(btn);
    } else {
      expandCard(btn, agentsData);
    }
  }

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

    // Update meta line
    if (meta) {
      var count = (data.agents || []).length;
      meta.textContent = count + ' agent' + (count === 1 ? '' : 's')
        + ' · window ' + (data.status_window_days || 30) + 'd';
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

    // Wire expand/collapse for each card (click + keyboard)
    // Multi-open accordion: expanding one card does NOT collapse others (SPEC §7.4).
    grid.querySelectorAll('.agent-card[aria-expanded]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        toggleCard(btn, data);
      });

      // Escape key while card has focus → collapse that card
      btn.addEventListener('keydown', function (e) {
        if (e.key === 'Escape') {
          var isExpanded = btn.getAttribute('aria-expanded') === 'true';
          if (isExpanded) {
            collapseCard(btn);
            btn.focus();
          }
        }
        // Enter/Space are already handled natively by the browser for <button>
      });
    });

    applyHashFilter();
  }

  // ── Error state ──────────────────────────────────────────────────────────────

  function renderError(status) {
    var grid = document.getElementById('agents-grid');
    if (!grid) { return; }
    grid.setAttribute('aria-busy', 'false');
    if (status === 401) {
      grid.innerHTML = '<div class="error-state" role="alert">'
        + '<strong>Authentication required.</strong> '
        + 'Re-authenticate by opening the panel with '
        + '<code>dadaia panel start</code> and using the token URL provided.'
        + '</div>';
    } else {
      grid.innerHTML = '<div class="error-state" role="alert">'
        + 'Failed to load agents (HTTP ' + escHtml(String(status)) + '). '
        + '<button type="button" id="agents-retry-btn" class="retry-link">Retry</button>'
        + '</div>';
      var retryBtn = document.getElementById('agents-retry-btn');
      if (retryBtn) {
        retryBtn.addEventListener('click', function () { load(); });
      }
    }
  }

  // ── Load ─────────────────────────────────────────────────────────────────────

  var loaded = false;

  function load() {
    var grid = document.getElementById('agents-grid');
    if (!grid) { return; }
    grid.setAttribute('aria-busy', 'true');
    grid.innerHTML = renderSkeletons(10);

    authedFetch('/api/agents')
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

  // ── Public API ───────────────────────────────────────────────────────────────

  window.Agents = {
    load: load,
    applyHashFilter: applyHashFilter,
    isLoaded: function () { return loaded; },
  };

})();
