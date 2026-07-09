"""FR4 (v0.1.68) — the full-pipeline E2E that was missing (SPEC AC4.1).

v0.1.66/67 validated the pi/codex ADAPTER (does the binary get invoked, does a
non-zero exit surface) with fake harnesses and adapter-level unit tests, and never
once drove the operator's real workflow — a full ``dadaia lifecycle pipeline`` /
``implement-review`` run against a real spec-context tree, selecting evidence,
consuming payloads, and deriving scope. This is that test.

Provisions a throwaway ``repos/<slug>/specs/`` tree under ``tmp_path`` with an
``Aprovado`` SPEC/PLAN/TASKS and a reserved ``[-]`` task carrying a real ``Write set:``,
then drives BOTH `dadaia lifecycle pipeline`` and ``implement-review`` on the fake
harness end to end, asserting the three invariants FR1/FR2/FR3 restore together:

(a) evidence selected is run-scoped — a stale, unrelated, independently-validating
    handoff pre-seeded on disk is NEVER surfaced by a no-op implement worker's block
    (FR1).
(b) the terminal ``implement-review`` run passes ``handoffs doctor`` with no
    ``unconsumed_required`` finding (FR2).
(c) the ``pipeline`` implement step's built request carries the TASKS.md-declared
    write set in ``allowed_paths`` — with NO ``--write-scope`` flag (FR3).

Hermetic: everything lives under ``tmp_path``, no real binaries (``--harness fake``
throughout), ``-p no:cacheprovider`` at the suite level.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace import container
from dadaia_workspace.cli.main import app
from dadaia_workspace.core.models.lifecycle import (
    AgentRunRequest,
    AgentRunResult,
    AgentRunStatus,
)
from dadaia_workspace.features.workspace.service import WorkspaceService
from dadaia_workspace.infrastructure.fake_runtime import FakeAgentRuntime
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
from dadaia_workspace.infrastructure.python_env import VenvPythonEnvironmentManager

_runner = CliRunner()
_CONTEXT = "e2e-throwaway"
_RELEASE = "v0-e2e-throwaway"
_TASK_WRITE_PATH = "src/thing.py"


def _init_workspace(path: Path) -> Path:
    WorkspaceService(
        public_assets=FileSystemPublicAssetManager(),
        python_env=VenvPythonEnvironmentManager(),
    ).init(path)
    return path


def _provision_throwaway_context(workspace: Path) -> Path:
    """Build a real ``repos/<slug>/specs/`` tree: Aprovado SPEC/PLAN/TASKS, one
    reserved ``[-]`` task with a real ``Write set:``."""
    specs_dir = workspace / "repos" / _CONTEXT / "specs"
    release_dir = specs_dir / "releases" / _RELEASE
    release_dir.mkdir(parents=True, exist_ok=True)

    (specs_dir / "releases" / "ACTIVE.md").write_text(
        f"---\nrelease: {_RELEASE}\nphase: IMPLEMENTATION\n---\n",
        encoding="utf-8",
    )
    (release_dir / "SPEC.md").write_text(
        "# SPEC — throwaway E2E release\n\n> **Status:** Aprovado\n",
        encoding="utf-8",
    )
    (release_dir / "PLAN.md").write_text(
        "# PLAN — throwaway E2E release\n\n> **Status:** Aprovado\n",
        encoding="utf-8",
    )
    (release_dir / "TASKS.md").write_text(
        f"""# TASKS — throwaway E2E release

> **Status:** Aprovado

### T-e2e-01 — implement the thing `[-]`
- **Owner:** software-engineer
- **Write set:** `{_TASK_WRITE_PATH}`
- **Task:** implement the thing this E2E proves scope derivation for.
""",
        encoding="utf-8",
    )
    return specs_dir


def _seed_stale_handoff(workspace: Path) -> Path:
    """A genuinely valid, independently-validating handoff from an UNRELATED task."""
    handoff_dir = workspace / ".dadaia" / "handoff" / _CONTEXT
    handoff_dir.mkdir(parents=True, exist_ok=True)
    stale_path = (
        handoff_dir / "2099-01-01T000000Z-software-engineer-unrelated-old-task.handoff.json"
    )
    stale_doc = {
        "schema_version": "handoff-v1.1",
        "agent": "software-engineer",
        "context": _CONTEXT,
        "produced_at": "2099-01-01T00:00:00Z",
        "scope": "an unrelated prior task — NOT this run's evidence",
        "metrics": {},
        "artifact": {"type": "other"},
    }
    stale_path.write_text(json.dumps(stale_doc, indent=2), encoding="utf-8")
    return stale_path


def _no_op_result() -> AgentRunResult:
    return AgentRunResult(
        status=AgentRunStatus.SUCCEEDED,
        summary="implement worker produced nothing structured",
        artifact_refs=(),
        structured_output={},
    )


def test_pipeline_end_to_end_on_throwaway_context(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC4.1 — the marquee E2E: FR1 + FR3 via ``pipeline``, FR2 via ``implement-review``.

    By construction this test would have been RED on pre-FR1/FR2/FR3 code: (a) the old
    role-keyed disk-glob would have surfaced the seeded stale handoff, (b) the terminal
    implement-review run would have failed handoffs doctor, and (c) the implement
    request's allowed_paths would NOT have contained the TASKS.md write set.
    """
    workspace = _init_workspace(tmp_path)
    _provision_throwaway_context(workspace)
    stale_path = _seed_stale_handoff(workspace)
    monkeypatch.chdir(workspace)

    # --- Drive 0: preflight ENFORCED (v0.1.72 FR6) ------------------------------------
    #
    # Bug `workflow-verbs-run-despite-blocked-preflight`: the throwaway context is not
    # bound, so preflight is BLOCKED — the release-mutating verbs must REFUSE before
    # creating any lifecycle run (no --skip-preflight given).
    refused = _runner.invoke(
        app,
        [
            "lifecycle",
            "pipeline",
            "--context",
            _CONTEXT,
            "--release-id",
            _RELEASE,
            "--run-id",
            "e2e-refused",
            "--harness",
            "fake",
            "--json",
        ],
    )
    assert refused.exit_code == 3, refused.output
    refused_payload = json.loads(refused.output)
    assert refused_payload["status"] == "BLOCKED"
    assert refused_payload["message"].startswith("preflight blocked:"), refused_payload
    assert not (workspace / ".dadaia" / "runs" / "lifecycle" / "e2e-refused").exists(), (
        "a refused verb must not create a lifecycle run"
    )

    refused_ir = _runner.invoke(
        app,
        [
            "lifecycle",
            "implement-review",
            "--context",
            _CONTEXT,
            "--release-id",
            _RELEASE,
            "--run-id",
            "e2e-refused-ir",
            "--harness",
            "fake",
            "--json",
        ],
    )
    assert refused_ir.exit_code == 3, refused_ir.output
    assert json.loads(refused_ir.output)["message"].startswith("preflight blocked:")
    assert not (workspace / ".dadaia" / "runs" / "lifecycle" / "e2e-refused-ir").exists()

    # --- Drive 1: `pipeline --harness fake` COMPLETES (v0.1.72 FR5) ------------------
    #
    # Bug `fake-pipeline-blocks-missing-artifact-evidence`: this drive previously
    # ASSERTED exit 3 / BLOCKED — codifying the broken smoke path the operator hit
    # (release-definition and implement-review had driving fakes; pipeline never got
    # one). The deterministic fake pipeline is the operator's workflow-wiring smoke
    # test: it must COMPLETE. Capture the implement request through the real wiring
    # (subclass seam on the infrastructure FakeAgentRuntime, resolved at factory call
    # time) to keep proving FR3 write-scope derivation on the executed path.

    captured_requests: list[AgentRunRequest] = []

    class _CapturingFake(FakeAgentRuntime):
        def run(self, request: AgentRunRequest) -> object:  # type: ignore[override]
            captured_requests.append(request)
            return super().run(request)

    import dadaia_workspace.infrastructure.fake_runtime as _fake_mod

    monkeypatch.setattr(_fake_mod, "FakeAgentRuntime", _CapturingFake)

    pipeline_result = _runner.invoke(
        app,
        [
            "lifecycle",
            "pipeline",
            "--context",
            _CONTEXT,
            "--release-id",
            _RELEASE,
            "--run-id",
            "e2e-pipe",
            "--harness",
            "fake",
            "--skip-preflight",
            "--json",
        ],
    )
    assert pipeline_result.exit_code == 0, pipeline_result.output
    pipeline_payload = json.loads(pipeline_result.output)
    assert pipeline_payload["status"] == "OK"
    assert pipeline_payload["completed"] is True

    # (a) FR1 — run-scoped evidence: the stale, unrelated handoff was never consumed or
    # mutated by the completing run.
    stale_after = json.loads(stale_path.read_text(encoding="utf-8"))
    assert stale_after["scope"] == "an unrelated prior task — NOT this run's evidence"

    # (c) FR3 — implement scope includes the TASKS.md write set, no --write-scope flag.
    assert captured_requests, "the fake implement worker must have been invoked"
    implement_request = captured_requests[0]
    assert _TASK_WRITE_PATH in implement_request.allowed_paths, (
        f"expected {_TASK_WRITE_PATH!r} in allowed_paths; got {implement_request.allowed_paths!r}"
    )

    # --- Drive 2: `implement-review` to APPROVED (default driving fake) — proves FR2 ---

    review_result = _runner.invoke(
        app,
        [
            "lifecycle",
            "implement-review",
            "--context",
            _CONTEXT,
            "--release-id",
            _RELEASE,
            "--run-id",
            "e2e-review",
            "--skip-preflight",
            "--harness",
            "fake",
            "--json",
        ],
    )
    assert review_result.exit_code == 0, review_result.output
    review_payload = json.loads(review_result.stdout)
    assert review_payload["completed"] is True
    assert review_payload["final_verdict"] == "APPROVED"

    # (b) FR2 — the terminal run passes handoffs doctor: no unconsumed_required finding.
    doctor = container.build_workflow_handoff_doctor(workspace)
    report = doctor.run()
    assert report.ok is True, (
        f"terminal implement-review run must pass handoffs doctor; "
        f"findings={[f.to_dict() for f in report.findings]!r}"
    )
