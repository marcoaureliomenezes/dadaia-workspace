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
from dadaia_workspace.core.models.workflow_execution import ResolvedModelConfig


class PromptScopeError(ValueError):
    """Raised when a worker prompt would be broader than its declared scope."""


@dataclass(frozen=True)
class FragmentBundle:
    """The static material for one fragment-driven step.

    ``body`` is the step's own fragment body; ``shared_bodies`` are the bodies of the
    shared fragments it cites (e.g. ``shared/output-handoff``), in citation order.
    ``output_schema`` is the fragment's declared output contract. Bundling these here
    keeps the workflow body free of fragment-assembly mechanics.
    """

    fragment_id: str
    role: str
    body: str
    output_schema: str
    shared_bodies: tuple[str, ...] = ()
    shared_ids: tuple[str, ...] = ()


def build_fragment_suffix(
    bundle: FragmentBundle,
    *,
    selected_context: str,
) -> str:
    """Assemble a step's variable prompt suffix from a fragment bundle + selected context.

    This is the fragment-driven replacement for the generic ``"Run the {label} step"``
    suffix. The stable, cacheable release context belongs in the :class:`PromptPrefix`
    (assembled once and reused verbatim across steps); this function produces only the
    per-step *variable* suffix: the shared fragments the step cites, the step's own
    fragment body, the resolved dynamic context, and the explicit output schema the
    worker must satisfy. The returned text contains fragment-sourced content (the
    fragment id banner + body), never a generic placeholder.

    Args:
        bundle: the step's fragment bundle (own body + cited shared bodies + schema).
        selected_context: the dynamic context resolved by the context selector,
            already bounded by each fragment's ``max_context_policy``.

    Returns:
        The variable suffix string to append after the cacheable :class:`PromptPrefix`.
    """
    sections: list[str] = []
    for shared_id, shared_body in zip(bundle.shared_ids, bundle.shared_bodies, strict=False):
        sections.append(f"<!-- fragment:{shared_id} -->\n{shared_body}".rstrip())
    sections.append(f"<!-- fragment:{bundle.fragment_id} -->\n{bundle.body}".rstrip())
    if selected_context.strip():
        sections.append(f"## Selected context\n{selected_context}".rstrip())
    sections.append(
        "## Required output\n"
        f"Emit a handoff whose structured_output.verdict is APPROVED or REJECTED and that "
        f"conforms to the output schema `{bundle.output_schema}`, with an artifact_ref "
        "pointing at the handoff document."
    )
    return "\n\n".join(sections)


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
    # The governance-resolved concrete model for this step (T-28-A-07). When present it is
    # threaded into the request so the adapter runs the policy-selected model (M2). Kept
    # additive-optional: ``model_profile`` stays for back-compat / observability.
    resolved_model: ResolvedModelConfig | None = None


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
            resolved_model=scope.resolved_model,
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
