"""Workflows tab view — the first-class Workflows panel section (v0.1.45 redesign).

The Workflows tab is a grid of big diagram cards, one per dadaia-workflow. Each card is
a native ``<details>`` disclosure (server-rendered, CSP-clean — no ``<dialog>``, no client
Mermaid). The collapsed face is the diagram card the operator scans first; **expanding it
reveals the human-readable detail** (v0.1.45 operator directive):

  1. a **legible server-rendered SVG fluxogram** as the visual centrepiece (each node
     carries the step label, role, gate marker, and the SELECTED model — the enlarged
     ``node_meta`` layout from ``dag.py``), and
  2. one **formatted step card per step** — a clean header (order + label + role + gate
     badge), a readable purpose body, and an **inline per-step model picker** for every
     model-driven step. The picker is a real ``<select>`` wired by ``workflow-policy.js`` to
     the governed model-policy control plane (profile registry + overlay + resolver), so
     the operator changes a step's model right where the workflow is shown.

The old separate collapsed "Model policy" matrix was folded away: the per-step pickers now
live inside each card's expand. A single visible **Validate / Save** toolbar in the section
header commits the pending overrides through ``PUT /api/workflow-model-policy``.

Security (OWASP A03): every operator-facing string interpolated into HTML is passed
through ``html.escape()``; ``wf.diagram_svg`` is server-generated (``dag.py``, all text
escaped) — no user-controlled markup is injected.
"""

from __future__ import annotations

import html

from dadaia_workspace.features.lifecycle import model_profiles
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


def _default_model_label(step: DadaiaWorkflowStepDTO) -> str:
    """The step's governed default ``harness · model`` label, resolved server-side.

    Shown as the picker's initial value so the operator sees the current model even
    before ``workflow-policy.js`` hydrates the live overlay. Derived ONLY from the step's
    ``default_profiles`` via the built-in registry — the same single source the resolver
    reads (no second table). A Python-owned gate step (no worker) has no model.
    """
    harness = step.default_harness
    if harness is None:
        return ""
    profile_id = step.default_profiles.get(harness)
    if profile_id is None:  # pragma: no cover - guarded by catalog import assert
        return html.escape(harness)
    model_id = model_profiles.resolve(profile_id).model_id
    return f"{html.escape(harness)} &middot; {html.escape(model_id)}"


def _render_step_card(workflow_name: str, step: DadaiaWorkflowStepDTO) -> str:
    """Render one workflow step as a human-formatted card (v0.1.45).

    Clean typographic hierarchy — a header row (step order + label + role + gate/worker
    badge), a readable purpose body, and (for a model-driven step) a labelled **inline
    model picker** mount. ``workflow-policy.js`` finds the mount by
    ``data-wfp-workflow``/``data-wfp-step`` and injects the real harness segment + profile
    ``<select>`` bound to the governed control plane. A Python-owned gate step carries no
    worker, so it shows a gate note instead of a picker (no monospace comma-dumps).
    """
    order = step.order
    label = html.escape(step.label)
    role = html.escape(step.role)
    purpose = html.escape(step.purpose)
    is_worker = step.default_harness is not None

    if step.is_gate:
        badge = '<span class="dadaia-wf-step-badge dadaia-wf-step-badge--gate">&#9673; gate</span>'
    else:
        badge = '<span class="dadaia-wf-step-badge dadaia-wf-step-badge--worker">worker</span>'

    if is_worker:
        default_label = _default_model_label(step)
        control = (
            '<div class="dadaia-wf-step-model">'
            '<span class="dadaia-wf-step-model-label">Model</span>'
            '<div class="wf-step-picker" '
            f'data-wfp-workflow="{html.escape(workflow_name)}" '
            f'data-wfp-step="{html.escape(step.label)}">'
            f'<span class="wf-step-picker-default">{default_label}</span>'
            "</div>"
            "</div>"
        )
    else:
        control = (
            '<p class="dadaia-wf-step-gatenote">Python-owned gate &mdash; no model worker.</p>'
        )

    gate_cls = " dadaia-wf-step--gate" if step.is_gate else ""
    return (
        f'<li class="dadaia-wf-step{gate_cls}" data-step-order="{order}">'
        '<header class="dadaia-wf-step-head">'
        f'<span class="dadaia-wf-step-order">{order}</span>'
        f'<span class="dadaia-wf-step-label">{label}</span>'
        f'<span class="dadaia-wf-step-role">{role}</span>'
        f"{badge}"
        "</header>"
        f'<p class="dadaia-wf-step-purpose">{purpose}</p>'
        f"{control}"
        "</li>"
    )


def _render_step_summary(steps: list[DadaiaWorkflowStepDTO]) -> str:
    """Compact one-line step chain for the collapsed card face.

    Renders the ordered step labels joined by arrows; CSS truncates with an ellipsis
    so the summary never wraps or overflows the card. The full per-step detail + pickers
    live in the expandable body.
    """
    if not steps:
        return ""
    chain = " → ".join(html.escape(s.label) for s in steps)
    return f'<p class="dadaia-wf-step-chain" title="{chain}">{chain}</p>'


def _render_dadaia_workflow_card(wf: DadaiaWorkflowDTO) -> str:
    """Render one dadaia-workflow as a big, expandable diagram card (v0.1.45 redesign).

    The card is a native ``<details>`` disclosure — server-rendered, CSP-clean, no client
    script and not a ``<dialog>``. The collapsed ``<summary>`` face carries the header
    (display-name, availability badge, step count), the purpose, and a compact step-chain
    summary — the diagram card the operator scans first. Expanding reveals the **legible
    server-rendered SVG fluxogram** as the centrepiece, followed by one formatted step card
    per step (header + purpose + inline model picker). The enhanced SVG is the single
    diagram source (the dead client-Mermaid layer was removed in v0.1.45).
    """
    steps_html = (
        '<ol class="dadaia-wf-steps">'
        + "".join(_render_step_card(wf.name, s) for s in wf.steps)
        + "</ol>"
        if wf.steps
        else '<p class="dadaia-wf-empty-steps">No steps yet — this workflow is scaffolded only.</p>'
    )
    # The legible server-rendered SVG fluxogram is the centrepiece of the expanded card.
    flux_block = (
        '<figure class="dadaia-wf-flux">'
        '<figcaption class="dadaia-wf-flux-cap">Flow — step, role, gate &amp; selected model</figcaption>'
        f'<div class="dadaia-wf-diagram-svg">{wf.diagram_svg}</div>'
        "</figure>"
        if wf.diagram_svg
        else ""
    )
    aria_unavail = ' aria-disabled="true"' if wf.availability == AVAILABILITY_DEFERRED else ""
    expand_hint = (
        '<span class="dadaia-wf-expand-hint" aria-hidden="true">Show fluxogram &amp; model pickers</span>'
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
        f"{_render_step_summary(wf.steps)}"
        f"{expand_hint}"
        "</summary>"
        f'<div class="dadaia-wf-detail">{flux_block}{steps_html}</div>'
        "</details>"
    )


def render_dadaia_workflows_section() -> str:
    """Server-rendered catalog of every dadaia-workflow (WS-8 / ADR-E; v0.1.45 redesign).

    Renders each workflow as a big, expandable ``<details>`` card whose expand carries the
    legible fluxogram + formatted per-step detail + inline model pickers. Fully
    server-rendered scaffold (no API round-trip for the layout); ``workflow-policy.js``
    hydrates the per-step pickers from the governed control plane after load.
    """
    workflows = list_dadaia_workflows()
    cards = "".join(_render_dadaia_workflow_card(wf) for wf in workflows)
    return (
        '<div class="ops-subsection" id="ops-subsection-dadaia-workflows">\n'
        '  <div class="ops-subsection-header">\n'
        '    <h3 class="ops-subsection-title">dadaia-workflows</h3>\n'
        '    <p class="section-meta">Every dadaia-workflow: purpose, step sequence, '
        "fluxogram, and an inline per-step model picker. Expand a card to change models.</p>\n"
        "  </div>\n"
        f'  <div class="dadaia-wf-catalog">{cards}</div>\n'
        "</div>"
    )


def render_workflows_first_class_section() -> str:
    """The first-class Workflows panel area (v0.1.45 redesign — merged model governance).

    The tab opens on the prominent, default-visible **dadaia-workflow diagram catalog** —
    one big card per workflow. Expanding a card shows a legible fluxogram plus one
    formatted card per step, each model-driven step carrying an **inline model picker**
    wired to the governed control plane. The old separate collapsed "Model policy" matrix
    was folded away — the pickers now live in the expand — leaving a single visible
    **Validate / Save** toolbar that commits pending overrides through
    ``PUT /api/workflow-model-policy`` (validate-before-save). ``#wfp-banner`` reports the
    validate/save result. The server-rendered SVG DAG is the canonical, offline diagram —
    browser-Mermaid is never an execution dependency.
    """
    return (
        '<section id="section-workflows" class="section panel-section" role="tabpanel" '
        'tabindex="0" aria-labelledby="tab-workflows">\n'
        '  <div class="section-header">\n'
        "    <h2>Workflows</h2>\n"
        "    <p>Every dadaia-workflow as a diagram card. Expand a card for the legible "
        "fluxogram and a formatted, per-step detail with an <strong>inline model "
        "picker</strong> — change a step's model right here, then Validate &amp; Save.</p>\n"
        '    <div class="wfp-toolbar" role="group" aria-label="Model policy actions">\n'
        '      <button type="button" class="wfp-validate-btn" id="wfp-validate-btn">'
        "Validate</button>\n"
        '      <button type="button" class="wfp-save-btn" id="wfp-save-btn">Save model policy'
        "</button>\n"
        '      <div class="wfp-banner" id="wfp-banner" role="status" aria-live="polite" '
        "hidden></div>\n"
        "    </div>\n"
        "  </div>\n"
        f"  {render_dadaia_workflows_section()}\n"
        "</section>"
    )
