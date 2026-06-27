"""End-to-end Ring-2 boundary test: PI adapter → LifecycleAgentRunner (T-PI-06).

Proves PI has a REAL write boundary: ``changed_paths`` is sourced from a (faked)
git diff inside the adapter, and the engine's post-flight out-of-scope block
(`agent_runner.py:114-123`) fires when those paths fall outside the request's
allowed set — exactly as for Codex. An in-scope diff advances the phase.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from dadaia_workspace.core.models.lifecycle import (
    AgentRunRequest,
    AgentRuntimeKind,
    GateEvidenceKind,
    LifecyclePhase,
    LifecycleRun,
    LifecycleRunStatus,
)
from dadaia_workspace.features.lifecycle.agent_runner import (
    AgentRunnerInput,
    LifecycleAgentRunner,
)
from dadaia_workspace.infrastructure.pi_runtime import PiHeadlessAdapter, PiHeadlessConfig


class _FakeGit:
    def __init__(self, changed: tuple[str, ...]) -> None:
        self._changed = changed

    def diff_name_only(self, path: Path) -> tuple[str, ...]:
        return self._changed


def _run() -> LifecycleRun:
    return LifecycleRun(
        run_id="run-pi",
        context="dadaia-workspace",
        release_id="pi-fourth-harness-v1",
        command="implement",
        phase=LifecyclePhase.IMPLEMENTATION,
        status=LifecycleRunStatus.RUNNING,
        current_step="implementation",
        idempotency_key="resume-pi",
    )


def _approved_message_end() -> str:
    fenced = (
        "Done.\n```json\n"
        + json.dumps(
            {
                "schema": "agent-run-result-v1",
                "verdict": "APPROVED",
                "summary": "implemented",
                "artifact_refs": [".dadaia/handoff/dadaia-workspace/se.handoff.json"],
            }
        )
        + "\n```\n"
    )
    return json.dumps({"type": "message_end", "message": {"content": fenced}})


def _adapter(changed: tuple[str, ...]) -> PiHeadlessAdapter:
    def fake_runner(*args: object, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        argv = args[0]
        assert isinstance(argv, list)
        return subprocess.CompletedProcess(argv, 0, stdout=_approved_message_end())

    return PiHeadlessAdapter(
        PiHeadlessConfig(cwd=Path("/repo")),
        runner=fake_runner,
        environ={},
        git=_FakeGit(changed=changed),
    )


def _request() -> AgentRunRequest:
    return AgentRunRequest(
        role="software-engineer",
        prompt="implement",
        runtime=AgentRuntimeKind.PI_HEADLESS,
        context="dadaia-workspace",
        release_id="pi-fourth-harness-v1",
        allowed_paths=(
            "src/**",
            ".dadaia/handoff/dadaia-workspace/**",
        ),
        required_evidence=(GateEvidenceKind.HANDOFF,),
        expected_schema="agent-run-result-v1",
    )


def test_pi_out_of_scope_changed_paths_blocks_transition() -> None:
    adapter = _adapter(changed=("secrets/leak.txt",))
    decision = LifecycleAgentRunner(runtime=adapter).run(
        _run(),
        AgentRunnerInput(
            request=_request(),
            target_phase=LifecyclePhase.QA_REVIEW,
            current_step="implementation",
        ),
    )

    assert decision.run.phase is LifecyclePhase.BLOCKED
    assert decision.run.blocked is not None
    assert "out-of-scope" in decision.run.blocked.reason
    assert "secrets/leak.txt" in decision.run.blocked.detail.get("out_of_scope", "")


def test_pi_in_scope_changed_paths_advances() -> None:
    adapter = _adapter(changed=("src/feature.py",))
    decision = LifecycleAgentRunner(runtime=adapter).run(
        _run(),
        AgentRunnerInput(
            request=_request(),
            target_phase=LifecyclePhase.QA_REVIEW,
            current_step="implementation",
        ),
    )

    assert decision.accepted is True
    assert decision.run.phase is LifecyclePhase.QA_REVIEW
    assert decision.run.blocked is None
