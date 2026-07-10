"""Integration tests for the lifecycle CLI command group.

Merged per plan-integration.md (18 -> 3): keep resume-still-blocked (real reason
surfaced, exit != 0); merge exit-code matrix (preflight 3 / status 0 / usage 2 /
resume-missing 1 / resume-ok 0 — absorbs the skeletons file's resume-ok test) -> 1;
merge auto-default (no-signal->fake-silent + entry-pin->pi_headless+loud echo +
explicit-wins + hermetic scrub, injected pi stream shared) -> 1. Deleted: 3 --help
greps, LAW1 claude dupes (owned by the policy matrix), claude-adapter-importable +
_HARNESS_KINDS (unit-ownable), --model dupe (owned by the AC-9 matrix), help-text
auto-default grep. Entry-harness auto-default echo (AC-9 sabotage anchor) kept.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app
from dadaia_workspace.features.workspace.service import WorkspaceService
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
from dadaia_workspace.infrastructure.python_env import VenvPythonEnvironmentManager

_runner = CliRunner()


def _init_workspace(path: Path) -> Path:
    WorkspaceService(
        public_assets=FileSystemPublicAssetManager(),
        python_env=VenvPythonEnvironmentManager(),
    ).init(path)
    return path


# ---------------------------------------------------------------------------
# T-66-07 (FR6) — AC6(repro): resume exits non-zero and surfaces the real
# blocked reason for a still-blocked run instead of lying "OK resumed".
# ---------------------------------------------------------------------------


def test_lifecycle_resume_cli_exits_nonzero_on_still_blocked_run(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC6(repro): drives the real ``dadaia lifecycle resume <run_id>`` CLI against a
    fixture run persisted with status=BLOCKED. On current code this exits 0 with
    "OK resumed <id>"; after the fix it exits non-zero and the output carries the
    run's real blocked.reason."""
    from dadaia_workspace.core.models.lifecycle import (
        BlockedState,
        LifecyclePhase,
        LifecycleRun,
        LifecycleRunStatus,
    )
    from dadaia_workspace.infrastructure.json_lifecycle_run_store import (
        JsonLifecycleRunStore,
    )

    workspace = _init_workspace(tmp_path)
    monkeypatch.chdir(workspace)

    real_reason = "agent result missing artifact evidence"
    run = LifecycleRun(
        run_id="run-blocked-1",
        context="dadaia-workspace",
        release_id="v0.1.66",
        command="implement",
        phase=LifecyclePhase.IMPLEMENTATION,
        status=LifecycleRunStatus.BLOCKED,
        current_step="implement",
        blocked=BlockedState(reason=real_reason, blocked_at_step="implement"),
    )
    JsonLifecycleRunStore(workspace).save(run)

    result = _runner.invoke(app, ["lifecycle", "resume", "run-blocked-1"])

    assert result.exit_code != 0, result.output
    assert real_reason in result.output


# ---------------------------------------------------------------------------
# Exit-code matrix: preflight 3 / status 0 / usage 2 / resume-missing 1 /
# resume-ok 0 (absorbs the command-skeletons file's resume-ok test).
# ---------------------------------------------------------------------------


def test_lifecycle_exit_code_matrix(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    workspace = _init_workspace(tmp_path)
    monkeypatch.chdir(workspace)

    preflight_result = _runner.invoke(app, ["lifecycle", "preflight"])
    assert preflight_result.exit_code == 3
    assert "BLOCKED" in preflight_result.output

    status_result = _runner.invoke(app, ["lifecycle", "status"])
    assert status_result.exit_code == 0, status_result.output
    assert "OK" in status_result.output

    usage_result = _runner.invoke(app, ["lifecycle", "resume"])
    assert usage_result.exit_code == 2

    resume_missing_result = _runner.invoke(app, ["lifecycle", "resume", "missing"])
    assert resume_missing_result.exit_code == 1
    assert "INTERNAL_ERROR" in resume_missing_result.output

    from dadaia_workspace.core.models.lifecycle import (
        LifecyclePhase,
        LifecycleRun,
        LifecycleRunStatus,
    )
    from dadaia_workspace.infrastructure.json_lifecycle_run_store import (
        JsonLifecycleRunStore,
    )

    JsonLifecycleRunStore(workspace).save(
        LifecycleRun(
            run_id="run-ok",
            context="dadaia-workspace",
            release_id="v0.1.15",
            command="implement",
            phase=LifecyclePhase.IMPLEMENTATION,
            status=LifecycleRunStatus.BLOCKED,
            current_step="preflight",
            expected_artifacts=(),
            idempotency_key="idem-run-ok",
        )
    )
    resume_ok_result = _runner.invoke(app, ["lifecycle", "resume", "run-ok"])
    assert resume_ok_result.exit_code == 0, resume_ok_result.output
    assert resume_ok_result.output.strip() == "OK resumed run-ok"


# ---------------------------------------------------------------------------
# v0.1.64 FR3 (AC-3/AC-4) — entry-harness auto-default on a single-step verb.
# ---------------------------------------------------------------------------

_AUTO_ECHO_PI = "[harness] auto-default: pi (from entry session; pass --harness to override)"


def _inject_pi_stream(monkeypatch: pytest.MonkeyPatch) -> list[object]:
    """Fake the ``pi --mode json`` subprocess + git seam — no real binary, no credits.

    v0.1.67 FR2 (T-67-07, F2 correction): migrated from the broken
    ``monkeypatch.setattr(".pi_runtime.subprocess.run", ...)`` pattern (the
    single-step-verb sibling of the pipeline-level false positive T-67-05 fixed) to
    the established constructor-injection pattern (patches
    ``container.build_agent_runtime``'s ``PI_HEADLESS`` branch). Returns the ``calls``
    call-recorder list so callers can assert the fake was genuinely invoked.
    """
    import json as _json
    import subprocess as _subprocess

    from dadaia_workspace import container
    from dadaia_workspace.infrastructure.git_subprocess import GitSubprocessClient
    from dadaia_workspace.infrastructure.pi_runtime import PiHeadlessAdapter, PiHeadlessConfig

    events = [
        {"type": "message_start"},
        {
            "type": "message_end",
            "message": {"role": "assistant", "content": "step executed via injected pi stream"},
        },
    ]
    stdout = "\n".join(_json.dumps(event) for event in events) + "\n"

    calls: list[object] = []

    def fake_pi_run(args: object, **kwargs: object) -> _subprocess.CompletedProcess[str]:
        calls.append(args)
        return _subprocess.CompletedProcess(args=args, returncode=0, stdout=stdout, stderr="")

    monkeypatch.setattr(
        "dadaia_workspace.infrastructure.git_subprocess.GitSubprocessClient.diff_name_only",
        lambda self, path: (),
    )

    real_build_agent_runtime = container.build_agent_runtime

    def patched_build_agent_runtime(
        kind: object, *, cwd: Path | None = None, model: object = None
    ) -> object:
        from dadaia_workspace.core.models.lifecycle import AgentRuntimeKind

        if kind is AgentRuntimeKind.PI_HEADLESS:
            run_dir = cwd or Path.cwd()
            pi_config = PiHeadlessConfig(cwd=run_dir)
            return PiHeadlessAdapter(
                pi_config, runner=fake_pi_run, environ={}, git=GitSubprocessClient()
            )
        return real_build_agent_runtime(kind, cwd=cwd, model=model)

    monkeypatch.setattr(container, "build_agent_runtime", patched_build_agent_runtime)

    return calls


def test_implement_entry_harness_auto_default_matrix(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC-3/AC-4: no-signal defaults fake silently; DADAIA_ENTRY_HARNESS=pi auto-defaults
    to pi with the loud echo (injected pi stream proves it reached the real adapter
    path); an explicit --harness always wins over the entry pin, no echo; and a
    simulated developer CODEX_SESSION_ID is scrubbed hermetically back to fake."""
    import json as _json

    # (a) no --harness + no entry signal => fake, no echo.
    no_signal_ws = _init_workspace(tmp_path / "no-signal")
    monkeypatch.chdir(no_signal_ws)
    no_signal_result = _runner.invoke(
        app, ["lifecycle", "implement", "--release-id", "multiharness-engine-v0116", "--json"]
    )
    assert no_signal_result.exit_code == 3, no_signal_result.output
    no_signal_payload = _json.loads(no_signal_result.output)
    assert no_signal_payload["runtime"] == "fake"
    assert "[harness] auto-default:" not in no_signal_result.stderr

    # (b) DADAIA_ENTRY_HARNESS=pi + no --harness => pi worker + the loud echo.
    entry_pin_ws = _init_workspace(tmp_path / "entry-pin")
    calls = _inject_pi_stream(monkeypatch)
    monkeypatch.chdir(entry_pin_ws)
    monkeypatch.setenv("DADAIA_ENTRY_HARNESS", "pi")
    entry_pin_result = _runner.invoke(
        app, ["lifecycle", "implement", "--release-id", "multiharness-engine-v0116", "--json"]
    )
    assert entry_pin_result.exit_code == 3, entry_pin_result.output
    entry_pin_payload = _json.loads(entry_pin_result.stdout)
    assert len(calls) == 1, "the faked pi subprocess seam must be invoked exactly once"
    assert entry_pin_payload["runtime"] == "pi_headless"
    # AC-9 sabotage (d): dropping the loud echo fails exactly here.
    assert _AUTO_ECHO_PI in entry_pin_result.stderr
    # --json stdout stays pure JSON — the echo rides stderr.
    assert "[harness]" not in entry_pin_result.stdout

    # (c) explicit --harness fake always wins over the entry pin — no auto-default, no echo.
    explicit_ws = _init_workspace(tmp_path / "explicit-wins")
    monkeypatch.chdir(explicit_ws)
    monkeypatch.setenv("DADAIA_ENTRY_HARNESS", "pi")
    explicit_result = _runner.invoke(
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
    assert explicit_result.exit_code == 3, explicit_result.output
    explicit_payload = _json.loads(explicit_result.stdout)
    assert explicit_payload["runtime"] == "fake"
    assert "[harness] auto-default:" not in explicit_result.stderr

    # (d) AC-4: a simulated developer CODEX_SESSION_ID + the shared envelope scrub still
    # resolves fake — a defaulted test can never spawn a real worker.
    from tests.fixtures.harness_env import scrub_entry_signal_env

    hermetic_ws = _init_workspace(tmp_path / "hermetic-scrub")
    monkeypatch.chdir(hermetic_ws)
    monkeypatch.setenv("CODEX_SESSION_ID", "developer-codex-tui-sess")
    scrub_entry_signal_env(monkeypatch)
    hermetic_result = _runner.invoke(
        app, ["lifecycle", "implement", "--release-id", "multiharness-engine-v0116", "--json"]
    )
    assert hermetic_result.exit_code == 3, hermetic_result.output
    hermetic_payload = _json.loads(hermetic_result.output)
    assert hermetic_payload["runtime"] == "fake"
    assert "[harness] auto-default:" not in hermetic_result.stderr
