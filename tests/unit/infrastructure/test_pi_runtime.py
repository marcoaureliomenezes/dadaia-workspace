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
# T-PI-02 — minimal adapter: kind, command, env, failure handling
# ---------------------------------------------------------------------------


def test_pi_adapter_runtime_kind() -> None:
    adapter = PiHeadlessAdapter(PiHeadlessConfig(cwd=Path("/tmp")), runner=lambda *a, **k: None)
    assert adapter.runtime_kind() is AgentRuntimeKind.PI_HEADLESS


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


def test_pi_adapter_discrete_model_reaches_pi_model_flag(tmp_path: Path) -> None:
    """WS-2 (LAW 2): the discrete GPT model id reaches ``pi --model <id>``.

    Built via the container seam ``build_agent_runtime(PI_HEADLESS, model=...)`` to prove
    the discrete catalog option threads all the way to the command.
    """
    from dadaia_workspace import container
    from dadaia_workspace.core.harness_models import validate
    from dadaia_workspace.core.models.lifecycle import AgentRuntimeKind as _Kind
    from dadaia_workspace.infrastructure.pi_runtime import PiHeadlessAdapter

    captured: dict[str, list[str]] = {}

    def fake_runner(*args: object, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        argv = args[0]
        assert isinstance(argv, list)
        captured["argv"] = argv
        return subprocess.CompletedProcess(argv, 0, stdout=_message_end("ok"))

    option = validate("pi", "gpt-5.3-codex:medium")
    adapter = container.build_agent_runtime(_Kind.PI_HEADLESS, cwd=tmp_path, model=option)
    assert isinstance(adapter, PiHeadlessAdapter)
    # Re-bind the runner onto the container-built adapter (it owns a real config).
    adapter._runner = fake_runner  # type: ignore[attr-defined]
    adapter._environ = {}  # type: ignore[attr-defined]
    adapter._git = None  # type: ignore[attr-defined]
    adapter.run(_request())

    argv = captured["argv"]
    assert argv[argv.index("--model") : argv.index("--model") + 2] == ["--model", "gpt-5.3-codex"]


def test_pi_config_carries_effort_for_observability(tmp_path: Path) -> None:
    """The discrete option's effort is recorded on the config even though PI has no
    verified effort flag (WS-2 limitation note)."""
    from dadaia_workspace import container
    from dadaia_workspace.core.harness_models import validate
    from dadaia_workspace.core.models.lifecycle import AgentRuntimeKind as _Kind
    from dadaia_workspace.infrastructure.pi_runtime import PiHeadlessAdapter

    option = validate("pi", "gpt-5.5:low")
    adapter = container.build_agent_runtime(_Kind.PI_HEADLESS, cwd=tmp_path, model=option)
    assert isinstance(adapter, PiHeadlessAdapter)
    assert adapter._config.model == "gpt-5.5"  # type: ignore[attr-defined]
    assert adapter._config.reasoning_effort == "low"  # type: ignore[attr-defined]


def test_pi_adapter_omits_model_flag_when_unset(tmp_path: Path) -> None:
    captured: dict[str, list[str]] = {}

    def fake_runner(*args: object, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        argv = args[0]
        assert isinstance(argv, list)
        captured["argv"] = argv
        return subprocess.CompletedProcess(argv, 0, stdout=_message_end("ok"))

    PiHeadlessAdapter(PiHeadlessConfig(cwd=tmp_path), runner=fake_runner, environ={}).run(
        _request()
    )
    assert "--model" not in captured["argv"]


def test_pi_adapter_rejects_wrong_runtime_without_calling_pi(tmp_path: Path) -> None:
    called = False

    def fake_runner(*args: object, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        nonlocal called
        called = True
        return subprocess.CompletedProcess([], 0)

    result = PiHeadlessAdapter(PiHeadlessConfig(cwd=tmp_path), runner=fake_runner, environ={}).run(
        _request(runtime=AgentRuntimeKind.FAKE)
    )

    assert result.status is AgentRunStatus.FAILED
    assert called is False


def test_pi_adapter_timeout_returns_failed(tmp_path: Path) -> None:
    def fake_runner(*args: object, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        raise subprocess.TimeoutExpired(cmd="pi", timeout=900)

    result = PiHeadlessAdapter(PiHeadlessConfig(cwd=tmp_path), runner=fake_runner, environ={}).run(
        _request()
    )

    assert result.status is AgentRunStatus.FAILED
    assert "timed out" in result.summary


def test_pi_adapter_oserror_returns_failed(tmp_path: Path) -> None:
    def fake_runner(*args: object, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        raise OSError("pi binary not found")

    result = PiHeadlessAdapter(PiHeadlessConfig(cwd=tmp_path), runner=fake_runner, environ={}).run(
        _request()
    )

    assert result.status is AgentRunStatus.FAILED
    assert "failed to start" in result.summary


def test_pi_adapter_nonzero_exit_with_no_output_returns_failed(tmp_path: Path) -> None:
    def fake_runner(*args: object, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        argv = args[0]
        assert isinstance(argv, list)
        return subprocess.CompletedProcess(argv, 1, stdout="", stderr="boom")

    result = PiHeadlessAdapter(PiHeadlessConfig(cwd=tmp_path), runner=fake_runner, environ={}).run(
        _request()
    )

    assert result.status is AgentRunStatus.FAILED
    assert "boom" in (result.error or "")


def test_pi_adapter_redacts_anthropic_api_key_from_error(tmp_path: Path) -> None:
    def fake_runner(*args: object, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        argv = args[0]
        assert isinstance(argv, list)
        return subprocess.CompletedProcess(argv, 1, stdout="", stderr="failed: sk-anthropic-xyz")

    result = PiHeadlessAdapter(
        PiHeadlessConfig(cwd=tmp_path),
        runner=fake_runner,
        environ={"PATH": "/bin", "ANTHROPIC_API_KEY": "sk-anthropic-xyz"},
    ).run(_request())

    assert result.status is AgentRunStatus.FAILED
    assert result.error == "failed: [REDACTED]"
    assert "sk-anthropic-xyz" not in (result.error or "")


def test_pi_adapter_redacts_anthropic_api_key_from_summary(tmp_path: Path) -> None:
    def fake_runner(*args: object, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        argv = args[0]
        assert isinstance(argv, list)
        return subprocess.CompletedProcess(
            argv, 0, stdout=_message_end("leaked sk-anthropic-xyz here")
        )

    result = PiHeadlessAdapter(
        PiHeadlessConfig(cwd=tmp_path),
        runner=fake_runner,
        environ={"PATH": "/bin", "ANTHROPIC_API_KEY": "sk-anthropic-xyz"},
    ).run(_request())

    assert result.status is AgentRunStatus.SUCCEEDED
    assert "sk-anthropic-xyz" not in result.summary
    assert "[REDACTED]" in result.summary


# ---------------------------------------------------------------------------
# T-PI-05 — result extraction hardening
# ---------------------------------------------------------------------------


def test_pi_adapter_last_message_end_wins(tmp_path: Path) -> None:
    stream = "\n".join(
        [
            json.dumps({"type": "message_start", "message": {}}),
            _message_end("first draft"),
            json.dumps({"type": "tool_use", "name": "edit"}),
            _message_end("FINAL ANSWER"),
        ]
    )

    def fake_runner(*args: object, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        argv = args[0]
        assert isinstance(argv, list)
        return subprocess.CompletedProcess(argv, 0, stdout=stream)

    result = PiHeadlessAdapter(PiHeadlessConfig(cwd=tmp_path), runner=fake_runner, environ={}).run(
        _request()
    )

    assert result.status is AgentRunStatus.SUCCEEDED
    assert result.summary == "FINAL ANSWER"


def test_pi_adapter_content_as_block_array(tmp_path: Path) -> None:
    content = [
        {"type": "text", "text": "block one. "},
        {"type": "text", "text": "block two."},
    ]

    def fake_runner(*args: object, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        argv = args[0]
        assert isinstance(argv, list)
        return subprocess.CompletedProcess(argv, 0, stdout=_message_end(content))

    result = PiHeadlessAdapter(PiHeadlessConfig(cwd=tmp_path), runner=fake_runner, environ={}).run(
        _request()
    )

    assert result.status is AgentRunStatus.SUCCEEDED
    assert result.summary == "block one. block two."


def test_pi_adapter_unparseable_line_degrades_to_summary(tmp_path: Path) -> None:
    stream = "this is not json at all\n{also broken"

    def fake_runner(*args: object, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        argv = args[0]
        assert isinstance(argv, list)
        return subprocess.CompletedProcess(argv, 0, stdout=stream)

    result = PiHeadlessAdapter(PiHeadlessConfig(cwd=tmp_path), runner=fake_runner, environ={}).run(
        _request()
    )

    assert result.status is AgentRunStatus.SUCCEEDED
    assert "not json" in result.summary


def test_pi_adapter_no_message_end_degrades_to_summary(tmp_path: Path) -> None:
    stream = "\n".join(
        [
            json.dumps({"type": "message_start", "message": {}}),
            json.dumps({"type": "tool_use", "name": "edit"}),
        ]
    )

    def fake_runner(*args: object, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        argv = args[0]
        assert isinstance(argv, list)
        return subprocess.CompletedProcess(argv, 0, stdout=stream)

    result = PiHeadlessAdapter(PiHeadlessConfig(cwd=tmp_path), runner=fake_runner, environ={}).run(
        _request()
    )

    assert result.status is AgentRunStatus.SUCCEEDED
    assert result.summary.strip() != ""


def test_pi_adapter_fenced_json_verdict_populates_structured_output(tmp_path: Path) -> None:
    fenced = (
        "Review complete.\n"
        "```json\n"
        + json.dumps(
            {
                "schema": "agent-run-result-v1",
                "verdict": "APPROVED",
                "commit_sha": "abc123",
                "summary": "looks good",
                "artifact_refs": [".dadaia/handoff/dadaia-workspace/x.handoff.json"],
            }
        )
        + "\n```\n"
    )

    def fake_runner(*args: object, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        argv = args[0]
        assert isinstance(argv, list)
        return subprocess.CompletedProcess(argv, 0, stdout=_message_end(fenced))

    result = PiHeadlessAdapter(PiHeadlessConfig(cwd=tmp_path), runner=fake_runner, environ={}).run(
        _request(expected_schema="agent-run-result-v1")
    )

    assert result.status is AgentRunStatus.SUCCEEDED
    assert result.structured_output["verdict"] == "APPROVED"
    assert result.structured_output["commit_sha"] == "abc123"
    assert result.summary == "looks good"
    assert result.artifact_refs == (".dadaia/handoff/dadaia-workspace/x.handoff.json",)


def test_pi_adapter_fenced_json_ignored_when_schema_mismatch(tmp_path: Path) -> None:
    fenced = "```json\n" + json.dumps({"schema": "other-schema", "verdict": "APPROVED"}) + "\n```"

    def fake_runner(*args: object, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        argv = args[0]
        assert isinstance(argv, list)
        return subprocess.CompletedProcess(argv, 0, stdout=_message_end(fenced))

    result = PiHeadlessAdapter(PiHeadlessConfig(cwd=tmp_path), runner=fake_runner, environ={}).run(
        _request(expected_schema="agent-run-result-v1")
    )

    assert result.status is AgentRunStatus.SUCCEEDED
    assert "verdict" not in result.structured_output


def test_pi_adapter_bare_json_result_without_fence_is_parsed(tmp_path: Path) -> None:
    """Real-worker tolerance (v0.1.31 R3 / C-02): a bare JSON object (no ```json fence).

    pi runs on the operator's OpenAI Codex subscription; gpt-5.x reliably emits the result
    object but frequently leaves it UNFENCED — the whole final message is the object. The
    strict fenced-only parse silently dropped it (live e2e: "agent result missing artifact
    evidence"). The hardened extractor accepts the whole stripped message as JSON.
    """
    bare = json.dumps(
        {
            "schema": "agent-run-result-v1",
            "status": "succeeded",
            "summary": "scope approved",
            "artifact_refs": [".dadaia/handoff/dadaia-workspace/scope.handoff.json"],
            "structured_output": {"verdict": "APPROVED"},
        }
    )

    def fake_runner(*args: object, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        argv = args[0]
        assert isinstance(argv, list)
        return subprocess.CompletedProcess(argv, 0, stdout=_message_end(bare))

    result = PiHeadlessAdapter(PiHeadlessConfig(cwd=tmp_path), runner=fake_runner, environ={}).run(
        _request(expected_schema="agent-run-result-v1")
    )

    assert result.status is AgentRunStatus.SUCCEEDED
    assert result.structured_output["verdict"] == "APPROVED"
    assert result.summary == "scope approved"
    assert result.artifact_refs == (".dadaia/handoff/dadaia-workspace/scope.handoff.json",)


def test_pi_adapter_bare_json_accepted_structurally_without_schema_field(tmp_path: Path) -> None:
    """Structural acceptance: the worker omits the top-level ``schema`` label entirely.

    Observed live: across runs gpt-5.5 inconsistently labels the ``schema`` field — one run
    carried ``schema: agent-run-result-v1``, the next omitted it and nested
    ``output_schema: release-scope-handoff-v1`` instead. Rather than BLOCK a correct result
    on a label mismatch, a payload that structurally IS the result (non-empty
    ``artifact_refs`` + ``status``/``summary``/``structured_output``) is accepted.
    """
    bare = json.dumps(
        {
            "status": "succeeded",
            "summary": "scope approved",
            "artifact_refs": [".dadaia/handoff/dadaia-workspace/scope.handoff.json"],
            "structured_output": {
                "verdict": "APPROVED",
                "output_schema": "release-scope-handoff-v1",
            },
        }
    )

    def fake_runner(*args: object, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        argv = args[0]
        assert isinstance(argv, list)
        return subprocess.CompletedProcess(argv, 0, stdout=_message_end(bare))

    result = PiHeadlessAdapter(PiHeadlessConfig(cwd=tmp_path), runner=fake_runner, environ={}).run(
        _request(expected_schema="agent-run-result-v1")
    )

    assert result.status is AgentRunStatus.SUCCEEDED
    assert result.structured_output["verdict"] == "APPROVED"
    assert result.artifact_refs == (".dadaia/handoff/dadaia-workspace/scope.handoff.json",)


def test_pi_adapter_bare_json_without_result_shape_is_rejected(tmp_path: Path) -> None:
    """Tolerance does not over-accept: arbitrary JSON lacking the result shape is dropped.

    A schema-mismatched object with NO ``artifact_refs`` is not the result object — the
    structural path requires a non-empty ``artifact_refs`` list, so it stays rejected.
    """
    bare = json.dumps({"schema": "something-else", "note": "not a result", "verdict": "APPROVED"})

    def fake_runner(*args: object, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        argv = args[0]
        assert isinstance(argv, list)
        return subprocess.CompletedProcess(argv, 0, stdout=_message_end(bare))

    result = PiHeadlessAdapter(PiHeadlessConfig(cwd=tmp_path), runner=fake_runner, environ={}).run(
        _request(expected_schema="agent-run-result-v1")
    )

    assert result.status is AgentRunStatus.SUCCEEDED
    assert "verdict" not in result.structured_output


# ---------------------------------------------------------------------------
# T-PI-06 — changed_paths from a FAKED git diff (never a model claim)
# ---------------------------------------------------------------------------


def test_pi_adapter_changed_paths_from_git_diff(tmp_path: Path) -> None:
    fake_git = _FakeGit(changed=("src/a.py", "src/b.py"))

    def fake_runner(*args: object, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        argv = args[0]
        assert isinstance(argv, list)
        return subprocess.CompletedProcess(argv, 0, stdout=_message_end("done"))

    result = PiHeadlessAdapter(
        PiHeadlessConfig(cwd=tmp_path), runner=fake_runner, environ={}, git=fake_git
    ).run(_request())

    assert result.status is AgentRunStatus.SUCCEEDED
    assert result.structured_output["changed_paths"] == "src/a.py,src/b.py"
    assert fake_git.calls == [tmp_path]


def test_pi_adapter_changed_paths_empty_when_no_diff(tmp_path: Path) -> None:
    fake_git = _FakeGit(changed=())

    def fake_runner(*args: object, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        argv = args[0]
        assert isinstance(argv, list)
        return subprocess.CompletedProcess(argv, 0, stdout=_message_end("done"))

    result = PiHeadlessAdapter(
        PiHeadlessConfig(cwd=tmp_path), runner=fake_runner, environ={}, git=fake_git
    ).run(_request())

    assert result.status is AgentRunStatus.SUCCEEDED
    assert result.structured_output.get("changed_paths", "") == ""


# ---------------------------------------------------------------------------
# T-28-A-06 — per-request resolved model reaches `pi --model` (AC-12)
# ---------------------------------------------------------------------------


def test_pi_per_request_resolved_model_reaches_command(tmp_path: Path) -> None:
    """The policy-resolved per-request model wins and is passed as ``pi --model <id>``."""
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

    # Construction-time model is one value; the per-request resolved model must override.
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


def test_pi_no_model_flag_when_neither_request_nor_config(tmp_path: Path) -> None:
    captured: list[list[str]] = []

    def fake_runner(*args: object, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        argv = args[0]
        assert isinstance(argv, list)
        captured.append(argv)
        return subprocess.CompletedProcess(argv, 0, stdout=_message_end("done"))

    PiHeadlessAdapter(PiHeadlessConfig(cwd=tmp_path), runner=fake_runner, environ={}).run(
        _request()
    )

    assert "--model" not in captured[0]
