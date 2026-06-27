"""Port for the operator-local model-profile store — ``core/protocols``.

The operator may register **their own** Layer-2 model profiles in a workspace-local
store (``.dadaia/states/workflow_model_profiles.local.json``) so a governed workflow step
can select a profile the built-in registry does not ship (Item 4 / WS-PROFILES). This port
is the seam the feature layer (:mod:`features.lifecycle.model_profiles`) reads through, so
``features``/``core`` never import the JSON adapter directly (the container injects it).

Two load paths, deliberately distinct (L3 — "missing != invalid"):

- **Missing store** ⇒ :meth:`load` returns an empty tuple ⇒ the feature layer surfaces the
  built-in profiles only (a workflow is runnable before any operator profile exists).
- **Present-but-invalid store** (corrupt JSON, unknown field, ``harness != "pi"``, an
  API-key-bearing field — L1/L8) ⇒ :meth:`load` raises so the caller fails closed before
  the first model call.

Implementations live outside ``core`` (the adapter under ``infrastructure/``); ``core``
carries only this Protocol and the typed error, so it stays import-linter clean.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from dadaia_workspace.core.models.workflow_execution import WorkflowModelProfile


class LocalModelProfileStoreError(Exception):
    """Raised when the operator-local model-profile store is present but invalid.

    A *missing* store is never an error (the loader returns an empty tuple); only a
    present-but-invalid store raises (L3 — missing != invalid). The message is actionable
    and never echoes a secret value (L8 — the store rejects API-key-bearing fields, but the
    error text names only the offending field, never its value).
    """


@runtime_checkable
class LocalModelProfileStorePort(Protocol):
    """Load operator-registered Layer-2 model profiles from a workspace-local store."""

    def load(self) -> tuple[WorkflowModelProfile, ...]:
        """Return the operator profiles; empty tuple when the store is absent.

        Raises:
            LocalModelProfileStoreError: when the store is present but invalid (corrupt
                JSON, unknown field, ``harness != "pi"`` per L1, or any API-key-bearing
                field per L8).
        """
        ...


__all__ = [
    "LocalModelProfileStoreError",
    "LocalModelProfileStorePort",
]
