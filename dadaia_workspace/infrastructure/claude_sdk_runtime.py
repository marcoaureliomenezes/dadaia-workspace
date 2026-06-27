"""Claude Agent SDK runtime adapter for lifecycle worker requests.

The Claude Agent SDK (``claude-agent-sdk``) is an **optional, operator-installed
runtime extra** — intentionally NOT a locked workspace dependency, so the offline-first
build and lockfile stay intact. Install it in the runtime environment
(``pip install claude-agent-sdk``) to enable live Claude execution; the adapter lazily
imports it and fails with an actionable message when it is absent.

Ring-1 write boundary: the adapter derives a permission decider from the request's
allowed/forbidden paths using the SAME scope matching the runner's Ring-2 detective
check uses (:mod:`dadaia_workspace.core.scope_match`) and wires it into the
SDK's ``can_use_tool`` callback, so out-of-scope writes are denied before bytes hit
disk. The SDK transport is injectable (``query_fn``), so the permission logic and result
mapping are exercised hermetically without the package installed.

Live-verification note: the precise ``claude-agent-sdk`` binding (async ``query()``,
``can_use_tool`` → ``PermissionResultDeny``, terminal ``ResultMessage`` extraction) is
isolated in :func:`_default_query_fn`. It is bound against ``claude-agent-sdk`` v0.2.110
(verified by introspection) and driven from the synchronous adapter via ``asyncio.run``.
The opt-in live contract test (``tests/integration/claude_live/``, gated on
``DADAIA_CLAUDE_LIVE=1``) confirms it against a networked install; everything the engine
depends on — the Ring-1 decider and the ``AgentRunResult`` mapping — is provider-agnostic
and fully tested hermetically with an injected fake SDK module.
"""

from __future__ import annotations

import asyncio
import os
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dadaia_workspace.core.models.lifecycle import (
    AgentRunRequest,
    AgentRunResult,
    AgentRunStatus,
    AgentRuntimeKind,
)
from dadaia_workspace.core.scope_match import is_in_scope

# Reuse ONLY the transport-neutral parts of the shared headless-adapter base:
# secret redaction (CWE-209 parity) and the git seam type (changed_paths parity).
# The Claude SDK adapter is NOT subprocess-backed, so it deliberately does not
# inherit ``SubprocessAdapterMixin`` (no Runner / env-allowlist / prompt envelope).
from dadaia_workspace.infrastructure.headless_adapter_base import RedactionMixin

#: ``path -> may the worker write it?`` — the Ring-1 pre-disk decision.
WritePermission = Callable[[str], bool]

#: Tool-input keys that carry a write target for Write/Edit-family tools.
_WRITE_PATH_KEYS = ("file_path", "path", "notebook_path")


@dataclass(frozen=True)
class ClaudeRunOutput:
    """Harness-neutral capture of one Claude run, mapped to ``AgentRunResult``."""

    summary: str
    verdict: str | None = None
    artifact_refs: tuple[str, ...] = ()
    changed_paths: tuple[str, ...] = ()
    error: str | None = None


#: ``(prompt, write_permission) -> output`` — the injectable SDK transport seam.
ClaudeQueryFn = Callable[[str, WritePermission], ClaudeRunOutput]

_MISSING_SDK = (
    "Claude execution requires the optional `claude-agent-sdk` package, which is "
    "intentionally NOT a locked workspace dependency (offline-first build). Install it "
    "in the runtime environment (`pip install claude-agent-sdk`) to enable the Claude "
    "harness, or inject a query_fn for tests."
)


class ClaudeSdkAdapter(RedactionMixin):
    """``AgentRuntimePort`` backed by the Claude Agent SDK (optional runtime extra).

    Reuses the shared ``RedactionMixin`` (secret scrub of surfaced output) from the
    headless-adapter base for single-source CWE-209 parity with the CLI adapters,
    without inheriting any subprocess machinery (this adapter is SDK-backed, not a
    subprocess CLI).
    """

    def __init__(
        self,
        *,
        cwd: Path | None = None,
        query_fn: ClaudeQueryFn | None = None,
        environ: dict[str, str] | None = None,
    ) -> None:
        self._cwd = cwd or Path.cwd()
        self._query_fn = query_fn
        self._environ = dict(os.environ) if environ is None else dict(environ)

    def runtime_kind(self) -> AgentRuntimeKind:
        return AgentRuntimeKind.CLAUDE_SDK

    def write_permission(self, request: AgentRunRequest) -> WritePermission:
        """Ring-1 decider: may the worker write ``path``? Mirrors the runner's Ring-2 scope."""
        allowed = request.allowed_paths
        forbidden = request.forbidden_paths

        def _decide(path: str) -> bool:
            return is_in_scope(path, allowed=allowed, forbidden=forbidden)

        return _decide

    def run(self, request: AgentRunRequest) -> AgentRunResult:
        if request.runtime is not AgentRuntimeKind.CLAUDE_SDK:
            return AgentRunResult(
                status=AgentRunStatus.FAILED,
                summary="request runtime does not match ClaudeSdkAdapter",
                error=f"unsupported runtime: {request.runtime.value}",
            )
        query_fn = self._query_fn or self._bound_default_query_fn(request)
        permission = self.write_permission(request)
        try:
            output = query_fn(request.prompt, permission)
        except ImportError as exc:
            return AgentRunResult(
                status=AgentRunStatus.FAILED,
                summary="claude-agent-sdk not installed",
                error=self._redact(str(exc)),
            )
        except Exception as exc:  # a bounded worker never crashes the engine
            return AgentRunResult(
                status=AgentRunStatus.FAILED,
                summary="claude run failed",
                error=self._redact(str(exc)),
            )
        if output.error:
            return AgentRunResult(
                status=AgentRunStatus.FAILED,
                summary=self._redact(output.summary),
                error=self._redact(output.error),
            )
        structured: dict[str, str] = {}
        if output.verdict is not None:
            structured["verdict"] = output.verdict
        if output.changed_paths:
            structured["changed_paths"] = ",".join(output.changed_paths)
        return AgentRunResult(
            status=AgentRunStatus.SUCCEEDED,
            summary=self._redact(output.summary),
            artifact_refs=output.artifact_refs,
            structured_output=structured,
        )

    def _bound_default_query_fn(self, request: AgentRunRequest) -> ClaudeQueryFn:
        """Bind ``cwd``/``model`` (adapter-owned) into the default SDK transport."""
        cwd = self._cwd
        model = request.model_profile

        def _query(prompt: str, permission: WritePermission) -> ClaudeRunOutput:
            return _default_query_fn(prompt, permission, cwd=cwd, model=model)

        return _query


def _build_can_use_tool(permission: WritePermission, sdk: Any) -> Any:
    """Adapt the synchronous Ring-1 decider into the SDK's async ``can_use_tool``.

    The SDK calls ``can_use_tool(tool_name, tool_input, ctx)`` and awaits an
    ``allow``/``deny`` result. For Write/Edit-family tools we extract the write target
    from ``tool_input`` and deny — before bytes hit disk — when it is out of scope.
    Tools that carry no write path (reads, bash, etc.) are allowed; the runner's Ring-2
    git detective remains the backstop.
    """

    async def _can_use_tool(
        tool_name: str,
        tool_input: dict[str, Any],
        ctx: Any,  # noqa: ARG001 — SDK passes a ToolPermissionContext we do not need here
    ) -> Any:
        path = _write_target(tool_input)
        if path is not None and not permission(path):
            return sdk.PermissionResultDeny(
                message=(
                    f"Ring-1 write boundary: '{path}' is outside the worker's "
                    f"allowed write scope for tool '{tool_name}'."
                ),
                interrupt=False,
            )
        return sdk.PermissionResultAllow()

    return _can_use_tool


def _write_target(tool_input: dict[str, Any]) -> str | None:
    """Return the write path from a tool input payload, or ``None`` for non-writes."""
    if not isinstance(tool_input, dict):
        return None
    for key in _WRITE_PATH_KEYS:
        value = tool_input.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def _default_query_fn(
    prompt: str,
    permission: WritePermission,
    *,
    cwd: Path | None = None,
    model: str | None = None,
) -> ClaudeRunOutput:
    """Default transport: lazily import ``claude-agent-sdk`` and run one bounded query.

    Lazily imports the optional ``claude-agent-sdk`` (raising an actionable ``ImportError``
    when absent — the offline build never imports it at module load), wires the Ring-1
    ``permission`` decider into the SDK's async ``can_use_tool`` callback, drives the async
    ``query()`` iterator to completion via ``asyncio.run``, and maps the terminal
    ``ResultMessage`` (falling back to concatenated assistant text) into a
    ``ClaudeRunOutput``. Any SDK error is surfaced as ``ClaudeRunOutput.error`` so the
    adapter maps it to a ``FAILED`` result.
    """
    try:
        import claude_agent_sdk as sdk
    except ImportError as exc:
        raise ImportError(_MISSING_SDK) from exc

    options = sdk.ClaudeAgentOptions(
        model=model,
        cwd=cwd,
        # ``can_use_tool`` is only consulted under the 'default' permission mode; the
        # other modes (acceptEdits/bypassPermissions/...) would bypass the Ring-1 decider.
        permission_mode="default",
        can_use_tool=_build_can_use_tool(permission, sdk),
    )

    try:
        return asyncio.run(_run_query(sdk, prompt, options))
    except (
        sdk.CLINotFoundError,
        sdk.CLIConnectionError,
        sdk.ProcessError,
        sdk.ClaudeSDKError,
    ) as exc:
        return ClaudeRunOutput(summary="claude-agent-sdk run failed", error=str(exc))


async def _run_query(sdk: Any, prompt: str, options: Any) -> ClaudeRunOutput:
    """Consume the async ``query()`` iterator, collecting assistant text + terminal result.

    The authoritative end is the terminal ``ResultMessage`` (mirrors PI's ``message_end``):
    its ``is_error`` flag decides success/failure and its ``result``/``structured_output``
    feed the summary. Assistant ``TextBlock`` text is concatenated as a fallback summary.
    """
    assistant_text_parts: list[str] = []
    result_message: Any = None

    async for message in sdk.query(prompt=prompt, options=options):
        if isinstance(message, sdk.AssistantMessage):
            assistant_text_parts.append(_assistant_text(message, sdk))
        elif isinstance(message, sdk.ResultMessage):
            result_message = message

    assistant_text = "".join(assistant_text_parts).strip()

    if result_message is not None:
        if getattr(result_message, "is_error", False):
            errors = getattr(result_message, "errors", None)
            error = "; ".join(errors) if errors else (result_message.result or "claude run error")
            return ClaudeRunOutput(summary="claude-agent-sdk reported an error", error=error)
        summary = result_message.result or assistant_text or "claude run completed"
        verdict = _verdict_from_structured(result_message.structured_output)
        return ClaudeRunOutput(summary=summary, verdict=verdict)

    return ClaudeRunOutput(summary=assistant_text or "claude run completed")


def _assistant_text(message: Any, sdk: Any) -> str:
    """Concatenate ``TextBlock.text`` from an ``AssistantMessage.content`` block list."""
    content = getattr(message, "content", None)
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""
    parts: list[str] = []
    for block in content:
        if isinstance(block, sdk.TextBlock):
            parts.append(block.text)
    return "".join(parts)


def _verdict_from_structured(structured: Any) -> str | None:
    """Pull a ``verdict`` field out of the terminal ``structured_output`` when present."""
    if isinstance(structured, dict):
        value = structured.get("verdict")
        if isinstance(value, str):
            return value
    return None
