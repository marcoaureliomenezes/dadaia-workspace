"""Integration proof: `dadaia lifecycle pipeline` runs the multi-step engine end-to-end."""

from __future__ import annotations

import json
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


def test_pipeline_runs_engine_and_blocks_at_first_step_on_fake(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = _init_workspace(tmp_path)
    monkeypatch.chdir(workspace)

    result = _runner.invoke(
        app,
        [
            "lifecycle",
            "pipeline",
            "--release-id",
            "multiharness-engine-v0116",
            "--run-id",
            "pipe-it",
            "--harness",
            "fake",
            "--step-harness",
            "review_qa=codex",
            "--json",
        ],
    )

    assert result.exit_code == 3, result.output
    payload = json.loads(result.output)
    assert payload["status"] == "BLOCKED"
    assert payload["completed"] is False
    # First step ran the engine on the fake harness and blocked on the missing verdict.
    assert payload["steps"][0]["label"] == "implement"
    assert payload["steps"][0]["runtime"] == "fake"
    assert payload["steps"][0]["accepted"] is False
    # The per-step override was accepted by the CLI (parsing path exercised).
    assert payload["blocked"]["reason"]


def test_pipeline_runs_first_step_on_pi_harness_end_to_end(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Layer-2 e2e: `--harness pi` resolves through the CLI to a real
    ``PiHeadlessAdapter`` built by ``container.build_agent_runtime``, which parses a
    genuine ``pi --mode json`` event stream. Only the ``pi`` subprocess and the git
    seam are faked — no real binary, no network, no credits. The engine must record
    the step runtime as ``pi_headless`` and block on the missing verdict (proving the
    PI worker actually ran and its output flowed through the gate)."""
    import subprocess as _subprocess

    # A genuine line-delimited pi --mode json stream whose terminal assistant message
    # carries plain text (no APPROVED verdict) -> the implement gate blocks.
    events = [
        {"type": "message_start"},
        {
            "type": "message_end",
            "message": {
                "role": "assistant",
                "content": "implementation step executed via injected pi stream",
            },
        },
    ]
    stdout = "\n".join(json.dumps(event) for event in events) + "\n"

    def fake_pi_run(args: object, **kwargs: object) -> _subprocess.CompletedProcess[str]:
        return _subprocess.CompletedProcess(args=args, returncode=0, stdout=stdout, stderr="")

    monkeypatch.setattr("dadaia_workspace.infrastructure.pi_runtime.subprocess.run", fake_pi_run)
    # Keep the Ring-2 git seam hermetic (no real repo in the temp workspace).
    monkeypatch.setattr(
        "dadaia_workspace.infrastructure.git_subprocess.GitSubprocessClient.diff_name_only",
        lambda self, path: (),
    )

    workspace = _init_workspace(tmp_path)
    monkeypatch.chdir(workspace)

    result = _runner.invoke(
        app,
        [
            "lifecycle",
            "pipeline",
            "--release-id",
            "multiharness-engine-v0116",
            "--run-id",
            "pipe-pi",
            "--harness",
            "pi",
            "--json",
        ],
    )

    assert result.exit_code == 3, result.output
    payload = json.loads(result.output)
    assert payload["status"] == "BLOCKED"
    assert payload["completed"] is False
    # The CLI resolved `--harness pi` -> PI_HEADLESS -> PiHeadlessAdapter, which ran
    # the injected stream; the engine recorded the worker runtime as pi_headless.
    assert payload["steps"][0]["label"] == "implement"
    assert payload["steps"][0]["runtime"] == "pi_headless"
    assert payload["steps"][0]["accepted"] is False
    assert payload["blocked"]["reason"]


# ---------------------------------------------------------------------------
# v0.1.64 FR3 (AC-3) — entry-harness auto-default on the multi-step pipeline.
# ---------------------------------------------------------------------------


def test_pipeline_defaults_fake_silently_with_no_entry_signal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No --harness + no entry signal ⇒ the pipeline runs fake with NO echo."""
    workspace = _init_workspace(tmp_path)
    monkeypatch.chdir(workspace)

    result = _runner.invoke(
        app,
        [
            "lifecycle",
            "pipeline",
            "--release-id",
            "multiharness-engine-v0116",
            "--run-id",
            "pipe-auto-fake",
            "--json",
        ],
    )

    assert result.exit_code == 3, result.output
    payload = json.loads(result.output)
    assert payload["steps"][0]["runtime"] == "fake"
    assert "[harness] auto-default:" not in result.stderr


def test_pipeline_auto_defaults_pi_from_entry_pin_with_loud_echo(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """DADAIA_ENTRY_HARNESS=pi (simulated PI entry session) + no --harness ⇒ the
    pipeline's first step runs on the real PI adapter path (injected stream — no
    binary, no credits) and the loud FR3 echo rides stderr, keeping --json pure."""
    import subprocess as _subprocess

    events = [
        {"type": "message_start"},
        {
            "type": "message_end",
            "message": {"role": "assistant", "content": "pipeline step via injected pi stream"},
        },
    ]
    stdout = "\n".join(json.dumps(event) for event in events) + "\n"

    def fake_pi_run(args: object, **kwargs: object) -> _subprocess.CompletedProcess[str]:
        return _subprocess.CompletedProcess(args=args, returncode=0, stdout=stdout, stderr="")

    monkeypatch.setattr("dadaia_workspace.infrastructure.pi_runtime.subprocess.run", fake_pi_run)
    monkeypatch.setattr(
        "dadaia_workspace.infrastructure.git_subprocess.GitSubprocessClient.diff_name_only",
        lambda self, path: (),
    )
    workspace = _init_workspace(tmp_path)
    monkeypatch.chdir(workspace)
    monkeypatch.setenv("DADAIA_ENTRY_HARNESS", "pi")

    result = _runner.invoke(
        app,
        [
            "lifecycle",
            "pipeline",
            "--release-id",
            "multiharness-engine-v0116",
            "--run-id",
            "pipe-auto-pi",
            "--json",
        ],
    )

    assert result.exit_code == 3, result.output
    payload = json.loads(result.stdout)
    assert payload["steps"][0]["runtime"] == "pi_headless"
    assert (
        "[harness] auto-default: pi (from entry session; pass --harness to override)"
        in result.stderr
    )
    # result.output is the COMBINED stream (Click 8.2+); stdout stays pure JSON.
    assert "[harness]" not in result.stdout


# ---------------------------------------------------------------------------
# v0.1.66 Wave A — FR3/FR4/FR5 executed-path reproductions (T-66-01..T-66-03).
# ---------------------------------------------------------------------------


def test_pi_openrouter_kimi_profile_reaches_command_with_valid_id(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """T-66-01 (FR3, AC3(repro)): ``--step-model implement=pi-openrouter-kimi-high``
    must reach the real ``pi`` subprocess argv with a valid OpenRouter model id.

    Drives the real CLI (``--step-model`` parsing, the real
    ``WorkflowExecutionPolicyResolver``, ``apply_resolved_policy``, the real
    ``LifecyclePipeline``/``LifecycleAgentRunner``/``LifecycleStateMachine`` chain) end
    to end. Only the outermost I/O boundary is faked: ``container.build_agent_runtime``'s
    ``PI_HEADLESS`` branch is patched to inject ``runner=fake_pi_run`` at
    ``PiHeadlessAdapter`` CONSTRUCTION (the same seam ``test_pi_runner_ring2.py`` and
    ``test_codex_exec_runtime.py`` use), because ``PiHeadlessAdapter.__init__`` binds its
    ``runner`` default (``subprocess.run``) at class-definition time — a later
    ``monkeypatch.setattr("...pi_runtime.subprocess.run", ...)`` does not reach an
    already-bound default (registered as bug
    ``pi-executed-path-cli-tests-invoke-real-pi-binary``). Everything above the
    constructor call — ``_command``'s real argv assembly, the real ``.run()`` body, the
    real gate — still runs unmodified, so this proves the real command-construction
    path, not just the profile registry in isolation.
    """
    import subprocess as _subprocess

    from dadaia_workspace import container
    from dadaia_workspace.infrastructure.git_subprocess import GitSubprocessClient
    from dadaia_workspace.infrastructure.pi_runtime import PiHeadlessAdapter, PiHeadlessConfig

    captured: dict[str, list[str]] = {}

    events = [
        {"type": "message_start"},
        {
            "type": "message_end",
            "message": {"role": "assistant", "content": "implementation via kimi profile"},
        },
    ]
    stdout = "\n".join(json.dumps(event) for event in events) + "\n"

    def fake_pi_run(args: object, **kwargs: object) -> _subprocess.CompletedProcess[str]:
        assert isinstance(args, list)
        captured["argv"] = args
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
            pi_config = (
                PiHeadlessConfig(cwd=run_dir, model=model.model_id, reasoning_effort=model.effort)
                if model is not None
                else PiHeadlessConfig(cwd=run_dir)
            )
            return PiHeadlessAdapter(
                pi_config, runner=fake_pi_run, environ={}, git=GitSubprocessClient()
            )
        return real_build_agent_runtime(kind, cwd=cwd, model=model)

    monkeypatch.setattr(container, "build_agent_runtime", patched_build_agent_runtime)

    workspace = _init_workspace(tmp_path)
    monkeypatch.chdir(workspace)

    result = _runner.invoke(
        app,
        [
            "lifecycle",
            "pipeline",
            "--release-id",
            "multiharness-engine-v0116",
            "--run-id",
            "pipe-kimi",
            "--harness",
            "pi",
            "--step-model",
            "implement=pi-openrouter-kimi-high",
            "--json",
        ],
    )

    assert result.exit_code == 3, result.output
    argv = captured["argv"]
    assert "--model" in argv, argv
    model_value = argv[argv.index("--model") + 1]
    # AC3(repro): on current code this captures the invalid literal "kimi-2.7" (fails
    # OpenRouter's id contract); after the fix it must be the valid, namespaced id.
    assert model_value == "moonshotai/kimi-k2.5", (
        f"expected the valid OpenRouter id 'moonshotai/kimi-k2.5', got {model_value!r} "
        f"(full argv: {argv})"
    )


def _patch_build_agent_runtime_for_codex(
    monkeypatch: pytest.MonkeyPatch, fake_runner: object
) -> None:
    """Inject ``runner=fake_runner`` into the real ``CodexExecAdapter`` construction.

    ``CodexExecAdapter.__init__`` binds its ``runner`` default (``subprocess.run``) at
    class-definition time (same root cause as
    ``pi-executed-path-cli-tests-invoke-real-pi-binary``), so a plain
    ``monkeypatch.setattr("...codex_runtime.subprocess.run", fake)`` never reaches an
    already-constructed adapter. This patches ``container.build_agent_runtime``'s
    ``CODEX_EXEC`` branch to pass the fake explicitly at construction — the same seam
    ``test_codex_exec_runtime.py`` uses — while every other real code path (``_command``,
    ``.run()``, the full ``LifecyclePipeline``/gate chain) stays real and unfaked.
    """
    from pathlib import Path as _Path

    from dadaia_workspace import container
    from dadaia_workspace.infrastructure.codex_runtime import CodexExecAdapter, CodexExecConfig
    from dadaia_workspace.infrastructure.git_subprocess import GitSubprocessClient

    real_build_agent_runtime = container.build_agent_runtime

    def patched_build_agent_runtime(
        kind: object, *, cwd: _Path | None = None, model: object = None
    ) -> object:
        from dadaia_workspace.core.models.lifecycle import AgentRuntimeKind

        if kind is AgentRuntimeKind.CODEX_EXEC:
            run_dir = cwd or _Path.cwd()
            codex_config = (
                CodexExecConfig(cwd=run_dir, model=model.model_id, reasoning_effort=model.effort)
                if model is not None
                else CodexExecConfig(cwd=run_dir)
            )
            return CodexExecAdapter(
                codex_config,
                runner=fake_runner,
                git=GitSubprocessClient(),
            )
        return real_build_agent_runtime(kind, cwd=cwd, model=model)

    monkeypatch.setattr(container, "build_agent_runtime", patched_build_agent_runtime)


def test_codex_pipeline_untrusted_dir_no_longer_blocks_on_trust_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """T-66-02 (FR4, AC4(repro)): the real codex argv must carry
    ``--skip-git-repo-check`` alongside ``--ignore-user-config``, so a governed worker
    running in a directory codex does not auto-trust never fails codex's own trust
    check.

    Drives the real CLI (``--harness codex``), the real ``LifecyclePipeline``/gate
    chain, and the real ``CodexExecAdapter._command``/``.run()``. Only
    ``subprocess.run`` is faked (constructor-injected — see
    ``_patch_build_agent_runtime_for_codex``): the fake inspects the REAL captured argv
    and returns codex's real trust-error stderr whenever ``--skip-git-repo-check`` is
    absent, exactly reproducing the user-hit failure mode on current code.
    """
    import subprocess as _subprocess

    captured: dict[str, list[str]] = {}

    def fake_codex_run(args: object, **kwargs: object) -> _subprocess.CompletedProcess[str]:
        assert isinstance(args, list)
        captured["argv"] = args
        if "--skip-git-repo-check" not in args:
            return _subprocess.CompletedProcess(
                args=args,
                returncode=1,
                stdout="",
                stderr="Not inside a trusted directory and --skip-git-repo-check was "
                "not specified.",
            )
        # Fulfil the --output-last-message contract so a trusted run "succeeds" cleanly.
        output_path = Path(args[args.index("--output-last-message") + 1])
        output_path.write_text(
            json.dumps({"summary": "codex exec completed via injected runner"}),
            encoding="utf-8",
        )
        return _subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

    _patch_build_agent_runtime_for_codex(monkeypatch, fake_codex_run)
    monkeypatch.setattr(
        "dadaia_workspace.infrastructure.git_subprocess.GitSubprocessClient.diff_name_only",
        lambda self, path: (),
    )

    workspace = _init_workspace(tmp_path)
    monkeypatch.chdir(workspace)

    result = _runner.invoke(
        app,
        [
            "lifecycle",
            "pipeline",
            "--release-id",
            "multiharness-engine-v0116",
            "--run-id",
            "pipe-codex-trust",
            "--harness",
            "codex",
            "--json",
        ],
    )

    argv = captured["argv"]
    # AC4(repro): on current code the argv omits --skip-git-repo-check, so the fake
    # returns the real trust error and the pipeline blocks with that reason.
    assert "--skip-git-repo-check" in argv, (
        f"expected '--skip-git-repo-check' in the real codex argv, got {argv!r} — the "
        f"fake returned codex's trust error because the flag was absent"
    )
    # The step must not have blocked on the trust error once the flag reaches argv.
    payload = json.loads(result.output)
    reason = (payload.get("blocked") or {}).get("reason", "")
    assert "trusted directory" not in reason, (
        f"pipeline still blocked on the codex trust error: {reason!r} (argv={argv!r})"
    )


def test_codex_pipeline_sandbox_override_avoids_container_bwrap_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """T-66-03 (FR5, AC5(repro)): ``DADAIA_CODEX_SANDBOX=workspace-write`` must reach the
    real ``--sandbox`` argv, so a governed worker running inside a constrained container
    (no ``bwrap`` loopback network capability) never fails codex's own sandbox setup on
    the compiled-in ``read-only`` default.

    Drives the real CLI (``--harness codex``), the real ``LifecyclePipeline``/gate
    chain, and the real ``CodexExecAdapter._command``/``.run()``/``CodexExecConfig``
    construction (the single choke point that resolves the env override — architect
    finding MEDIUM-1). Only ``subprocess.run`` is faked (constructor-injected — see
    ``_patch_build_agent_runtime_for_codex``): the fake inspects the REAL captured argv
    and returns the real bwrap-failure stderr whenever ``--sandbox`` is ``read-only``,
    exactly reproducing the user-hit container failure mode on current code.
    """
    import subprocess as _subprocess

    captured: dict[str, list[str]] = {}

    def fake_codex_run(args: object, **kwargs: object) -> _subprocess.CompletedProcess[str]:
        assert isinstance(args, list)
        captured["argv"] = args
        sandbox_value = args[args.index("--sandbox") + 1] if "--sandbox" in args else None
        if sandbox_value == "read-only":
            return _subprocess.CompletedProcess(
                args=args,
                returncode=1,
                stdout="",
                stderr="bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted",
            )
        output_path = Path(args[args.index("--output-last-message") + 1])
        output_path.write_text(
            json.dumps({"summary": "codex exec completed via injected runner"}),
            encoding="utf-8",
        )
        return _subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

    _patch_build_agent_runtime_for_codex(monkeypatch, fake_codex_run)
    monkeypatch.setattr(
        "dadaia_workspace.infrastructure.git_subprocess.GitSubprocessClient.diff_name_only",
        lambda self, path: (),
    )
    monkeypatch.setenv("DADAIA_CODEX_SANDBOX", "workspace-write")

    workspace = _init_workspace(tmp_path)
    monkeypatch.chdir(workspace)

    result = _runner.invoke(
        app,
        [
            "lifecycle",
            "pipeline",
            "--release-id",
            "multiharness-engine-v0116",
            "--run-id",
            "pipe-codex-sandbox",
            "--harness",
            "codex",
            "--json",
        ],
    )

    argv = captured["argv"]
    # AC5(repro): on current code nothing reads DADAIA_CODEX_SANDBOX, so the argv still
    # carries read-only, the fake returns the real bwrap failure, and the pipeline
    # blocks on it.
    assert argv[argv.index("--sandbox") :][:2] == ["--sandbox", "workspace-write"], (
        f"expected '--sandbox workspace-write' in the real codex argv, got {argv!r} — "
        f"the fake returned the bwrap failure because the env override never reached argv"
    )
    payload = json.loads(result.output)
    reason = (payload.get("blocked") or {}).get("reason", "")
    assert "bwrap" not in reason, (
        f"pipeline still blocked on the container bwrap failure: {reason!r} (argv={argv!r})"
    )


def test_codex_pipeline_sandbox_default_stays_read_only_when_env_unset(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC5.2 regression guard, executed-path: with no env override, the real argv still
    carries the compiled-in `--sandbox read-only` default — no behavior change for the
    already-correct unset case."""
    import subprocess as _subprocess

    captured: dict[str, list[str]] = {}

    def fake_codex_run(args: object, **kwargs: object) -> _subprocess.CompletedProcess[str]:
        assert isinstance(args, list)
        captured["argv"] = args
        output_path = Path(args[args.index("--output-last-message") + 1])
        output_path.write_text(json.dumps({"summary": "codex exec completed"}), encoding="utf-8")
        return _subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

    _patch_build_agent_runtime_for_codex(monkeypatch, fake_codex_run)
    monkeypatch.setattr(
        "dadaia_workspace.infrastructure.git_subprocess.GitSubprocessClient.diff_name_only",
        lambda self, path: (),
    )
    monkeypatch.delenv("DADAIA_CODEX_SANDBOX", raising=False)

    workspace = _init_workspace(tmp_path)
    monkeypatch.chdir(workspace)

    _runner.invoke(
        app,
        [
            "lifecycle",
            "pipeline",
            "--release-id",
            "multiharness-engine-v0116",
            "--run-id",
            "pipe-codex-sandbox-default",
            "--harness",
            "codex",
            "--json",
        ],
    )

    argv = captured["argv"]
    assert argv[argv.index("--sandbox") :][:2] == ["--sandbox", "read-only"]
