"""Unit tests for the exec-backed Codex runtime adapter."""

from __future__ import annotations

import dataclasses
import json
import subprocess
from pathlib import Path
from typing import Any

import pytest

from dadaia_workspace.core.models.lifecycle import (
    AgentRunRequest,
    AgentRunStatus,
    AgentRuntimeKind,
    GateEvidenceKind,
)
from dadaia_workspace.infrastructure.codex_runtime import CodexExecAdapter, CodexExecConfig


class _SequenceGit:
    def __init__(self, *states: tuple[str, ...]) -> None:
        self._states = list(states)
        self.calls: list[Path] = []

    def diff_name_only(self, path: Path) -> tuple[str, ...]:
        self.calls.append(path)
        if len(self._states) > 1:
            return self._states.pop(0)
        return self._states[0]


def _request(*, model_profile: str | None = "dispatch") -> AgentRunRequest:
    return AgentRunRequest(
        role="software-engineer",
        prompt="Do bounded work and return JSON.",
        runtime=AgentRuntimeKind.CODEX_EXEC,
        context="dadaia-workspace",
        release_id="v0.1.15",
        task_id="T-015-17",
        model_profile=model_profile,
        allowed_paths=("src/**",),
        forbidden_paths=("secrets/**",),
        expected_schema="agent-run-result-v1",
        required_evidence=(GateEvidenceKind.HANDOFF,),
    )


def test_codex_changed_paths_are_content_delta_from_attempt_not_preexisting_dirt(
    tmp_path: Path,
) -> None:
    (tmp_path / "preexisting-clean.txt").write_text("same", encoding="utf-8")
    (tmp_path / "preexisting-changed.txt").write_text("before", encoding="utf-8")
    (tmp_path / "preexisting-removed.txt").write_text("before", encoding="utf-8")
    git = _SequenceGit(
        ("preexisting-clean.txt", "preexisting-changed.txt", "preexisting-removed.txt"),
        (
            "preexisting-clean.txt",
            "preexisting-changed.txt",
            "preexisting-removed.txt",
            "new.txt",
        ),
    )

    def fake_runner(*args: object, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        argv = args[0]
        assert isinstance(argv, list)
        (tmp_path / "preexisting-changed.txt").write_text("after", encoding="utf-8")
        (tmp_path / "preexisting-removed.txt").unlink()
        (tmp_path / "new.txt").write_text("new", encoding="utf-8")
        output = Path(argv[argv.index("--output-last-message") + 1])
        output.write_text(
            json.dumps(
                {
                    "schema": "agent-run-result-v1",
                    "summary": "done",
                    "artifact_refs": [".dadaia/handoff/dadaia-workspace/codex.handoff.json"],
                    "changed_paths": ["model-lie.txt"],
                }
            ),
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

    result = CodexExecAdapter(
        CodexExecConfig(cwd=tmp_path), runner=fake_runner, environ={}, git=git
    ).run(_request())

    assert result.structured_output["changed_paths"] == (
        "new.txt,preexisting-changed.txt,preexisting-removed.txt"
    )
    assert len(git.calls) == 2


def test_codex_exec_adapter_builds_controlled_command_and_env(tmp_path: Path) -> None:
    calls: list[dict[str, Any]] = []

    def fake_runner(*args: object, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        argv = args[0]
        assert isinstance(argv, list)
        calls.append({"args": args, "kwargs": kwargs})
        output = Path(argv[argv.index("--output-last-message") + 1])
        output.write_text(
            json.dumps(
                {
                    "summary": "done",
                    "artifact_refs": [".dadaia/handoff/dadaia-workspace/qa.handoff.json"],
                    "structured_output": {"verdict": "APPROVED"},
                }
            ),
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

    adapter = CodexExecAdapter(
        CodexExecConfig(
            cwd=tmp_path,
            codex_bin="/usr/bin/codex",
            model="gpt-test",
            reasoning_effort="medium",
            sandbox="workspace-write",
        ),
        runner=fake_runner,
        environ={
            "PATH": "/bin",
            "HOME": "/home/operator",
            "OPENAI_API_KEY": "secret-key",
            "PYTHONDONTWRITEBYTECODE": "1",
            "DADAIA_PRIVATE": "private",
        },
    )

    result = adapter.run(_request())

    assert result.status is AgentRunStatus.SUCCEEDED
    assert result.summary == "done"
    call = calls[0]
    argv = call["args"][0]
    assert isinstance(argv, list)
    assert argv[:2] == ["/usr/bin/codex", "exec"]
    assert "--ignore-user-config" in argv
    # FR4 (v0.1.66, AC4.1): --skip-git-repo-check MUST accompany --ignore-user-config
    # so a governed worker in an untrusted directory never fails codex's own trust
    # check.
    assert "--skip-git-repo-check" in argv
    assert argv[argv.index("--sandbox") :][:2] == ["--sandbox", "workspace-write"]
    # W1-1: `--ask-for-approval` is interactive-only and rejected by `codex exec` on
    # codex-cli 0.142.4; the adapter must NOT pass it (exec never prompts).
    assert "--ask-for-approval" not in argv
    assert ["--cd", str(tmp_path)] == argv[argv.index("--cd") :][:2]
    assert argv[argv.index("-m") :][:2] == ["-m", "gpt-test"]
    assert 'model_reasoning_effort="medium"' in argv
    assert argv[-1] == "-"
    assert call["kwargs"]["cwd"] == tmp_path
    assert call["kwargs"]["env"] == {
        "PYTHONDONTWRITEBYTECODE": "1",
        "PATH": "/bin",
        "HOME": "/home/operator",
    }
    assert "secret-key" not in str(call["kwargs"])


@pytest.mark.parametrize(
    "case",
    [
        "tier-fallback",
        "discrete-verbatim",
        "no-discrete-uses-tier",
        "resolved-wins-over-config-and-tier",
    ],
)
def test_codex_model_precedence(tmp_path: Path, case: str) -> None:
    """WS-2 (LAW 2) / T-28-A-06 (M2): the ordered precedence is
    resolved_model > config.model > model_profile tier > dispatch default."""
    from dadaia_workspace import container
    from dadaia_workspace.core.harness_models import validate

    captured: dict[str, list[str]] = {}

    def fake_runner(*args: object, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        argv = args[0]
        assert isinstance(argv, list)
        captured["argv"] = argv
        output = Path(argv[argv.index("--output-last-message") + 1])
        output.write_text('{"summary":"done"}', encoding="utf-8")
        return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

    if case == "tier-fallback":
        result = CodexExecAdapter(
            CodexExecConfig(cwd=tmp_path),
            runner=fake_runner,
            environ={},
        ).run(_request(model_profile="fast"))
        assert result.status is AgentRunStatus.SUCCEEDED
        assert captured["argv"][captured["argv"].index("-m") + 1] == "gpt-5.3-codex-spark"
        assert 'model_reasoning_effort="medium"' in captured["argv"]

    elif case == "discrete-verbatim":
        option = validate("codex", "gpt-5.3-codex-spark:medium")
        adapter = container.build_agent_runtime(
            AgentRuntimeKind.CODEX_EXEC, cwd=tmp_path, model=option
        )
        assert isinstance(adapter, CodexExecAdapter)
        adapter._runner = fake_runner  # type: ignore[attr-defined]
        adapter._environ = {}  # type: ignore[attr-defined]
        adapter._git = None  # type: ignore[attr-defined]
        # Request carries a tier profile, which MUST be ignored in favour of the
        # discrete model.
        adapter.run(_request(model_profile="deep"))
        argv = captured["argv"]
        assert argv[argv.index("-m") + 1] == "gpt-5.3-codex-spark"
        assert 'model_reasoning_effort="medium"' in argv

    elif case == "no-discrete-uses-tier":
        adapter = container.build_agent_runtime(AgentRuntimeKind.CODEX_EXEC, cwd=tmp_path)
        assert isinstance(adapter, CodexExecAdapter)
        adapter._runner = fake_runner  # type: ignore[attr-defined]
        adapter._environ = {}  # type: ignore[attr-defined]
        adapter._git = None  # type: ignore[attr-defined]
        adapter.run(_request(model_profile="fast"))
        argv = captured["argv"]
        # 'fast' tier resolves to gpt-5.4-mini via codex_tier_views().
        assert argv[argv.index("-m") + 1] == "gpt-5.3-codex-spark"

    else:  # resolved-wins-over-config-and-tier
        from dadaia_workspace.core.models.workflow_execution import (
            PolicySource,
            ResolvedModelConfig,
        )

        # Construction-time config model is gpt-5.3-codex-spark:medium ...
        option = validate("codex", "gpt-5.3-codex-spark:medium")
        adapter = CodexExecAdapter(
            CodexExecConfig(cwd=tmp_path, model=option.model_id, reasoning_effort=option.effort),
            runner=fake_runner,
            environ={},
        )
        # ... but the resolved_model says gpt-5.3-codex-spark:high — which must win.
        request = dataclasses.replace(
            _request(model_profile="deep"),
            resolved_model=ResolvedModelConfig(
                profile_id="codex-review-deep",
                harness="codex",
                model="gpt-5.3-codex-spark",
                reasoning="high",
                source=PolicySource.CLI,
            ),
        )
        adapter.run(request)
        argv = captured["argv"]
        assert argv[argv.index("-m") + 1] == "gpt-5.3-codex-spark"
        assert 'model_reasoning_effort="high"' in argv


@pytest.mark.parametrize(
    ("exit_code", "stderr", "expected_summary", "expected_error_contains"),
    [
        pytest.param(
            2,
            "error: unexpected argument '--ask-for-approval' found",
            "codex exec rejected an argument (incompatible codex-cli flag contract)",
            ["--ask-for-approval", "-c approval_policy=", "unexpected argument"],
            id="unexpected-argument-mapped-to-actionable-error",
        ),
        pytest.param(
            1,
            "model timeout",
            "codex exec returned non-zero exit",
            ["model timeout"],
            id="generic-nonzero-exit-keeps-raw-stderr",
        ),
    ],
)
def test_codex_stderr_mapping(
    tmp_path: Path,
    exit_code: int,
    stderr: str,
    expected_summary: str,
    expected_error_contains: list[str],
) -> None:
    """W1-1: codex exec stderr is mapped to an actionable message when it names an
    argv-contract violation, else the raw stderr is kept as-is."""

    def fake_runner(*args: object, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        argv = args[0]
        assert isinstance(argv, list)
        return subprocess.CompletedProcess(argv, exit_code, stdout="", stderr=stderr)

    result = CodexExecAdapter(
        CodexExecConfig(cwd=tmp_path),
        runner=fake_runner,
        environ={"PATH": "/bin"},
    ).run(_request())

    assert result.status is AgentRunStatus.FAILED
    assert result.summary == expected_summary
    assert result.error is not None
    for token in expected_error_contains:
        assert token in result.error


# ---------------------------------------------------------------------------
# T-32-B-01 — codex extractor parity: fenced+bare parse, strict-primary +
# structural-fallback acceptance, no-op→empty refs, reject-guard (A10/A11/C4).
# These FAIL against the pre-parity codex (single ``json.loads`` of the whole
# file, no fenced/bare/sliced candidates, no ``schema`` acceptance, ANY dict
# mapped to a result).
# ---------------------------------------------------------------------------


def _codex_run_with_message(tmp_path: Path, last_message_text: str) -> Any:
    """Run the codex adapter, writing *last_message_text* verbatim to the temp file.

    The text is whatever a real codex worker would leave in ``--output-last-message``:
    a bare JSON object, a fenced ```json block, JSON with trailing prose, or junk.
    """

    def fake_runner(*args: object, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        argv = args[0]
        assert isinstance(argv, list)
        output = Path(argv[argv.index("--output-last-message") + 1])
        output.write_text(last_message_text, encoding="utf-8")
        return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

    return CodexExecAdapter(CodexExecConfig(cwd=tmp_path), runner=fake_runner, environ={}).run(
        _request()
    )


def test_codex_schema_shaped_result_without_refs_carries_diagnostic(tmp_path: Path) -> None:
    payload = json.dumps(
        {"schema": "agent-run-result-v1", "summary": "no evidence", "artifact_refs": []}
    )
    result = _codex_run_with_message(tmp_path, payload)

    assert result.artifact_refs == ()
    assert result.diagnostic is not None
    assert result.diagnostic.parser_classification == "result-without-artifact-refs"
    assert payload in result.diagnostic.output_tail


def test_codex_schema_shaped_result_with_missing_ref_carries_diagnostic(tmp_path: Path) -> None:
    payload = json.dumps(
        {
            "schema": "agent-run-result-v1",
            "summary": "claimed only",
            "artifact_refs": [".dadaia/handoff/missing.json"],
        }
    )
    result = _codex_run_with_message(tmp_path, payload)

    assert result.artifact_refs == (".dadaia/handoff/missing.json",)
    assert result.diagnostic is not None
    assert result.diagnostic.parser_classification == "referenced-artifact-missing"


@pytest.mark.parametrize(
    ("payload_text", "expected_summary", "expected_refs"),
    [
        pytest.param(
            json.dumps(
                {
                    "schema": "agent-run-result-v1",
                    "summary": "bare codex strict",
                    "artifact_refs": [".dadaia/handoff/dadaia-workspace/c1.handoff.json"],
                    "structured_output": {"verdict": "APPROVED"},
                }
            ),
            "bare codex strict",
            (".dadaia/handoff/dadaia-workspace/c1.handoff.json",),
            id="strict-primary-accepts-bare-payload",
        ),
        pytest.param(
            "Here is my result.\n```json\n"
            + json.dumps(
                {
                    "schema": "agent-run-result-v1",
                    "summary": "fenced codex strict",
                    "artifact_refs": [".dadaia/handoff/dadaia-workspace/c2.handoff.json"],
                    "structured_output": {"verdict": "APPROVED"},
                }
            )
            + "\n```\nDone.\n",
            "fenced codex strict",
            (".dadaia/handoff/dadaia-workspace/c2.handoff.json",),
            id="strict-primary-accepts-fenced-payload",
        ),
        pytest.param(
            json.dumps(
                {
                    "schema": "release-scope-handoff-v1",  # wrong (domain) id
                    "status": "succeeded",
                    "summary": "codex mislabelled but valid",
                    "artifact_refs": [".dadaia/handoff/dadaia-workspace/c3.handoff.json"],
                    "structured_output": {"verdict": "APPROVED"},
                }
            ),
            "codex mislabelled but valid",
            (".dadaia/handoff/dadaia-workspace/c3.handoff.json",),
            id="structural-fallback-accepts-mislabelled-payload",
        ),
    ],
)
def test_codex_extractor_accept_matrix(
    tmp_path: Path,
    payload_text: str,
    expected_summary: str,
    expected_refs: tuple[str, ...],
) -> None:
    """A10/A11 — strict-primary (bare/fenced) and structural-fallback (mislabelled
    schema) payloads are all accepted."""
    result = _codex_run_with_message(tmp_path, payload_text)
    assert result.status is AgentRunStatus.SUCCEEDED
    assert result.summary == expected_summary
    assert result.artifact_refs == expected_refs
    assert result.structured_output["verdict"] == "APPROVED"


@pytest.mark.parametrize(
    "payload_text",
    [
        pytest.param("I had nothing structured to emit.", id="noop-worker-blocks"),
        pytest.param(
            json.dumps({"schema": "something-else", "note": "not a result", "verdict": "APPROVED"}),
            id="shapeless-dict-rejected",
        ),
    ],
)
def test_codex_extractor_reject_matrix(tmp_path: Path, payload_text: str) -> None:
    """A11/C4 — a no-op worker (no result payload) and an arbitrary shapeless JSON dict
    (no schema match, no non-empty artifact_refs) both yield EMPTY ``artifact_refs``,
    which downstream gates BLOCK on. SPEC v0.1.66 forbids editing this invariant —
    ``id="noop-worker-blocks"`` is a permanent regression param."""
    result = _codex_run_with_message(tmp_path, payload_text)
    assert result.status is AgentRunStatus.SUCCEEDED
    assert result.artifact_refs == ()
    assert "verdict" not in result.structured_output


# ---------------------------------------------------------------------------
# T-32-B-03 — A12 / C3: positively prove ONE shared extraction implementation.
# Patch the shared helper in headless_adapter_base and assert BOTH pi_runtime
# AND codex_runtime resolve result extraction through it (not a grep).
# ---------------------------------------------------------------------------


def test_pi_and_codex_share_one_extraction_helper(tmp_path: Path, monkeypatch: Any) -> None:
    """A12 / C3 — both adapters call the SAME ``extract_result_payload`` shared helper.

    A sentinel patch over ``headless_adapter_base.extract_result_payload`` records every
    call. Driving a real ``pi`` run and a real ``codex`` run (both fully faked at the
    subprocess seam) must each invoke the patched helper — proving pi and codex resolve
    result extraction through one implementation, so copy-paste divergence cannot reappear.
    """
    from dadaia_workspace.infrastructure import headless_adapter_base
    from dadaia_workspace.infrastructure.pi_runtime import PiHeadlessAdapter, PiHeadlessConfig

    calls: list[str] = []

    def _spy(text: str, expected_schema: str | None) -> dict[str, object] | None:
        calls.append("called")
        return {
            "schema": expected_schema,
            "summary": "spied",
            "artifact_refs": [".dadaia/handoff/dadaia-workspace/spy.handoff.json"],
            "structured_output": {"verdict": "APPROVED"},
        }

    monkeypatch.setattr(headless_adapter_base, "extract_result_payload", _spy)

    # --- pi run (faked subprocess) ---
    def _pi_runner(*args: object, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        argv = args[0]
        assert isinstance(argv, list)
        message = json.dumps(
            {"type": "message_end", "message": {"role": "assistant", "content": "bare"}}
        )
        return subprocess.CompletedProcess(argv, 0, stdout=message)

    pi_request = AgentRunRequest(
        role="software-engineer",
        prompt="work",
        runtime=AgentRuntimeKind.PI_HEADLESS,
        context="dadaia-workspace",
        release_id="v0.1.32",
        expected_schema="agent-run-result-v1",
    )
    PiHeadlessAdapter(PiHeadlessConfig(cwd=tmp_path), runner=_pi_runner, environ={}).run(pi_request)
    assert len(calls) == 1, "pi_runtime did not call the shared extract_result_payload helper"

    # --- codex run (faked subprocess) ---
    _codex_run_with_message(tmp_path, '{"summary":"ignored by spy"}')
    assert len(calls) == 2, "codex_runtime did not call the shared extract_result_payload helper"


# ---------------------------------------------------------------------------
# v0.1.66 FR5 (T-66-03) — DADAIA_CODEX_SANDBOX env override, single choke point.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "case",
    [
        "env-override-reaches-resolved-config",
        "default-stays-read-only-when-env-unset",
        "env-invalid-value-fails-loud-at-construction",
        "explicit-caller-value-wins-over-env",
        "explicit-caller-invalid-value-still-fails-loud",
        "override-reaches-the-command-argv",
    ],
)
def test_codex_sandbox_env_choke_point(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, case: str
) -> None:
    """AC5.1-5.3: DADAIA_CODEX_SANDBOX is a single, unconditional validation choke
    point — env override, unset default, explicit-caller precedence, and invalid
    values (from either source) all resolve/fail through the same path, reaching the
    real command argv."""
    if case == "env-override-reaches-resolved-config":
        monkeypatch.setenv("DADAIA_CODEX_SANDBOX", "workspace-write")
        config = CodexExecConfig(cwd=tmp_path)
        assert config.sandbox == "workspace-write"
        assert config.resolved_sandbox == "workspace-write"

    elif case == "default-stays-read-only-when-env-unset":
        monkeypatch.delenv("DADAIA_CODEX_SANDBOX", raising=False)
        config = CodexExecConfig(cwd=tmp_path)
        assert config.sandbox == "read-only"
        assert config.resolved_sandbox == "read-only"

    elif case == "env-invalid-value-fails-loud-at-construction":
        monkeypatch.setenv("DADAIA_CODEX_SANDBOX", "not-a-real-value")
        with pytest.raises(ValueError, match="invalid Codex sandbox mode"):
            CodexExecConfig(cwd=tmp_path)

    elif case == "explicit-caller-value-wins-over-env":
        monkeypatch.setenv("DADAIA_CODEX_SANDBOX", "workspace-write")
        config = CodexExecConfig(cwd=tmp_path, sandbox="danger-full-access")
        assert config.sandbox == "danger-full-access"

    elif case == "explicit-caller-invalid-value-still-fails-loud":
        monkeypatch.delenv("DADAIA_CODEX_SANDBOX", raising=False)
        with pytest.raises(ValueError, match="invalid Codex sandbox mode"):
            CodexExecConfig(cwd=tmp_path, sandbox="not-a-real-value")

    else:  # override-reaches-the-command-argv
        monkeypatch.setenv("DADAIA_CODEX_SANDBOX", "danger-full-access")
        captured: dict[str, list[str]] = {}

        def fake_runner(*args: object, **kwargs: Any) -> subprocess.CompletedProcess[str]:
            argv = args[0]
            assert isinstance(argv, list)
            captured["argv"] = argv
            output = Path(argv[argv.index("--output-last-message") + 1])
            output.write_text(json.dumps({"summary": "done"}), encoding="utf-8")
            return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

        CodexExecAdapter(CodexExecConfig(cwd=tmp_path), runner=fake_runner, environ={}).run(
            _request()
        )
        argv = captured["argv"]
        assert argv[argv.index("--sandbox") :][:2] == ["--sandbox", "danger-full-access"]


# ---------------------------------------------------------------------------
# T-67-03 (SPEC v0.1.67 AC1(repro), codex half) — call-time-vs-construction-time
# runner resolution. Mirrors test_pi_runtime.py's
# test_default_runner_resolves_subprocess_run_at_call_time_not_construction_time.
# ---------------------------------------------------------------------------


def test_default_runner_resolves_subprocess_run_at_call_time_not_construction_time(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    real_worker_guard_bypass_for_mechanism_proof: None,
) -> None:
    """AC1(repro), AC1.2: no explicit ``runner=`` at construction; the module-level
    ``subprocess.run`` attribute is monkeypatched to a fake AFTER construction. The
    fake must be invoked when ``.run()`` executes.

    On current code (``runner: Runner = subprocess.run`` bound at class-definition
    time) this FAILS: the adapter's ``self._runner`` was already bound to the real
    ``subprocess.run`` function object before this monkeypatch ever ran, so the fake
    is never reached and the call-recorder stays empty.

    Requests ``real_worker_guard_bypass_for_mechanism_proof`` (T-67-08, FR3):
    this test IS the mechanism FR3's guard also patches (the call-time-vs-
    construction-time fallback to ``subprocess.run``), so it must opt out of the
    guard explicitly — see that fixture's docstring for why this stays hermetic:
    the module-level monkeypatch below runs BEFORE ``.run()`` is ever called, so no
    real subprocess is spawned regardless of the guard's bypass.
    """
    calls: list[object] = []

    def fake_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(args)
        argv = args[0]
        assert isinstance(argv, list)
        output_path = Path(argv[argv.index("--output-last-message") + 1])
        output_path.write_text(
            json.dumps({"summary": "call-time interception proof"}), encoding="utf-8"
        )
        return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

    # Construct with NO runner= kwarg — the adapter must fall back to a live,
    # call-time lookup of the module-level `subprocess.run` attribute.
    adapter = CodexExecAdapter(CodexExecConfig(cwd=tmp_path), environ={})

    # Patch the MODULE attribute strictly AFTER construction — this is the exact
    # monkeypatch shape used by the (now-fixed) executed-path CLI tests.
    monkeypatch.setattr("dadaia_workspace.infrastructure.codex_runtime.subprocess.run", fake_run)

    result = adapter.run(_request())

    assert len(calls) == 1, (
        "the module-level subprocess.run monkeypatch was never reached — the runner "
        "was bound at class-definition time instead of resolved at call time"
    )
    assert result.status is AgentRunStatus.SUCCEEDED
    assert result.summary == "call-time interception proof"


# ---------------------------------------------------------------------------
# T-67-08 (SPEC v0.1.67 FR3, AC3.2) — real-binary guardrail, codex mirror. See
# test_pi_runtime.py's test_no_runner_injected_and_no_live_flag_raises_guard_error_
# instead_of_real_binary for the full rationale. PERMANENT regression test.
# ---------------------------------------------------------------------------


def test_no_runner_injected_and_no_live_flag_raises_guard_error_instead_of_real_binary(
    tmp_path: Path,
) -> None:
    """AC3.2: constructing `CodexExecAdapter` with no `runner=` and calling `.run()`
    with none of the 4 live-opt-in flags set must raise the suite-wide guard's
    `RuntimeError` — never silently spawn/hang on the real `codex` binary.

    Safety (F6): `timeout_seconds=1` bounds any accidental real-binary spawn to a fast,
    caught `TimeoutExpired` rather than a hanging live call — this body never lets a
    real subprocess run to completion, even before the guard exists.
    """
    adapter = CodexExecAdapter(CodexExecConfig(cwd=tmp_path, timeout_seconds=1), environ={})

    with pytest.raises(RuntimeError, match="real pi/codex binary invocation attempted"):
        adapter.run(_request())


def _capture_argv(cfg: CodexExecConfig) -> list[str]:
    """Run the adapter with a fake runner and return the argv it built."""
    captured: dict[str, list[str]] = {}

    def fake_runner(*args: object, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        argv = args[0]
        assert isinstance(argv, list)
        captured["argv"] = argv
        Path(argv[argv.index("--output-last-message") + 1]).write_text(
            json.dumps({"summary": "ok", "artifact_refs": [], "structured_output": {}}),
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

    CodexExecAdapter(cfg, runner=fake_runner, environ={"PATH": "/bin", "HOME": "/h"}).run(
        _request()
    )
    return captured["argv"]


def test_sandbox_bypass_mode_emits_dangerously_bypass_and_omits_sandbox(tmp_path: Path) -> None:
    """Bug codex-adapter-cannot-run-in-nested-container: dadaia's Codex adapter always
    passed `--sandbox <mode>`, which needs namespace creation (bwrap) that fails in a
    nested/unprivileged container (e.g. the Hermes worker) — so Codex-harness workflows
    could not run there, even though the same container runs Codex fine with the bypass
    flag. The opt-in `danger-bypass` mode emits `--dangerously-bypass-approvals-and-sandbox`
    (mutually exclusive with `--sandbox`) so a trusted containerized consumer can run."""
    argv = _capture_argv(
        CodexExecConfig(
            cwd=tmp_path, codex_bin="/usr/bin/codex", model="m", reasoning_effort="medium",
            sandbox="danger-bypass",
        )
    )
    assert "--dangerously-bypass-approvals-and-sandbox" in argv
    assert "--sandbox" not in argv, "bypass and --sandbox are mutually exclusive"


def test_normal_sandbox_mode_emits_sandbox_and_no_bypass(tmp_path: Path) -> None:
    """The default/secure path is unchanged: a normal mode emits `--sandbox <mode>` and
    never the bypass flag."""
    argv = _capture_argv(
        CodexExecConfig(
            cwd=tmp_path, codex_bin="/usr/bin/codex", model="m", reasoning_effort="medium",
            sandbox="read-only",
        )
    )
    assert argv[argv.index("--sandbox") :][:2] == ["--sandbox", "read-only"]
    assert "--dangerously-bypass-approvals-and-sandbox" not in argv


def test_sandbox_bypass_selectable_via_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The single env choke point DADAIA_CODEX_SANDBOX accepts the bypass sentinel."""
    monkeypatch.setenv("DADAIA_CODEX_SANDBOX", "danger-bypass")
    cfg = CodexExecConfig(cwd=tmp_path, codex_bin="/usr/bin/codex", model="m", reasoning_effort="medium")
    assert cfg.bypass_sandbox is True
