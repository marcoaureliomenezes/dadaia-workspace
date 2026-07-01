"""Workflows tab view. Renders a static scaffold for the card-grid Workflows experience.

PR3-16: The old 2-pane layout (workflows-list nav + workflows-detail pane) is replaced
by a full-width card grid sourced from /api/workflows. The div#workflows-grid is now the
container workflows.js populates with one .workflow-card per workflow.

PR3-17 will extend this scaffold with the detail-view overlay HTML.

Security (OWASP A03):
  This module returns a static HTML scaffold only. No workflow data is
  serialised server-side — all dynamic content is rendered client-side by
  window.Workflows in workflows.js after the auth handshake.
"""

from __future__ import annotations

import html

from dadaia_workspace.features.workflows.dadaia_catalog import (
    AVAILABILITY_AVAILABLE,
    AVAILABILITY_DEFERRED,
    AVAILABILITY_PARTIAL,
    DadaiaWorkflowDTO,
    DadaiaWorkflowStepDTO,
    list_dadaia_workflows,
)

_AVAILABILITY_LABEL: dict[str, str] = {
    AVAILABILITY_AVAILABLE: "Available",
    AVAILABILITY_PARTIAL: "Partial",
    AVAILABILITY_DEFERRED: "Deferred / unavailable",
}


def _availability_badge(availability: str) -> str:
    label = _AVAILABILITY_LABEL.get(availability, availability)
    unavailable = " dadaia-wf-badge--unavailable" if availability == AVAILABILITY_DEFERRED else ""
    return (
        f'<span class="dadaia-wf-badge dadaia-wf-badge--{html.escape(availability)}{unavailable}" '
        f'data-availability="{html.escape(availability)}">{html.escape(label)}</span>'
    )


def _render_step_harness(step: DadaiaWorkflowStepDTO) -> str:
    if not step.harness_options:
        return '<span class="dadaia-wf-step-harness dadaia-wf-step-harness--none">— (Python gate, no worker)</span>'
    parts: list[str] = []
    for harness in step.harness_options:
        models = step.model_options.get(harness, [])
        models_txt = ", ".join(html.escape(m) for m in models) if models else "—"
        parts.append(
            f'<span class="dadaia-wf-harness"><strong>{html.escape(harness)}</strong>: '
            f"{models_txt}</span>"
        )
    return '<span class="dadaia-wf-step-harness">' + " &nbsp;|&nbsp; ".join(parts) + "</span>"


def _render_step_row(step: DadaiaWorkflowStepDTO) -> str:
    gate = (
        ' <span class="dadaia-wf-step-gate" title="gate step">&#9673; gate</span>'
        if step.is_gate
        else ""
    )
    return (
        '<li class="dadaia-wf-step">'
        f'<span class="dadaia-wf-step-order">{step.order}.</span> '
        f'<span class="dadaia-wf-step-label">{html.escape(step.label)}</span>{gate}'
        f'<span class="dadaia-wf-step-role"> — {html.escape(step.role)}</span>'
        f'<p class="dadaia-wf-step-purpose">{html.escape(step.purpose)}</p>'
        f"{_render_step_harness(step)}"
        "</li>"
    )


def _render_step_summary(steps: list[DadaiaWorkflowStepDTO]) -> str:
    """Compact one-line step chain for the collapsed card face.

    Renders the ordered step labels joined by arrows; CSS truncates with an ellipsis
    so the summary never wraps or overflows the card. The full per-step detail lives
    in the expandable body.
    """
    if not steps:
        return ""
    chain = " → ".join(html.escape(s.label) for s in steps)
    return f'<p class="dadaia-wf-step-chain" title="{chain}">{chain}</p>'


def _render_dadaia_workflow_card(wf: DadaiaWorkflowDTO) -> str:
    """Render one dadaia-workflow as a big, expandable diagram card (AC-1 / T-45-03).

    The card is a native ``<details>`` disclosure — server-rendered and CSP-clean, no
    client script, not a ``<dialog>``. The collapsed ``<summary>`` face carries the
    header (display-name, availability badge, step count), the purpose, the enhanced
    server-rendered SVG fluxogram (nodes carry role + gate marker + harness/model), and
    a compact step-chain summary. Expanding reveals the full per-step detail
    (order, label, gate flag, role, purpose, harness/model). The dead client-Mermaid
    block and its producer chain were removed (arch finding #5) — the enhanced SVG is
    the single diagram source on both the card and the detail.
    """
    steps_html = (
        '<ol class="dadaia-wf-steps">' + "".join(_render_step_row(s) for s in wf.steps) + "</ol>"
        if wf.steps
        else '<p class="dadaia-wf-empty-steps">No steps yet — this workflow is scaffolded only.</p>'
    )
    # The server-rendered SVG DAG is always available even without JS.
    diagram_block = (
        f'<div class="dadaia-wf-diagram-svg">{wf.diagram_svg}</div>' if wf.diagram_svg else ""
    )
    aria_unavail = ' aria-disabled="true"' if wf.availability == AVAILABILITY_DEFERRED else ""
    expand_hint = (
        '<span class="dadaia-wf-expand-hint" aria-hidden="true">Show step detail</span>'
        if wf.steps
        else ""
    )
    return (
        f'<details class="dadaia-wf-card" data-workflow="{html.escape(wf.name)}" '
        f'data-availability="{html.escape(wf.availability)}"{aria_unavail}>'
        '<summary class="dadaia-wf-card-summary">'
        '<header class="dadaia-wf-card-header">'
        f'<h4 class="dadaia-wf-card-title">{html.escape(wf.display_name)}</h4>'
        f"{_availability_badge(wf.availability)}"
        f'<span class="dadaia-wf-step-count">{wf.step_count} steps</span>'
        "</header>"
        f'<p class="dadaia-wf-purpose">{html.escape(wf.purpose)}</p>'
        f'<div class="dadaia-wf-diagram">{diagram_block}</div>'
        f"{_render_step_summary(wf.steps)}"
        f"{expand_hint}"
        "</summary>"
        f'<div class="dadaia-wf-detail">{steps_html}</div>'
        "</details>"
    )


def render_dadaia_workflows_section() -> str:
    """Server-rendered catalog of every dadaia-workflow (WS-8 / ADR-E).

    Renders each workflow as a big, expandable ``<details>`` card: its purpose,
    availability badge (deferred workflows are visibly marked unavailable), the
    enhanced server-rendered SVG fluxogram (nodes carry role + gate marker +
    harness/model), a compact step-chain summary on the collapsed face, and the full
    ordered step sequence with per-step role + harness/model options in the expanded
    body. Fully server-rendered — no API round-trip, no client script — so the
    operator sees the complete catalog on first paint. The server-rendered SVG is the
    single diagram source; the dead client-Mermaid layer was removed in v0.1.45.
    """
    workflows = list_dadaia_workflows()
    cards = "".join(_render_dadaia_workflow_card(wf) for wf in workflows)
    return (
        '<div class="ops-subsection" id="ops-subsection-dadaia-workflows">\n'
        '  <div class="ops-subsection-header">\n'
        '    <h3 class="ops-subsection-title">dadaia-workflows</h3>\n'
        '    <p class="section-meta">Every dadaia-workflow: purpose, step sequence, '
        "per-step harness/model, diagram, and availability.</p>\n"
        "  </div>\n"
        f'  <div class="dadaia-wf-catalog">{cards}</div>\n'
        "</div>"
    )


def render_workflows_first_class_section() -> str:
    """The first-class Workflows panel area (D-5, T-28-C-03; IA flip v0.1.45 / T-45-08).

    Promotes Workflows from the Ops subtab to a top-level nav area. **Cards lead, policy
    is secondary** (operator directive, v0.1.45): the tab opens on the prominent,
    default-visible **dadaia-workflow diagram catalog** — one big card per workflow with a
    server-rendered SVG fluxogram (nodes carry role + gate marker + harness/model) and
    click-to-expand step detail — because that is what the operator scans first. Below it,
    the **model-governance editor** is demoted into a collapsed ``Model policy`` disclosure
    (secondary, opt-in): a toolbar (validate / save) + banner + an empty ``#wfp-root`` that
    ``workflow-policy.js`` populates with one step matrix per governed workflow (Step | Role
    | Harness | Model profile | Concrete model | Fragments | Gate | default-vs-effective
    diff), the segmented codex/pi harness control, the harness-filtered profile dropdown,
    reset-to-default, validate-before-save, save→PUT, and the per-workflow run-snapshot
    evidence view (reads the persisted snapshot — never re-resolves).

    Both surfaces stay fully functional: ``#wfp-root`` is populated on load regardless of
    the disclosure's open state, so demoting the matrix into a collapsed ``<details>``
    changes only its prominence, not its behavior. The server-rendered SVG DAG is the
    canonical, offline diagram — browser-Mermaid is never an execution dependency.

    Agents and Kanban remain available in the Ops tab during the transition (D-5).
    """
    return (
        '<section id="section-workflows" class="section panel-section" role="tabpanel" '
        'tabindex="0" aria-labelledby="tab-workflows">\n'
        '  <div class="section-header">\n'
        "    <h2>Workflows</h2>\n"
        "    <p>Every dadaia-workflow as a diagram card — purpose, step fluxogram, per-step "
        "harness/model, and availability. Expand a card for the full step detail; open "
        "<strong>Model policy</strong> below to govern per-step model selection.</p>\n"
        "  </div>\n"
        # Cards LEAD — prominent, default-visible catalog (operator directive, T-45-08).
        f"  {render_dadaia_workflows_section()}\n"
        # Model policy is SECONDARY — demoted into a collapsed disclosure below the cards.
        '  <details class="wfp-policy">\n'
        '    <summary class="wfp-policy-summary">\n'
        '      <span class="wfp-policy-title">Model policy</span>\n'
        '      <span class="wfp-policy-hint">Govern the per-step harness &amp; model for '
        "every workflow, and inspect what each run executed.</span>\n"
        "    </summary>\n"
        '    <div class="wfp-policy-body">\n'
        '      <div class="wfp-toolbar">\n'
        '        <button type="button" class="wfp-validate-btn" id="wfp-validate-btn">'
        "Validate</button>\n"
        '        <button type="button" class="wfp-save-btn" id="wfp-save-btn">Save policy'
        "</button>\n"
        "      </div>\n"
        '      <div class="wfp-banner" id="wfp-banner" role="status" aria-live="polite" '
        "hidden></div>\n"
        '      <div id="wfp-root" class="wfp-catalog" aria-live="polite">'
        '<p class="wfp-loading">Loading workflow model policy…</p></div>\n'
        "    </div>\n"
        "  </details>\n"
        "</section>"
    )


def render_workflows_section() -> str:
    """Return the static HTML scaffold for the Workflows tab card grid (legacy).

    Kept for backward compatibility. Returns the sub-section HTML used inside
    the consolidated Ops tab.
    """
    return render_workflows_subsection()


def render_workflows_subsection() -> str:
    """Return the compact sub-section HTML for Workflows inside the Ops tab.

    workflows.js fetches /api/workflows on Ops tab activation and populates
    #workflows-grid with one .workflow-card per workflow.
    """
    empty_msg = html.escape("Nenhum workflow descoberto.")
    return (
        '<div class="ops-subsection" id="ops-subsection-workflows">\n'
        '  <div class="ops-subsection-header">\n'
        '    <h3 class="ops-subsection-title">Workflows</h3>\n'
        '    <p class="section-meta" id="workflows-meta" aria-live="polite"></p>\n'
        '    <div class="runtime-switcher" role="radiogroup" aria-label="Active runtime" style="margin-left:auto;">\n'
        '      <button type="button" class="runtime-btn runtime-btn--claude"\n'
        '        id="workflows-runtime-btn-claude" role="radio" aria-checked="true"\n'
        '        data-runtime-value="claude" aria-label="Claude runtime">\n'
        '        <span class="runtime-btn-icon" aria-hidden="true">&#9672;</span>\n'
        '        <span class="runtime-btn-label">Claude</span>\n'
        "      </button>\n"
        '      <button type="button" class="runtime-btn runtime-btn--codex"\n'
        '        id="workflows-runtime-btn-codex" role="radio" aria-checked="false"\n'
        '        data-runtime-value="codex" aria-label="Codex runtime">\n'
        '        <span class="runtime-btn-icon" aria-hidden="true">&#9667;</span>\n'
        '        <span class="runtime-btn-label">Codex</span>\n'
        "      </button>\n"
        '      <button type="button" class="runtime-btn runtime-btn--pi"\n'
        '        id="workflows-runtime-btn-pi" role="radio" aria-checked="false"\n'
        '        data-runtime-value="pi" aria-label="PI runtime">\n'
        '        <span class="runtime-btn-icon" aria-hidden="true">&#9678;</span>\n'
        '        <span class="runtime-btn-label">PI</span>\n'
        "      </button>\n"
        "    </div>\n"
        "  </div>\n"
        '  <p id="workflows-empty" class="empty-state" hidden>' + empty_msg + "</p>\n"
        # Card grid container — workflows.js renders .workflow-card elements inside.
        # aria-busy="false" is the default; workflows.js sets it to "true" during fetch.
        '  <div id="workflows-grid" class="workflows-card-grid workflows-grid--compact" '
        'aria-busy="false"></div>\n'
        # Legacy pane elements retained as hidden stubs.
        '  <nav class="workflows-list" aria-label="Workflow list" '
        'id="workflows-list" hidden></nav>\n'
        '  <div class="workflows-detail" id="workflows-detail" '
        'role="region" aria-label="Workflow detail" aria-live="polite" hidden></div>\n'
        "</div>"
    )
