"""Claude Agent SDK runtime adapter for lifecycle worker requests.

The Claude Agent SDK (``claude-agent-sdk``) is an **optional, operator-installed
runtime extra** — intentionally NOT a locked workspace dependency, so the offline-first
build and lockfile stay intact. Install it in the runtime environment
(``pip install claude-agent-sdk``) to enable live Claude execution; the adapter lazily
imports it and fails with an actionable message when it is absent.

Ring-1 write boundary: the adapter derives a permission decider from the request's
allowed/forbidden paths using the SAME scope matching the runner's Ring-2 detective
check uses (:mod:`dadaia_workspace.features.lifecycle.scope_match`) and wires it into the
SDK's ``can_use_tool`` callback, so out-of-scope writes are denied before bytes hit
disk. The SDK transport is injectable (``query_fn``), so the permission logic and result
mapping are exercised hermetically without the package installed.

Live-verification note: the precise ``claude-agent-sdk`` binding (``query()``,
``can_use_tool`` → ``PermissionResultDeny``) is isolated in :func:`_default_query_fn` and
must be confirmed against the installed SDK the first time the package is present in a
networked environment. Everything the engine depends on — the Ring-1 decider and the
``AgentRunResult`` mapping — is provider-agnostic and fully tested here.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from dadaia_workspace.core.models.lifecycle import (
    AgentRunRequest,
    AgentRunResult,
    AgentRunStatus,
    AgentRuntimeKind,
)
from dadaia_workspace.features.lifecycle.scope_match import is_in_scope

#: ``path -> may the worker write it?`` — the Ring-1 pre-disk decision.
WritePermission = Callable[[str], bool]


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


class ClaudeSdkAdapter:
    """``AgentRuntimePort`` backed by the Claude Agent SDK (optional runtime extra)."""

    def __init__(
        self,
        *,
        cwd: Path | None = None,
        query_fn: ClaudeQueryFn | None = None,
    ) -> None:
        self._cwd = cwd or Path.cwd()
        self._query_fn = query_fn

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
        query_fn = self._query_fn or _default_query_fn
        permission = self.write_permission(request)
        try:
            output = query_fn(request.prompt, permission)
        except ImportError as exc:
            return AgentRunResult(
                status=AgentRunStatus.FAILED,
                summary="claude-agent-sdk not installed",
                error=str(exc),
            )
        except Exception as exc:  # a bounded worker never crashes the engine
            return AgentRunResult(
                status=AgentRunStatus.FAILED,
                summary="claude run failed",
                error=str(exc),
            )
        if output.error:
            return AgentRunResult(
                status=AgentRunStatus.FAILED,
                summary=output.summary,
                error=output.error,
            )
        structured: dict[str, str] = {}
        if output.verdict is not None:
            structured["verdict"] = output.verdict
        if output.changed_paths:
            structured["changed_paths"] = ",".join(output.changed_paths)
        return AgentRunResult(
            status=AgentRunStatus.SUCCEEDED,
            summary=output.summary,
            artifact_refs=output.artifact_refs,
            structured_output=structured,
        )


def _default_query_fn(prompt: str, permission: WritePermission) -> ClaudeRunOutput:
    """Default transport: lazily import ``claude-agent-sdk`` and run one bounded query.

    Isolated for live API verification (see module docstring). Raises ``ImportError`` with
    an actionable message when the optional package is absent; when present, the precise
    SDK binding must be completed/verified against the installed API.
    """
    try:
        import claude_agent_sdk  # noqa: F401
    except ImportError as exc:
        raise ImportError(_MISSING_SDK) from exc
    # The exact query()/can_use_tool binding is verified on first networked install.
    raise NotImplementedError(  # pragma: no cover
        "claude-agent-sdk is installed but its live transport binding is pending "
        "first-install API verification; inject a query_fn or complete _default_query_fn "
        "against the installed SDK (wire `permission` into can_use_tool)."
    )
