"""Integration tests for the dadaia-workflow panel catalog (WS-8 / ADR-E, T-24-12).

Covers the dadaia-workflow catalog surface that fully self-describes every
Python-owned dadaia-workflow (release_definition, implementation, deferred) for the
panel: purpose, per-step harness/model options, availability, and a server-rendered
SVG DAG fluxogram.

Merged per plan-integration.md (13 -> 2): (1) list availability (release_definition,
backlog_definition, wave-E available; step counts; purpose); (2) detail fully-described
(9 §6.1 steps, worker/gate harness+model options, SVG node-meta, no diagram_mermaid) +
400/404. The top-level-key/field-presence fns and the HTML section class-name grep
(brittle CSS wording — the Playwright e2e owns the rendered panel) are dropped.

The catalog is sourced from the real workflow definitions, so no on-disk fixtures or
mocks are needed — the endpoint closures are exercised directly.
"""

from __future__ import annotations

import json
from typing import Any

from dadaia_workspace.features.panel.views.api_workflows import (
    render_api_dadaia_workflow_detail,
    render_api_dadaia_workflows_list,
)
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


def test_list_availability_step_counts_and_purpose() -> None:
    status, data = _list()
    assert status == 200
    for key in ("generated_at", "source_hint", "workflows"):
        assert key in data

    by_name = {w["name"]: w for w in data["workflows"]}
    assert "release_definition" in by_name
    assert "backlog_definition" in by_name
    assert by_name["release_definition"]["availability"] == AVAILABILITY_AVAILABLE
    # backlog_definition shipped its real workflow body in v0.1.26 R2 — now available.
    assert by_name["backlog_definition"]["availability"] == AVAILABILITY_AVAILABLE

    # T-30-E-04: audit/research/bug_report ship real bodies — listed as available.
    for name in ("audit", "research", "bug_report"):
        assert by_name[name]["availability"] == AVAILABILITY_AVAILABLE
        assert by_name[name]["step_count"] == 4

    for item in data["workflows"]:
        assert isinstance(item["purpose"], str) and item["purpose"]
        assert isinstance(item["step_count"], int)


def test_detail_fully_described_with_400_and_404() -> None:
    """Detail carries diagram_svg + full step description; 400/404 on bad names.

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

    # Every §6.1 step is present with role + per-step harness/model + purpose, in order,
    # terminating in the Python commit gate.
    labels = [s["label"] for s in data["steps"]]
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

    # A worker step lists pi + codex harnesses, each with its discrete model catalog.
    worker = next(s for s in data["steps"] if s["label"] == "spec_create")
    assert worker["harness_options"] == ["pi", "codex"]
    assert worker["model_options"]["pi"] == [
        "gpt-5.5:high",
        "gpt-5.5:low",
        "gpt-5.3-codex:medium",
        "moonshotai/kimi-k2.5:high",
    ]
    assert worker["model_options"]["codex"] == ["gpt-5.5:high", "gpt-5.5:medium"]

    # The terminal Python commit gate runs no worker -> no harness/model options.
    gate = next(s for s in data["steps"] if s["label"] == "definition_commit_gate")
    assert gate["is_gate"] is True
    assert gate["harness_options"] == []
    assert gate["model_options"] == {}

    # The detail's server-SVG fluxogram is enriched with per-node harness/model.
    svg = data["diagram_svg"]
    assert svg.startswith("<svg")
    assert "node-meta" in svg
    assert "codex" in svg or "pi" in svg

    # T-30-E-04: the audit detail is a real available body with its fragment+gate steps.
    status, data = _detail("audit")
    assert status == 200
    assert data["availability"] == AVAILABILITY_AVAILABLE
    labels = [s["label"] for s in data["steps"]]
    assert labels == ["audit_scope", "drift_scan", "triage", "audit_disposition_gate"]

    status, data = _detail("bad..name")
    assert status == 400
    assert data["error"] == "invalid_workflow_name"

    status, data = _detail("no-such-workflow")
    assert status == 404
    assert data["error"] == "not_found"
