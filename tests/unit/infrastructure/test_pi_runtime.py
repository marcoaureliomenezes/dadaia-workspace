"""Unit tests for the headless PI runtime adapter (subprocess `pi --mode json`).

Mirrors ``test_codex_exec_runtime.py``. The runner is injected and fully faked —
no live ``pi`` binary, no network, no Node. The single unverified upstream seam
(``AgentMessage.content`` string-vs-blocks shape) is covered defensively by both
content shapes here; the live verification lives behind the opt-in
``tests/integration/pi_live/`` seam.
"""

from __future__ import annotations

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
from dadaia_workspace.infrastructure.pi_runtime import PiHeadlessAdapter, PiHeadlessConfig


def _request(
    *,
    runtime: AgentRuntimeKind = AgentRuntimeKind.PI_HEADLESS,
    expected_schema: str | None = "agent-run-result-v1",
    allowed_paths: tuple[str, ...] = ("src/**",),
    forbidden_paths: tuple[str, ...] = ("secrets/**",),
) -> AgentRunRequest:
    return AgentRunRequest(
        role="software-engineer",
        prompt="Do bounded work and return JSON.",
        runtime=runtime,
        context="dadaia-workspace",
        release_id="pi-fourth-harness-v1",
        task_id="T-PI-02",
        allowed_paths=allowed_paths,
        forbidden_paths=forbidden_paths,
        expected_schema=expected_schema,
        required_evidence=(GateEvidenceKind.HANDOFF,),
    )


def _message_end(content: object) -> str:
    return json.dumps({"type": "message_end", "message": {"role": "assistant", "content": content}})


class _FakeGit:
    """Fake GitSubprocessClient seam — returns canned diff lists per cwd snapshot."""

    def __init__(self, changed: tuple[str, ...] = ()) -> None:
        self._changed = changed
        self.calls: list[Path] = []

    def diff_name_only(self, path: Path) -> tuple[str, ...]:
        self.calls.append(path)
        return self._changed


# ---------------------------------------------------------------------------
# T-PI-02 — minimal adapter: command, env, failure handling
# ---------------------------------------------------------------------------


def test_pi_adapter_builds_controlled_command_and_env(tmp_path: Path) -> None:
    calls: list[dict[str, Any]] = []

    def fake_runner(*args: object, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        argv = args[0]
        assert isinstance(argv, list)
        calls.append({"args": args, "kwargs": kwargs})
        return subprocess.CompletedProcess(argv, 0, stdout=_message_end("done"), stderr="")

    adapter = PiHeadlessAdapter(
        PiHeadlessConfig(cwd=tmp_path, pi_bin="/usr/bin/pi", model="claude-test"),
        runner=fake_runner,
        environ={
            "PATH": "/bin",
            "HOME": "/home/operator",
            "ANTHROPIC_API_KEY": "secret-key",
            "DADAIA_PRIVATE": "private",
        },
    )

    result = adapter.run(_request())

    assert result.status is AgentRunStatus.SUCCEEDED
    call = calls[0]
    argv = call["args"][0]
    assert isinstance(argv, list)
    assert argv[0] == "/usr/bin/pi"
    assert argv[argv.index("--mode") : argv.index("--mode") + 2] == ["--mode", "json"]
    assert argv[argv.index("--tools") + 1] == "read,write,edit,bash"
    assert argv[argv.index("--model") : argv.index("--model") + 2] == ["--model", "claude-test"]
    # ``-p`` (--print) only; the prompt is piped via stdin — NO trailing ``-`` (pi has no
    # such option; bug pi-headless-command-trailing-dash-breaks-layer2).
    assert argv[-1] == "-p"
    assert "-" not in argv
    assert call["kwargs"]["cwd"] == tmp_path
    # Env is filtered to the allowlist only (ANTHROPIC_API_KEY is allowlisted).
    assert call["kwargs"]["env"] == {
        "PATH": "/bin",
        "HOME": "/home/operator",
        "ANTHROPIC_API_KEY": "secret-key",
    }
    # Prompt is delivered on stdin.
    assert isinstance(call["kwargs"]["input"], str)
    assert "Do bounded work" in call["kwargs"]["input"]


@pytest.mark.parametrize(
    "case",
    [
        "discrete-model-reaches-model-flag",
        "omit-model-flag-when-unset",
        "per-request-resolved-model-overrides-construction",
        "openrouter-model-id-passes-through-unchanged",
        "no-model-flag-when-neither-request-nor-config",
    ],
)
def test_pi_model_flag_resolution(tmp_path: Path, case: str) -> None:
    """WS-2 (LAW 2) / T-28-A-06 (AC-12) / AC-5 (v0.1.44): the ordered model
    resolution — resolved_model wins over config.model wins over discrete-catalog
    tier — reaches ``pi --model <id>`` verbatim, or is omitted entirely when no
    model is available anywhere."""
    captured: list[list[str]] = []

    def fake_runner(*args: object, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        argv = args[0]
        assert isinstance(argv, list)
        captured.append(argv)
        return subprocess.CompletedProcess(argv, 0, stdout=_message_end("done"))

    if case == "discrete-model-reaches-model-flag":
        from dadaia_workspace import container
        from dadaia_workspace.core.harness_models import validate

        option = validate("pi", "gpt-5.3-codex:medium")
        adapter = container.build_agent_runtime(
            AgentRuntimeKind.PI_HEADLESS, cwd=tmp_path, model=option
        )
        assert isinstance(adapter, PiHeadlessAdapter)
        adapter._runner = fake_runner  # type: ignore[attr-defined]
        adapter._environ = {}  # type: ignore[attr-defined]
        adapter._git = None  # type: ignore[attr-defined]
        adapter.run(_request())
        argv = captured[0]
        assert argv[argv.index("--model") : argv.index("--model") + 2] == [
            "--model",
            "gpt-5.3-codex",
        ]

    elif case == "omit-model-flag-when-unset":
        PiHeadlessAdapter(PiHeadlessConfig(cwd=tmp_path), runner=fake_runner, environ={}).run(
            _request()
        )
        assert "--model" not in captured[0]

    elif case == "per-request-resolved-model-overrides-construction":
        import dataclasses

        from dadaia_workspace.core.models.workflow_execution import (
            PolicySource,
            ResolvedModelConfig,
        )

        adapter = PiHeadlessAdapter(
            PiHeadlessConfig(cwd=tmp_path, model="gpt-5.3-codex"),
            runner=fake_runner,
            environ={},
        )
        request = dataclasses.replace(
            _request(),
            resolved_model=ResolvedModelConfig(
                profile_id="pi-reasoning-high",
                harness="pi",
                model="gpt-5.5",
                reasoning="high",
                source=PolicySource.CLI,
            ),
        )
        adapter.run(request)
        argv = captured[0]
        assert argv[argv.index("--model") : argv.index("--model") + 2] == ["--model", "gpt-5.5"]

    elif case == "openrouter-model-id-passes-through-unchanged":
        import dataclasses

        from dadaia_workspace.core.harness_models import validate
        from dadaia_workspace.core.models.workflow_execution import (
            PolicySource,
            ResolvedModelConfig,
        )

        option = validate("pi", "moonshotai/kimi-k2.5:high")
        assert option.model_id == "moonshotai/kimi-k2.5"
        adapter = PiHeadlessAdapter(PiHeadlessConfig(cwd=tmp_path), runner=fake_runner, environ={})
        request = dataclasses.replace(
            _request(),
            resolved_model=ResolvedModelConfig(
                profile_id="pi-operator-kimi",
                harness="pi",
                model="moonshotai/kimi-k2.5",
                reasoning="high",
                source=PolicySource.CLI,
            ),
        )
        adapter.run(request)
        argv = captured[0]
        assert argv[: argv.index("--model")] == [
            "pi",
            "--mode",
            "json",
            "--tools",
            "read,write,edit,bash",
        ]
        assert argv[argv.index("--model") : argv.index("--model") + 2] == [
            "--model",
            "moonshotai/kimi-k2.5",
        ]

    else:  # no-model-flag-when-neither-request-nor-config
        PiHeadlessAdapter(PiHeadlessConfig(cwd=tmp_path), runner=fake_runner, environ={}).run(
            _request()
        )
        assert "--model" not in captured[0]


@pytest.mark.parametrize(
    "case",
    [
        "wrong-runtime",
        "timeout",
        "oserror",
        "nonzero-exit-no-output",
        "nonzero-exit-with-setup-stdout",
    ],
)
def test_pi_adapter_failure_modes(tmp_path: Path, case: str) -> None:
    if case == "nonzero-exit-with-setup-stdout":
        """AC1.1 (bug: pi-headless-nonzero-exit-misreported). PERMANENT regression.

        A pi setup failure (e.g. missing API key) still emits a JSONL session/event
        preamble to stdout before dying — there is no usable ``message_end`` in it.
        On current (buggy) code, ``_result_from_output``'s ``returncode != 0 and not
        text`` guard treats non-empty stdout as a signal the run "completed" and
        reports SUCCEEDED, discarding the real non-zero exit and the actionable
        stderr. The fix must classify ANY non-zero returncode as FAILED regardless
        of stdout content, and ``run()``'s stderr-backfill must thread the real
        stderr into ``result.error``."""
        preamble_stdout = (
            "\n".join(
                [
                    json.dumps({"type": "session_start", "session_id": "abc123"}),
                    json.dumps({"type": "message_start"}),
                ]
            )
            + "\n"
        )

        def fake_runner(*args: object, **kwargs: Any) -> subprocess.CompletedProcess[str]:
            argv = args[0]
            assert isinstance(argv, list)
            return subprocess.CompletedProcess(
                argv,
                1,
                stdout=preamble_stdout,
                stderr="No API key found for azure-openai-responses.",
            )

        result = PiHeadlessAdapter(
            PiHeadlessConfig(cwd=tmp_path), runner=fake_runner, environ={}
        ).run(_request())
        assert result.status is AgentRunStatus.FAILED
        assert result.error == "No API key found for azure-openai-responses."

    elif case == "wrong-runtime":
        called = False

        def fake_runner(*args: object, **kwargs: Any) -> subprocess.CompletedProcess[str]:
            nonlocal called
            called = True
            return subprocess.CompletedProcess([], 0)

        result = PiHeadlessAdapter(
            PiHeadlessConfig(cwd=tmp_path), runner=fake_runner, environ={}
        ).run(_request(runtime=AgentRuntimeKind.FAKE))
        assert result.status is AgentRunStatus.FAILED
        assert called is False

    elif case == "timeout":

        def fake_runner(*args: object, **kwargs: Any) -> subprocess.CompletedProcess[str]:
            raise subprocess.TimeoutExpired(cmd="pi", timeout=900)

        result = PiHeadlessAdapter(
            PiHeadlessConfig(cwd=tmp_path), runner=fake_runner, environ={}
        ).run(_request())
        assert result.status is AgentRunStatus.FAILED
        assert "timed out" in result.summary

    elif case == "oserror":

        def fake_runner(*args: object, **kwargs: Any) -> subprocess.CompletedProcess[str]:
            raise OSError("pi binary not found")

        result = PiHeadlessAdapter(
            PiHeadlessConfig(cwd=tmp_path), runner=fake_runner, environ={}
        ).run(_request())
        assert result.status is AgentRunStatus.FAILED
        assert "failed to start" in result.summary

    else:  # nonzero-exit-no-output

        def fake_runner(*args: object, **kwargs: Any) -> subprocess.CompletedProcess[str]:
            argv = args[0]
            assert isinstance(argv, list)
            return subprocess.CompletedProcess(argv, 1, stdout="", stderr="boom")

        result = PiHeadlessAdapter(
            PiHeadlessConfig(cwd=tmp_path), runner=fake_runner, environ={}
        ).run(_request())
        assert result.status is AgentRunStatus.FAILED
        assert "boom" in (result.error or "")


@pytest.mark.parametrize("surface", ["error", "summary"])
def test_pi_adapter_redacts_anthropic_api_key(tmp_path: Path, surface: str) -> None:
    secret = "sk-anthropic-xyz"
    if surface == "error":

        def fake_runner(*args: object, **kwargs: Any) -> subprocess.CompletedProcess[str]:
            argv = args[0]
            assert isinstance(argv, list)
            return subprocess.CompletedProcess(argv, 1, stdout="", stderr=f"failed: {secret}")

        result = PiHeadlessAdapter(
            PiHeadlessConfig(cwd=tmp_path),
            runner=fake_runner,
            environ={"PATH": "/bin", "ANTHROPIC_API_KEY": secret},
        ).run(_request())
        assert result.status is AgentRunStatus.FAILED
        assert result.error == "failed: [REDACTED]"
        assert secret not in (result.error or "")
    else:

        def fake_runner(*args: object, **kwargs: Any) -> subprocess.CompletedProcess[str]:
            argv = args[0]
            assert isinstance(argv, list)
            return subprocess.CompletedProcess(
                argv, 0, stdout=_message_end(f"leaked {secret} here")
            )

        result = PiHeadlessAdapter(
            PiHeadlessConfig(cwd=tmp_path),
            runner=fake_runner,
            environ={"PATH": "/bin", "ANTHROPIC_API_KEY": secret},
        ).run(_request())
        assert result.status is AgentRunStatus.SUCCEEDED
        assert secret not in result.summary
        assert "[REDACTED]" in result.summary


# ---------------------------------------------------------------------------
# T-PI-05 / T-32-B-01 — result extraction hardening: last-message-wins, block-array
# content, unparseable/no-message-end degradation, strict-primary (fenced/bare),
# structural fallback, and the reject/noop matrix.
# ---------------------------------------------------------------------------


def _pi_run_with_message(tmp_path: Path, content: object, stream: str | None = None) -> Any:
    def fake_runner(*args: object, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        argv = args[0]
        assert isinstance(argv, list)
        return subprocess.CompletedProcess(
            argv, 0, stdout=stream if stream is not None else _message_end(content)
        )

    return PiHeadlessAdapter(PiHeadlessConfig(cwd=tmp_path), runner=fake_runner, environ={}).run(
        _request(expected_schema="agent-run-result-v1")
    )


@pytest.mark.parametrize(
    ("kind", "payload", "expected_summary", "expected_refs"),
    [
        pytest.param(
            "stream",
            "\n".join(
                [
                    json.dumps({"type": "message_start", "message": {}}),
                    _message_end("first draft"),
                    json.dumps({"type": "tool_use", "name": "edit"}),
                    _message_end("FINAL ANSWER"),
                ]
            ),
            "FINAL ANSWER",
            None,
            id="last-message-end-wins",
        ),
        pytest.param(
            "content",
            [{"type": "text", "text": "block one. "}, {"type": "text", "text": "block two."}],
            "block one. block two.",
            None,
            id="content-as-block-array",
        ),
        pytest.param(
            "content",
            json.dumps(
                {
                    "schema": "agent-run-result-v1",
                    "summary": "bare strict",
                    "artifact_refs": [".dadaia/handoff/dadaia-workspace/b.handoff.json"],
                    "structured_output": {"verdict": "APPROVED"},
                }
            ),
            "bare strict",
            (".dadaia/handoff/dadaia-workspace/b.handoff.json",),
            id="strict-primary-bare-payload",
        ),
        pytest.param(
            "content",
            (
                "Done.\n```json\n"
                + json.dumps(
                    {
                        "schema": "agent-run-result-v1",
                        "summary": "fenced strict",
                        "artifact_refs": [".dadaia/handoff/dadaia-workspace/a.handoff.json"],
                        "structured_output": {"verdict": "APPROVED"},
                    }
                )
                + "\n```\n"
            ),
            "fenced strict",
            (".dadaia/handoff/dadaia-workspace/a.handoff.json",),
            id="strict-primary-fenced-payload",
        ),
        pytest.param(
            "content",
            json.dumps(
                {
                    "schema": "release-scope-handoff-v1",  # wrong (domain, not transport) id
                    "status": "succeeded",
                    "summary": "mislabelled but valid",
                    "artifact_refs": [".dadaia/handoff/dadaia-workspace/c.handoff.json"],
                    "structured_output": {"verdict": "APPROVED"},
                }
            ),
            "mislabelled but valid",
            (".dadaia/handoff/dadaia-workspace/c.handoff.json",),
            id="structural-fallback-mislabelled-payload",
        ),
        pytest.param(
            "content",
            json.dumps(
                {
                    "status": "succeeded",
                    "summary": "scope approved",
                    "artifact_refs": [".dadaia/handoff/dadaia-workspace/scope.handoff.json"],
                    "structured_output": {
                        "verdict": "APPROVED",
                        "output_schema": "release-scope-handoff-v1",
                    },
                }
            ),
            "scope approved",
            (".dadaia/handoff/dadaia-workspace/scope.handoff.json",),
            id="structural-acceptance-without-schema-field",
        ),
        pytest.param(
            "stream",
            "this is not json at all\n{also broken",
            None,
            None,
            id="unparseable-line-degrades-to-nonempty-summary",
        ),
        pytest.param(
            "stream",
            "\n".join(
                [
                    json.dumps({"type": "message_start", "message": {}}),
                    json.dumps({"type": "tool_use", "name": "edit"}),
                ]
            ),
            None,
            None,
            id="no-message-end-degrades-to-nonempty-summary",
        ),
        pytest.param(
            "content",
            json.dumps({"type": "message_start", "message": {}}),
            None,
            None,
            id="unrecognized-content-degrades-to-nonempty-summary",
        ),
    ],
)
def test_pi_extraction_accept_matrix(
    tmp_path: Path,
    kind: str,
    payload: object,
    expected_summary: str | None,
    expected_refs: tuple[str, ...] | None,
) -> None:
    if kind == "stream":
        result = _pi_run_with_message(tmp_path, None, stream=payload)  # type: ignore[arg-type]
    else:
        result = _pi_run_with_message(tmp_path, payload)
    assert result.status is AgentRunStatus.SUCCEEDED
    if expected_summary is None:
        assert result.summary.strip() != ""  # degraded fallback: any non-empty summary
    else:
        assert result.summary == expected_summary
    if expected_refs is not None:
        assert result.artifact_refs == expected_refs
        assert result.structured_output["verdict"] == "APPROVED"


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param("I had nothing structured to emit.", id="noop-worker-blocks"),
        pytest.param(
            json.dumps({"schema": "something-else", "note": "not a result", "verdict": "APPROVED"}),
            id="shapeless-dict-rejected",
        ),
        pytest.param(
            "```json\n" + json.dumps({"schema": "other-schema", "verdict": "APPROVED"}) + "\n```",
            id="fenced-json-ignored-when-schema-mismatch",
        ),
    ],
)
def test_pi_extraction_reject_matrix(tmp_path: Path, payload: str) -> None:
    """A8/C4 — a no-op worker (no result payload) and an arbitrary shapeless JSON
    dict (no schema match, no non-empty artifact_refs) both yield EMPTY
    ``artifact_refs``, which downstream gates BLOCK on. SPEC v0.1.66 forbids editing
    this invariant — ``id="noop-worker-blocks"`` is a permanent regression param."""
    result = _pi_run_with_message(tmp_path, payload)
    assert result.status is AgentRunStatus.SUCCEEDED
    assert result.artifact_refs == ()
    assert "verdict" not in result.structured_output


def test_pi_strict_primacy_is_pinned_by_behaviour(tmp_path: Path) -> None:
    """A9 / C5 — strict primacy pinned by BEHAVIOUR (not docstring).

    The shared classifier reports WHICH acceptance path matched. A payload that is BOTH
    structurally-valid AND ``schema``-matched MUST classify as STRICT; a structurally-valid
    but ``schema``-mismatched payload MUST classify only as STRUCTURAL (the documented
    fallback). A future reorder that lets the structural check shadow strict would classify
    the both-valid payload as STRUCTURAL and FAIL this test.
    """
    from dadaia_workspace.infrastructure.headless_adapter_base import (
        ResultMatch,
        classify_result_payload,
    )

    both_valid = {
        "schema": "agent-run-result-v1",
        "status": "succeeded",
        "summary": "both",
        "artifact_refs": [".dadaia/handoff/dadaia-workspace/d.handoff.json"],
        "structured_output": {"verdict": "APPROVED"},
    }
    structural_only = {
        "schema": "release-scope-handoff-v1",  # schema mismatch
        "status": "succeeded",
        "summary": "structural",
        "artifact_refs": [".dadaia/handoff/dadaia-workspace/e.handoff.json"],
        "structured_output": {"verdict": "APPROVED"},
    }
    not_a_result = {"schema": "something-else", "note": "no refs"}

    assert classify_result_payload(both_valid, "agent-run-result-v1") is ResultMatch.STRICT
    assert classify_result_payload(structural_only, "agent-run-result-v1") is ResultMatch.STRUCTURAL
    assert classify_result_payload(not_a_result, "agent-run-result-v1") is ResultMatch.NONE


# ---------------------------------------------------------------------------
# T-67-01 (SPEC v0.1.67 AC1(repro), pi half) — call-time-vs-construction-time
# runner resolution. PERMANENT regression test.
# ---------------------------------------------------------------------------


def test_default_runner_resolves_subprocess_run_at_call_time_not_construction_time(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    real_worker_guard_bypass_for_mechanism_proof: None,
) -> None:
    """AC1(repro), AC1.1: no explicit ``runner=`` at construction; the module-level
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
        return subprocess.CompletedProcess(
            argv, 0, stdout=_message_end("call-time interception proof"), stderr=""
        )

    # Construct with NO runner= kwarg — the adapter must fall back to a live,
    # call-time lookup of the module-level `subprocess.run` attribute.
    adapter = PiHeadlessAdapter(PiHeadlessConfig(cwd=tmp_path))

    # Patch the MODULE attribute strictly AFTER construction — this is the exact
    # monkeypatch shape used by the (now-fixed) executed-path CLI tests.
    monkeypatch.setattr("dadaia_workspace.infrastructure.pi_runtime.subprocess.run", fake_run)

    result = adapter.run(_request())

    assert len(calls) == 1, (
        "the module-level subprocess.run monkeypatch was never reached — the runner "
        "was bound at class-definition time instead of resolved at call time"
    )
    assert result.status is AgentRunStatus.SUCCEEDED
    assert result.summary == "call-time interception proof"


# ---------------------------------------------------------------------------
# T-67-08 (SPEC v0.1.67 FR3, AC3.1) — real-binary guardrail: fails loud instead of
# silently spawning/hanging on the real `pi` binary when no runner= is injected and
# no live-opt-in flag is set. This is a PERMANENT regression test pinning the
# suite-wide autouse guard fixture in tests/conftest.py — kept after this release,
# not deleted once exercised (per SPEC's TDD mandate step 4).
# ---------------------------------------------------------------------------


def test_no_runner_injected_and_no_live_flag_raises_guard_error_instead_of_real_binary(
    tmp_path: Path,
) -> None:
    """AC3.1: constructing `PiHeadlessAdapter` with no `runner=` and calling `.run()`
    with none of the 4 live-opt-in flags set must raise the suite-wide guard's
    `RuntimeError` — never silently spawn/hang on the real `pi` binary.

    The guard fixture itself lives in `tests/conftest.py` (autouse=True) and patches
    the module-level `pi_runtime.subprocess.run` to a raising sentinel unless one of
    `DADAIA_E2E_REAL_WORKER`/`DADAIA_PI_LIVE`/`DADAIA_CODEX_LIVE`/`DADAIA_CLAUDE_LIVE`
    is `"1"`. This test intentionally does NOT set any of those flags — the ambient
    test environment's `_scrub_entry_signal_env`/lack of live opt-in is the precondition.

    Safety (F6): before the guard exists, this body must NEVER run a real binary to
    completion. `timeout_seconds=1` bounds any accidental real-binary spawn to a fast,
    caught `TimeoutExpired` (adapter.run() maps it to a FAILED result, not a raised
    RuntimeError) rather than a multi-second/hanging live call.
    """
    adapter = PiHeadlessAdapter(PiHeadlessConfig(cwd=tmp_path, timeout_seconds=1))

    with pytest.raises(RuntimeError, match="real pi/codex binary invocation attempted"):
        adapter.run(_request())


# ---------------------------------------------------------------------------
# v0.1.78 T-D / FR-D — worker-noncompliance diagnostic evidence + PI --thinking
# (bug worker-noncompliance-block-carries-no-diagnostic-evidence).
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "case",
    [
        "resolved-model-reasoning-reaches-thinking-flag",
        "construction-config-reasoning-reaches-thinking-flag",
        "resolved-model-reasoning-overrides-construction",
        "no-reasoning-anywhere-omits-thinking-flag",
    ],
)
def test_pi_thinking_flag_resolution(tmp_path: Path, case: str) -> None:
    """``PiHeadlessConfig.reasoning_effort`` (and the per-request resolved reasoning)
    forwards to PI's ``--thinking <level>`` flag — same ordered precedence as ``--model``
    (resolved_model wins over construction-time config)."""
    import dataclasses

    from dadaia_workspace.core.models.workflow_execution import (
        PolicySource,
        ResolvedModelConfig,
    )

    captured: list[list[str]] = []

    def fake_runner(*args: object, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        argv = args[0]
        assert isinstance(argv, list)
        captured.append(argv)
        return subprocess.CompletedProcess(argv, 0, stdout=_message_end("done"))

    if case == "resolved-model-reasoning-reaches-thinking-flag":
        adapter = PiHeadlessAdapter(PiHeadlessConfig(cwd=tmp_path), runner=fake_runner, environ={})
        request = dataclasses.replace(
            _request(),
            resolved_model=ResolvedModelConfig(
                profile_id="pi-reasoning-high",
                harness="pi",
                model="gpt-5.5",
                reasoning="high",
                source=PolicySource.CLI,
            ),
        )
        adapter.run(request)
        argv = captured[0]
        assert argv[argv.index("--thinking") : argv.index("--thinking") + 2] == [
            "--thinking",
            "high",
        ]

    elif case == "construction-config-reasoning-reaches-thinking-flag":
        adapter = PiHeadlessAdapter(
            PiHeadlessConfig(cwd=tmp_path, reasoning_effort="medium"),
            runner=fake_runner,
            environ={},
        )
        adapter.run(_request())
        argv = captured[0]
        assert argv[argv.index("--thinking") : argv.index("--thinking") + 2] == [
            "--thinking",
            "medium",
        ]

    elif case == "resolved-model-reasoning-overrides-construction":
        adapter = PiHeadlessAdapter(
            PiHeadlessConfig(cwd=tmp_path, reasoning_effort="low"),
            runner=fake_runner,
            environ={},
        )
        request = dataclasses.replace(
            _request(),
            resolved_model=ResolvedModelConfig(
                profile_id="pi-reasoning-high",
                harness="pi",
                model="gpt-5.5",
                reasoning="high",
                source=PolicySource.CLI,
            ),
        )
        adapter.run(request)
        argv = captured[0]
        assert argv[argv.index("--thinking") : argv.index("--thinking") + 2] == [
            "--thinking",
            "high",
        ]

    else:  # no-reasoning-anywhere-omits-thinking-flag
        adapter = PiHeadlessAdapter(PiHeadlessConfig(cwd=tmp_path), runner=fake_runner, environ={})
        adapter.run(_request())
        assert "--thinking" not in captured[0]


def test_pi_thinking_flag_precedes_print_flag_and_stays_after_model(tmp_path: Path) -> None:
    """Contract test on the assembled command line (SPEC guidance: not a live-PI test)."""
    captured: list[list[str]] = []

    def fake_runner(*args: object, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        argv = args[0]
        assert isinstance(argv, list)
        captured.append(argv)
        return subprocess.CompletedProcess(argv, 0, stdout=_message_end("done"))

    adapter = PiHeadlessAdapter(
        PiHeadlessConfig(cwd=tmp_path, model="gpt-5.5", reasoning_effort="high"),
        runner=fake_runner,
        environ={},
    )
    adapter.run(_request())
    argv = captured[0]
    assert argv[argv.index("--model") : argv.index("--model") + 2] == ["--model", "gpt-5.5"]
    assert argv[argv.index("--thinking") : argv.index("--thinking") + 2] == [
        "--thinking",
        "high",
    ]
    assert argv[-1] == "-p"


@pytest.mark.parametrize(
    "case",
    [
        "no-message-end-nonzero-exit-classifies-as-no-result",
        "no-message-end-zero-exit-classifies-as-no-result",
        "noop-worker-classifies-as-missing-artifact-refs",
    ],
)
def test_pi_degraded_result_carries_diagnostic(tmp_path: Path, case: str) -> None:
    """Every degraded/noncompliant PI result carries a ``WorkerDiagnostic`` — the
    adapter never discards the evidence a noncompliant attempt produced (bug
    ``worker-noncompliance-block-carries-no-diagnostic-evidence``)."""
    if case == "no-message-end-nonzero-exit-classifies-as-no-result":

        def fake_runner(*args: object, **kwargs: Any) -> subprocess.CompletedProcess[str]:
            argv = args[0]
            assert isinstance(argv, list)
            return subprocess.CompletedProcess(argv, 1, stdout="", stderr="boom")

        adapter = PiHeadlessAdapter(
            PiHeadlessConfig(cwd=tmp_path, model="gpt-5.5", reasoning_effort="high"),
            runner=fake_runner,
            environ={},
        )
        result = adapter.run(_request())
        assert result.status is AgentRunStatus.FAILED
        assert result.diagnostic is not None
        assert result.diagnostic.runtime == "pi_headless"
        assert result.diagnostic.model == "gpt-5.5"
        assert result.diagnostic.requested_reasoning == "high"
        assert result.diagnostic.exit_code == 1
        assert result.diagnostic.parser_classification == "no-result"

    elif case == "no-message-end-zero-exit-classifies-as-no-result":

        def fake_runner(*args: object, **kwargs: Any) -> subprocess.CompletedProcess[str]:
            argv = args[0]
            assert isinstance(argv, list)
            return subprocess.CompletedProcess(argv, 0, stdout="not json at all", stderr="")

        adapter = PiHeadlessAdapter(
            PiHeadlessConfig(cwd=tmp_path, model="gpt-5.5"), runner=fake_runner, environ={}
        )
        result = adapter.run(_request())
        assert result.status is AgentRunStatus.SUCCEEDED
        assert result.diagnostic is not None
        assert result.diagnostic.exit_code == 0
        assert result.diagnostic.parser_classification == "no-result"
        assert "not json at all" in result.diagnostic.output_tail

    else:  # noop-worker-classifies-as-missing-artifact-refs
        payload = "I had nothing structured to emit."

        def fake_runner(*args: object, **kwargs: Any) -> subprocess.CompletedProcess[str]:
            argv = args[0]
            assert isinstance(argv, list)
            return subprocess.CompletedProcess(argv, 0, stdout=_message_end(payload), stderr="")

        adapter = PiHeadlessAdapter(
            PiHeadlessConfig(cwd=tmp_path, model="gpt-5.5"), runner=fake_runner, environ={}
        )
        result = adapter.run(_request(expected_schema="agent-run-result-v1"))
        assert result.status is AgentRunStatus.SUCCEEDED
        assert result.artifact_refs == ()
        assert result.diagnostic is not None
        assert result.diagnostic.parser_classification == "no-artifact-refs"
        assert payload in result.diagnostic.output_tail


def test_pi_compliant_result_carries_no_diagnostic(tmp_path: Path) -> None:
    """A normal compliant result (populated artifact_refs) attaches NO diagnostic — the
    field stays additive-optional and never pollutes the happy path."""

    def fake_runner(*args: object, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        argv = args[0]
        assert isinstance(argv, list)
        payload = json.dumps(
            {
                "schema": "agent-run-result-v1",
                "summary": "ok",
                "artifact_refs": [".dadaia/handoff/dadaia-workspace/x.handoff.json"],
                "structured_output": {"verdict": "APPROVED"},
            }
        )
        return subprocess.CompletedProcess(argv, 0, stdout=_message_end(payload), stderr="")

    adapter = PiHeadlessAdapter(PiHeadlessConfig(cwd=tmp_path), runner=fake_runner, environ={})
    result = adapter.run(_request(expected_schema="agent-run-result-v1"))
    assert result.status is AgentRunStatus.SUCCEEDED
    assert result.artifact_refs
    assert result.diagnostic is None


def test_pi_diagnostic_output_tail_is_redacted_and_bounded(tmp_path: Path) -> None:
    """The diagnostic's ``output_tail`` runs through the adapter's own redaction and is
    bounded (never an unbounded raw stdout dump)."""
    secret = "sk-anthropic-xyz"
    huge_tail = "x" * 10_000 + secret

    def fake_runner(*args: object, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        argv = args[0]
        assert isinstance(argv, list)
        return subprocess.CompletedProcess(argv, 0, stdout=huge_tail, stderr="")

    adapter = PiHeadlessAdapter(
        PiHeadlessConfig(cwd=tmp_path),
        runner=fake_runner,
        environ={"PATH": "/bin", "ANTHROPIC_API_KEY": secret},
    )
    result = adapter.run(_request())
    assert result.diagnostic is not None
    assert secret not in result.diagnostic.output_tail
    assert len(result.diagnostic.output_tail) <= 4096
