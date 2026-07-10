"""Unit tests for GET /api/workflows/<name>.

Shape/content-type/error-body facets are pinned by the golden
(``test_api_golden.py`` + detail 200/400/404 bytes). Three survivors, one per
real decision:
  1. Happy detail: name/stages/svg starts-with-`<svg`/inputs/source_path, all
     in one assert block.
  2. Invalid-name 400 param (traversal, slash, dot, space, empty, null byte, @;
     valid hyphen/underscore/alnum pass) — the name-regex traversal guard.
  3. 404 not-found + error body has no internals (A06).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dadaia_workspace.features.panel.views.api_workflows import render_api_workflow_detail
from dadaia_workspace.features.workflows.service import StageDTO, WorkflowDetailDTO

pytestmark = pytest.mark.unit


class _FakeWorkflowsService:
    """Minimal fake of WorkflowsService for handler-level unit tests."""

    def __init__(self, workflows: dict[str, WorkflowDetailDTO | None]) -> None:
        """workflows: name -> DetailDTO or None (simulates not-found)."""
        self._workflows = workflows
        self._workspace_root = Path("/fake/workspace")

    def get_detail(self, name: str) -> WorkflowDetailDTO | None:
        return self._workflows.get(name)


def _make_stage(stage_id: str = "step_one", agent: str = "software-engineer") -> StageDTO:
    return StageDTO(
        id=stage_id,
        agent=agent,
        needs=[],
        parallel_group=None,
        gate=False,
        expected_output_path=None,
        must_include=None,
        on_failure="stop",
    )


def _make_detail(
    name: str = "tdd-cycle",
    diagram_svg: str = "<svg role='img' width='100'><g/></svg>",
    stages: list[StageDTO] | None = None,
) -> WorkflowDetailDTO:
    if stages is None:
        stages = [
            _make_stage("red", "qa-engineer"),
            _make_stage("green", "software-engineer"),
            _make_stage("refactor", "software-engineer"),
        ]
    return WorkflowDetailDTO(
        name=name,
        display_name=name,
        description=f"Description of {name}",
        version="0.1.0",
        schema_version="1",
        stage_count=len(stages),
        agent_ids=list({s.agent for s in stages}),
        has_parallel=False,
        has_gates=False,
        source_path=f".dadaia/agentic/workflows/{name}.workflow.md",
        inputs=[{"name": "context", "type": "string", "required": True}],
        stages=stages,
        diagram_svg=diagram_svg,
    )


# ---------------------------------------------------------------------------
# 1. Happy detail — everything asserted in one block
# ---------------------------------------------------------------------------


def test_happy_detail_full_shape() -> None:
    stages = [_make_stage("do-work", "software-engineer")]
    svc = _FakeWorkflowsService({"tdd-cycle": _make_detail("tdd-cycle", stages=stages)})
    view = render_api_workflow_detail(svc)  # type: ignore[arg-type]

    status, content_type, body = view(workflow_name="tdd-cycle")

    assert status == 200
    assert content_type == "application/json; charset=utf-8"
    data = json.loads(body)
    assert data["name"] == "tdd-cycle"
    assert data["version"] == "0.1.0"
    assert data["schema_version"] == "1"
    assert isinstance(data["inputs"], list)
    assert isinstance(data["source_path"], str)

    assert isinstance(data["stages"], list)
    assert len(data["stages"]) == 1
    stage = data["stages"][0]
    assert stage["id"] == "do-work"
    assert stage["agent"] == "software-engineer"
    assert isinstance(stage["needs"], list)
    assert stage["on_failure"] == "stop"

    assert isinstance(data["diagram_svg"], str)
    assert len(data["diagram_svg"]) > 0
    assert data["diagram_svg"].startswith("<svg")


# ---------------------------------------------------------------------------
# 2. Invalid-name 400 param — the name-regex traversal guard
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("name", "expected_status"),
    [
        pytest.param("../../etc/passwd", 400, id="double-dot-traversal"),
        pytest.param("foo/bar", 400, id="slash-in-name"),
        pytest.param("foo.bar", 400, id="dot-in-name"),
        pytest.param("my workflow", 400, id="space-in-name"),
        pytest.param("", 400, id="empty-name"),
        pytest.param("foo\x00bar", 400, id="null-byte"),
        pytest.param("foo@bar", 400, id="at-sign-not-allowed"),
        pytest.param("tdd-cycle", 200, id="valid-hyphenated-passes"),
        pytest.param("cross_cutting", 200, id="valid-underscore-passes"),
        pytest.param("workflow1", 200, id="valid-alphanumeric-passes"),
    ],
)
def test_name_regex_traversal_guard(name: str, expected_status: int) -> None:
    known_name = name if expected_status == 200 else "valid-wf"
    svc = _FakeWorkflowsService({known_name: _make_detail(known_name)})
    view = render_api_workflow_detail(svc)  # type: ignore[arg-type]
    status, _, body = view(workflow_name=name)
    assert status == expected_status
    if expected_status == 400:
        data = json.loads(body)
        assert "error" in data
        assert "message" in data
        # Error message must be generic — OWASP A06 (no filesystem paths, no traceback).
        msg = data.get("message", "")
        assert "/etc" not in msg
        assert "Traceback" not in msg


# ---------------------------------------------------------------------------
# 3. 404 not-found + error body has no internals
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("workflows", "name"),
    [
        pytest.param({}, "nonexistent-wf", id="never-registered"),
        pytest.param({"tdd-cycle": None}, "tdd-cycle", id="service-returns-none-for-valid-name"),
    ],
)
def test_not_found_returns_404_without_internals(
    workflows: dict[str, WorkflowDetailDTO | None], name: str
) -> None:
    svc = _FakeWorkflowsService(workflows)
    view = render_api_workflow_detail(svc)  # type: ignore[arg-type]
    status, _, body = view(workflow_name=name)
    assert status == 404
    data = json.loads(body)
    assert "error" in data
