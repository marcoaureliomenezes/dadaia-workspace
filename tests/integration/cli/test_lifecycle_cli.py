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


# ---------------------------------------------------------------------------
# v0.1.64 FR3 (AC-3/AC-4) — entry-harness auto-default on a single-step verb.
# ---------------------------------------------------------------------------

_AUTO_ECHO_PI = "[harness] auto-default: pi (from entry session; pass --harness to override)"


def _inject_pi_stream(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fake the ``pi --mode json`` subprocess + git seam — no real binary, no credits."""
    import json as _json
    import subprocess as _subprocess

    events = [
        {"type": "message_start"},
        {
            "type": "message_end",
            "message": {"role": "assistant", "content": "step executed via injected pi stream"},
        },
    ]
    stdout = "\n".join(_json.dumps(event) for event in events) + "\n"

    def fake_pi_run(args: object, **kwargs: object) -> _subprocess.CompletedProcess[str]:
        return _subprocess.CompletedProcess(args=args, returncode=0, stdout=stdout, stderr="")

    monkeypatch.setattr("dadaia_workspace.infrastructure.pi_runtime.subprocess.run", fake_pi_run)
    monkeypatch.setattr(
        "dadaia_workspace.infrastructure.git_subprocess.GitSubprocessClient.diff_name_only",
        lambda self, path: (),
    )


def test_implement_defaults_fake_silently_with_no_entry_signal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC-3: no --harness + no entry signal ⇒ fake, NO echo (behavior unchanged)."""
    import json as _json

    workspace = _init_workspace(tmp_path)
    monkeypatch.chdir(workspace)

    result = _runner.invoke(
        app, ["lifecycle", "implement", "--release-id", "multiharness-engine-v0116", "--json"]
    )

    assert result.exit_code == 3, result.output
    payload = _json.loads(result.output)
    assert payload["runtime"] == "fake"
    assert "[harness] auto-default:" not in result.stderr


def test_implement_auto_defaults_pi_from_entry_pin_with_loud_echo(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC-3: DADAIA_ENTRY_HARNESS=pi + no --harness ⇒ pi worker + the loud echo.

    Only the pi subprocess stream is injected (no real binary, no credits); the engine
    records the step runtime as ``pi_headless`` — proof the auto-default reached the
    real adapter path, not just the resolver.
    """
    import json as _json

    _inject_pi_stream(monkeypatch)
    workspace = _init_workspace(tmp_path)
    monkeypatch.chdir(workspace)
    monkeypatch.setenv("DADAIA_ENTRY_HARNESS", "pi")

    result = _runner.invoke(
        app, ["lifecycle", "implement", "--release-id", "multiharness-engine-v0116", "--json"]
    )

    assert result.exit_code == 3, result.output
    payload = _json.loads(result.stdout)
    assert payload["runtime"] == "pi_headless"
    # AC-9 sabotage (d): dropping the loud echo fails exactly here.
    assert _AUTO_ECHO_PI in result.stderr
    # --json stdout stays pure JSON — the echo rides stderr.
    # result.output is the COMBINED stream (Click 8.2+); stdout stays pure JSON.
    assert "[harness]" not in result.stdout


def test_implement_explicit_fake_wins_over_entry_pin_no_echo(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC-3: explicit --harness fake always wins — no auto-default, no echo."""
    import json as _json

    workspace = _init_workspace(tmp_path)
    monkeypatch.chdir(workspace)
    monkeypatch.setenv("DADAIA_ENTRY_HARNESS", "pi")

    result = _runner.invoke(
        app,
        [
            "lifecycle",
            "implement",
            "--release-id",
            "multiharness-engine-v0116",
            "--harness",
            "fake",
            "--json",
        ],
    )

    assert result.exit_code == 3, result.output
    payload = _json.loads(result.stdout)
    assert payload["runtime"] == "fake"
    assert "[harness] auto-default:" not in result.stderr


def test_implement_envelope_hermetic_against_developer_codex_session(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC-4: a simulated developer CODEX_SESSION_ID + the shared envelope scrub still
    resolves ``fake`` — a defaulted test can never spawn a real worker."""
    import json as _json

    from tests.fixtures.harness_env import scrub_entry_signal_env

    workspace = _init_workspace(tmp_path)
    monkeypatch.chdir(workspace)
    monkeypatch.setenv("CODEX_SESSION_ID", "developer-codex-tui-sess")
    scrub_entry_signal_env(monkeypatch)

    result = _runner.invoke(
        app, ["lifecycle", "implement", "--release-id", "multiharness-engine-v0116", "--json"]
    )

    assert result.exit_code == 3, result.output
    payload = _json.loads(result.output)
    assert payload["runtime"] == "fake"
    assert "[harness] auto-default:" not in result.stderr


def test_implement_help_text_names_auto_default() -> None:
    """FR3: the --harness help names the auto sentinel + the Layer-1 claude exclusion."""
    result = _runner.invoke(app, ["lifecycle", "implement", "--help"])

    assert result.exit_code == 0, result.output
    # Strip Rich box glyphs + collapse whitespace so the assert survives help wrapping.
    normalized = " ".join("".join(" " if ch in "│╭╮╰╯─" else ch for ch in result.output).split())
    assert "auto (entry session)" in normalized
