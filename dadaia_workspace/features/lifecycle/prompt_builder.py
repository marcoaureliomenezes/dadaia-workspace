"""Scoped lifecycle worker prompt builder."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

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


#: The single transport-envelope schema id a worker emits in the ``schema`` field
#: (v0.1.32 / L1 / D-1). This is the one schema target named in every "## Required
#: output" section — never the fragment's descriptive ``output_schema`` (domain) id.
#: It matches :attr:`PromptScope.expected_schema`'s default, so no per-step
#: ``expected_schema`` wiring is needed.
_TRANSPORT_SCHEMA_ID = "agent-run-result-v1"


def canonical_worker_output_ref(context: str, task_id: str) -> str:
    """Return the deterministic raw-output path assigned to one worker step.

    The workflow engine owns ``context`` and ``task_id``; workers no longer invent a
    filename and then risk claiming a path they never materialized. The raw
    ``agent-run-result-v1`` object is deliberately stored outside
    ``.dadaia/handoff``: that namespace is reserved for public ``handoff-v1.x``
    documents. Python promotes the validated domain payload into the immutable
    run-scoped workflow ledger under ``.dadaia/runs/lifecycle``.

    The short digest prevents two task ids that sanitize to the same filename from
    colliding while keeping the reference readable. ``.dadaia/tmp`` is ADDITIVE and
    cleanup-governed, so a failed worker cannot pollute durable handoff evidence.
    """
    stem = re.sub(r"[^A-Za-z0-9._-]+", "-", task_id).strip("-._") or "step"
    digest = hashlib.sha256(task_id.encode("utf-8")).hexdigest()[:12]
    return f".dadaia/tmp/lifecycle-worker/{context}/{stem}-{digest}.step-output.json"


def worker_output_glob(context: str) -> str:
    """Return the only additive raw-output zone a lifecycle worker may use."""
    return f".dadaia/tmp/lifecycle-worker/{context}/**"


def filter_context_spec_paths(
    paths: tuple[str, ...],
    *,
    workspace_root: Path | None,
    specs_dir: Path | None,
) -> tuple[str, ...]:
    """Remove generic/foreign specs fallbacks when the real context root is known.

    Declarative step tables carry both ``repos/{context}/specs/**`` and ``specs/**``
    so direct fixture workspaces remain usable.  Production composition knows the
    exact context ``specs_dir``; retaining both there lets a worker satisfy the gate
    in the wrong tree.  Non-spec paths are preserved unchanged.
    """
    if workspace_root is None or specs_dir is None:
        return paths
    try:
        prefix = specs_dir.resolve().relative_to(workspace_root.resolve()).as_posix()
    except ValueError:
        return paths
    return tuple(
        path
        for path in paths
        if "specs/" not in path or path == prefix or path.startswith(f"{prefix}/")
    )


def _materialization_instruction(scope: PromptScope) -> str:
    if GateEvidenceKind.HANDOFF not in scope.required_evidence:
        return ""
    ref = canonical_worker_output_ref(scope.context, scope.task_id)
    return (
        "## Mandatory evidence materialization\n"
        f"Write your `agent-run-result-v1` JSON object to exactly `{ref}` (relative to "
        "the prompt envelope's `execution_root`), read it back to confirm it exists, and "
        f"set `artifact_refs` to include exactly `{ref}`. Use no other path for this file; "
        "Python promotes it into the workflow handoff ledger."
    )


def _worker_prompt(scope: PromptScope) -> str:
    materialization = _materialization_instruction(scope)
    if not materialization:
        return scope.prompt
    return f"{scope.prompt}\n\n{materialization}"


def _required_output_section(*, is_review: bool) -> str:
    """The step-kind-aware "## Required output" instruction (v0.1.32 / L1·L2·L3 / D-1·D-2·D-3).

    Names exactly ONE schema target — the literal field ``schema`` set to the transport id
    ``agent-run-result-v1`` — and never surfaces the fragment's domain ``output_schema`` as a
    competing schema-to-emit. The instruction is step-kind-aware:

    - **review step** (``is_review=True``): emit ``structured_output.verdict`` =
      APPROVED/REJECTED plus evidence (``verdict_reason``/``findings``);
    - **create step** (``is_review=False``): emit the produced artifact + ``artifact_refs``
      and do NOT self-verdict (no ``verdict`` field is required for a create step).
    """
    if is_review:
        body = (
            "Emit one result object whose `schema` field is the literal transport id "
            f"`{_TRANSPORT_SCHEMA_ID}`. Because this is a REVIEW step, set "
            "`structured_output.verdict` to APPROVED or REJECTED and justify it with "
            "`verdict_reason` (and `findings` when REJECTED). Include `artifact_refs` "
            "pointing at the assigned step-output artifact. Before returning, write it to "
            "disk inside the allowed write scope; never reference a nonexistent file."
        )
    else:
        body = (
            "Emit one result object whose `schema` field is the literal transport id "
            f"`{_TRANSPORT_SCHEMA_ID}`. Because this is a CREATE step, emit the produced "
            "artifact and list it in `artifact_refs` pointing at the assigned step-output. "
            "Before returning, write that step-output to disk inside the allowed write scope; "
            "never reference a nonexistent file. Do "
            "NOT self-judge: a create step does not emit an APPROVED/REJECTED decision — "
            "the review gate owns that."
        )
    return f"## Required output\n{body}"


def build_fragment_suffix(
    bundle: FragmentBundle,
    *,
    selected_context: str,
    is_review: bool,
) -> str:
    """Assemble a step's variable prompt suffix from a fragment bundle + selected context.

    This is the fragment-driven replacement for the generic ``"Run the {label} step"``
    suffix. The stable, cacheable release context belongs in the :class:`PromptPrefix`
    (assembled once and reused verbatim across steps); this function produces only the
    per-step *variable* suffix: the shared fragments the step cites, the step's own
    fragment body, the resolved dynamic context, and the step-kind-aware output contract.
    The returned text contains fragment-sourced content (the fragment id banner + body),
    never a generic placeholder.

    The "## Required output" section is **coherent by design** (v0.1.32 / L1·L2·L3):
    it names exactly ONE schema target — the literal field ``schema`` =
    ``agent-run-result-v1`` (the transport envelope) — and is step-kind-aware. It does NOT
    surface ``bundle.output_schema`` (the fragment's descriptive *domain* schema) as a
    competing schema-to-emit; that id stays on :class:`FragmentBundle` for Python tagging of
    the produced payload, never as a worker emit target.

    Args:
        bundle: the step's fragment bundle (own body + cited shared bodies + domain schema).
        selected_context: the dynamic context resolved by the context selector,
            already bounded by each fragment's ``max_context_policy``.
        is_review: whether this is a REVIEW step. **Keyword-only with no default** so every
            caller is forced to choose (D-2 / C2): a forgotten flag is a call/type error,
            never a review step silently fed create-step text. Review steps are told to
            self-verdict; create steps are told to emit an artifact and NOT to self-verdict.

    Returns:
        The variable suffix string to append after the cacheable :class:`PromptPrefix`.
    """
    sections: list[str] = []
    for shared_id, shared_body in zip(bundle.shared_ids, bundle.shared_bodies, strict=False):
        sections.append(f"<!-- fragment:{shared_id} -->\n{shared_body}".rstrip())
    sections.append(f"<!-- fragment:{bundle.fragment_id} -->\n{bundle.body}".rstrip())
    if selected_context.strip():
        sections.append(f"## Selected context\n{selected_context}".rstrip())
    sections.append(_required_output_section(is_review=is_review))
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
    # The resolved Layer-2 persona mandate for this step's role(s) (v0.1.44 / AC-2). When
    # present it is threaded into the request and emitted into the worker envelope as an
    # operative directive (act-per-mandate). Additive-optional: ``None`` (shared / no-atom
    # role) carries no persona block, keeping the persona-less payload byte-identical.
    persona: str | None = None


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
        scoped_prompt = _worker_prompt(scope)
        worker_prompt = scoped_prompt if prefix is None else f"{prefix.text}\n\n{scoped_prompt}"
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
            persona=scope.persona,
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
            "instructions": _worker_prompt(scope),
            "write_scope": {
                "allowed_paths": list(scope.allowed_paths),
                "forbidden_paths": list(scope.forbidden_paths),
            },
            "expected_schema": scope.expected_schema,
            "required_evidence": [kind.value for kind in scope.required_evidence],
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
