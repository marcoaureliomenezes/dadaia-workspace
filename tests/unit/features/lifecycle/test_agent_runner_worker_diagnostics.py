"""v0.1.78 T-D / FR-D — worker-noncompliance diagnostic evidence (bug
``worker-noncompliance-block-carries-no-diagnostic-evidence``).

RED-first proof: today a noncompliant worker result (SUCCEEDED, empty ``artifact_refs``)
collapses the gate to ``"agent result missing artifact evidence"`` with NOTHING persisted
— the operator cannot tell prompt vs model vs adapter vs config failure. The fix persists a
redacted, run-scoped :class:`WorkerDiagnostic` referenced from ``BlockedState.detail`` for
EVERY real worker attempt that ends blocked-for-noncompliance.
"""

from __future__ import annotations

import json
from pathlib import Path

from dadaia_workspace.core.models.lifecycle import (
    AgentRunRequest,
    AgentRunResult,
    AgentRunStatus,
    AgentRuntimeKind,
    GateEvidenceKind,
    LifecyclePhase,
    LifecycleRun,
    LifecycleRunStatus,
    WorkerDiagnostic,
)
from dadaia_workspace.features.lifecycle.agent_runner import (
    AgentRunnerInput,
    LifecycleAgentRunner,
)
from dadaia_workspace.infrastructure.fake_runtime import FakeAgentRuntime
from dadaia_workspace.infrastructure.runtime_files import FilesystemRuntimeFileAdapter


def _run() -> LifecycleRun:
    return LifecycleRun(
        run_id="diag-run-1",
        context="dadaia-workspace",
        release_id="v0.1.78",
        command="pipeline",
        phase=LifecyclePhase.IMPLEMENTATION,
        status=LifecycleRunStatus.RUNNING,
        current_step="implement",
        idempotency_key="diag-run-1",
    )


def _request() -> AgentRunRequest:
    return AgentRunRequest(
        role="software-engineer",
        prompt="run the step",
        runtime=AgentRuntimeKind.PI_HEADLESS,
        context="dadaia-workspace",
        release_id="v0.1.78",
        allowed_paths=(".dadaia/handoff/dadaia-workspace/**",),
        required_evidence=(GateEvidenceKind.HANDOFF,),
    )


def _init_workspace(tmp_path: Path) -> Path:
    from dadaia_workspace.features.workspace.service import WorkspaceService
    from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
    from dadaia_workspace.infrastructure.python_env import VenvPythonEnvironmentManager

    WorkspaceService(
        public_assets=FileSystemPublicAssetManager(),
        python_env=VenvPythonEnvironmentManager(),
    ).init(tmp_path)
    return tmp_path


def test_noncompliant_result_persists_diagnostic_and_references_it_in_blocked_detail(
    tmp_path: Path,
) -> None:
    """A no-op worker (empty artifact_refs) with a WorkerDiagnostic attached still BLOCKS
    — but the block now carries a diagnostic_ref pointing at a persisted, readable record
    whose fields are exactly the evidence the operator needs."""
    workspace_root = _init_workspace(tmp_path)
    writer = FilesystemRuntimeFileAdapter(workspace_root)

    diagnostic = WorkerDiagnostic(
        runtime="pi_headless",
        model="gpt-5.5",
        requested_reasoning="high",
        actual_reasoning="medium",
        exit_code=0,
        parser_classification="no-result",
        output_tail="raw pi stdout tail, secret=[REDACTED]",
        session_ref="pi-session-abc123",
    )
    result = AgentRunResult(
        status=AgentRunStatus.SUCCEEDED,
        summary="pi headless completed",
        artifact_refs=(),
        diagnostic=diagnostic,
    )
    runner = LifecycleAgentRunner(
        runtime=FakeAgentRuntime(result=result),
        runtime_files=writer,
    )

    blocked = runner.evaluate_gate(
        _run(),
        AgentRunnerInput(
            request=_request(),
            target_phase=LifecyclePhase.QA_REVIEW,
            current_step="implement",
            is_review=False,
        ),
    )

    assert blocked is not None
    assert blocked.reason == "agent result missing artifact evidence"
    diagnostic_ref = blocked.detail.get("diagnostic_ref")
    assert diagnostic_ref, (
        f"BlockedState.detail must carry a diagnostic_ref; got {blocked.detail!r}"
    )

    persisted_path = workspace_root / diagnostic_ref
    assert persisted_path.is_file(), f"diagnostic_ref must point at a real file: {persisted_path}"
    payload = json.loads(persisted_path.read_text(encoding="utf-8"))
    assert payload["runtime"] == "pi_headless"
    assert payload["model"] == "gpt-5.5"
    assert payload["requested_reasoning"] == "high"
    assert payload["actual_reasoning"] == "medium"
    assert payload["exit_code"] == 0
    assert payload["parser_classification"] == "no-result"
    assert payload["session_ref"] == "pi-session-abc123"
    assert "[REDACTED]" in payload["output_tail"]


def test_failed_result_with_diagnostic_also_persists_evidence(tmp_path: Path) -> None:
    """A structurally FAILED result (non-zero exit, adapter error) also carries a
    diagnostic when the adapter attaches one — the block is never evidence-free."""
    workspace_root = _init_workspace(tmp_path)
    writer = FilesystemRuntimeFileAdapter(workspace_root)

    diagnostic = WorkerDiagnostic(
        runtime="pi_headless",
        model="gpt-5.3-codex",
        requested_reasoning="medium",
        actual_reasoning=None,
        exit_code=1,
        parser_classification="malformed-json",
        output_tail="traceback tail",
        session_ref=None,
    )
    result = AgentRunResult(
        status=AgentRunStatus.FAILED,
        summary="pi headless returned non-zero exit",
        error="",
        diagnostic=diagnostic,
    )
    runner = LifecycleAgentRunner(
        runtime=FakeAgentRuntime(result=result),
        runtime_files=writer,
    )

    blocked = runner.evaluate_gate(
        _run(),
        AgentRunnerInput(
            request=_request(),
            target_phase=LifecyclePhase.QA_REVIEW,
            current_step="implement",
            is_review=False,
        ),
    )

    assert blocked is not None
    diagnostic_ref = blocked.detail.get("diagnostic_ref")
    assert diagnostic_ref
    persisted_path = workspace_root / diagnostic_ref
    payload = json.loads(persisted_path.read_text(encoding="utf-8"))
    assert payload["parser_classification"] == "malformed-json"
    assert payload["exit_code"] == 1


def test_no_diagnostic_attached_blocks_without_diagnostic_ref(tmp_path: Path) -> None:
    """When the adapter attaches no diagnostic (e.g. FAKE runtime, or a compliant adapter
    path that never populates one), the gate still blocks on missing evidence but the
    detail carries no diagnostic_ref — nothing to reference, no crash."""
    workspace_root = _init_workspace(tmp_path)
    writer = FilesystemRuntimeFileAdapter(workspace_root)
    runner = LifecycleAgentRunner(
        runtime=FakeAgentRuntime(),
        runtime_files=writer,
    )

    blocked = runner.evaluate_gate(
        _run(),
        AgentRunnerInput(
            request=_request(),
            target_phase=LifecyclePhase.QA_REVIEW,
            current_step="implement",
            is_review=False,
        ),
    )

    assert blocked is not None
    assert "diagnostic_ref" not in blocked.detail


def test_runner_with_no_writer_injected_still_blocks_gracefully(tmp_path: Path) -> None:
    """``runtime_files=None`` (the default — every pre-existing caller) is a no-op:
    the gate still blocks, with no diagnostic_ref and no crash — additive-optional."""
    diagnostic = WorkerDiagnostic(
        runtime="pi_headless",
        model=None,
        requested_reasoning=None,
        actual_reasoning=None,
        exit_code=None,
        parser_classification="no-result",
        output_tail="",
    )
    result = AgentRunResult(
        status=AgentRunStatus.SUCCEEDED,
        summary="pi headless completed",
        artifact_refs=(),
        diagnostic=diagnostic,
    )
    runner = LifecycleAgentRunner(runtime=FakeAgentRuntime(result=result))

    blocked = runner.evaluate_gate(
        _run(),
        AgentRunnerInput(
            request=_request(),
            target_phase=LifecyclePhase.QA_REVIEW,
            current_step="implement",
            is_review=False,
        ),
    )

    assert blocked is not None
    assert "diagnostic_ref" not in blocked.detail


def test_run_with_result_also_persists_diagnostic_on_block(tmp_path: Path) -> None:
    """``run_with_result`` (used by the pipeline) gets the same diagnostic-persistence
    behavior as ``evaluate_gate`` — not a second, divergent code path."""
    workspace_root = _init_workspace(tmp_path)
    writer = FilesystemRuntimeFileAdapter(workspace_root)
    diagnostic = WorkerDiagnostic(
        runtime="pi_headless",
        model="gpt-5.5",
        requested_reasoning="high",
        actual_reasoning="high",
        exit_code=0,
        parser_classification="no-result",
        output_tail="tail",
    )
    result = AgentRunResult(
        status=AgentRunStatus.SUCCEEDED,
        summary="pi headless completed",
        artifact_refs=(),
        diagnostic=diagnostic,
    )
    runner = LifecycleAgentRunner(runtime=FakeAgentRuntime(result=result), runtime_files=writer)

    decision, worker_result = runner.run_with_result(
        _run(),
        AgentRunnerInput(
            request=_request(),
            target_phase=LifecyclePhase.QA_REVIEW,
            current_step="implement",
            is_review=False,
        ),
    )

    assert decision.run.blocked is not None
    diagnostic_ref = decision.run.blocked.detail.get("diagnostic_ref")
    assert diagnostic_ref
    assert (workspace_root / diagnostic_ref).is_file()
    assert worker_result.diagnostic is diagnostic


# ── bug r25-block-reason-claims-missing-diagnostic-ref (validator R25 / R-23 + R-27) ──
#
# The truncation fix promised "the full transcript is in the persisted diagnostic referenced
# by detail.diagnostic_ref" on every truncated reason. The validator found `detail` was `{}`:
# a diagnostic is persisted only when the adapter attached one AND a runtime-file writer is
# wired. A message written to stop this field from asserting something untrue was itself
# made to assert something untrue, in the same field, hours later.
#
# Both directions are pinned, because either one alone is the bug: never promise what is not
# there, and do point at it when it is.


def _long_failure() -> str:
    return "banner\n" * 50 + "ERROR: unexpected status 401 Unauthorized\n" + "noise\n" * 200


def test_a_truncated_reason_makes_no_promise_when_nothing_was_persisted(
    tmp_path: Path,
) -> None:
    from dadaia_workspace.core.worker_failure import summarize_worker_failure

    reason = summarize_worker_failure(_long_failure())

    assert "401 Unauthorized" in reason
    assert "truncated" in reason
    assert "diagnostic_ref" not in reason, (
        "the reason pointed the operator at a key that is absent from detail — the exact "
        f"shape the validator reported: {reason}"
    )
