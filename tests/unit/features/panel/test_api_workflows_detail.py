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


# ---------------------------------------------------------------------------
# AGT-33 — audit-cycle DETAIL (4-way parallel DAG coverage)
# ---------------------------------------------------------------------------


def _make_audit_cycle_detail() -> WorkflowDetailDTO:
    """Construct a WorkflowDetailDTO that mirrors the audit-cycle topology.

    audit-cycle: intake (gate) → 4-way parallel audit group (code_review,
    security_review, research_review, qa_audit) → synthesis.  Total: 6 stages.
    """
    audit_stages = [
        StageDTO(
            id="audit_intake",
            agent="project-auditor",
            needs=[],
            parallel_group=None,
            gate=True,
            expected_output_path=None,
            must_include=None,
            on_failure="stop",
        ),
        StageDTO(
            id="code_review",
            agent="code-reviewer",
            needs=["audit_intake"],
            parallel_group="audit",
            gate=False,
            expected_output_path=None,
            must_include=None,
            on_failure="stop",
        ),
        StageDTO(
            id="security_review",
            agent="security-reviewer",
            needs=["audit_intake"],
            parallel_group="audit",
            gate=False,
            expected_output_path=None,
            must_include=None,
            on_failure="stop",
        ),
        StageDTO(
            id="research_review",
            agent="researcher",
            needs=["audit_intake"],
            parallel_group="audit",
            gate=False,
            expected_output_path=None,
            must_include=None,
            on_failure="stop",
        ),
        StageDTO(
            id="qa_audit",
            agent="qa-engineer",
            needs=["audit_intake"],
            parallel_group="audit",
            gate=False,
            expected_output_path=None,
            must_include=None,
            on_failure="stop",
        ),
        StageDTO(
            id="synthesis",
            agent="project-auditor",
            needs=["code_review", "security_review", "research_review", "qa_audit"],
            parallel_group=None,
            gate=False,
            expected_output_path=None,
            must_include=None,
            on_failure="stop",
        ),
    ]
    return WorkflowDetailDTO(
        name="audit-cycle",
        display_name="audit-cycle",
        description="4-way parallel deep audit orchestrated by project-auditor.",
        version="0.1.0",
        schema_version="1",
        stage_count=len(audit_stages),
        agent_ids=["project-auditor", "code-reviewer", "security-reviewer",
                   "researcher", "qa-engineer"],
        has_parallel=True,
        has_gates=True,
        source_path=".dadaia/agentic/workflows/audit-cycle.workflow.md",
        inputs=[{"name": "context", "type": "string", "required": True}],
        stages=audit_stages,
        diagram_svg="<svg role='img'><title>audit-cycle DAG</title><g/></svg>",
    )


class TestAuditCycleDetail:
    """DETAIL coverage for the audit-cycle workflow (4-way parallel group, gate stage)."""

    def _call(self) -> tuple[int, str, dict]:
        detail = _make_audit_cycle_detail()
        svc = _FakeWorkflowsService({"audit-cycle": detail})
        view = render_api_workflow_detail(svc)  # type: ignore[arg-type]
        status, ct, body = view(workflow_name="audit-cycle")
        return status, ct, json.loads(body)

    def test_audit_cycle_returns_200(self) -> None:
        """audit-cycle DETAIL returns 200."""
        status, _, _ = self._call()
        assert status == 200

    def test_audit_cycle_stage_count_is_6(self) -> None:
        """audit-cycle has 6 stages (intake + 4 parallel + synthesis)."""
        _, _, data = self._call()
        assert data["stage_count"] == 6
        assert len(data["stages"]) == 6

    def test_audit_cycle_has_parallel(self) -> None:
        """audit-cycle has_parallel must be True (4-way audit group)."""
        _, _, data = self._call()
        assert data["has_parallel"] is True

    def test_audit_cycle_has_gates(self) -> None:
        """audit-cycle has_gates must be True (intake is a gate)."""
        _, _, data = self._call()
        assert data["has_gates"] is True

    def test_audit_cycle_parallel_stages_present(self) -> None:
        """The 4 parallel audit stages must all be present in stages[]."""
        _, _, data = self._call()
        stage_ids = {s["id"] for s in data["stages"]}
        assert "code_review" in stage_ids
        assert "security_review" in stage_ids
        assert "research_review" in stage_ids
        assert "qa_audit" in stage_ids

    def test_audit_cycle_gate_stage_present(self) -> None:
        """audit_intake must appear in stages[] as the gate stage."""
        _, _, data = self._call()
        intake = next((s for s in data["stages"] if s["id"] == "audit_intake"), None)
        assert intake is not None, "audit_intake gate stage missing from stages[]"

    def test_audit_cycle_synthesis_stage_present(self) -> None:
        """synthesis stage must appear in stages[]."""
        _, _, data = self._call()
        synthesis = next((s for s in data["stages"] if s["id"] == "synthesis"), None)
        assert synthesis is not None, "synthesis stage missing from stages[]"

    def test_audit_cycle_diagram_svg_present(self) -> None:
        """audit-cycle DETAIL must include a non-empty diagram_svg."""
        _, _, data = self._call()
        assert "diagram_svg" in data
        assert isinstance(data["diagram_svg"], str)
        assert data["diagram_svg"].startswith("<svg")
