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

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


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


__all__ = [
    "PolicySource",
    "ResolvedModelConfig",
    "WorkflowModelProfile",
    "WorkflowPolicySnapshot",
    "WorkflowPolicyStepEntry",
]


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    return str(value)
