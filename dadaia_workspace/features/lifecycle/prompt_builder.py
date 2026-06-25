"""Scoped lifecycle worker prompt builder."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass

from dadaia_workspace.core.models.lifecycle import (
    AgentRunRequest,
    AgentRuntimeKind,
    GateEvidenceKind,
)


class PromptScopeError(ValueError):
    """Raised when a worker prompt would be broader than its declared scope."""


@dataclass(frozen=True)
class PromptPrefix:
    """A deterministic, byte-identical stable context block shared across steps.

    The prefix carries the release-stable context (constitution / tech-stack /
    architecture / memory / SPEC·PLAN·TASKS) assembled once and reused verbatim by every
    worker step, so a provider prompt cache reads it at a fraction of the cost (EPIC D11).
    ``content_hash`` lets callers assert byte-identity across steps — the property that
    makes the prefix cacheable.
    """

    text: str
    content_hash: str

    @classmethod
    def from_sections(cls, sections: Mapping[str, str]) -> PromptPrefix:
        """Assemble a prefix from named sections, deterministically (sorted, fixed delims)."""
        text = "\n\n".join(f"## {name}\n{sections[name]}" for name in sorted(sections))
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        return cls(text=text, content_hash=digest)


@dataclass(frozen=True)
class PromptScope:
    """Scope contract for one bounded worker request."""

    role: str
    context: str
    release_id: str
    task_id: str
    prompt: str
    allowed_paths: tuple[str, ...]
    forbidden_paths: tuple[str, ...] = ()
    expected_schema: str = "agent-run-result-v1"
    required_evidence: tuple[GateEvidenceKind, ...] = ()
    model_profile: str | None = None


@dataclass(frozen=True)
class BuiltPrompt:
    """Prompt text plus matching runtime request."""

    request: AgentRunRequest
    prompt_text: str
    prefix_hash: str | None = None


class LifecyclePromptBuilder:
    """Build scoped JSON prompts for lifecycle worker agents."""

    def build(
        self,
        scope: PromptScope,
        *,
        runtime: AgentRuntimeKind = AgentRuntimeKind.CODEX_EXEC,
        prefix: PromptPrefix | None = None,
    ) -> BuiltPrompt:
        self._validate_scope(scope)
        # The cacheable prefix leads the worker prompt verbatim; the per-step scope is the
        # variable suffix. Identical prefix bytes across steps => provider cache hit.
        worker_prompt = scope.prompt if prefix is None else f"{prefix.text}\n\n{scope.prompt}"
        request = AgentRunRequest(
            role=scope.role,
            prompt=worker_prompt,
            runtime=runtime,
            context=scope.context,
            release_id=scope.release_id,
            task_id=scope.task_id,
            model_profile=scope.model_profile,
            allowed_paths=scope.allowed_paths,
            forbidden_paths=scope.forbidden_paths,
            expected_schema=scope.expected_schema,
            required_evidence=scope.required_evidence,
        )
        prompt_text = self._prompt_text(scope)
        if prefix is not None:
            prompt_text = f"{prefix.text}\n\n---\n\n{prompt_text}"
        return BuiltPrompt(
            request=request,
            prompt_text=prompt_text,
            prefix_hash=prefix.content_hash if prefix else None,
        )

    def _prompt_text(self, scope: PromptScope) -> str:
        payload = {
            "role": scope.role,
            "context": scope.context,
            "release_id": scope.release_id,
            "task_id": scope.task_id,
            "instructions": scope.prompt,
            "write_scope": {
                "allowed_paths": list(scope.allowed_paths),
                "forbidden_paths": list(scope.forbidden_paths),
            },
            "expected_schema": scope.expected_schema,
            "required_evidence": [kind.value for kind in scope.required_evidence],
            "output_contract": {
                "structured_output": {
                    "verdict": "APPROVED|REJECTED",
                    "changed_paths": "comma-separated workspace-relative paths",
                },
                "artifact_refs": "workspace-relative evidence paths",
            },
        }
        return json.dumps(payload, indent=2, sort_keys=True)

    def _validate_scope(self, scope: PromptScope) -> None:
        if not scope.role:
            raise PromptScopeError("role is required")
        if not scope.context:
            raise PromptScopeError("context is required")
        if not scope.release_id:
            raise PromptScopeError("release_id is required")
        if not scope.task_id:
            raise PromptScopeError("task_id is required")
        if not scope.allowed_paths:
            raise PromptScopeError("allowed_paths are required")
        for path in (*scope.allowed_paths, *scope.forbidden_paths):
            self._validate_path(path)

    @staticmethod
    def _validate_path(path: str) -> None:
        if path in {"", ".", "./", "**", "*/**", "/"}:
            raise PromptScopeError("whole-workspace paths are not allowed")
        if path.startswith("/") or ".." in path.split("/"):
            raise PromptScopeError(f"unsafe scoped path: {path}")
        parts = path.split("/")
        if path.startswith("repos/") and (len(parts) < 3 or parts[2] in {"*", "**", ""}):
            raise PromptScopeError(f"repo-wide scoped path is not allowed: {path}")
