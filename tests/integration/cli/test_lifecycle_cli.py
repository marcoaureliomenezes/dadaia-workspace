"""Integration tests for the lifecycle CLI command group."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

import dadaia_workspace.container as container
from dadaia_workspace.cli.commands.lifecycle import _phase_step_prompt
from dadaia_workspace.cli.main import app
from dadaia_workspace.core.models.lifecycle import (
    AgentRunResult,
    AgentRunStatus,
    LifecyclePhase,
    LifecycleRunStatus,
)
from dadaia_workspace.features.lifecycle.phase_workflow import LifecyclePhaseWorkflow
from dadaia_workspace.features.workspace.service import WorkspaceService
from dadaia_workspace.infrastructure.fake_runtime import FakeAgentRuntime
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
from dadaia_workspace.infrastructure.python_env import VenvPythonEnvironmentManager

_runner = CliRunner()


def _init_workspace(path: Path) -> Path:
    WorkspaceService(
        public_assets=FileSystemPublicAssetManager(),
        python_env=VenvPythonEnvironmentManager(),
    ).init(path)
    return path


def test_lifecycle_help_exposes_required_command_group() -> None:
    result = _runner.invoke(app, ["lifecycle", "--help"])

    assert result.exit_code == 0, result.output
    for command in (
        "status",
        "preflight",
        "hygiene",
        "report",
        "resume",
        "backlog",
        "release",
        "implement",
        "review",
        "close",
    ):
        assert command in result.output


def test_lifecycle_hygiene_help_exposes_status_and_clean() -> None:
    result = _runner.invoke(app, ["lifecycle", "hygiene", "--help"])

    assert result.exit_code == 0, result.output
    assert "status" in result.output
    assert "clean" in result.output


def test_lifecycle_review_help_exposes_review_gates() -> None:
    result = _runner.invoke(app, ["lifecycle", "review", "--help"])

    assert result.exit_code == 0, result.output
    assert "qa" in result.output
    assert "security" in result.output
    assert "code" in result.output


def test_lifecycle_preflight_uses_blocked_exit_code(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = _init_workspace(tmp_path)
    monkeypatch.chdir(workspace)

    result = _runner.invoke(app, ["lifecycle", "preflight"])

    assert result.exit_code == 3
    assert "BLOCKED" in result.output


def test_lifecycle_status_uses_ok_exit_code(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace = _init_workspace(tmp_path)
    monkeypatch.chdir(workspace)

    result = _runner.invoke(app, ["lifecycle", "status"])

    assert result.exit_code == 0, result.output
    assert "OK" in result.output


def test_lifecycle_status_no_args_uses_bounded_run_store_not_hygiene_scan(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace = _init_workspace(tmp_path)
    monkeypatch.chdir(workspace)

    def fail_hygiene(*args: object, **kwargs: object) -> object:
        raise AssertionError("top-level lifecycle status must not run hygiene scan")

    monkeypatch.setattr(container, "build_lifecycle_hygiene_service", fail_hygiene)

    result = _runner.invoke(app, ["lifecycle", "status", "--json"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload == {
        "blocked": 0,
        "completed": 0,
        "run_count": 0,
        "running": 0,
        "status": "OK",
    }


def test_successful_single_step_review_persists_completed_run_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace = _init_workspace(tmp_path)
    monkeypatch.chdir(workspace)
    approving_runtime = FakeAgentRuntime(
        result=AgentRunResult(
            status=AgentRunStatus.SUCCEEDED,
            summary="approved",
            artifact_refs=(".dadaia/handoff/dadaia-workspace/security.handoff.json",),
            structured_output={"verdict": "APPROVED"},
        ),
    )

    def build_phase_workflow(*args: object, **kwargs: object) -> LifecyclePhaseWorkflow:
        return LifecyclePhaseWorkflow(
            runtime=approving_runtime,
            run_store=container.build_lifecycle_run_store(workspace),
        )

    monkeypatch.setattr(container, "build_lifecycle_phase_workflow", build_phase_workflow)

    result = _runner.invoke(
        app,
        [
            "lifecycle",
            "review",
            "security",
            "--release-id",
            "v9.9.9",
            "--run-id",
            "security-review-completes",
            "--harness",
            "fake",
            "--json",
        ],
    )

    assert result.exit_code == 0, result.output
    run = container.build_lifecycle_run_store(workspace).load("security-review-completes")
    assert run is not None
    assert run.status is LifecycleRunStatus.COMPLETED
    assert run.blocked is None


def test_lifecycle_close_fake_harness_emits_evidence_and_advances(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Regression — bug ``lifecycle-close-fake-harness-blocks-on-missing-artifact-evidence``.

    The close step is a create step (target phase CLOSURE), so without an emitted artifact
    the default FAKE runtime fell through to a no-op result and the step blocked on
    "agent result missing artifact evidence". The FAKE closure writer must now emit a
    closure handoff so the evidence gate passes and ``lifecycle close --harness fake``
    advances to CLOSURE. Runs against the REAL default ``FakeAgentRuntime`` (no injected
    result) so it genuinely exercises the writer.
    """
    workspace = _init_workspace(tmp_path)
    monkeypatch.chdir(workspace)

    result = _runner.invoke(
        app,
        [
            "lifecycle",
            "close",
            "--release-id",
            "v9.9.9",
            "--run-id",
            "close-fake-advances",
            "--harness",
            "fake",
            "--json",
        ],
    )

    assert result.exit_code == 0, result.output
    run = container.build_lifecycle_run_store(workspace).load("close-fake-advances")
    assert run is not None
    assert run.status is LifecycleRunStatus.COMPLETED
    assert run.blocked is None
    assert run.phase is LifecyclePhase.CLOSURE
    closure_handoffs = list(
        (workspace / ".dadaia" / "handoff" / "dadaia-workspace").glob("*-fake-closure.handoff.json")
    )
    assert closure_handoffs, "FAKE close step must write a closure handoff artifact"


def test_review_phase_prompt_requires_exact_full_commit_sha() -> None:
    sha = "d9f1d81c686f4aea5a60d16722d72b86457b7896"

    prompt = _phase_step_prompt(
        "security",
        "v9.9.9",
        "dadaia-workspace",
        LifecyclePhase.SECURITY_REVIEW,
        commit_sha=sha,
    )

    assert "metrics.commit_sha" in prompt
    assert sha in prompt
    assert "Do not abbreviate it" in prompt


def test_lifecycle_usage_error_uses_typer_exit_code() -> None:
    result = _runner.invoke(app, ["lifecycle", "resume"])

    assert result.exit_code == 2


def test_lifecycle_resume_missing_uses_internal_error_exit_code(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = _init_workspace(tmp_path)
    monkeypatch.chdir(workspace)

    result = _runner.invoke(app, ["lifecycle", "resume", "missing"])

    assert result.exit_code == 1
    assert "INTERNAL_ERROR" in result.output


# ---------------------------------------------------------------------------
# WS-2 (T-24-06) — LAW 1 harness restriction + LAW 2 discrete model validation
# ---------------------------------------------------------------------------


def test_lifecycle_implement_rejects_claude_harness_with_layer1_pointer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """LAW 1: ``--harness claude`` is rejected, pointing to Layer-1 use."""
    workspace = _init_workspace(tmp_path)
    monkeypatch.chdir(workspace)

    result = _runner.invoke(
        app,
        ["lifecycle", "implement", "--release-id", "v0.1.24", "--harness", "claude"],
    )

    assert result.exit_code != 0
    assert "Layer-1" in result.output
    assert "pi or codex" in result.output


def test_lifecycle_implement_rejects_invalid_model_with_valid_set(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """LAW 2: an invalid ``(harness, model)`` pair lists the harness's valid options."""
    workspace = _init_workspace(tmp_path)
    monkeypatch.chdir(workspace)

    result = _runner.invoke(
        app,
        [
            "lifecycle",
            "implement",
            "--release-id",
            "v0.1.24",
            "--harness",
            "codex",
            "--model",
            "gpt-9.9:high",
        ],
    )

    assert result.exit_code != 0
    assert "gpt-5.5:high" in result.output
    assert "gpt-5.5:medium" in result.output


def test_lifecycle_implement_rejects_claude_step_harness_in_pipeline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """LAW 1: ``--step-harness label=claude`` is rejected in the pipeline too."""
    workspace = _init_workspace(tmp_path)
    monkeypatch.chdir(workspace)

    result = _runner.invoke(
        app,
        [
            "lifecycle",
            "pipeline",
            "--release-id",
            "v0.1.24",
            "--step-harness",
            "implement=claude",
        ],
    )

    assert result.exit_code != 0
    assert "Layer-1" in result.output


def test_claude_sdk_adapter_remains_importable_and_enum_value_kept() -> None:
    """LAW 1 keeps the CLAUDE_SDK adapter + enum value in code (Layer-1 unaffected)."""
    from dadaia_workspace.core.models.lifecycle import AgentRuntimeKind
    from dadaia_workspace.infrastructure.claude_sdk_runtime import ClaudeSdkAdapter

    assert AgentRuntimeKind.CLAUDE_SDK.value == "claude_sdk"
    adapter = ClaudeSdkAdapter(cwd=Path("/tmp"))
    assert adapter.runtime_kind() is AgentRuntimeKind.CLAUDE_SDK


def test_claude_not_a_workflow_harness_choice() -> None:
    """LAW 1: ``claude`` is not in the Layer-2 workflow harness set."""
    from dadaia_workspace.cli.commands.lifecycle import _HARNESS_KINDS

    assert "claude" not in _HARNESS_KINDS
    assert set(_HARNESS_KINDS) == {"fake", "codex", "pi"}
