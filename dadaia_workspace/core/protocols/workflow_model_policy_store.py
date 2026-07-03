"""Port for the workflow-model-policy overlay store — ``core/protocols``.

A lean read/parse/write seam so the feature layer (``features.lifecycle.policy_doctor``,
``features.panel.views.workflow_policy``) depends on ``core`` and never imports the JSON
adapter under ``infrastructure/`` directly — the container injects the concrete
``JsonWorkflowModelPolicyStore`` (composed via
:func:`dadaia_workspace.container.build_workflow_model_policy_store`).

The three methods mirror the concrete store's real signatures:

- :meth:`load` returns the parsed overlay, or ``None`` when the overlay file is absent
  (missing != invalid — the caller falls back to library defaults); it raises the store's
  typed error when the file is present but invalid.
- :meth:`parse` validates an in-memory dict candidate (no I/O) — the panel validate/PUT path
  binds a candidate overlay before persisting it.
- :meth:`save` atomically persists the overlay.

``core`` carries only this Protocol and depends on the pure overlay type in
:mod:`core.models.workflow_execution`, so it stays import-linter clean.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from dadaia_workspace.core.models.workflow_execution import WorkflowModelPolicyOverlay


@runtime_checkable
class WorkflowModelPolicyStorePort(Protocol):
    """Load / parse / save the workflow-model-policy overlay."""

    def load(self) -> WorkflowModelPolicyOverlay | None:
        """Return the parsed overlay; ``None`` when absent, raising when present-but-invalid."""
        ...

    def parse(self, raw: dict[str, object]) -> WorkflowModelPolicyOverlay:
        """Validate and parse an in-memory overlay dict (no I/O)."""
        ...

    def save(self, overlay: WorkflowModelPolicyOverlay) -> None:
        """Atomically persist the overlay, backing up the prior valid file first."""
        ...


__all__ = [
    "WorkflowModelPolicyStorePort",
]
