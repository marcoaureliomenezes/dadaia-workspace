"""Deterministic in-process fake AgentRuntime for dry-runs and tests.

Returns a canned ``SUCCEEDED`` result without network or a model. For workflow create
steps that explicitly allow a canonical release artifact path, it materializes a small
deterministic Markdown artifact so Python gates can exercise the same file/hash checks
used for real workers.
The runtime factory (``container.build_agent_runtime``) maps
``AgentRuntimeKind.FAKE`` here so a lifecycle workflow can be exercised end-to-end
with no real harness. Tests that need a specific result inject their own via
``result=``.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from pathlib import Path

from dadaia_workspace.core.models.lifecycle import (
    AgentRunRequest,
    AgentRunResult,
    AgentRunStatus,
    AgentRuntimeKind,
)
from dadaia_workspace.core.models.workflow_execution import ResolvedModelConfig


class FakeAgentRuntime:
    """An ``AgentRuntimePort`` that returns deterministic output, no side effects.

    Records every request it receives in :attr:`received_requests` so tests can assert
    that policy resolution threaded the right ``resolved_model`` into each step's request
    — without a live provider (T-28-A-06). An optional ``on_run`` hook fires before each
    canned result, letting a test mutate external state *between* steps (used by the AC-6
    in-flight-mutation demo in T-28-A-10).
    """

    def __init__(
        self,
        *,
        result: AgentRunResult | None = None,
        on_run: Callable[[AgentRunRequest], None] | None = None,
    ) -> None:
        self._result = result
        self._on_run = on_run
        self.received_requests: list[AgentRunRequest] = []

    def runtime_kind(self) -> AgentRuntimeKind:
        return AgentRuntimeKind.FAKE

    @property
    def received_models(self) -> list[ResolvedModelConfig | None]:
        """The resolved model config recorded for each request, in call order."""
        return [req.resolved_model for req in self.received_requests]

    def run(self, request: AgentRunRequest) -> AgentRunResult:
        self.received_requests.append(request)
        if self._on_run is not None:
            self._on_run(request)
        if self._result is not None:
            return self._result
        artifact_ref = _write_allowed_create_artifact(request)
        if artifact_ref is not None:
            content_hash = hashlib.sha256((Path.cwd() / artifact_ref).read_bytes()).hexdigest()
            return AgentRunResult(
                status=AgentRunStatus.SUCCEEDED,
                summary=f"fake runtime: {request.role} wrote {artifact_ref}",
                artifact_refs=(artifact_ref,),
                structured_output={
                    "content_hash": content_hash,
                    f"{Path(artifact_ref).stem.lower()}_hash": content_hash,
                },
            )
        review_ref = _write_allowed_review_handoff(request)
        if review_ref is not None:
            return AgentRunResult(
                status=AgentRunStatus.SUCCEEDED,
                summary=f"fake runtime: {request.role} APPROVED",
                artifact_refs=(review_ref,),
                structured_output={
                    "verdict": "APPROVED",
                    "verdict_reason": "deterministic fake review approval",
                },
            )
        return AgentRunResult(
            status=AgentRunStatus.SUCCEEDED,
            summary=f"fake runtime: {request.role} (no-op)",
        )


def _write_allowed_create_artifact(request: AgentRunRequest) -> str | None:
    for allowed in request.allowed_paths:
        if not allowed.startswith(("repos/", "specs/")):
            continue
        if not allowed.endswith(("SPEC.md", "PLAN.md", "TASKS.md")):
            continue
        path = Path.cwd() / allowed
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_artifact_body(path.name, request), encoding="utf-8")
        return allowed
    return None


def _write_allowed_review_handoff(request: AgentRunRequest) -> str | None:
    if "verdict is APPROVED or REJECTED" not in request.prompt:
        return None
    handoff_root = f".dadaia/handoff/{request.context}/"
    if not any(path == f"{handoff_root}**" for path in request.allowed_paths):
        return None
    safe_task = _safe_path_part(request.task_id or "review")
    safe_role = _safe_path_part(request.role)
    ref = f"{handoff_root}{safe_task}-{safe_role}-fake-review.handoff.json"
    path = Path.cwd() / ref
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "agent": request.role,
        "context": request.context,
        "release_id": request.release_id,
        "task_id": request.task_id,
        "verdict": "APPROVED",
        "verdict_reason": "deterministic fake review approval",
        "summary": f"fake runtime: {request.role} APPROVED",
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return ref


def _safe_path_part(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in value).strip("-")


def _artifact_body(filename: str, request: AgentRunRequest) -> str:
    title = {
        "SPEC.md": "SPEC",
        "PLAN.md": "PLAN",
        "TASKS.md": "TASKS",
    }.get(filename, filename)
    return (
        f"# {title}: {request.release_id}\n\n"
        "**Status:** Aprovado\n"
        f"**Release ID:** {request.release_id}\n"
        f"**Generated By:** fake lifecycle runtime\n\n"
        f"Deterministic fake artifact for `{request.task_id}`.\n"
    )
