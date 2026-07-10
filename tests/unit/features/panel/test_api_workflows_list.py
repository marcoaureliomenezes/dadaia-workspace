"""Unit tests for GET /api/workflows.

Golden pins list bytes. Two survivors:
  1. Envelope + items match the service + empty-list 200 (never 503).
  2. Leanliness: no diagram_svg/dag_svg/stages/inputs on LIST items (D1).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dadaia_workspace.features.panel.views.api_workflows import render_api_workflows_list
from dadaia_workspace.features.workflows.service import WorkflowSummaryDTO

pytestmark = pytest.mark.unit


class _FakeService:
    """Minimal PanelService fake that allows injecting workflow summaries."""

    def __init__(
        self, summaries: list[WorkflowSummaryDTO], workflows_dir: str = ".dadaia/agentic/workflows/"
    ) -> None:
        self._summaries = summaries
        self._workflows_dir = workflows_dir
        self._workspace_root = Path("/fake/workspace")

    def list_workflow_summaries(self) -> list[WorkflowSummaryDTO]:
        return self._summaries


def _make_summary(
    name: str = "my-wf",
    stage_count: int = 3,
    has_parallel: bool = False,
    has_gates: bool = False,
) -> WorkflowSummaryDTO:
    return WorkflowSummaryDTO(
        name=name,
        display_name=name,
        description=f"Description of {name}",
        version="0.1.0",
        schema_version="1",
        stage_count=stage_count,
        agent_ids=["software-engineer"],
        has_parallel=has_parallel,
        has_gates=has_gates,
        source_path=f".dadaia/agentic/workflows/{name}.workflow.md",
    )


# ---------------------------------------------------------------------------
# 1. Envelope + items match the service + empty-list 200
# ---------------------------------------------------------------------------


def test_envelope_and_items_match_service_including_empty() -> None:
    summaries = [
        _make_summary("tdd-cycle", stage_count=5, has_parallel=True, has_gates=True),
        _make_summary("wf-2"),
    ]
    service = _FakeService(summaries)
    view = render_api_workflows_list(service)  # type: ignore[arg-type]

    status, content_type, body = view()

    assert status == 200
    assert content_type == "application/json; charset=utf-8"
    data = json.loads(body)
    assert isinstance(data, dict)
    assert "generated_at" in data and isinstance(data["generated_at"], str) and data["generated_at"]
    assert "source_hint" in data
    assert len(data["workflows"]) == 2

    item = data["workflows"][0]
    assert item["name"] == "tdd-cycle"
    assert item["display_name"] == "tdd-cycle"
    assert isinstance(item["description"], str)
    assert item["version"] == "0.1.0"
    assert item["schema_version"] == "1"
    assert isinstance(item["stage_count"], int)
    assert item["stage_count"] == 5
    assert isinstance(item["agent_ids"], list)
    assert item["has_parallel"] is True
    assert item["has_gates"] is True
    assert isinstance(item["source_path"], str)

    # Empty source dir -> 200 with workflows: [] (not 503, never a telemetry-style failure).
    empty_service = _FakeService([])
    empty_view = render_api_workflows_list(empty_service)  # type: ignore[arg-type]
    empty_status, _, empty_body = empty_view()
    assert empty_status == 200
    assert json.loads(empty_body)["workflows"] == []


# ---------------------------------------------------------------------------
# 2. Leanliness — D1 synthesis decision
# ---------------------------------------------------------------------------


def test_list_items_are_lean_no_detail_only_fields() -> None:
    """LIST items must not carry diagram_svg/dag_svg/stages/inputs (detail-only)."""
    service = _FakeService([_make_summary()])
    view = render_api_workflows_list(service)  # type: ignore[arg-type]
    _, _, body = view()
    item = json.loads(body)["workflows"][0]

    assert "diagram_svg" not in item, "LIST /api/workflows must not include diagram_svg"
    assert "dag_svg" not in item, "legacy alias must not leak either"
    assert "stages" not in item, "LIST /api/workflows must not include stages"
    assert "inputs" not in item, "inputs is a detail-only field"
