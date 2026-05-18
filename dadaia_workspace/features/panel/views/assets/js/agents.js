// agents.js — Agents tab UI (collapsed card grid + skeleton + error/empty states)
// PR3-10 (collapsed) / PR3-11 (expanded — filled in next PR)
//
// Depends on: authedFetch() defined in core.js (loaded before this script)
//
// API contract (SPEC §5.1 — normative):
//   GET /api/agents → { agents: [ { agent_id, display_name, description, status,
//                                    skills, telemetry: { session_count,
//                                    total_cost_usd, total_cost_30d_usd, cost_known,
//                                    last_activity_at, ... } } ], ... }
//
// Card lifecycle:
//   1. Tab activation → Agents.load() called once
//   2. fetch in-flight → skeleton cards rendered with aria-busy="true"
//   3. fetch resolves → real cards rendered
//   4. each card root is a <button aria-expanded="false"> (PR3-11 wires expand)
//   5. error → error-state banner; empty → empty-state element revealed

(function () {
  'use strict';

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
  // Returns "Never" if null/empty. Returns "today", "yesterday", "N days ago",
  // "N months ago", "N years ago".
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

  // Format cost: null/undefined → "—"; otherwise "$N.NN"
  function fmtCost(v, costKnown) {
    if (!costKnown || v == null) { return '—'; }
    return '$' + Number(v).toFixed(2);
  }

  // ── Skeleton rendering ───────────────────────────────────────────────────────

  // Render N placeholder skeleton cards while the API fetch is in flight.
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

  // ── Card rendering ───────────────────────────────────────────────────────────

  // Render a single collapsed agent card.
  // Card root is a <button aria-expanded="false"> per SPEC §7.4.
  // PR3-11 will wire the click → expand + lazy prompt fetch.
  function renderCard(agent) {
    var tel = agent.telemetry || {};
    var isActive = agent.status === 'active';
    var statusClass = isActive ? 'agent-status-badge--active' : 'agent-status-badge--inactive';
    var statusLabel = isActive ? 'ACTIVE' : 'INACTIVE';
    var borderClass = isActive ? 'agent-card--active' : '';

    var sessions = tel.session_count != null ? String(tel.session_count) : '0';
    var cost = fmtCost(tel.total_cost_usd, tel.cost_known);
    var lastSeen = fmtRelativeDate(tel.last_activity_at);

    // Skills chips: show first 2, then "+N more" if more exist
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
      + '<!-- PR3-11: expanded content inserted here on first expand -->'
      + '</div>'
      + '</button>';
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

    // Wire expand/collapse for accessibility (keyboard + click)
    // PR3-11 will replace this stub with the full expand handler
    grid.querySelectorAll('.agent-card[aria-expanded]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        // Stub: PR3-11 implements the full expand/collapse + lazy prompt fetch
        var expanded = btn.getAttribute('aria-expanded') === 'true';
        btn.setAttribute('aria-expanded', String(!expanded));
        var chevron = btn.querySelector('.agent-card__chevron');
        if (chevron) {
          chevron.style.transform = !expanded ? 'rotate(180deg)' : '';
        }
        var detailEl = document.getElementById(btn.getAttribute('aria-controls'));
        if (detailEl) {
          detailEl.hidden = expanded;
        }
      });
      // Enter / Space already handled via button's native click on keydown
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
