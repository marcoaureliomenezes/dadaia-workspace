"""WS-4 — ClaudeSdkAdapter: Ring-1 write boundary + result mapping via injected transport.

The Claude Agent SDK is an optional operator-installed extra; these tests inject the
transport seam (`query_fn`) so the security-critical permission logic and the
AgentRunResult mapping are exercised without the package installed.
"""

from __future__ import annotations

import asyncio
import sys
from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass, field
from typing import Any

import pytest

from dadaia_workspace.core.models.lifecycle import (
    AgentRunRequest,
    AgentRunStatus,
    AgentRuntimeKind,
)
from dadaia_workspace.core.protocols.agent_runtime import AgentRuntimePort
from dadaia_workspace.infrastructure import claude_sdk_runtime
from dadaia_workspace.infrastructure.claude_sdk_runtime import (
    ClaudeRunOutput,
    ClaudeSdkAdapter,
    WritePermission,
    _build_can_use_tool,
    _default_query_fn,
)


def _request() -> AgentRunRequest:
    return AgentRunRequest(
        role="software-engineer",
        prompt="implement",
        runtime=AgentRuntimeKind.CLAUDE_SDK,
        context="dadaia-workspace",
        release_id="multiharness-engine-v0116",
        allowed_paths=(".dadaia/handoff/dadaia-workspace/**",),
        forbidden_paths=("repos/dadaia-workspace/secrets.py",),
    )


def test_adapter_satisfies_port() -> None:
    adapter = ClaudeSdkAdapter()
    assert isinstance(adapter, AgentRuntimePort)
    assert adapter.runtime_kind() is AgentRuntimeKind.CLAUDE_SDK


def test_ring1_write_permission_mirrors_scope() -> None:
    decide = ClaudeSdkAdapter().write_permission(_request())
    assert decide(".dadaia/handoff/dadaia-workspace/qa.handoff.json") is True
    assert decide("repos/dadaia-workspace/secrets.py") is False  # forbidden
    assert decide("repos/dadaia-workspace/src/app.py") is False  # outside allowed


def test_run_redacts_secret_env_value_from_surfaced_error() -> None:
    """CWE-209 parity: a secret-named env value must never surface in the error string,
    matching the codex redaction discipline."""
    secret = "sk-ant-supersecret-xyz"

    def _leaky_query(prompt: str, permission: WritePermission) -> ClaudeRunOutput:
        raise RuntimeError(f"connection failed using token {secret}")

    adapter = ClaudeSdkAdapter(
        query_fn=_leaky_query,
        environ={"ANTHROPIC_API_KEY": secret},
    )
    result = adapter.run(_request())
    assert result.status is AgentRunStatus.FAILED
    assert secret not in (result.error or "")
    assert "[REDACTED]" in (result.error or "")


def test_run_maps_approved_output_to_succeeded_result() -> None:
    def query_fn(prompt: str, permission: WritePermission) -> ClaudeRunOutput:
        # The transport is handed the Ring-1 decider; an out-of-scope write is denied.
        assert permission(".dadaia/handoff/dadaia-workspace/qa.handoff.json") is True
        assert permission("repos/dadaia-workspace/secrets.py") is False
        return ClaudeRunOutput(
            summary="done",
            verdict="APPROVED",
            artifact_refs=(".dadaia/handoff/dadaia-workspace/qa.handoff.json",),
            changed_paths=(".dadaia/handoff/dadaia-workspace/qa.handoff.json",),
        )

    result = ClaudeSdkAdapter(query_fn=query_fn).run(_request())
    assert result.status is AgentRunStatus.SUCCEEDED
    assert result.structured_output["verdict"] == "APPROVED"
    assert result.artifact_refs == (".dadaia/handoff/dadaia-workspace/qa.handoff.json",)
    assert result.structured_output["changed_paths"].endswith("qa.handoff.json")


def test_run_returns_failed_when_sdk_absent() -> None:
    def query_fn(prompt: str, permission: WritePermission) -> ClaudeRunOutput:
        raise ImportError("Claude execution requires the optional `claude-agent-sdk` package")

    result = ClaudeSdkAdapter(query_fn=query_fn).run(_request())
    assert result.status is AgentRunStatus.FAILED
    assert result.error is not None
    assert "claude-agent-sdk" in result.error


def test_run_rejects_mismatched_runtime() -> None:
    bad = AgentRunRequest(
        role="x",
        prompt="y",
        runtime=AgentRuntimeKind.CODEX_EXEC,
        context="c",
        release_id="r",
    )
    result = ClaudeSdkAdapter(query_fn=lambda p, perm: ClaudeRunOutput(summary="")).run(bad)
    assert result.status is AgentRunStatus.FAILED
    assert "unsupported runtime" in (result.error or "")


def test_run_propagates_transport_error_as_failed() -> None:
    def query_fn(prompt: str, permission: WritePermission) -> ClaudeRunOutput:
        return ClaudeRunOutput(summary="boom", error="model refused")

    result = ClaudeSdkAdapter(query_fn=query_fn).run(_request())
    assert result.status is AgentRunStatus.FAILED
    assert result.error == "model refused"


def test_module_does_not_import_the_sdk_at_load() -> None:
    assert "claude_agent_sdk" not in sys.modules


# --------------------------------------------------------------------------- #
# T-23-10 — permission wiring against a FAKE claude_agent_sdk module.          #
#                                                                             #
# The real SDK is an optional, network-bound extra absent from CI. These tests #
# inject a hermetic fake `claude_agent_sdk` into sys.modules so the security-  #
# critical `_default_query_fn` binding (can_use_tool → write_permission, async  #
# query() consumption, ResultMessage mapping, SDK-error mapping) is exercised   #
# WITHOUT the package and WITHOUT any network.                                  #
# --------------------------------------------------------------------------- #


@dataclass
class _FakePermissionResultAllow:
    behavior: str = "allow"
    updated_input: Any = None
    updated_permissions: Any = None


@dataclass
class _FakePermissionResultDeny:
    message: str = ""
    interrupt: bool = False
    behavior: str = "deny"


@dataclass
class _FakeTextBlock:
    text: str


@dataclass
class _FakeAssistantMessage:
    content: Any


@dataclass
class _FakeResultMessage:
    result: str | None = None
    is_error: bool = False
    structured_output: Any = None
    errors: list[str] | None = None


@dataclass
class _FakeClaudeAgentOptions:
    model: str | None = None
    cwd: Any = None
    permission_mode: str | None = None
    can_use_tool: Any = None


class _FakeClaudeSDKError(Exception):
    pass


class _FakeCLINotFoundError(_FakeClaudeSDKError):
    pass


class _FakeCLIConnectionError(_FakeClaudeSDKError):
    pass


class _FakeProcessError(_FakeClaudeSDKError):
    pass


@dataclass
class _FakeSdkModule:
    """A stand-in `claude_agent_sdk` module exposing exactly the surface used."""

    messages: list[Any] = field(default_factory=list)
    raise_on_query: Exception | None = None
    last_options: Any = None

    PermissionResultAllow = _FakePermissionResultAllow
    PermissionResultDeny = _FakePermissionResultDeny
    TextBlock = _FakeTextBlock
    AssistantMessage = _FakeAssistantMessage
    ResultMessage = _FakeResultMessage
    ClaudeAgentOptions = _FakeClaudeAgentOptions
    ClaudeSDKError = _FakeClaudeSDKError
    CLINotFoundError = _FakeCLINotFoundError
    CLIConnectionError = _FakeCLIConnectionError
    ProcessError = _FakeProcessError

    def query(self, *, prompt: str, options: Any) -> AsyncIterator[Any]:
        self.last_options = options

        async def _gen() -> AsyncIterator[Any]:
            if self.raise_on_query is not None:
                raise self.raise_on_query
            for message in self.messages:
                yield message

        return _gen()


@pytest.fixture
def fake_sdk(monkeypatch: pytest.MonkeyPatch) -> Iterator[_FakeSdkModule]:
    """Install a fake `claude_agent_sdk` so the lazy `import` inside the default
    transport resolves to it, without the real package or any network."""
    module = _FakeSdkModule()
    monkeypatch.setitem(sys.modules, "claude_agent_sdk", module)
    yield module


def test_can_use_tool_allows_in_scope_write(fake_sdk: _FakeSdkModule) -> None:
    decide = ClaudeSdkAdapter().write_permission(_request())
    can_use_tool = _build_can_use_tool(decide, fake_sdk)

    result = asyncio.run(
        can_use_tool(
            "Write",
            {"file_path": ".dadaia/handoff/dadaia-workspace/qa.handoff.json"},
            None,
        )
    )
    assert isinstance(result, _FakePermissionResultAllow)


def test_can_use_tool_denies_out_of_scope_write(fake_sdk: _FakeSdkModule) -> None:
    decide = ClaudeSdkAdapter().write_permission(_request())
    can_use_tool = _build_can_use_tool(decide, fake_sdk)

    result = asyncio.run(
        can_use_tool("Edit", {"file_path": "repos/dadaia-workspace/secrets.py"}, None)
    )
    assert isinstance(result, _FakePermissionResultDeny)
    assert "secrets.py" in result.message
    assert result.interrupt is False


def test_can_use_tool_allows_tool_without_write_path(fake_sdk: _FakeSdkModule) -> None:
    decide = ClaudeSdkAdapter().write_permission(_request())
    can_use_tool = _build_can_use_tool(decide, fake_sdk)

    # A read/bash tool carries no file_path — never blocked by Ring-1 (git Ring-2 backstop).
    result = asyncio.run(can_use_tool("Bash", {"command": "ls"}, None))
    assert isinstance(result, _FakePermissionResultAllow)


def test_default_query_fn_wires_permission_into_can_use_tool(fake_sdk: _FakeSdkModule) -> None:
    fake_sdk.messages = [
        _FakeAssistantMessage(content=[_FakeTextBlock(text="hello ")]),
        _FakeResultMessage(result="done", structured_output={"verdict": "APPROVED"}),
    ]
    decide = ClaudeSdkAdapter().write_permission(_request())

    output = _default_query_fn("go", decide, cwd=None, model="claude-opus-4-8")

    assert output.error is None
    assert output.summary == "done"
    assert output.verdict == "APPROVED"
    # The options carried our async can_use_tool and the default permission mode.
    assert fake_sdk.last_options.permission_mode == "default"
    assert fake_sdk.last_options.model == "claude-opus-4-8"
    can_use_tool = fake_sdk.last_options.can_use_tool
    denied = asyncio.run(
        can_use_tool("Write", {"file_path": "repos/dadaia-workspace/secrets.py"}, None)
    )
    assert isinstance(denied, _FakePermissionResultDeny)


def test_default_query_fn_falls_back_to_assistant_text(fake_sdk: _FakeSdkModule) -> None:
    fake_sdk.messages = [
        _FakeAssistantMessage(content=[_FakeTextBlock(text="just "), _FakeTextBlock(text="text")]),
    ]
    decide = ClaudeSdkAdapter().write_permission(_request())

    output = _default_query_fn("go", decide)
    assert output.error is None
    assert output.summary == "just text"


def test_default_query_fn_maps_result_error_to_failure(fake_sdk: _FakeSdkModule) -> None:
    fake_sdk.messages = [
        _FakeResultMessage(is_error=True, errors=["rate limited", "retry later"]),
    ]
    decide = ClaudeSdkAdapter().write_permission(_request())

    output = _default_query_fn("go", decide)
    assert output.error == "rate limited; retry later"


def test_default_query_fn_maps_sdk_exception_to_failure(fake_sdk: _FakeSdkModule) -> None:
    fake_sdk.raise_on_query = _FakeProcessError("cli crashed")
    decide = ClaudeSdkAdapter().write_permission(_request())

    output = _default_query_fn("go", decide)
    assert output.error is not None
    assert "cli crashed" in output.error


def test_adapter_run_uses_default_transport_through_fake_sdk(fake_sdk: _FakeSdkModule) -> None:
    """End-to-end: ClaudeSdkAdapter().run() with NO injected query_fn drives the default
    transport, which resolves the lazy `import claude_agent_sdk` to the fake module."""
    fake_sdk.messages = [
        _FakeResultMessage(result="ok", structured_output={"verdict": "APPROVED"}),
    ]
    result = ClaudeSdkAdapter().run(_request())
    assert result.status is AgentRunStatus.SUCCEEDED
    assert result.summary == "ok"
    assert result.structured_output["verdict"] == "APPROVED"


def test_default_query_fn_raises_actionable_import_error_when_absent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """With no `claude_agent_sdk` importable, the lazy import raises an actionable
    ImportError naming the optional extra — and the adapter maps it to FAILED."""
    monkeypatch.setitem(sys.modules, "claude_agent_sdk", None)  # force ImportError
    decide = ClaudeSdkAdapter().write_permission(_request())

    with pytest.raises(ImportError) as excinfo:
        _default_query_fn("go", decide)
    assert "claude-agent-sdk" in str(excinfo.value)

    result = ClaudeSdkAdapter().run(_request())
    assert result.status is AgentRunStatus.FAILED
    assert result.error is not None
    assert "claude-agent-sdk" in result.error


def test_default_transport_does_not_persist_sdk_import(monkeypatch: pytest.MonkeyPatch) -> None:
    """Even after a default-transport run, no real SDK was imported at module scope:
    the fake is the only `claude_agent_sdk` and it came from this test's injection."""
    module = _FakeSdkModule(messages=[_FakeResultMessage(result="ok")])
    monkeypatch.setitem(sys.modules, "claude_agent_sdk", module)
    assert claude_sdk_runtime.__name__  # module loaded without importing the SDK
    result = ClaudeSdkAdapter().run(_request())
    assert result.status is AgentRunStatus.SUCCEEDED
