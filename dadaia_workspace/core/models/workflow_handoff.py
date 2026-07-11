"""Pure models for the run-scoped workflow-step handoff ledger (v0.1.30 Item 5).

This is the **control plane** of the workflow-step data plane: the immutable step
payloads live on disk under ``.dadaia/runs/lifecycle/<run_id>/steps/`` (the data plane),
while the ledger of *what was produced, by which step+attempt, who must consume it, and
who has* is carried on :class:`~dadaia_workspace.core.models.lifecycle.LifecycleRun` as a
backward-compatible ``workflow_steps`` field.

The ledger is what makes prompt-to-prompt communication **addressable by (run id,
producer step, attempt)** rather than the slop "latest handoff by agent filename"
(SPEC A25). A downstream step resolves the exact upstream payload it declared a
``consumes`` edge on; a missing or malformed required payload BLOCKS the workflow
(A20); consumption transitions ``produced → consumed_partial → consumed_all`` are
recorded per declared consumer (A22), and a payload is cleanup-eligible only once every
declared consumer has consumed it.

Design notes:
- Every model is a frozen dataclass with explicit ``to_dict``/``from_dict`` round-trips
  (the run store persists the whole :class:`LifecycleRun`; these serialise transitively).
- ``WorkflowStepRecord`` carries the *declared* downstream consumer step names and the
  *actual* consumption records. The consumption **state** is derived, never stored as a
  divergent field (single source of truth).
- ``RetentionMode`` encodes the GRILL-resolved retention policy per payload:
  transient prompt-to-prompt payloads are ``delete-after-consumed``; review verdicts and
  the consumed_backlog ledger are ``promote-to-evidence``; failed/blocked-run payloads
  are ``keep-until-failure-ttl``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class RetentionMode(StrEnum):
    """How a produced step payload is retained after the run progresses.

    - ``DELETE_AFTER_CONSUMED`` — transient prompt-to-prompt payload; reclaimable once
      every declared consumer consumed it and the consumed TTL has elapsed (default).
    - ``PROMOTE_TO_EVIDENCE`` — durable evidence (review verdicts, the consumed_backlog
      ledger) that feeds CLOSURE / report / panel; never reclaimed by the consumed-TTL
      sweep.
    - ``KEEP_UNTIL_FAILURE_TTL`` — payloads of a failed/blocked run kept for
      investigation until a longer failure TTL; never reclaimed while the run is live.
    """

    DELETE_AFTER_CONSUMED = "delete_after_consumed"
    PROMOTE_TO_EVIDENCE = "promote_to_evidence"
    KEEP_UNTIL_FAILURE_TTL = "keep_until_failure_ttl"


class WorkflowStepConsumptionState(StrEnum):
    """Derived consumption state of a produced step payload (A22).

    The state is a pure function of the *declared* consumer set vs the *recorded*
    consumptions — never stored as an independent field.
    """

    #: No declared consumer has consumed the payload yet (or there are no consumers).
    PRODUCED = "produced"
    #: Some, but not all, declared consumers have consumed the payload.
    CONSUMED_PARTIAL = "consumed_partial"
    #: Every declared consumer has consumed the payload — cleanup-eligible.
    CONSUMED_ALL = "consumed_all"


@dataclass(frozen=True)
class WorkflowStepConsumerRecord:
    """One recorded consumption of a produced step payload by a downstream step.

    Addressed by the *consuming* step name + the consumer's own attempt number, so the
    ledger captures exactly which (consumer step, attempt) read which producer payload —
    the data behind A19/A24 (``implement#2`` consumes ``qa#1``, not ``qa#0``).
    """

    consumer_step: str
    consumer_attempt: int
    consumed_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "consumer_step": self.consumer_step,
            "consumer_attempt": self.consumer_attempt,
            "consumed_at": self.consumed_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> WorkflowStepConsumerRecord:
        return cls(
            consumer_step=str(data["consumer_step"]),
            consumer_attempt=int(str(data["consumer_attempt"])),
            consumed_at=str(data["consumed_at"]),
        )


@dataclass(frozen=True)
class WorkflowStepRecord:
    """A single immutable step payload's control-plane ledger entry.

    Identity is ``(run_id, producer_step, attempt)`` — the addressable key A19/A25 require.
    The record points at the immutable on-disk payload (``payload_ref`` +
    ``content_hash``) and carries the *declared* downstream consumer step names plus the
    *recorded* consumptions. The consumption :class:`WorkflowStepConsumptionState` is
    derived from those two sets.
    """

    run_id: str
    producer_step: str
    attempt: int
    output_schema: str
    payload_ref: str
    content_hash: str
    produced_at: str
    retention_mode: RetentionMode = RetentionMode.DELETE_AFTER_CONSUMED
    declared_consumers: tuple[str, ...] = ()
    consumptions: tuple[WorkflowStepConsumerRecord, ...] = ()

    @property
    def key(self) -> tuple[str, str, int]:
        """The addressable identity ``(run_id, producer_step, attempt)`` (A19)."""
        return (self.run_id, self.producer_step, self.attempt)

    def consumption_state(self) -> WorkflowStepConsumptionState:
        """Derive the consumption state from declared consumers vs recorded consumptions.

        A payload with no declared consumers stays ``PRODUCED`` (nothing must consume it,
        so it is never auto-``consumed_all`` — promote-to-evidence payloads typically have
        no declared consumer and survive on their retention mode, not on consumption).
        """
        if not self.declared_consumers:
            return WorkflowStepConsumptionState.PRODUCED
        consumed = {record.consumer_step for record in self.consumptions}
        declared = set(self.declared_consumers)
        if declared.issubset(consumed):
            return WorkflowStepConsumptionState.CONSUMED_ALL
        if consumed & declared:
            return WorkflowStepConsumptionState.CONSUMED_PARTIAL
        return WorkflowStepConsumptionState.PRODUCED

    def is_cleanup_eligible(self) -> bool:
        """True iff this payload may be reclaimed by the consumed-TTL sweep (A22).

        Cleanup-eligibility is *necessary* but not *sufficient* for reclaim: the consumed
        TTL and the live-run guard are applied by the retention sweep on top of this.
        Eligibility requires BOTH:

        - ``retention_mode is DELETE_AFTER_CONSUMED`` — only transient prompt-to-prompt
          payloads are reclaimed on the consumed-TTL path. ``PROMOTE_TO_EVIDENCE`` is
          durable evidence; ``KEEP_UNTIL_FAILURE_TTL`` is kept on a separate (longer)
          failure schedule, never reclaimed by the consumed-TTL sweep. Excluding both here
          is the single source of truth the reclaim-allow set (container) and the doctor's
          stale gate both rely on — a non-delete-after-consumed payload is NEVER eligible.
        - every declared consumer has consumed it (``consumed_all``).
        """
        if self.retention_mode is not RetentionMode.DELETE_AFTER_CONSUMED:
            return False
        return self.consumption_state() is WorkflowStepConsumptionState.CONSUMED_ALL

    def with_consumption(self, record: WorkflowStepConsumerRecord) -> WorkflowStepRecord:
        """Return a copy with *record* appended (idempotent per (step, attempt)).

        Re-recording the same (consumer step, attempt) is a no-op — the ledger stays the
        single source of truth and consumption recording is safe to retry.
        """
        for existing in self.consumptions:
            if (
                existing.consumer_step == record.consumer_step
                and existing.consumer_attempt == record.consumer_attempt
            ):
                return self
        return _replace_consumptions(self, (*self.consumptions, record))

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "producer_step": self.producer_step,
            "attempt": self.attempt,
            "output_schema": self.output_schema,
            "payload_ref": self.payload_ref,
            "content_hash": self.content_hash,
            "produced_at": self.produced_at,
            "retention_mode": self.retention_mode.value,
            "declared_consumers": list(self.declared_consumers),
            "consumptions": [record.to_dict() for record in self.consumptions],
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> WorkflowStepRecord:
        declared_raw = data.get("declared_consumers", [])
        consumptions_raw = data.get("consumptions", [])
        assert isinstance(declared_raw, list)
        assert isinstance(consumptions_raw, list)
        consumptions: list[WorkflowStepConsumerRecord] = []
        for entry in consumptions_raw:
            assert isinstance(entry, dict)
            consumptions.append(WorkflowStepConsumerRecord.from_dict(entry))
        retention_raw = data.get("retention_mode", RetentionMode.DELETE_AFTER_CONSUMED.value)
        return cls(
            run_id=str(data["run_id"]),
            producer_step=str(data["producer_step"]),
            attempt=int(str(data["attempt"])),
            output_schema=str(data["output_schema"]),
            payload_ref=str(data["payload_ref"]),
            content_hash=str(data["content_hash"]),
            produced_at=str(data["produced_at"]),
            retention_mode=RetentionMode(str(retention_raw)),
            declared_consumers=tuple(str(item) for item in declared_raw),
            consumptions=tuple(consumptions),
        )


def _replace_consumptions(
    record: WorkflowStepRecord, consumptions: tuple[WorkflowStepConsumerRecord, ...]
) -> WorkflowStepRecord:
    return WorkflowStepRecord(
        run_id=record.run_id,
        producer_step=record.producer_step,
        attempt=record.attempt,
        output_schema=record.output_schema,
        payload_ref=record.payload_ref,
        content_hash=record.content_hash,
        produced_at=record.produced_at,
        retention_mode=record.retention_mode,
        declared_consumers=record.declared_consumers,
        consumptions=consumptions,
    )


@dataclass(frozen=True)
class WorkflowStepLedger:
    """An ordered, addressable collection of :class:`WorkflowStepRecord` entries.

    This is the value carried by ``LifecycleRun.workflow_steps``. Lookups are by the
    ``(producer_step, attempt)`` key within the run; the run id is implicit (every record
    in a run's ledger shares it). Insertion order is preserved for deterministic
    serialisation.
    """

    records: tuple[WorkflowStepRecord, ...] = field(default_factory=tuple)

    def __len__(self) -> int:
        return len(self.records)

    def __iter__(self) -> _LedgerIterator:
        return _LedgerIterator(self.records)

    def find(self, producer_step: str, attempt: int) -> WorkflowStepRecord | None:
        """Return the record for ``(producer_step, attempt)`` or ``None``."""
        for record in self.records:
            if record.producer_step == producer_step and record.attempt == attempt:
                return record
        return None

    def latest_attempt(self, producer_step: str) -> WorkflowStepRecord | None:
        """Return the highest-attempt record for *producer_step* or ``None``.

        Used only by callers that legitimately want "the most recent attempt of a named
        producer step" (e.g. a digest of the current best output) — NOT a substitute for
        the exact-attempt lookup A19/A24 require for required prompt-to-prompt edges.
        """
        candidates = [r for r in self.records if r.producer_step == producer_step]
        if not candidates:
            return None
        return max(candidates, key=lambda r: r.attempt)

    def upsert(self, record: WorkflowStepRecord) -> WorkflowStepLedger:
        """Return a ledger with *record* inserted or replaced by its key."""
        replaced = False
        out: list[WorkflowStepRecord] = []
        for existing in self.records:
            if (
                existing.producer_step == record.producer_step
                and existing.attempt == record.attempt
            ):
                out.append(record)
                replaced = True
            else:
                out.append(existing)
        if not replaced:
            out.append(record)
        return WorkflowStepLedger(records=tuple(out))

    def remove(self, producer_step: str, attempt: int) -> WorkflowStepLedger:
        """Return a ledger with the ``(producer_step, attempt)`` record dropped (v0.1.78 T-C).

        Used by a reclaim path that physically deletes a cleanup-eligible on-disk payload
        (hygiene clean's step-payload coverage): the ledger record must be dropped in the
        SAME operation, or the doctor immediately flags the now-diskless record as
        ``ORPHAN`` — a reclaim that "fixes" one finding by creating another. A no-op
        (byte-identical ledger returned) when the key is absent.
        """
        return WorkflowStepLedger(
            records=tuple(
                existing
                for existing in self.records
                if not (existing.producer_step == producer_step and existing.attempt == attempt)
            )
        )

    def to_list(self) -> list[dict[str, Any]]:
        return [record.to_dict() for record in self.records]

    @classmethod
    def from_list(cls, data: list[object]) -> WorkflowStepLedger:
        records: list[WorkflowStepRecord] = []
        for entry in data:
            assert isinstance(entry, dict)
            records.append(WorkflowStepRecord.from_dict(entry))
        return cls(records=tuple(records))


class _LedgerIterator:
    """Minimal iterator so ``for record in ledger`` works without exposing the tuple."""

    def __init__(self, records: tuple[WorkflowStepRecord, ...]) -> None:
        self._records = records
        self._index = 0

    def __iter__(self) -> _LedgerIterator:
        return self

    def __next__(self) -> WorkflowStepRecord:
        if self._index >= len(self._records):
            raise StopIteration
        record = self._records[self._index]
        self._index += 1
        return record


__all__ = [
    "RetentionMode",
    "WorkflowStepConsumerRecord",
    "WorkflowStepConsumptionState",
    "WorkflowStepLedger",
    "WorkflowStepRecord",
]
