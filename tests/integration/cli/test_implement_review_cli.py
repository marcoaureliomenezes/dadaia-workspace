"""v0.1.56 FR3 (T-56-30) — ``dadaia lifecycle implement-review`` CLI caller (AC-4(c)).

The loop verb is born resolver-governed: it resolves the ``implementation`` workflow snapshot
through the shared ``WorkflowExecutionPolicyResolver``, applies it to the implement + review
steps, and freezes it onto the run before step 1 (LAW 7). Under ``--harness fake`` a driving
fake returns an APPROVED in-scope handoff so the loop reaches COMPLETED; a scripted all-REJECTED
runtime (injected at the module-level ``_implement_review_runtime_factory`` seam) exhausts the
bounded retry budget and BLOCKS. Each drive persists a resolver-derived
``LifecycleRun.workflow_policy`` snapshot in the run-store record (extends the W1 AC-1 channel).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import pytest
import typer
from typer.testing import CliRunner

from dadaia_workspace import container
from dadaia_workspace.cli.commands import lifecycle as lifecycle_cli
from dadaia_workspace.cli.commands.lifecycle import app as lifecycle_app
from dadaia_workspace.cli.main import app
from dadaia_workspace.core.models.lifecycle import (
    AgentRunRequest,
    AgentRunResult,
    AgentRunStatus,
    AgentRuntimeKind,
)
from dadaia_workspace.features.workspace.service import WorkspaceService
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
from dadaia_workspace.infrastructure.python_env import VenvPythonEnvironmentManager
from tests.helpers.golden_platform import norm_stderr

# _norm_stderr: consolidated into tests/helpers/golden_platform.norm_stderr (v0.1.64 FR1).


_runner = CliRunner()
_RELEASE = "v0.1.56"
_CONTEXT = "dadaia-workspace"


@pytest.fixture
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    WorkspaceService(
        public_assets=FileSystemPublicAssetManager(),
        python_env=VenvPythonEnvironmentManager(),
    ).init(tmp_path)
    monkeypatch.chdir(tmp_path)
    return tmp_path


@dataclass
class _RejectingRuntime:
    """A structurally-valid worker (in-scope artifact_ref) that always verdicts REJECTED.

    The review's REJECTED verdict drives the attempt ledger without ever blocking the loop
    structurally (populated ``artifact_refs`` pass the evidence-only gate), so the loop retries
    until the bounded budget is exhausted → BLOCK.
    """

    kind: AgentRuntimeKind
    received_requests: list[AgentRunRequest] = field(default_factory=list)

    def runtime_kind(self) -> AgentRuntimeKind:
        return self.kind

    def run(self, request: AgentRunRequest) -> AgentRunResult:
        self.received_requests.append(request)
        return AgentRunResult(
            status=AgentRunStatus.SUCCEEDED,
            summary="review verdict REJECTED",
            artifact_refs=(f".dadaia/handoff/{_CONTEXT}/impl.handoff.json",),
            structured_output={"verdict": "REJECTED"},
        )


def _assert_resolver_derived_snapshot(workspace_root: Path, run_id: str) -> None:
    """The persisted run carries a resolver-derived ``implementation`` snapshot (AC-1 channel)."""
    run = container.build_lifecycle_run_store(workspace_root).load(run_id)
    assert run is not None
    policy = run.workflow_policy
    assert policy is not None, "workflow_policy is None — implement-review is not resolver-governed"
    assert policy.workflow_id == "implementation"
    resolver = container.build_workflow_policy_resolver(workspace_root, context=_CONTEXT)
    expected = resolver.resolve("implementation", context="default")
    for label in ("implement", "review_qa"):
        entry = policy.step(label)
        exp = expected.step(label)
        assert entry is not None
        assert exp is not None
        assert (entry.harness, entry.model_profile, entry.model, entry.reasoning) == (
            exp.harness,
            exp.model_profile,
            exp.model,
            exp.reasoning,
        )
        # The governed harness is a real Layer-2 worker — never ``fake`` (fake is never resolved).
        assert entry.harness in {"codex", "pi"}


def test_implement_review_approved_round_completes_and_persists_snapshot(workspace: Path) -> None:
    """AC-4(c): an APPROVED round → COMPLETED, leaving a resolver-derived run-store snapshot."""
    result = _runner.invoke(
        app,
        [
            "lifecycle",
            "implement-review",
            "--skip-preflight",
            "--release-id",
            _RELEASE,
            "--run-id",
            "fr3-approved",
            "--harness",
            "fake",
            "--json",
        ],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["completed"] is True
    assert payload["final_verdict"] == "APPROVED"
    assert payload["attempts"] == 1
    _assert_resolver_derived_snapshot(workspace, "fr3-approved")


def test_implement_review_all_rejected_run_blocks_and_persists_snapshot(
    workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC-4(c): an all-REJECTED run → BLOCK (retry exhaustion), still leaving a snapshot."""
    rejecting = _RejectingRuntime(AgentRuntimeKind.FAKE)

    def _factory(workspace_root: Path, *, context: str) -> object:
        return lambda kind: rejecting

    monkeypatch.setattr(lifecycle_cli, "_implement_review_runtime_factory", _factory)

    result = _runner.invoke(
        app,
        [
            "lifecycle",
            "implement-review",
            "--skip-preflight",
            "--release-id",
            _RELEASE,
            "--run-id",
            "fr3-rejected",
            "--harness",
            "fake",
            "--max-review-retries",
            "1",
            "--json",
        ],
    )
    assert result.exit_code == 3, result.output
    payload = json.loads(result.stdout)
    assert payload["completed"] is False
    assert payload["blocked"] is not None
    assert "bounded retry" in payload["blocked"]["reason"]
    assert payload["rounds"] and all(r["review_verdict"] == "REJECTED" for r in payload["rounds"])
    # The snapshot-freezing wiring ran (only the runtime factory was injected) → snapshot persists.
    _assert_resolver_derived_snapshot(workspace, "fr3-rejected")


def test_implement_review_is_a_registered_verb() -> None:
    """AC-4(c): the verb is registered on the lifecycle app."""
    registered = set(typer.main.get_command(lifecycle_app).commands)
    assert "implement-review" in registered


def test_implement_review_rejects_raw_step_model(workspace: Path) -> None:
    """AC-2(iii) parity: a raw ``--step-model label=<id>:<effort>`` is a D-3 rejection."""
    result = _runner.invoke(
        app,
        [
            "lifecycle",
            "implement-review",
            "--skip-preflight",
            "--release-id",
            _RELEASE,
            "--harness",
            "fake",
            "--step-model",
            "implement=gpt-5.5:high",
        ],
    )
    assert result.exit_code != 0
    assert "profile id" in result.output


def test_implement_review_model_flag_is_removed(workspace: Path) -> None:
    """v0.1.57 FR6 (inverted from the v0.1.56 non-fatal-deprecation case): ``--model`` is now
    an UNKNOWN option — exit 2 + ``No such option: --model`` on stderr + empty stdout (Q4)."""
    result = _runner.invoke(
        app,
        [
            "lifecycle",
            "implement-review",
            "--skip-preflight",
            "--release-id",
            _RELEASE,
            "--harness",
            "fake",
            "--model",
            "anything:high",
            "--json",
        ],
    )
    assert result.exit_code == 2
    assert "No such option: --model" in norm_stderr(result.stderr)
    assert result.stdout == ""
