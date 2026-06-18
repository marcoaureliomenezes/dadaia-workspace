"""Runtime file writer ports for canonical workflow artifacts."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol, runtime_checkable

from dadaia_workspace.core.models.hygiene import HygieneSnapshot


class RuntimeFileKind(StrEnum):
    REPORT = "report"
    HANDOFF = "handoff"
    TMP = "tmp"
    RUN_ARTIFACT = "run_artifact"
    HYGIENE_SNAPSHOT = "hygiene_snapshot"


@dataclass(frozen=True)
class RuntimeFileRef:
    kind: RuntimeFileKind
    path: str
    content_hash: str | None = None
    ttl_seconds: int | None = None


@runtime_checkable
class RuntimeFilePort(Protocol):
    """Create lifecycle runtime files only through canonical paths.

    Implementations are responsible for filesystem I/O and validation. This
    port defines the workflow-facing surface without importing any concrete
    adapter into ``core``.
    """

    def write_report(
        self,
        *,
        context: str,
        agent: str,
        filename: str,
        html: str,
    ) -> RuntimeFileRef:
        """Write a human-readable HTML report artifact."""
        ...

    def write_handoff(
        self,
        *,
        context: str,
        filename: str,
        payload: dict[str, object],
    ) -> RuntimeFileRef:
        """Write a machine-readable handoff artifact."""
        ...

    def write_tmp(
        self,
        *,
        workflow: str,
        date_slug: str,
        filename: str,
        content: str,
        ttl_seconds: int,
    ) -> RuntimeFileRef:
        """Write an ephemeral workflow temp file with TTL metadata."""
        ...

    def write_run_artifact(
        self,
        *,
        run_id: str,
        filename: str,
        content: str,
    ) -> RuntimeFileRef:
        """Write a durable lifecycle run artifact."""
        ...

    def write_hygiene_snapshot(self, snapshot: HygieneSnapshot) -> RuntimeFileRef:
        """Write a structured hygiene snapshot for a lifecycle run."""
        ...
