"""Lifecycle run-store port and errors."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from dadaia_workspace.core.models.lifecycle import LifecycleRun


@dataclass(frozen=True)
class LifecycleRunStoreError(Exception):
    """Actionable lifecycle run-store failure."""

    message: str
    path: Path | None = None

    def __str__(self) -> str:
        if self.path is None:
            return self.message
        return f"{self.message}: {self.path}"


class LifecycleRunStore(Protocol):
    """Port for persistent lifecycle run state."""

    def save(self, run: LifecycleRun) -> None:
        """Persist or replace a lifecycle run."""

    def load(self, run_id: str) -> LifecycleRun | None:
        """Load a run by id, or return None when absent."""

    def resume(self, run_id: str) -> LifecycleRun:
        """Return persisted run state for idempotent resume."""

    def list_runs(self) -> list[LifecycleRun]:
        """Return every persisted lifecycle run (run-history read)."""
