"""Unit tests for GET /api/workflows/<name> — PR3-15.

Coverage (per TASKS.md PR3-15 + SPEC §5.4 acceptance):
- Happy path: valid name returns 200 with correct shape.
- Response shape: includes stages[], diagram_svg (non-empty), source_path.
- Invalid name (regex fails) → 400 (not 404, not 500).
- Path traversal attempt (dots/slashes) → 400.
- Valid name but no matching workflow → 404.
- diagram_svg is non-empty string starting with "<svg".
- stages[] is a list (not empty for a real workflow).
- inputs[] is present.
- Security: all entries in the name regex whitelist pass; traversal patterns blocked.
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import pytest

from dadaia_workspace.features.panel.views.api import render_api_workflow_detail
from dadaia_workspace.features.workflows.service import (
    StageDTO,
    WorkflowDetailDTO,
)


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class _FakeWorkflowsService:
    """Minimal fake of WorkflowsService for handler-level unit tests."""

    def __init__(self, workflows: dict[str, WorkflowDetailDTO | None]) -> None:
        """workflows: name → DetailDTO or None (simulates not-found)."""
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
    diagram_svg: str = "<svg role='img'><g/></svg>",
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
# Tests: happy path
# ---------------------------------------------------------------------------


class TestApiWorkflowDetailHappyPath:
    def _call(self, name: str, workflows_svc: _FakeWorkflowsService) -> tuple[int, str, dict]:
        view = render_api_workflow_detail(workflows_svc)  # type: ignore[arg-type]
        status, ct, body = view(workflow_name=name)
        return status, ct, json.loads(body)

    def test_returns_200_for_existing_workflow(self) -> None:
        svc = _FakeWorkflowsService({"tdd-cycle": _make_detail()})
        status, _, _ = self._call("tdd-cycle", svc)
        assert status == 200

    def test_content_type_is_json(self) -> None:
        svc = _FakeWorkflowsService({"tdd-cycle": _make_detail()})
        _, ct, _ = self._call("tdd-cycle", svc)
        assert ct == "application/json; charset=utf-8"

    def test_response_has_name(self) -> None:
        svc = _FakeWorkflowsService({"tdd-cycle": _make_detail("tdd-cycle")})
        _, _, data = self._call("tdd-cycle", svc)
        assert data["name"] == "tdd-cycle"

    def test_response_has_description(self) -> None:
        svc = _FakeWorkflowsService({"tdd-cycle": _make_detail()})
        _, _, data = self._call("tdd-cycle", svc)
        assert "description" in data

    def test_response_has_version(self) -> None:
        svc = _FakeWorkflowsService({"tdd-cycle": _make_detail()})
        _, _, data = self._call("tdd-cycle", svc)
        assert data["version"] == "0.1.0"

    def test_response_has_schema_version(self) -> None:
        svc = _FakeWorkflowsService({"tdd-cycle": _make_detail()})
        _, _, data = self._call("tdd-cycle", svc)
        assert data["schema_version"] == "1"

    def test_response_has_inputs_list(self) -> None:
        svc = _FakeWorkflowsService({"tdd-cycle": _make_detail()})
        _, _, data = self._call("tdd-cycle", svc)
        assert "inputs" in data
        assert isinstance(data["inputs"], list)

    def test_response_has_source_path(self) -> None:
        svc = _FakeWorkflowsService({"tdd-cycle": _make_detail()})
        _, _, data = self._call("tdd-cycle", svc)
        assert "source_path" in data
        assert isinstance(data["source_path"], str)


# ---------------------------------------------------------------------------
# Tests: stages[] present and correct
# ---------------------------------------------------------------------------


class TestApiWorkflowDetailStages:
    def test_response_has_stages_list(self) -> None:
        """DETAIL response must include stages[] (SPEC §5.4)."""
        svc = _FakeWorkflowsService({"tdd-cycle": _make_detail()})
        view = render_api_workflow_detail(svc)  # type: ignore[arg-type]
        _, _, body = view(workflow_name="tdd-cycle")
        data = json.loads(body)
        assert "stages" in data
        assert isinstance(data["stages"], list)

    def test_stages_list_is_non_empty(self) -> None:
        stages = [_make_stage("s1"), _make_stage("s2")]
        svc = _FakeWorkflowsService({"my-wf": _make_detail("my-wf", stages=stages)})
        view = render_api_workflow_detail(svc)  # type: ignore[arg-type]
        _, _, body = view(workflow_name="my-wf")
        data = json.loads(body)
        assert len(data["stages"]) == 2

    def test_stage_has_id_and_agent(self) -> None:
        stages = [_make_stage("do-work", "software-engineer")]
        svc = _FakeWorkflowsService({"my-wf": _make_detail("my-wf", stages=stages)})
        view = render_api_workflow_detail(svc)  # type: ignore[arg-type]
        _, _, body = view(workflow_name="my-wf")
        data = json.loads(body)
        stage = data["stages"][0]
        assert stage["id"] == "do-work"
        assert stage["agent"] == "software-engineer"

    def test_stage_has_needs_list(self) -> None:
        stages = [_make_stage("step")]
        svc = _FakeWorkflowsService({"my-wf": _make_detail("my-wf", stages=stages)})
        view = render_api_workflow_detail(svc)  # type: ignore[arg-type]
        _, _, body = view(workflow_name="my-wf")
        data = json.loads(body)
        assert isinstance(data["stages"][0]["needs"], list)

    def test_stage_has_on_failure(self) -> None:
        stages = [_make_stage()]
        svc = _FakeWorkflowsService({"my-wf": _make_detail("my-wf", stages=stages)})
        view = render_api_workflow_detail(svc)  # type: ignore[arg-type]
        _, _, body = view(workflow_name="my-wf")
        data = json.loads(body)
        assert data["stages"][0]["on_failure"] == "stop"


# ---------------------------------------------------------------------------
# Tests: diagram_svg present and non-empty
# ---------------------------------------------------------------------------


class TestApiWorkflowDetailDiagramSvg:
    def test_diagram_svg_present(self) -> None:
        """DETAIL response must include diagram_svg (SPEC §5.4)."""
        svc = _FakeWorkflowsService({"tdd-cycle": _make_detail()})
        view = render_api_workflow_detail(svc)  # type: ignore[arg-type]
        _, _, body = view(workflow_name="tdd-cycle")
        data = json.loads(body)
        assert "diagram_svg" in data

    def test_diagram_svg_is_non_empty(self) -> None:
        """diagram_svg must be a non-empty string (not '' or None)."""
        svc = _FakeWorkflowsService({"tdd-cycle": _make_detail(diagram_svg="<svg role='img'><g/></svg>")})
        view = render_api_workflow_detail(svc)  # type: ignore[arg-type]
        _, _, body = view(workflow_name="tdd-cycle")
        data = json.loads(body)
        assert isinstance(data["diagram_svg"], str)
        assert len(data["diagram_svg"]) > 0

    def test_diagram_svg_starts_with_svg_tag(self) -> None:
        """diagram_svg must start with '<svg' (server-rendered, not placeholder)."""
        svc = _FakeWorkflowsService({"tdd-cycle": _make_detail(diagram_svg="<svg role='img' width='100'><g/></svg>")})
        view = render_api_workflow_detail(svc)  # type: ignore[arg-type]
        _, _, body = view(workflow_name="tdd-cycle")
        data = json.loads(body)
        assert data["diagram_svg"].startswith("<svg")


# ---------------------------------------------------------------------------
# Tests: 400 on invalid name (regex guard)
# ---------------------------------------------------------------------------


class TestApiWorkflowDetailInvalidName:
    """Name validation: ^[A-Za-z0-9_-]+$ (SPEC §5.4, §6 path traversal guard)."""

    def _call_status(self, name: str) -> int:
        svc = _FakeWorkflowsService({"valid-wf": _make_detail("valid-wf")})
        view = render_api_workflow_detail(svc)  # type: ignore[arg-type]
        status, _, _ = view(workflow_name=name)
        return status

    def test_double_dot_returns_400(self) -> None:
        """'../../etc/passwd' must return 400 (path traversal, SPEC G12 / E2E-API-12)."""
        assert self._call_status("../../etc/passwd") == 400

    def test_slash_in_name_returns_400(self) -> None:
        """Name with slash must return 400."""
        assert self._call_status("foo/bar") == 400

    def test_dot_in_name_returns_400(self) -> None:
        """Name with dot must return 400 (path separator guard)."""
        assert self._call_status("foo.bar") == 400

    def test_space_in_name_returns_400(self) -> None:
        """Name with space must return 400."""
        assert self._call_status("my workflow") == 400

    def test_empty_name_returns_400(self) -> None:
        """Empty name must return 400."""
        assert self._call_status("") == 400

    def test_null_byte_returns_400(self) -> None:
        """Null byte in name must return 400."""
        assert self._call_status("foo\x00bar") == 400

    def test_at_sign_returns_400(self) -> None:
        """'@' is not in the allowed set."""
        assert self._call_status("foo@bar") == 400

    def test_valid_name_with_hyphen_passes(self) -> None:
        """Hyphenated names like 'tdd-cycle' must pass validation."""
        svc = _FakeWorkflowsService({"tdd-cycle": _make_detail("tdd-cycle")})
        view = render_api_workflow_detail(svc)  # type: ignore[arg-type]
        status, _, _ = view(workflow_name="tdd-cycle")
        assert status == 200

    def test_valid_name_with_underscore_passes(self) -> None:
        """Names with underscores like 'cross_cutting_feature' must pass."""
        svc = _FakeWorkflowsService({"cross_cutting": _make_detail("cross_cutting")})
        view = render_api_workflow_detail(svc)  # type: ignore[arg-type]
        status, _, _ = view(workflow_name="cross_cutting")
        assert status == 200

    def test_valid_alphanumeric_name_passes(self) -> None:
        """Pure alphanumeric names must pass validation."""
        svc = _FakeWorkflowsService({"workflow1": _make_detail("workflow1")})
        view = render_api_workflow_detail(svc)  # type: ignore[arg-type]
        status, _, _ = view(workflow_name="workflow1")
        assert status == 200


# ---------------------------------------------------------------------------
# Tests: 400 error body shape
# ---------------------------------------------------------------------------


class TestApiWorkflowDetailErrorShapes:
    def test_400_body_has_error_key(self) -> None:
        svc = _FakeWorkflowsService({})
        view = render_api_workflow_detail(svc)  # type: ignore[arg-type]
        _, _, body = view(workflow_name="../../etc/passwd")
        data = json.loads(body)
        assert "error" in data

    def test_400_body_has_message_key(self) -> None:
        svc = _FakeWorkflowsService({})
        view = render_api_workflow_detail(svc)  # type: ignore[arg-type]
        _, _, body = view(workflow_name="../../etc/passwd")
        data = json.loads(body)
        assert "message" in data

    def test_400_message_does_not_expose_internals(self) -> None:
        """Error message must be generic — OWASP A06."""
        svc = _FakeWorkflowsService({})
        view = render_api_workflow_detail(svc)  # type: ignore[arg-type]
        _, _, body = view(workflow_name="../../etc/passwd")
        data = json.loads(body)
        msg = data.get("message", "")
        # Must not contain filesystem paths or stack trace fragments.
        assert "/etc" not in msg
        assert "Traceback" not in msg


# ---------------------------------------------------------------------------
# Tests: 404 on valid name with no matching workflow
# ---------------------------------------------------------------------------


class TestApiWorkflowDetailNotFound:
    def test_valid_name_not_found_returns_404(self) -> None:
        """Valid name that doesn't exist in the store → 404 (not 400, not 500)."""
        svc = _FakeWorkflowsService({})  # no workflows registered
        view = render_api_workflow_detail(svc)  # type: ignore[arg-type]
        status, _, _ = view(workflow_name="nonexistent-wf")
        assert status == 404

    def test_404_body_has_error_key(self) -> None:
        svc = _FakeWorkflowsService({})
        view = render_api_workflow_detail(svc)  # type: ignore[arg-type]
        _, _, body = view(workflow_name="nonexistent-wf")
        data = json.loads(body)
        assert "error" in data

    def test_valid_name_returns_none_from_service_is_404(self) -> None:
        """Service returning None for a valid name → 404."""
        svc = _FakeWorkflowsService({"tdd-cycle": None})
        view = render_api_workflow_detail(svc)  # type: ignore[arg-type]
        status, _, _ = view(workflow_name="tdd-cycle")
        assert status == 404
