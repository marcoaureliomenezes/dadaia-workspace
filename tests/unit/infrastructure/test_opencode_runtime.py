"""Unit tests for the headless OpenCode runtime adapter (`opencode run --format json`).

Mirrors ``test_pi_runtime.py``. The runner is injected and fully faked — no live
``opencode`` binary, no network. The one upstream-owned seam (the success-path
event schema) is verified only on the operator's live run (ADR-23-2); here it is
covered defensively across multiple plausible message/part shapes, and the
verified ``error`` event shape is asserted directly. The live verification lives
behind the opt-in ``tests/integration/opencode_live/`` seam.
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
from dadaia_workspace.core.protocols.agent_runtime import AgentRuntimePort
from dadaia_workspace.infrastructure.opencode_runtime import OpenCodeAdapter, OpenCodeConfig


def _request(
    *,
    runtime: AgentRuntimeKind = AgentRuntimeKind.OPENCODE_RUN,
    prompt: str = "Do bounded work and return text.",
) -> AgentRunRequest:
    return AgentRunRequest(
        role="software-engineer",
        prompt=prompt,
        runtime=runtime,
        context="dadaia-workspace",
        release_id="v0.1.23",
        task_id="T-23-07",
        allowed_paths=("src/**",),
        forbidden_paths=("secrets/**",),
        expected_schema="agent-run-result-v1",
        required_evidence=(GateEvidenceKind.HANDOFF,),
    )


def _text_part_event(text: str) -> str:
    """A message-part text event (one plausible upstream success shape)."""
    return json.dumps({"type": "message.part.updated", "part": {"type": "text", "text": text}})


def _error_event(message: str) -> str:
    """The VERIFIED opencode error event shape (invalid-model probe)."""
    return json.dumps(
        {
            "type": "error",
            "timestamp": 1782440437312,
            "sessionID": "ses_test",
            "error": {"name": "UnknownError", "data": {"message": message}},
        }
    )


class _FakeGit:
    """Fake GitSubprocessClient seam — returns a canned diff list per cwd snapshot."""

    def __init__(self, changed: tuple[str, ...] = ()) -> None:
        self._changed = changed
        self.calls: list[Path] = []

    def diff_name_only(self, path: Path) -> tuple[str, ...]:
        self.calls.append(path)
        return self._changed


# ---------------------------------------------------------------------------
# Port conformance + command/env
# ---------------------------------------------------------------------------


def test_opencode_adapter_satisfies_port() -> None:
    adapter = OpenCodeAdapter()
    assert isinstance(adapter, AgentRuntimePort)
    assert adapter.runtime_kind() is AgentRuntimeKind.OPENCODE_RUN


def test_opencode_adapter_builds_controlled_command_and_env(tmp_path: Path) -> None:
    calls: list[dict[str, Any]] = []

    def fake_runner(*args: object, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        argv = args[0]
        assert isinstance(argv, list)
        calls.append({"args": args, "kwargs": kwargs})
        return subprocess.CompletedProcess(argv, 0, stdout=_text_part_event("done"), stderr="")

    adapter = OpenCodeAdapter(
        config=OpenCodeConfig(cwd=tmp_path, opencode_bin="/usr/bin/opencode", model="nvidia/x"),
        runner=fake_runner,
        environ={
            "PATH": "/bin",
            "HOME": "/home/operator",
            "OPENCODE_SERVER_PASSWORD": "hunter2",
            "DADAIA_PRIVATE": "private",
        },
    )

    result = adapter.run(_request(prompt="please ping"))

    assert result.status is AgentRunStatus.SUCCEEDED
    call = calls[0]
    argv = call["args"][0]
    assert isinstance(argv, list)
    assert argv[0] == "/usr/bin/opencode"
    assert argv[1] == "run"
    assert argv[argv.index("--format") : argv.index("--format") + 2] == ["--format", "json"]
    assert argv[argv.index("--model") : argv.index("--model") + 2] == ["--model", "nvidia/x"]
    # Prompt is the trailing positional (no shell interpolation).
    assert argv[-1] == "please ping"
    assert call["kwargs"]["cwd"] == tmp_path
    # Env is filtered to the allowlist only; DADAIA_PRIVATE is dropped.
    assert call["kwargs"]["env"] == {
        "PATH": "/bin",
        "HOME": "/home/operator",
        "OPENCODE_SERVER_PASSWORD": "hunter2",
    }


def test_opencode_adapter_omits_model_flag_when_unset(tmp_path: Path) -> None:
    captured: dict[str, list[str]] = {}

    def fake_runner(*args: object, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        argv = args[0]
        assert isinstance(argv, list)
        captured["argv"] = argv
        return subprocess.CompletedProcess(argv, 0, stdout=_text_part_event("ok"))

    OpenCodeAdapter(config=OpenCodeConfig(cwd=tmp_path), runner=fake_runner, environ={}).run(
        _request()
    )
    assert "--model" not in captured["argv"]


# ---------------------------------------------------------------------------
# Failure handling
# ---------------------------------------------------------------------------


def test_opencode_adapter_rejects_wrong_runtime_without_calling_opencode(tmp_path: Path) -> None:
    called = False

    def fake_runner(*args: object, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        nonlocal called
        called = True
        return subprocess.CompletedProcess([], 0)

    result = OpenCodeAdapter(
        config=OpenCodeConfig(cwd=tmp_path), runner=fake_runner, environ={}
    ).run(_request(runtime=AgentRuntimeKind.FAKE))

    assert result.status is AgentRunStatus.FAILED
    assert called is False
    assert "does not match" in result.summary


def test_opencode_adapter_timeout_returns_failed(tmp_path: Path) -> None:
    def fake_runner(*args: object, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        raise subprocess.TimeoutExpired(cmd="opencode", timeout=900)

    result = OpenCodeAdapter(
        config=OpenCodeConfig(cwd=tmp_path), runner=fake_runner, environ={}
    ).run(_request())

    assert result.status is AgentRunStatus.FAILED
    assert "timed out" in result.summary


def test_opencode_adapter_oserror_returns_failed(tmp_path: Path) -> None:
    def fake_runner(*args: object, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        raise OSError("opencode binary not found")

    result = OpenCodeAdapter(
        config=OpenCodeConfig(cwd=tmp_path), runner=fake_runner, environ={}
    ).run(_request())

    assert result.status is AgentRunStatus.FAILED
    assert "failed to start" in result.summary


def test_opencode_adapter_nonzero_exit_with_no_output_returns_failed(tmp_path: Path) -> None:
    def fake_runner(*args: object, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        argv = args[0]
        assert isinstance(argv, list)
        return subprocess.CompletedProcess(argv, 1, stdout="", stderr="boom")

    result = OpenCodeAdapter(
        config=OpenCodeConfig(cwd=tmp_path), runner=fake_runner, environ={}
    ).run(_request())

    assert result.status is AgentRunStatus.FAILED
    assert "boom" in (result.error or "")


def test_opencode_adapter_error_event_maps_to_failed(tmp_path: Path) -> None:
    """The VERIFIED error event (invalid-model probe) maps to FAILED with its message."""
    stream = "\n".join(
        [
            _text_part_event("partial work"),
            _error_event("Model not found: invalid/invalid."),
        ]
    )

    def fake_runner(*args: object, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        argv = args[0]
        assert isinstance(argv, list)
        # opencode returns exit 0 even on a stream-reported error.
        return subprocess.CompletedProcess(argv, 0, stdout=stream)

    result = OpenCodeAdapter(
        config=OpenCodeConfig(cwd=tmp_path), runner=fake_runner, environ={}
    ).run(_request())

    assert result.status is AgentRunStatus.FAILED
    assert "Model not found" in (result.error or "")


# ---------------------------------------------------------------------------
# Success-path text harvesting (defensive, ADR-23-2)
# ---------------------------------------------------------------------------


def test_opencode_adapter_harvests_text_from_part_events(tmp_path: Path) -> None:
    stream = "\n".join(
        [
            json.dumps({"type": "session.updated", "info": {"id": "ses_x"}}),
            _text_part_event("hello "),
            _text_part_event("world"),
            json.dumps({"type": "step.finished"}),
        ]
    )

    def fake_runner(*args: object, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        argv = args[0]
        assert isinstance(argv, list)
        return subprocess.CompletedProcess(argv, 0, stdout=stream)

    result = OpenCodeAdapter(
        config=OpenCodeConfig(cwd=tmp_path), runner=fake_runner, environ={}
    ).run(_request())

    assert result.status is AgentRunStatus.SUCCEEDED
    assert result.summary == "hello world"


def test_opencode_adapter_harvests_text_from_content_block_array(tmp_path: Path) -> None:
    """An alternate plausible shape: message.content is a content-block list."""
    event = json.dumps(
        {
            "type": "message.updated",
            "message": {
                "role": "assistant",
                "content": [
                    {"type": "text", "text": "block one. "},
                    {"type": "text", "text": "block two."},
                ],
            },
        }
    )

    def fake_runner(*args: object, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        argv = args[0]
        assert isinstance(argv, list)
        return subprocess.CompletedProcess(argv, 0, stdout=event)

    result = OpenCodeAdapter(
        config=OpenCodeConfig(cwd=tmp_path), runner=fake_runner, environ={}
    ).run(_request())

    assert result.status is AgentRunStatus.SUCCEEDED
    assert result.summary == "block one. block two."


def test_opencode_adapter_malformed_lines_degrade_to_summary(tmp_path: Path) -> None:
    """Non-JSON / garbage lines are tolerated; never crash, never raise."""
    stream = "this is not json at all\n{also broken\n[]"

    def fake_runner(*args: object, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        argv = args[0]
        assert isinstance(argv, list)
        return subprocess.CompletedProcess(argv, 0, stdout=stream)

    result = OpenCodeAdapter(
        config=OpenCodeConfig(cwd=tmp_path), runner=fake_runner, environ={}
    ).run(_request())

    assert result.status is AgentRunStatus.SUCCEEDED
    assert "not json" in result.summary


def test_opencode_adapter_no_text_degrades_to_summary(tmp_path: Path) -> None:
    stream = "\n".join(
        [
            json.dumps({"type": "session.updated", "info": {"id": "ses_x"}}),
            json.dumps({"type": "step.finished"}),
        ]
    )

    def fake_runner(*args: object, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        argv = args[0]
        assert isinstance(argv, list)
        return subprocess.CompletedProcess(argv, 0, stdout=stream)

    result = OpenCodeAdapter(
        config=OpenCodeConfig(cwd=tmp_path), runner=fake_runner, environ={}
    ).run(_request())

    assert result.status is AgentRunStatus.SUCCEEDED
    assert result.summary.strip() != ""


# ---------------------------------------------------------------------------
# Secret redaction
# ---------------------------------------------------------------------------


def test_opencode_adapter_redacts_secret_from_error(tmp_path: Path) -> None:
    stream = _error_event("auth failed for token sk-opencode-xyz")

    def fake_runner(*args: object, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        argv = args[0]
        assert isinstance(argv, list)
        return subprocess.CompletedProcess(argv, 0, stdout=stream)

    result = OpenCodeAdapter(
        config=OpenCodeConfig(cwd=tmp_path),
        runner=fake_runner,
        environ={"PATH": "/bin", "OPENCODE_API_KEY": "sk-opencode-xyz"},
    ).run(_request())

    assert result.status is AgentRunStatus.FAILED
    assert "sk-opencode-xyz" not in (result.error or "")
    assert "[REDACTED]" in (result.error or "")


def test_opencode_adapter_redacts_secret_from_summary(tmp_path: Path) -> None:
    def fake_runner(*args: object, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        argv = args[0]
        assert isinstance(argv, list)
        return subprocess.CompletedProcess(
            argv, 0, stdout=_text_part_event("leaked sk-opencode-xyz here")
        )

    result = OpenCodeAdapter(
        config=OpenCodeConfig(cwd=tmp_path),
        runner=fake_runner,
        environ={"PATH": "/bin", "OPENCODE_API_KEY": "sk-opencode-xyz"},
    ).run(_request())

    assert result.status is AgentRunStatus.SUCCEEDED
    assert "sk-opencode-xyz" not in result.summary
    assert "[REDACTED]" in result.summary


# ---------------------------------------------------------------------------
# changed_paths from a FAKED git diff (never a model claim)
# ---------------------------------------------------------------------------


def test_opencode_adapter_changed_paths_from_git_diff(tmp_path: Path) -> None:
    fake_git = _FakeGit(changed=("src/a.py", "src/b.py"))

    def fake_runner(*args: object, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        argv = args[0]
        assert isinstance(argv, list)
        return subprocess.CompletedProcess(argv, 0, stdout=_text_part_event("done"))

    result = OpenCodeAdapter(
        config=OpenCodeConfig(cwd=tmp_path), runner=fake_runner, environ={}, git=fake_git
    ).run(_request())

    assert result.status is AgentRunStatus.SUCCEEDED
    assert result.structured_output["changed_paths"] == "src/a.py,src/b.py"
    assert fake_git.calls == [tmp_path]


def test_opencode_adapter_changed_paths_empty_when_no_diff(tmp_path: Path) -> None:
    fake_git = _FakeGit(changed=())

    def fake_runner(*args: object, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        argv = args[0]
        assert isinstance(argv, list)
        return subprocess.CompletedProcess(argv, 0, stdout=_text_part_event("done"))

    result = OpenCodeAdapter(
        config=OpenCodeConfig(cwd=tmp_path), runner=fake_runner, environ={}, git=fake_git
    ).run(_request())

    assert result.status is AgentRunStatus.SUCCEEDED
    assert result.structured_output.get("changed_paths", "") == ""


def test_opencode_adapter_git_diff_overrides_self_reported_changed_paths(tmp_path: Path) -> None:
    """A worker self-report cannot win — the real git diff unconditionally overrides."""
    fake_git = _FakeGit(changed=("real/changed.py",))
    # Even if a part event smuggled a changed_paths claim, only git diff is honored.
    event = json.dumps(
        {"type": "message.part.updated", "part": {"type": "text", "text": "I changed evil.py"}}
    )

    def fake_runner(*args: object, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        argv = args[0]
        assert isinstance(argv, list)
        return subprocess.CompletedProcess(argv, 0, stdout=event)

    result = OpenCodeAdapter(
        config=OpenCodeConfig(cwd=tmp_path), runner=fake_runner, environ={}, git=fake_git
    ).run(_request())

    assert result.structured_output["changed_paths"] == "real/changed.py"
