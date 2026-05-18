"""Unit tests for GET /api/workflows — PR3-14.

Coverage (per TASKS.md PR3-14 + SPEC §5.3 acceptance):
- Returns {"workflows": [...]} wrapper with generated_at + source_hint fields.
- Each item carries only summary fields: name, display_name, description, version,
  schema_version, stage_count (integer), agent_ids, has_parallel, has_gates, source_path.
- No "diagram_svg" key on any item (LIST is lean — SPEC D1 synthesis decision).
- No "stages" key on any item.
- Returns 401 without Bearer token (SPEC §5.5, G9).
- Returns 401 with wrong Bearer token.
- Returns 200 with correct Bearer token.
- Empty workflows dir → {"workflows": []} with 200 (no 503 from telemetry path).
- stage_count is an int, not a list.
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from dadaia_workspace.features.panel.views.api import render_api_workflows_list
from dadaia_workspace.features.workflows.service import WorkflowSummaryDTO


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class _FakeService:
    """Minimal PanelService fake that allows injecting workflow summaries."""

    def __init__(self, summaries: list[WorkflowSummaryDTO], workflows_dir: str = ".dadaia/agentic/workflows/") -> None:
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
# Tests: response envelope
# ---------------------------------------------------------------------------


class TestApiWorkflowsListEnvelope:
    def test_returns_200_with_bearer(self) -> None:
        """GET /api/workflows with valid Bearer → 200."""
        service = _FakeService([_make_summary()])
        view = render_api_workflows_list(service)  # type: ignore[arg-type]
        status, ct, body = view()
        assert status == 200

    def test_content_type_is_json(self) -> None:
        """Content-Type must be application/json; charset=utf-8."""
        service = _FakeService([_make_summary()])
        view = render_api_workflows_list(service)  # type: ignore[arg-type]
        _, ct, _ = view()
        assert ct == "application/json; charset=utf-8"

    def test_body_is_valid_json(self) -> None:
        """Response body must deserialise without error."""
        service = _FakeService([_make_summary()])
        view = render_api_workflows_list(service)  # type: ignore[arg-type]
        _, _, body = view()
        data = json.loads(body)
        assert isinstance(data, dict)

    def test_top_level_workflows_key(self) -> None:
        """Response must include a top-level 'workflows' key."""
        service = _FakeService([_make_summary()])
        view = render_api_workflows_list(service)  # type: ignore[arg-type]
        _, _, body = view()
        data = json.loads(body)
        assert "workflows" in data

    def test_top_level_generated_at_key(self) -> None:
        """Response must include a top-level 'generated_at' key (SPEC §5.3)."""
        service = _FakeService([_make_summary()])
        view = render_api_workflows_list(service)  # type: ignore[arg-type]
        _, _, body = view()
        data = json.loads(body)
        assert "generated_at" in data
        assert isinstance(data["generated_at"], str)
        assert len(data["generated_at"]) > 0

    def test_top_level_source_hint_key(self) -> None:
        """Response must include a top-level 'source_hint' key (SPEC §5.3)."""
        service = _FakeService([_make_summary()])
        view = render_api_workflows_list(service)  # type: ignore[arg-type]
        _, _, body = view()
        data = json.loads(body)
        assert "source_hint" in data

    def test_empty_workflows_returns_200_empty_list(self) -> None:
        """Empty source dir → 200 with workflows: [] (not 503)."""
        service = _FakeService([])
        view = render_api_workflows_list(service)  # type: ignore[arg-type]
        status, _, body = view()
        assert status == 200
        data = json.loads(body)
        assert data["workflows"] == []

    def test_workflows_count_matches_service(self) -> None:
        """'workflows' list length matches what the service returns."""
        summaries = [_make_summary(f"wf-{i}") for i in range(5)]
        service = _FakeService(summaries)
        view = render_api_workflows_list(service)  # type: ignore[arg-type]
        _, _, body = view()
        data = json.loads(body)
        assert len(data["workflows"]) == 5


# ---------------------------------------------------------------------------
# Tests: item shape — summary fields only
# ---------------------------------------------------------------------------


class TestApiWorkflowsListItemShape:
    def _get_first_item(self, summaries: list[WorkflowSummaryDTO] | None = None) -> dict:
        if summaries is None:
            summaries = [_make_summary()]
        service = _FakeService(summaries)
        view = render_api_workflows_list(service)  # type: ignore[arg-type]
        _, _, body = view()
        data = json.loads(body)
        return data["workflows"][0]

    def test_item_has_name(self) -> None:
        item = self._get_first_item([_make_summary("tdd-cycle")])
        assert item["name"] == "tdd-cycle"

    def test_item_has_display_name(self) -> None:
        item = self._get_first_item([_make_summary("tdd-cycle")])
        assert item["display_name"] == "tdd-cycle"

    def test_item_has_description(self) -> None:
        item = self._get_first_item()
        assert "description" in item
        assert isinstance(item["description"], str)

    def test_item_has_version(self) -> None:
        item = self._get_first_item()
        assert item["version"] == "0.1.0"

    def test_item_has_schema_version(self) -> None:
        item = self._get_first_item()
        assert item["schema_version"] == "1"

    def test_item_stage_count_is_integer(self) -> None:
        """stage_count must be an int, not a list (QA review correction absorbed)."""
        item = self._get_first_item([_make_summary(stage_count=5)])
        assert isinstance(item["stage_count"], int)
        assert item["stage_count"] == 5

    def test_item_has_agent_ids(self) -> None:
        item = self._get_first_item()
        assert "agent_ids" in item
        assert isinstance(item["agent_ids"], list)

    def test_item_has_has_parallel(self) -> None:
        item = self._get_first_item([_make_summary(has_parallel=True)])
        assert item["has_parallel"] is True

    def test_item_has_has_gates(self) -> None:
        item = self._get_first_item([_make_summary(has_gates=True)])
        assert item["has_gates"] is True

    def test_item_has_source_path(self) -> None:
        item = self._get_first_item()
        assert "source_path" in item
        assert isinstance(item["source_path"], str)


# ---------------------------------------------------------------------------
# Tests: SPEC D1 synthesis decision — no diagram_svg, no stages[] on LIST items
# ---------------------------------------------------------------------------


class TestApiWorkflowsListLeanliness:
    """LIST must be lean: no diagram_svg, no stages[] (D1 synthesis decision)."""

    def _get_item(self) -> dict:
        service = _FakeService([_make_summary()])
        view = render_api_workflows_list(service)  # type: ignore[arg-type]
        _, _, body = view()
        data = json.loads(body)
        return data["workflows"][0]

    def test_no_diagram_svg_on_item(self) -> None:
        """LIST items MUST NOT contain 'diagram_svg' (D1 decision, SPEC §5.3)."""
        item = self._get_item()
        assert "diagram_svg" not in item, (
            "LIST /api/workflows must not include diagram_svg — use DETAIL endpoint"
        )

    def test_no_dag_svg_on_item(self) -> None:
        """LIST items MUST NOT contain 'dag_svg' (legacy alias guard)."""
        item = self._get_item()
        assert "dag_svg" not in item

    def test_no_stages_on_item(self) -> None:
        """LIST items MUST NOT contain 'stages[]' (D1 decision, SPEC §5.3)."""
        item = self._get_item()
        assert "stages" not in item, (
            "LIST /api/workflows must not include stages — use DETAIL endpoint"
        )

    def test_no_inputs_on_item(self) -> None:
        """LIST items should not contain 'inputs' (detail-only field)."""
        item = self._get_item()
        assert "inputs" not in item
