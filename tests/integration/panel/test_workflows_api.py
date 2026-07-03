"""Integration tests for the dadaia-workflow panel catalog (WS-8 / ADR-E, T-24-12).

These cover the *new* dadaia-workflow catalog surface that fully self-describes every
Python-owned dadaia-workflow (release_definition, implementation, deferred) for the
panel: purpose, per-step harness/model options, availability, and a server-rendered
SVG DAG fluxogram. They assert the detail shape carries ``diagram_svg`` PLUS the
descriptive fields — and that:

- a deferred workflow is shown unavailable;
- release-definition is fully described (every §6.1 step + per-step harness_options +
  model_options + purpose);
- the enhanced server-SVG fluxogram carries per-node harness/model (v0.1.45); the dead
  client-Mermaid layer was removed.

The catalog is sourced from the real workflow definitions, so no on-disk fixtures or
mocks are needed — the endpoint closures are exercised directly (the dispatch envelope
is already covered by test_api_workflows.py for the legacy endpoints).
"""

from __future__ import annotations

import json
from typing import Any

from dadaia_workspace.features.panel.views.api_workflows import (
    render_api_dadaia_workflow_detail,
    render_api_dadaia_workflows_list,
)
from dadaia_workspace.features.panel.views.workflows import render_dadaia_workflows_section
from dadaia_workspace.features.workflows.dadaia_catalog import (
    AVAILABILITY_AVAILABLE,
)


class _Service:
    """Thin shim exposing the catalog accessors the views call (real catalog data)."""

    def list_dadaia_workflows(self) -> Any:
        from dadaia_workspace.features.workflows.dadaia_catalog import list_dadaia_workflows

        return list_dadaia_workflows()

    def get_dadaia_workflow(self, name: str) -> Any:
        from dadaia_workspace.features.workflows.dadaia_catalog import get_dadaia_workflow

        return get_dadaia_workflow(name)


def _detail(name: str) -> tuple[int, dict[str, Any]]:
    view = render_api_dadaia_workflow_detail(_Service())
    status, _ctype, body = view(workflow_name=name)
    return status, json.loads(body) if body else {}


def _list() -> tuple[int, dict[str, Any]]:
    view = render_api_dadaia_workflows_list(_Service())
    status, _ctype, body = view()
    return status, json.loads(body)


# ---------------------------------------------------------------------------
# List endpoint
# ---------------------------------------------------------------------------


class TestDadaiaWorkflowsList:
    def test_list_top_level_keys(self) -> None:
        status, data = _list()
        assert status == 200
        for key in ("generated_at", "source_hint", "workflows"):
            assert key in data

    def test_list_includes_release_definition_and_deferred(self) -> None:
        _status, data = _list()
        by_name = {w["name"]: w for w in data["workflows"]}
        assert "release_definition" in by_name
        assert "backlog_definition" in by_name
        assert by_name["release_definition"]["availability"] == AVAILABILITY_AVAILABLE
        # backlog_definition shipped its real workflow body in v0.1.26 R2 — now available.
        assert by_name["backlog_definition"]["availability"] == AVAILABILITY_AVAILABLE

    def test_list_marks_wave_e_bodies_available(self) -> None:
        """T-30-E-04: audit/research/bug_report ship real bodies — listed as available."""
        _status, data = _list()
        by_name = {w["name"]: w for w in data["workflows"]}
        for name in ("audit", "research", "bug_report"):
            assert by_name[name]["availability"] == AVAILABILITY_AVAILABLE
            assert by_name[name]["step_count"] == 4

    def test_list_items_carry_purpose_and_step_count(self) -> None:
        _status, data = _list()
        for item in data["workflows"]:
            assert isinstance(item["purpose"], str) and item["purpose"]
            assert isinstance(item["step_count"], int)


# ---------------------------------------------------------------------------
# Detail endpoint — additive shape + full description
# ---------------------------------------------------------------------------


class TestDadaiaWorkflowDetailAdditive:
    def test_detail_additive_shape_keeps_diagram_svg(self) -> None:
        """Detail carries ``diagram_svg`` PLUS the descriptive fields.

        v0.1.45 removed the dead client-Mermaid layer — the server-rendered SVG is the
        single diagram source, so ``diagram_mermaid`` is no longer emitted.
        """
        status, data = _detail("release_definition")
        assert status == 200
        assert "diagram_svg" in data
        assert data["diagram_svg"].startswith("<svg")
        for key in ("purpose", "availability", "steps"):
            assert key in data, f"missing key: {key}"
        assert "diagram_mermaid" not in data

    def test_release_definition_fully_described(self) -> None:
        """Every §6.1 step is present with role + per-step harness/model + purpose."""
        _status, data = _detail("release_definition")
        labels = [s["label"] for s in data["steps"]]
        # All 9 §6.1 steps, in order, terminating in the Python commit gate.
        assert labels == [
            "release_scope",
            "spec_create",
            "spec_arch_review",
            "spec_qa_review",
            "plan_create",
            "plan_review",
            "tasks_create",
            "tasks_implementability_review",
            "definition_commit_gate",
        ]
        for step in data["steps"]:
            assert step["role"], f"step {step['label']} missing role"
            assert step["purpose"], f"step {step['label']} missing purpose"
            assert "harness_options" in step
            assert "model_options" in step

    def test_worker_steps_offer_pi_and_codex_discrete_models(self) -> None:
        """A worker step lists pi + codex harnesses, each with its discrete model catalog."""
        _status, data = _detail("release_definition")
        worker = next(s for s in data["steps"] if s["label"] == "spec_create")
        assert worker["harness_options"] == ["pi", "codex"]
        assert worker["model_options"]["pi"] == [
            "gpt-5.5:high",
            "gpt-5.5:low",
            "gpt-5.3-codex:medium",
            "kimi-2.7:high",
        ]
        assert worker["model_options"]["codex"] == ["gpt-5.5:high", "gpt-5.5:medium"]

    def test_python_gate_step_has_no_harness_or_model(self) -> None:
        """The terminal Python commit gate runs no worker → no harness/model options."""
        _status, data = _detail("release_definition")
        gate = next(s for s in data["steps"] if s["label"] == "definition_commit_gate")
        assert gate["is_gate"] is True
        assert gate["harness_options"] == []
        assert gate["model_options"] == {}

    def test_svg_fluxogram_carries_per_node_harness_model(self) -> None:
        """The detail's server-SVG fluxogram is enriched with per-node harness/model."""
        _status, data = _detail("release_definition")
        svg = data["diagram_svg"]
        assert svg.startswith("<svg")
        # The enrichment adds the node-meta text class (only present when node_meta passed).
        assert "node-meta" in svg
        # A governed harness label appears in the fluxogram nodes.
        assert "codex" in svg or "pi" in svg
        # The dead client-Mermaid field is gone.
        assert "diagram_mermaid" not in data

    def test_wave_e_body_detail_available_with_real_steps(self) -> None:
        """T-30-E-04: the audit detail is a real available body with its fragment+gate steps."""
        status, data = _detail("audit")
        assert status == 200
        assert data["availability"] == AVAILABILITY_AVAILABLE
        labels = [s["label"] for s in data["steps"]]
        assert labels == ["audit_scope", "drift_scan", "triage", "audit_disposition_gate"]

    def test_invalid_name_400(self) -> None:
        status, data = _detail("bad..name")
        assert status == 400
        assert data["error"] == "invalid_workflow_name"

    def test_unknown_name_404(self) -> None:
        status, data = _detail("no-such-workflow")
        assert status == 404
        assert data["error"] == "not_found"


# ---------------------------------------------------------------------------
# Server-rendered catalog view
# ---------------------------------------------------------------------------


class TestDadaiaWorkflowsSectionView:
    def test_section_renders_expandable_cards_and_availability_badges(self) -> None:
        html = render_dadaia_workflows_section()
        # v0.1.45: cards are native <details> disclosures — no client-Mermaid block.
        assert 'pre class="mermaid"' not in html
        assert '<details class="dadaia-wf-card"' in html
        assert '<summary class="dadaia-wf-card-summary">' in html
        # Compact step-chain summary on the collapsed face.
        assert "dadaia-wf-step-chain" in html
        # Each workflow carries an availability badge. As of v0.1.30 Wave E no workflow is
        # deferred (the --unavailable modifier only renders for deferred), but the
        # available + partial badges are present.
        assert "dadaia-wf-badge--available" in html
        assert "dadaia-wf-badge--partial" in html
        assert "dadaia-wf-badge--unavailable" not in html
        # Server-rendered SVG DAG is present (offline-safe diagram).
        assert "dadaia-wf-diagram-svg" in html
        # Per-step model surfaced for the operator: each model-driven step renders an
        # inline picker whose default label is the governed "harness &middot; model_id"
        # (v0.1.45 redesign — the label shows the resolved model id, not model:effort).
        assert "wf-step-picker-default" in html
        assert 'class="wf-step-picker"' in html
        assert "&middot;" in html
        assert "gpt-5.5" in html
