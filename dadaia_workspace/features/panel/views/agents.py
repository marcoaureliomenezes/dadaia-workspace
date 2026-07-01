"""Agents tab view. Renders cards with metrics + context breakdown + drill-down.

Consumes /api/agents JSON via PANEL_JS lazy fetch on tab activation.
SPEC § Contratos de endpoint, § Acceptance criteria #3.

Security (OWASP A03):
  This module only returns a static HTML scaffold. No agent data is serialized
  server-side into HTML — all dynamic content is rendered client-side (vanilla JS
  in PANEL_JS) after the auth handshake. This prevents any accidental injection of
  API payloads into HTML and keeps the server-side template free of user-controlled
  data.

Recovery / Secure-Delete Procedure (devops T12):
  If the telemetry database is suspected to be compromised, or if corruption is
  detected (503 on API endpoints with ``telemetry_degraded``), use the following
  secure-delete recipe to purge the sensitive local state:

      shred -u ~/.dadaia/state/telemetry/telemetry.sqlite

  After shredding, restart the panel via ``dadaia panel``.  A fresh SQLite
  database will be generated on next startup.  (The panel uses no auth token.)

  Corrupt database quarantine files (``telemetry.sqlite.corrupt.<utc_ts>``) can be
  found at ``~/.dadaia/state/telemetry/`` and should also be shredded:

      shred -u ~/.dadaia/state/telemetry/telemetry.sqlite.corrupt.*

  Note: ``shred`` is available on Linux (GNU coreutils).  On macOS, use
  ``rm -P`` instead.  On encrypted filesystems (e.g. LUKS, FileVault), ordinary
  ``rm`` is sufficient since the key protects at-rest data.
"""

from __future__ import annotations

import html

from dadaia_workspace.features.lifecycle import model_profiles
from dadaia_workspace.features.lifecycle.personas.loader import Persona, PersonaLoader
from dadaia_workspace.features.workflows.dadaia_catalog import (
    DadaiaWorkflowStepDTO,
    list_dadaia_workflows,
)

#: Constant layer label for every Layer-2 persona (a persona has no single model —
#: model is a per-workflow-STEP binding, never a persona attribute; arch finding #1).
_PERSONA_LAYER = "Layer-2"


def render_agents_section() -> str:
    """Return the static HTML scaffold for the Agents tab (legacy top-level section).

    Kept for backward compatibility. Returns the sub-section HTML used inside
    the consolidated Ops tab.
    """
    return render_agents_subsection()


def render_agents_subsection() -> str:
    """Return the compact sub-section HTML for Agents inside the Ops tab.

    JS fetches dynamic data from /api/agents and /api/agents/{id}/sessions after
    the Ops tab is activated. The server never serializes agent records into this HTML.

    All dynamic content is rendered client-side via the Agents module in PANEL_JS.
    """
    return (
        '<div class="ops-subsection" id="ops-subsection-agents">\n'
        '  <div class="ops-subsection-header">\n'
        '    <h3 class="ops-subsection-title">Claude sub-agents</h3>\n'
        '    <p class="section-meta" id="agents-meta" aria-live="polite">'
        "Harness-native Claude Code sub-agents (role, tier, model).</p>\n"
        '    <div class="runtime-switcher" role="radiogroup" aria-label="Active runtime" style="margin-left:auto;">\n'
        '      <button type="button" class="runtime-btn runtime-btn--claude" id="agents-runtime-btn-claude"\n'
        '        role="radio" aria-checked="true" data-runtime-value="claude" aria-label="Claude runtime">\n'
        '        <span class="runtime-btn-icon" aria-hidden="true">&#9672;</span>\n'
        '        <span class="runtime-btn-label">Claude</span>\n'
        "      </button>\n"
        '      <button type="button" class="runtime-btn runtime-btn--codex" id="agents-runtime-btn-codex"\n'
        '        role="radio" aria-checked="false" data-runtime-value="codex" aria-label="Codex runtime">\n'
        '        <span class="runtime-btn-icon" aria-hidden="true">&#9667;</span>\n'
        '        <span class="runtime-btn-label">Codex</span>\n'
        "      </button>\n"
        '      <button type="button" class="runtime-btn runtime-btn--pi" id="agents-runtime-btn-pi"\n'
        '        role="radio" aria-checked="false" data-runtime-value="pi" aria-label="PI runtime">\n'
        '        <span class="runtime-btn-icon" aria-hidden="true">&#9678;</span>\n'
        '        <span class="runtime-btn-label">PI</span>\n'
        "      </button>\n"
        "    </div>\n"
        "  </div>\n"
        '  <div id="agents-staleness-banner" class="warning-banner" hidden role="status"></div>\n'
        '  <div id="agents-grid" class="card-grid agents-grid agents-grid--compact" aria-busy="false"></div>\n'
        '  <p id="agents-empty" class="empty-state" hidden>'
        + html.escape("Nenhum agente observado ainda.")
        + "</p>\n"
        '  <dialog id="agent-modal"\n'
        '          class="agent-modal"\n'
        '          aria-modal="true"\n'
        '          aria-labelledby="agent-modal-title"\n'
        '          role="dialog">\n'
        '    <div class="agent-modal__inner">\n'
        '      <div class="agent-modal__header">\n'
        '        <h3 class="agent-modal__title" id="agent-modal-title">Agent detail</h3>\n'
        '        <button type="button" class="agent-modal__close" id="agent-modal-close"\n'
        '                aria-label="Close">&#10005;</button>\n'
        "      </div>\n"
        '      <div class="agent-modal__body" id="agent-modal-body">\n'
        "        <!-- populated by JS before showModal() -->\n"
        "      </div>\n"
        "    </div>\n"
        "  </dialog>\n"
        "</div>"
    )


# ---------------------------------------------------------------------------
# Layer-2 personas roster (v0.1.45 / T-45-05) — server-rendered, CSP-clean
# ---------------------------------------------------------------------------


def _step_binding_label(step: DadaiaWorkflowStepDTO) -> str:
    """Render one governed step's harness/model binding for a persona 'where used' row.

    The model shown for a persona is derived ONLY from the STEP binding (arch finding #1):
    the step's governed default harness + concrete model (resolved from its default
    profile). A Python-owned gate step (no worker) carries no harness/model.
    """
    harness = step.default_harness
    if harness is None:
        return "gate — no worker"
    profile_id = step.default_profiles.get(harness)
    if profile_id is None:  # pragma: no cover - guarded by catalog import assert
        return html.escape(harness)
    model_id = model_profiles.resolve(profile_id).model_id
    return f"{html.escape(harness)} · {html.escape(model_id)}"


def _where_used_for_role(role: str) -> list[str]:
    """List the governed workflow steps referencing *role*, as display rows.

    Derived from ``list_dadaia_workflows()`` — each row is
    ``<workflow display-name> → <step label> (<harness · model>)``. Empty when the role
    maps to zero catalog steps (rendered as an explicit "not referenced" line by the
    caller, R5).
    """
    rows: list[str] = []
    for wf in list_dadaia_workflows():
        for step in wf.steps:
            if step.role == role:
                gate = " ⊙" if step.is_gate else ""
                rows.append(
                    f'<li class="persona-step">'
                    f'<span class="persona-step-wf">{html.escape(wf.display_name)}</span>'
                    f'<span class="persona-step-arrow"> → </span>'
                    f'<span class="persona-step-label">{html.escape(step.label)}{gate}</span>'
                    f'<span class="persona-step-binding">{_step_binding_label(step)}</span>'
                    "</li>"
                )
    return rows


def _render_persona_card(persona: Persona) -> str:
    """Render one Layer-2 persona as a data-dense card keyed by role.

    Shows role, ``summary``, ``source_agent``, the constant ``Layer-2`` label (never a
    per-persona model column), and the governed steps that reference the role. All text
    is HTML-escaped (OWASP A03).
    """
    where_used = _where_used_for_role(persona.role)
    if where_used:
        used_html = (
            '<span class="persona-whereused-label">Referenced by governed steps</span>'
            f'<ul class="persona-step-list">{"".join(where_used)}</ul>'
        )
    else:
        used_html = '<p class="persona-whereused-empty">not referenced by any governed step</p>'
    return (
        f'<article class="persona-card" data-role="{html.escape(persona.role)}">'
        '<header class="persona-card-header">'
        f'<h4 class="persona-card-role">{html.escape(persona.role)}</h4>'
        f'<span class="persona-layer-badge">{html.escape(_PERSONA_LAYER)}</span>'
        "</header>"
        f'<p class="persona-summary">{html.escape(persona.summary)}</p>'
        f'<p class="persona-source"><span class="persona-source-label">source</span> '
        f"{html.escape(persona.source_agent)}</p>"
        f'<div class="persona-whereused">{used_html}</div>'
        "</article>"
    )


def render_personas_subsection(loader: PersonaLoader | None = None) -> str:
    """Server-rendered Layer-2 persona roster for the Agentic tab (T-45-05).

    The second labelled roster (keyed by role) beside the Claude sub-agents grid: each of
    the 8 non-PM personas from ``public/personas/`` with role, summary, source_agent, the
    constant ``Layer-2`` label, and the governed workflow steps that reference its role.
    Fully server-rendered (no client script, CSP-clean) so it renders on first paint and
    is unit-testable; any model shown is derived ONLY from step bindings, never invented.
    """
    pl = loader if loader is not None else PersonaLoader()
    try:
        personas = pl.list_personas()
    except Exception:  # noqa: BLE001
        personas = []
    cards = "".join(_render_persona_card(p) for p in personas)
    body = (
        f'<div class="personas-grid">{cards}</div>'
        if personas
        else '<p class="empty-state">No Layer-2 personas found.</p>'
    )
    return (
        '<div class="ops-subsection" id="ops-subsection-personas">\n'
        '  <div class="ops-subsection-header">\n'
        '    <h3 class="ops-subsection-title">Layer-2 personas</h3>\n'
        '    <p class="section-meta">Harness-universal role mandates '
        "(public/personas/). A persona&rsquo;s model is a per-workflow-step binding, "
        "not a persona attribute.</p>\n"
        "  </div>\n"
        f"  {body}\n"
        "</div>"
    )
