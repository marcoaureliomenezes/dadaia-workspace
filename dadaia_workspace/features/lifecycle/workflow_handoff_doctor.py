"""Workflow-step handoff doctor (v0.1.30 Item 5 / T-30-D-08 / A26).

A read-only coherence check over the run-scoped workflow-step handoff system. It
reconciles every persisted ``LifecycleRun.workflow_steps`` ledger with the immutable
on-disk payloads under ``.dadaia/runs/lifecycle/<run_id>/steps/`` and fails on:

- **orphan** — a ledger record whose on-disk payload file is missing.
- **malformed** — an on-disk ``*.step-payload.json`` that is not valid JSON / not an object.
- **stale** — a cleanup-eligible payload (``consumed_all`` + delete-after-consumed) still
  on disk past the consumed TTL — the retention sweep should have reclaimed it.
- **undeclared** — an on-disk payload with no matching ledger record (run id, step,
  attempt) — a data-plane file the control plane does not know about.
- **unconsumed-required** — a TERMINAL run with a declared-consumer payload still in
  ``produced`` / ``consumed_partial`` — a required prompt-to-prompt edge that was never
  fully consumed.

The doctor never deletes or mutates — it reports. ``ok`` is ``True`` only when there are
no findings. Layering: ``features/`` importing ``core/`` + the run-store protocol; the
on-disk reconciliation uses the workspace root directly (read-only).
"""

from __future__ import annotations

import datetime as dt
import json
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

from dadaia_workspace.core.models.hygiene import SlopPolicy
from dadaia_workspace.core.models.lifecycle import LifecycleRunStatus
from dadaia_workspace.core.models.workflow_handoff import (
    RetentionMode,
    WorkflowStepConsumptionState,
)
from dadaia_workspace.core.protocols.lifecycle_run_store import LifecycleRunStore


class WorkflowHandoffFindingKind(StrEnum):
    ORPHAN = "orphan"
    MALFORMED = "malformed"
    STALE = "stale"
    UNDECLARED = "undeclared"
    UNCONSUMED_REQUIRED = "unconsumed_required"


@dataclass(frozen=True)
class WorkflowHandoffFinding:
    kind: WorkflowHandoffFindingKind
    ref: str
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {"kind": self.kind.value, "ref": self.ref, "message": self.message}


@dataclass(frozen=True)
class WorkflowHandoffDoctorReport:
    ok: bool
    findings: tuple[WorkflowHandoffFinding, ...]

    def to_dict(self) -> dict[str, Any]:
        return {"ok": self.ok, "findings": [f.to_dict() for f in self.findings]}


class WorkflowHandoffDoctor:
    """Reconcile the workflow-step ledger ↔ on-disk payloads and report incoherences."""

    def __init__(
        self,
        workspace_root: Path,
        run_store: LifecycleRunStore,
        *,
        now: dt.datetime | None = None,
        policy: SlopPolicy | None = None,
    ) -> None:
        self._workspace_root = workspace_root.resolve()
        self._steps_root = self._workspace_root / ".dadaia" / "runs" / "lifecycle"
        self._run_store = run_store
        self._now = (now or dt.datetime.now(tz=dt.UTC)).astimezone(dt.UTC)
        self._policy = policy or SlopPolicy()

    def run(self) -> WorkflowHandoffDoctorReport:
        findings: list[WorkflowHandoffFinding] = []
        ledger_refs: set[str] = set()
        terminal = {LifecycleRunStatus.COMPLETED, LifecycleRunStatus.FAILED}
        consumed_ttl = self._policy.tmp_ttl_seconds
        cutoff = self._now - dt.timedelta(seconds=consumed_ttl)

        for run in self._run_store.list_runs():
            run_terminal = run.status in terminal
            for record in run.workflow_steps:
                ledger_refs.add(record.payload_ref)
                payload_path = self._workspace_root / record.payload_ref
                if not payload_path.is_file():
                    findings.append(
                        WorkflowHandoffFinding(
                            kind=WorkflowHandoffFindingKind.ORPHAN,
                            ref=record.payload_ref,
                            message=(
                                f"ledger record {record.producer_step}#{record.attempt} of run "
                                f"{run.run_id} has no on-disk payload"
                            ),
                        )
                    )
                # stale: a cleanup-eligible delete-after-consumed payload still present
                # past the consumed TTL — retention should have reclaimed it.
                elif (
                    record.is_cleanup_eligible()
                    and record.retention_mode is RetentionMode.DELETE_AFTER_CONSUMED
                    and self._mtime(payload_path) < cutoff
                ):
                    findings.append(
                        WorkflowHandoffFinding(
                            kind=WorkflowHandoffFindingKind.STALE,
                            ref=record.payload_ref,
                            message=(
                                f"cleanup-eligible payload {record.producer_step}#{record.attempt} "
                                f"is past the consumed TTL but not reclaimed"
                            ),
                        )
                    )
                # unconsumed-required: a terminal run whose declared-consumer payload was
                # never fully consumed — a required edge silently went unfilled.
                if (
                    run_terminal
                    and record.declared_consumers
                    and record.consumption_state() is not WorkflowStepConsumptionState.CONSUMED_ALL
                ):
                    findings.append(
                        WorkflowHandoffFinding(
                            kind=WorkflowHandoffFindingKind.UNCONSUMED_REQUIRED,
                            ref=record.payload_ref,
                            message=(
                                f"terminal run {run.run_id}: required payload "
                                f"{record.producer_step}#{record.attempt} is "
                                f"{record.consumption_state().value}, not consumed_all"
                            ),
                        )
                    )

        findings.extend(self._scan_disk(ledger_refs))
        return WorkflowHandoffDoctorReport(ok=not findings, findings=tuple(findings))

    def _scan_disk(self, ledger_refs: set[str]) -> list[WorkflowHandoffFinding]:
        findings: list[WorkflowHandoffFinding] = []
        if not self._steps_root.is_dir():
            return findings
        for payload in sorted(self._steps_root.rglob("*.step-payload.json")):
            if not payload.is_file():
                continue
            rel = payload.resolve().relative_to(self._workspace_root).as_posix()
            try:
                doc = json.loads(payload.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                findings.append(
                    WorkflowHandoffFinding(
                        kind=WorkflowHandoffFindingKind.MALFORMED,
                        ref=rel,
                        message="on-disk step payload is not valid JSON",
                    )
                )
                continue
            if not isinstance(doc, dict):
                findings.append(
                    WorkflowHandoffFinding(
                        kind=WorkflowHandoffFindingKind.MALFORMED,
                        ref=rel,
                        message="on-disk step payload is not a JSON object",
                    )
                )
                continue
            if rel not in ledger_refs:
                findings.append(
                    WorkflowHandoffFinding(
                        kind=WorkflowHandoffFindingKind.UNDECLARED,
                        ref=rel,
                        message="on-disk step payload has no matching ledger record",
                    )
                )
        return findings

    @staticmethod
    def _mtime(path: Path) -> dt.datetime:
        return dt.datetime.fromtimestamp(path.stat().st_mtime, tz=dt.UTC)


__all__ = [
    "WorkflowHandoffDoctor",
    "WorkflowHandoffDoctorReport",
    "WorkflowHandoffFinding",
    "WorkflowHandoffFindingKind",
]
