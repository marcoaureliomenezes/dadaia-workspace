"""Port for workflow-model-policy overlay persistence.

The feature layer resolves and validates workflow model policy, but the JSON persistence
adapter lives in ``infrastructure``. This module carries the shared overlay data model,
store protocol, and typed error so features depend on ``core.protocols`` while the
composition root injects the concrete adapter.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

DEFAULT_CONTEXT = "default"


class WorkflowModelPolicyStoreError(Exception):
    """Raised when the workflow-model-policy store is present but invalid or unwritable."""


@dataclass(frozen=True)
class WorkflowModelPolicyOverlay:
    """Parsed workflow-model-policy overlay."""

    policy_id: str
    contexts: dict[str, dict[str, dict[str, str]]]
    default_harness_overlay: dict[str, dict[str, str]] = field(default_factory=dict)
    step_harness_overlay: dict[str, dict[str, dict[str, str]]] = field(default_factory=dict)
    extends: dict[str, str] = field(default_factory=dict)

    def _resolution_chain(self, context: str) -> list[str]:
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
        for level in self._resolution_chain(context):
            value = self.contexts.get(level, {}).get(workflow_id, {}).get(step)
            if value is not None:
                return value
        return None

    def workflow_default_harness(self, context: str, workflow_id: str) -> str | None:
        for level in self._resolution_chain(context):
            value = self.default_harness_overlay.get(level, {}).get(workflow_id)
            if value is not None:
                return value
        return None

    def step_harness(self, context: str, workflow_id: str, step: str) -> str | None:
        for level in self._resolution_chain(context):
            value = self.step_harness_overlay.get(level, {}).get(workflow_id, {}).get(step)
            if value is not None:
                return value
        return None

    def to_dict(self) -> dict[str, Any]:
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
            "schema_version": "workflow-model-policy-v1",
            "policy_id": self.policy_id,
            "contexts": contexts,
        }


@runtime_checkable
class WorkflowModelPolicyStorePort(Protocol):
    """Load, parse, and save workflow-model-policy overlays."""

    @property
    def path(self) -> Path: ...

    @property
    def last_good_path(self) -> Path: ...

    def load(self) -> WorkflowModelPolicyOverlay | None: ...

    def parse(self, raw: dict[str, object]) -> WorkflowModelPolicyOverlay: ...

    def save(self, overlay: WorkflowModelPolicyOverlay) -> None: ...


__all__ = [
    "DEFAULT_CONTEXT",
    "WorkflowModelPolicyOverlay",
    "WorkflowModelPolicyStoreError",
    "WorkflowModelPolicyStorePort",
]
