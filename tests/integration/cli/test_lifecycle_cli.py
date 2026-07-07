"""Integration tests for the lifecycle CLI command group."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app
from dadaia_workspace.features.workspace.service import WorkspaceService
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
from dadaia_workspace.infrastructure.python_env import VenvPythonEnvironmentManager
from tests.helpers.golden_platform import norm_stderr

# _norm_stderr: consolidated into tests/helpers/golden_platform.norm_stderr (v0.1.64 FR1).


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


def test_lifecycle_implement_rejects_raw_step_model_and_unknown_model(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """v0.1.57 FR6 (the (b) clause inverted from the v0.1.56 non-fatal-deprecation case):

    (a) ``--step-model implement=<id>:<effort>`` (a raw model string) is STILL rejected as a
        D-3 profile-id violation (KEPT); (b) ``--model`` is now an UNKNOWN option — exit 2 +
        ``No such option: --model`` on stderr + empty stdout (Q4), not a deprecation warning.
    """
    workspace = _init_workspace(tmp_path)
    monkeypatch.chdir(workspace)

    # (a) raw --step-model is a D-3 rejection (profile ids only) — UNCHANGED.
    raw = _runner.invoke(
        app,
        [
            "lifecycle",
            "implement",
            "--release-id",
            "v0.1.24",
            "--harness",
            "codex",
            "--step-model",
            "implement=gpt-5.5:high",
        ],
    )
    assert raw.exit_code != 0
    assert "profile id" in raw.output

    # (b) --model is hard-removed — an unknown-option UsageError on stderr, exit 2, empty stdout.
    dep = _runner.invoke(
        app,
        [
            "lifecycle",
            "implement",
            "--release-id",
            "v0.1.24",
            "--harness",
            "fake",
            "--model",
            "anything:high",
        ],
    )
    assert dep.exit_code == 2
    assert "No such option: --model" in norm_stderr(dep.stderr)
    assert dep.stdout == ""


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
