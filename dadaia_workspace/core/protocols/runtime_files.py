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


@dataclass(frozen=True)
class StepPayloadRef:
    """Where an immutable workflow-step payload was written + its content hash.

    The workflow-step handoff data plane (v0.1.30 Item 5) returns this from the
    payload-writer port; the content hash is the immutability proof the resolver verifies
    on every read. Lives in ``core`` so both the ``infrastructure`` adapter and the
    ``features`` resolver reference it without a layer violation.
    """

    payload_ref: str
    content_hash: str


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

    def write_step_payload(
        self,
        *,
        run_id: str,
        producer_step: str,
        attempt: int,
        content: str,
    ) -> StepPayloadRef:
        """Write an immutable workflow-step payload envelope under the run steps zone."""
        ...

    def read_step_payload(self, payload_ref: str) -> str | None:
        """Return the raw step payload envelope JSON at ``payload_ref``, or ``None``."""
        ...
