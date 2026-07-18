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
    """The engine's evidence gate still blocks a NO-EVIDENCE worker result.

    v0.1.72 FR5: the PLAIN default fake now carries the driving APPROVED+evidence
    result (the smoke path completes), so this block-proof injects a SCRIPTED
    no-evidence fake through the preserved ``container.build_agent_runtime`` seam —
    the engine (not the fake) is what blocks at implement.
    """
    from dadaia_workspace import container
    from dadaia_workspace.core.models.lifecycle import (
        AgentRunResult,
        AgentRunStatus,
        AgentRuntimeKind,
    )
    from dadaia_workspace.infrastructure.fake_runtime import FakeAgentRuntime

    workspace = _init_workspace(tmp_path)
    monkeypatch.chdir(workspace)
    monkeypatch.setenv(
        "DADAIA_CONTEXT", "dadaia-workspace"
    )  # explicit rung (no first-ALIVE/terminal fallback)

    real_build = container.build_agent_runtime
    no_evidence = AgentRunResult(
        status=AgentRunStatus.SUCCEEDED,
        summary="worker produced no artifact evidence",
        artifact_refs=(),
    )

    def scripted(kind: AgentRuntimeKind, **kwargs: object) -> object:
        if kind is AgentRuntimeKind.FAKE:
            return FakeAgentRuntime(result=no_evidence)
        return real_build(kind, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(container, "build_agent_runtime", scripted)

    result = _runner.invoke(
        app,
        [
            "lifecycle",
            "implementation-reviews",
            "--skip-preflight",
            "--release-id",
            "v0.1.16",
            "--run-id",
            "pipe-it",
            "--harness",
            "fake",
            "--step-harness",
            "review_combined=codex",
            "--json",
        ],
    )

    assert result.exit_code == 3, result.output
    payload = json.loads(result.output)
    assert payload["status"] == "BLOCKED"
    assert payload["completed"] is False
    # First step ran the engine on the fake harness and blocked on the missing evidence.
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
    PI worker actually ran and its output flowed through the gate).

    v0.1.67 FR2 (F3-corrected idiom, T-67-05): rewritten from the pre-existing
    ``monkeypatch.setattr(".pi_runtime.subprocess.run", ...)`` pattern (false-positive
    bug ``pi-e2e-test-false-positive-loose-blocked-reason-assertion`` — a truthy-only
    ``assert payload["blocked"]["reason"]`` was equally satisfied by a real-binary auth
    failure) to the established constructor-injection pattern (belt-and-suspenders,
    independent of the FR1 mechanism fix — see
    ``test_pi_openrouter_kimi_profile_reaches_command_with_valid_id`` below for the same
    shape) plus a ``calls`` call-recorder that only the fake can populate.
    """
    import subprocess as _subprocess

    from dadaia_workspace import container
    from dadaia_workspace.infrastructure.git_subprocess import GitSubprocessClient
    from dadaia_workspace.infrastructure.pi_runtime import PiHeadlessAdapter, PiHeadlessConfig

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

    calls: list[object] = []

    def fake_pi_run(args: object, **kwargs: object) -> _subprocess.CompletedProcess[str]:
        calls.append(args)
        return _subprocess.CompletedProcess(args=args, returncode=0, stdout=stdout, stderr="")

    # Keep the Ring-2 git seam hermetic (no real repo in the temp workspace).
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

    workspace = _init_workspace(tmp_path)
    monkeypatch.chdir(workspace)
    monkeypatch.setenv(
        "DADAIA_CONTEXT", "dadaia-workspace"
    )  # explicit rung (no first-ALIVE/terminal fallback)

    result = _runner.invoke(
        app,
        [
            "lifecycle",
            "implementation-reviews",
            "--skip-preflight",
            "--release-id",
            "v0.1.16",
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
    # `calls` proves the FAKE was invoked — a real-binary run leaves this list empty
    # (F3 correction: the fake-derivation proof, not the fixed block-reason constant).
    assert len(calls) == 2, (
        "the faked pi subprocess seam must run once plus the bounded structural correction"
    )
    # The CLI resolved `--harness pi` -> PI_HEADLESS -> PiHeadlessAdapter, which ran
    # the injected stream; the engine recorded the worker runtime as pi_headless.
    assert payload["steps"][0]["label"] == "implement"
    assert payload["steps"][0]["runtime"] == "pi_headless"
    assert payload["steps"][0]["accepted"] is False
    # The create-step gate's fixed constant (agent_runner.py:220) — an honest
    # structural check, not a claimed fake-content anchor (F3 correction).
    assert payload["blocked"]["reason"] == "agent result missing artifact evidence"


# ---------------------------------------------------------------------------
# v0.1.66 Wave A — FR3/FR4/FR5 executed-path reproductions (T-66-01..T-66-03).
#
# Pipeline-specific entry-harness auto-default coverage is dropped here: the
# resolver + loud-echo mechanism is shared code and is already proven by the
# single-step verb's auto-default matrix (test_lifecycle_cli.py).
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
    monkeypatch.setenv(
        "DADAIA_CONTEXT", "dadaia-workspace"
    )  # explicit rung (no first-ALIVE/terminal fallback)

    result = _runner.invoke(
        app,
        [
            "lifecycle",
            "implementation-reviews",
            "--skip-preflight",
            "--release-id",
            "v0.1.16",
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


def test_codex_pipeline_trust_flag_and_sandbox_override_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """T-66-02/T-66-03 (FR4/FR5, AC4/AC5(repro)) + AC5.2 regression guard, merged: the
    real codex argv carries ``--skip-git-repo-check`` (so a governed worker running in
    a directory codex does not auto-trust never fails codex's own trust check);
    ``DADAIA_CODEX_SANDBOX=workspace-write`` reaches the real ``--sandbox`` argv (so a
    constrained container never fails codex's own sandbox setup on the compiled-in
    ``read-only`` default); and with no env override, the real argv still carries the
    compiled-in ``--sandbox read-only`` default.

    Drives the real CLI (``--harness codex``), the real ``LifecyclePipeline``/gate
    chain, and the real ``CodexExecAdapter._command``/``.run()``/``CodexExecConfig``
    construction (the single choke point that resolves the env override — architect
    finding MEDIUM-1). Only ``subprocess.run`` is faked (constructor-injected — see
    ``_patch_build_agent_runtime_for_codex``, shared across all three invocations): the
    fake inspects the REAL captured argv and returns codex's real trust-error /
    bwrap-failure stderr whenever the relevant flag is absent/wrong, exactly
    reproducing the user-hit failure modes on current code.
    """
    import subprocess as _subprocess

    def _fake_codex_run_factory(
        captured: dict[str, list[str]],
        *,
        reject_missing_skip_git_check: bool = False,
        reject_sandbox_read_only: bool = False,
    ):  # type: ignore[no-untyped-def]
        def fake_codex_run(args: object, **kwargs: object) -> _subprocess.CompletedProcess[str]:
            assert isinstance(args, list)
            captured["argv"] = args
            if reject_missing_skip_git_check and "--skip-git-repo-check" not in args:
                return _subprocess.CompletedProcess(
                    args=args,
                    returncode=1,
                    stdout="",
                    stderr="Not inside a trusted directory and --skip-git-repo-check was "
                    "not specified.",
                )
            if reject_sandbox_read_only:
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

        return fake_codex_run

    def _run_pipeline(workspace: Path, run_id: str):  # type: ignore[no-untyped-def]
        monkeypatch.chdir(workspace)
        monkeypatch.setenv("DADAIA_CONTEXT", "dadaia-workspace")  # explicit rung
        return _runner.invoke(
            app,
            [
                "lifecycle",
                "implementation-reviews",
                "--skip-preflight",
                "--release-id",
                "v0.1.16",
                "--run-id",
                run_id,
                "--harness",
                "codex",
                "--json",
            ],
        )

    monkeypatch.setattr(
        "dadaia_workspace.infrastructure.git_subprocess.GitSubprocessClient.diff_name_only",
        lambda self, path: (),
    )

    # (1) trust flag: AC4(repro).
    trust_captured: dict[str, list[str]] = {}
    _patch_build_agent_runtime_for_codex(
        monkeypatch,
        _fake_codex_run_factory(trust_captured, reject_missing_skip_git_check=True),
    )
    trust_ws = _init_workspace(tmp_path / "trust-case")
    trust_result = _run_pipeline(trust_ws, "pipe-codex-trust")
    trust_argv = trust_captured["argv"]
    assert "--skip-git-repo-check" in trust_argv, (
        f"expected '--skip-git-repo-check' in the real codex argv, got {trust_argv!r} — the "
        f"fake returned codex's trust error because the flag was absent"
    )
    trust_payload = json.loads(trust_result.output)
    trust_reason = (trust_payload.get("blocked") or {}).get("reason", "")
    assert "trusted directory" not in trust_reason, (
        f"pipeline still blocked on the codex trust error: {trust_reason!r} (argv={trust_argv!r})"
    )

    # (2) sandbox override: AC5(repro).
    sandbox_captured: dict[str, list[str]] = {}
    _patch_build_agent_runtime_for_codex(
        monkeypatch,
        _fake_codex_run_factory(sandbox_captured, reject_sandbox_read_only=True),
    )
    monkeypatch.setenv("DADAIA_CODEX_SANDBOX", "workspace-write")
    sandbox_ws = _init_workspace(tmp_path / "sandbox-override-case")
    sandbox_result = _run_pipeline(sandbox_ws, "pipe-codex-sandbox")
    sandbox_argv = sandbox_captured["argv"]
    assert sandbox_argv[sandbox_argv.index("--sandbox") :][:2] == [
        "--sandbox",
        "workspace-write",
    ], (
        f"expected '--sandbox workspace-write' in the real codex argv, got {sandbox_argv!r} — "
        f"the fake returned the bwrap failure because the env override never reached argv"
    )
    sandbox_payload = json.loads(sandbox_result.output)
    sandbox_reason = (sandbox_payload.get("blocked") or {}).get("reason", "")
    assert "bwrap" not in sandbox_reason, (
        f"pipeline still blocked on the container bwrap failure: "
        f"{sandbox_reason!r} (argv={sandbox_argv!r})"
    )

    # (3) sandbox default: AC5.2 regression guard.
    default_captured: dict[str, list[str]] = {}
    _patch_build_agent_runtime_for_codex(monkeypatch, _fake_codex_run_factory(default_captured))
    monkeypatch.delenv("DADAIA_CODEX_SANDBOX", raising=False)
    default_ws = _init_workspace(tmp_path / "sandbox-default-case")
    _run_pipeline(default_ws, "pipe-codex-sandbox-default")
    default_argv = default_captured["argv"]
    assert default_argv[default_argv.index("--sandbox") :][:2] == ["--sandbox", "read-only"]
