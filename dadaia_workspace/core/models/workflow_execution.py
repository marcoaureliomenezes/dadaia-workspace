"""Pure DTOs for the workflow model-governance layer — ``core/models/workflow_execution``.

These are the data objects the governance layer threads through every layer (CLI,
resolver, adapters, run store, panel). They carry **no I/O** and import only stdlib +
``core`` siblings, so they stay import-linter clean in ``core`` (the
``core-no-os-primitives`` contract holds).

The four types:

- :class:`PolicySource` — the precedence axis (CLI > context overlay > default overlay >
  library default). Stable string tokens so a persisted snapshot stays readable.
- :class:`WorkflowModelProfile` — a **named** model profile (e.g.
  ``codex-implementation-standard``) layered over the discrete
  :mod:`core.harness_models` catalog. A profile resolves to a
  ``HarnessModelOption`` (its ``model_id`` MUST exist in the registry — asserted in
  ``features/lifecycle/model_profiles.py``, not here, to keep ``core`` data pure).
- :class:`ResolvedModelConfig` — the resolved concrete model handed to one adapter:
  ``(profile_id, harness, model, reasoning, source)``.
- :class:`WorkflowPolicyStepEntry` / :class:`WorkflowPolicySnapshot` — the auditable,
  persisted per-run snapshot (LAW 6): which model each step actually used, plus the
  fragments / output schema / prefix hash / overlay id / source.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any

#: The overlay serialization schema version (``workflow-model-policy-v1``). It is a property
#: of the overlay data format: :meth:`WorkflowModelPolicyOverlay.to_dict` stamps it and the
#: infrastructure store's parser validates against it — single-sourced here so the on-disk
#: contract cannot drift between the model and its store.
_SCHEMA_VERSION = "workflow-model-policy-v1"

#: The inheritance-root context. A non-``default`` context resolves through its ``extends``
#: chain up to ``default`` (WS-OVERLAYS); ``default`` itself may not declare ``extends``.
DEFAULT_CONTEXT = "default"


class PolicySource(StrEnum):
    """Where a resolved value came from, in descending precedence order.

    The resolver applies ``CLI > CONTEXT_OVERLAY > DEFAULT_OVERLAY > LIBRARY_DEFAULT``
    (only the ``default`` context overlay is honored this release — D-2). Persisted as a
    stable string token so a run snapshot remains readable across releases.
    """

    CLI = "cli"
    CONTEXT_OVERLAY = "context-overlay"
    DEFAULT_OVERLAY = "default-overlay"
    LIBRARY_DEFAULT = "library-default"


@dataclass(frozen=True)
class WorkflowModelProfile:
    """A named, governed Layer-2 model profile (D-2: built-in only this release).

    ``model_id`` + ``effort`` resolve to a discrete :class:`harness_models.HarnessModelOption`
    for ``harness`` (the model-profile registry asserts this at import time). ``deprecated``
    profiles MUST carry a ``replacement`` profile id (enforced by the registry / resolver),
    so a deprecated profile is never a dead end.
    """

    id: str
    harness: str
    label: str
    model_id: str
    effort: str
    purpose: str
    availability: str = "available"
    source: str = "built-in"
    deprecated: bool = False
    replacement: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "harness": self.harness,
            "label": self.label,
            "model_id": self.model_id,
            "effort": self.effort,
            "purpose": self.purpose,
            "availability": self.availability,
            "source": self.source,
            "deprecated": self.deprecated,
            "replacement": self.replacement,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> WorkflowModelProfile:
        return cls(
            id=str(data["id"]),
            harness=str(data["harness"]),
            label=str(data["label"]),
            model_id=str(data["model_id"]),
            effort=str(data["effort"]),
            purpose=str(data["purpose"]),
            availability=str(data.get("availability", "available")),
            source=str(data.get("source", "built-in")),
            deprecated=bool(data.get("deprecated", False)),
            replacement=_optional_str(data.get("replacement")),
        )


@dataclass(frozen=True)
class ResolvedModelConfig:
    """The resolved concrete model one adapter runs with (LAW 2 / ADR-B).

    ``model`` is the discrete GPT/codex model id; ``reasoning`` is the Codex
    reasoning-effort axis. ``profile_id`` records the named profile this resolved from;
    ``source`` records which precedence layer won. Adapters consume this verbatim — PI
    passes ``--model <model>``, Codex passes ``-m <model> -c model_reasoning_effort=<reasoning>``.
    """

    profile_id: str
    harness: str
    model: str
    reasoning: str
    source: PolicySource = PolicySource.LIBRARY_DEFAULT

    def to_dict(self) -> dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "harness": self.harness,
            "model": self.model,
            "reasoning": self.reasoning,
            "source": self.source.value,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> ResolvedModelConfig:
        return cls(
            profile_id=str(data["profile_id"]),
            harness=str(data["harness"]),
            model=str(data["model"]),
            reasoning=str(data["reasoning"]),
            source=PolicySource(str(data.get("source", PolicySource.LIBRARY_DEFAULT.value))),
        )


@dataclass(frozen=True)
class WorkflowPolicyStepEntry:
    """One step's resolved policy inside a run snapshot (auditable; LAW 6)."""

    step: str
    harness: str
    model_profile: str
    model: str
    reasoning: str
    source: PolicySource
    fragments: tuple[str, ...] = ()
    output_schema: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "step": self.step,
            "harness": self.harness,
            "model_profile": self.model_profile,
            "model": self.model,
            "reasoning": self.reasoning,
            "source": self.source.value,
            "fragments": list(self.fragments),
            "output_schema": self.output_schema,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> WorkflowPolicyStepEntry:
        fragments_raw = data.get("fragments", [])
        assert isinstance(fragments_raw, list)
        return cls(
            step=str(data["step"]),
            harness=str(data["harness"]),
            model_profile=str(data["model_profile"]),
            model=str(data["model"]),
            reasoning=str(data["reasoning"]),
            source=PolicySource(str(data["source"])),
            fragments=tuple(str(item) for item in fragments_raw),
            output_schema=_optional_str(data.get("output_schema")),
        )


@dataclass(frozen=True)
class WorkflowPolicySnapshot:
    """The resolved policy for a whole workflow run, persisted on the run (LAW 6/7).

    Resolved + frozen once before the first step; an in-flight run reads this snapshot,
    never the live overlay (LAW 7 — mid-run safety). Each ``steps`` entry records the
    model that step actually ran on, even after the current policy later changes.
    """

    workflow_id: str
    policy_id: str
    resolved_at: str
    source_precedence: tuple[str, ...] = ()
    overlay_id: str | None = None
    steps: tuple[WorkflowPolicyStepEntry, ...] = ()
    prefix_hash: str | None = None

    def step(self, label: str) -> WorkflowPolicyStepEntry | None:
        """Return the resolved entry for *label*, or ``None`` when absent."""
        for entry in self.steps:
            if entry.step == label:
                return entry
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "policy_id": self.policy_id,
            "resolved_at": self.resolved_at,
            "source_precedence": list(self.source_precedence),
            "overlay_id": self.overlay_id,
            "steps": [entry.to_dict() for entry in self.steps],
            "prefix_hash": self.prefix_hash,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> WorkflowPolicySnapshot:
        precedence_raw = data.get("source_precedence", [])
        steps_raw = data.get("steps", [])
        assert isinstance(precedence_raw, list)
        assert isinstance(steps_raw, list)
        steps: list[WorkflowPolicyStepEntry] = []
        for entry in steps_raw:
            assert isinstance(entry, dict)
            steps.append(WorkflowPolicyStepEntry.from_dict(entry))
        return cls(
            workflow_id=str(data["workflow_id"]),
            policy_id=str(data["policy_id"]),
            resolved_at=str(data["resolved_at"]),
            source_precedence=tuple(str(item) for item in precedence_raw),
            overlay_id=_optional_str(data.get("overlay_id")),
            steps=tuple(steps),
            prefix_hash=_optional_str(data.get("prefix_hash")),
        )


# ---------------------------------------------------------------------------
# Workflow-model-policy overlay data types — relocated from
# ``infrastructure/json_workflow_model_policy_store`` in v0.1.54 (FR1a). These are pure,
# I/O-free data objects: the overlay carries the parsed per-context/-workflow/-step policy
# and the ``extends`` resolution chain; the error is the typed store failure. The JSON store
# under ``infrastructure/`` imports them (a legal ``infrastructure -> core`` edge) and the
# feature layer resolves the types here (a legal ``features -> core`` edge), so the resolver
# / doctor / panel no longer reach into ``infrastructure`` for them.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class WorkflowModelPolicyStoreError(Exception):
    """Actionable workflow-model-policy overlay failure."""

    message: str
    path: Path | None = None

    def __str__(self) -> str:
        if self.path is None:
            return self.message
        return f"{self.message}: {self.path}"


@dataclass(frozen=True)
class WorkflowModelPolicyOverlay:
    """Parsed, validated overlay (in-memory).

    ``contexts`` maps a context name to ``{workflow_id -> {step_label -> profile_id}}``.
    ``default_harness_overlay`` (v0.1.29 / D-3) maps a context to
    ``{workflow_id -> harness}`` (a per-workflow default harness override) and
    ``step_harness_overlay`` to ``{workflow_id -> {step_label -> harness}}`` (a per-step
    harness override). ``extends`` maps a context name to its parent context (WS-OVERLAYS).

    **Per-context inheritance (WS-OVERLAYS).** A non-``default`` context is now honored: the
    accessors walk ``context → extends… → default`` and return the first level that defines
    the requested value. ``default`` is the inheritance root. The ``extends`` graph is
    validated at parse time (every parent exists; no cycles; ``default`` declares no parent),
    so the accessors can walk safely without re-validating.

    **Back-compat (L7):** ``extends`` defaults to empty and the harness overlays default to
    empty, so a v0.1.28/29 overlay (no ``extends`` / no harness field) parses and resolves
    byte-identically; :meth:`to_dict` omits the harness fields when empty and ``extends``
    when a context declares none (byte-stable round-trip).
    """

    policy_id: str
    contexts: dict[str, dict[str, dict[str, str]]]
    default_harness_overlay: dict[str, dict[str, str]] = field(default_factory=dict)
    step_harness_overlay: dict[str, dict[str, dict[str, str]]] = field(default_factory=dict)
    extends: dict[str, str] = field(default_factory=dict)

    def _resolution_chain(self, context: str) -> list[str]:
        """Return the ordered context lookup chain ``[context, parent…, default]``.

        Walks ``extends`` from *context* toward ``default``. The graph is parse-validated
        (no cycles, every parent present), so this terminates; a defensive ``seen`` guard
        breaks any pathological case rather than looping. ``default`` is always the tail
        even when *context* is unknown (an unknown context simply inherits the root).
        """
        chain: list[str] = []
        seen: set[str] = set()
        current: str | None = context
        while current is not None and current not in seen:
            chain.append(current)
            seen.add(current)
            current = self.extends.get(current)
        if DEFAULT_CONTEXT not in chain:
            chain.append(DEFAULT_CONTEXT)
        return chain

    def step_profile(self, context: str, workflow_id: str, step: str) -> str | None:
        """Return the overridden profile id for a step, walking the ``extends`` chain.

        Returns the first level (nearest the requested context) that defines the step's
        profile; ``None`` when no level in the chain overrides it.
        """
        for level in self._resolution_chain(context):
            value = self.contexts.get(level, {}).get(workflow_id, {}).get(step)
            if value is not None:
                return value
        return None

    def workflow_default_harness(self, context: str, workflow_id: str) -> str | None:
        """Return the per-workflow default harness, walking the ``extends`` chain (D-3)."""
        for level in self._resolution_chain(context):
            value = self.default_harness_overlay.get(level, {}).get(workflow_id)
            if value is not None:
                return value
        return None

    def step_harness(self, context: str, workflow_id: str, step: str) -> str | None:
        """Return the per-step harness override, walking the ``extends`` chain (D-3)."""
        for level in self._resolution_chain(context):
            value = self.step_harness_overlay.get(level, {}).get(workflow_id, {}).get(step)
            if value is not None:
                return value
        return None

    def to_dict(self) -> dict[str, Any]:
        # Serialize the UNION of all three context maps plus declared `extends`
        # parents, so a save/load round-trip is identity even for harness-only
        # workflows (named only in default_harness_overlay / step_harness_overlay
        # with no profile `steps` entry) and extends-only contexts. Mirrors the
        # union the WMP doctor (`_resolve_overlay`) and panel `_semantic_check` use.
        ctx_keys = (
            set(self.contexts)
            | set(self.default_harness_overlay)
            | set(self.step_harness_overlay)
            | set(self.extends)
        )
        contexts: dict[str, Any] = {}
        for ctx in sorted(ctx_keys):
            workflows = self.contexts.get(ctx, {})
            ctx_default_harness = self.default_harness_overlay.get(ctx, {})
            ctx_step_harness = self.step_harness_overlay.get(ctx, {})
            wf_keys = set(workflows) | set(ctx_default_harness) | set(ctx_step_harness)
            wf_out: dict[str, Any] = {}
            for wf in sorted(wf_keys):
                entry: dict[str, Any] = {}
                steps = workflows.get(wf, {})
                if steps:
                    entry["steps"] = dict(steps)
                default_harness = ctx_default_harness.get(wf)
                if default_harness is not None:
                    entry["default_harness"] = default_harness
                harnesses = ctx_step_harness.get(wf, {})
                if harnesses:
                    entry["harnesses"] = dict(harnesses)
                wf_out[wf] = entry
            ctx_out: dict[str, Any] = {}
            if wf_out:
                ctx_out["workflows"] = wf_out
            parent = self.extends.get(ctx)
            if parent is not None:
                ctx_out["extends"] = parent
            contexts[ctx] = ctx_out
        return {
            "schema_version": _SCHEMA_VERSION,
            "policy_id": self.policy_id,
            "contexts": contexts,
        }


__all__ = [
    "DEFAULT_CONTEXT",
    "PolicySource",
    "ResolvedModelConfig",
    "WorkflowModelPolicyOverlay",
    "WorkflowModelPolicyStoreError",
    "WorkflowModelProfile",
    "WorkflowPolicySnapshot",
    "WorkflowPolicyStepEntry",
]


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    return str(value)
