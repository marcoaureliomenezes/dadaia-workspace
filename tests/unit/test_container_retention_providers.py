"""Integration tests for the REAL container retention providers (v0.1.30 Wave D / A23).

The A23 unit tests in ``test_retention_step_payloads.py`` inject FAKE allow/live-claim
sets. These tests exercise the actual composition-root derivation
(``_step_payload_reclaim_allow`` / ``_live_lifecycle_claims``) from persisted
``LifecycleRun`` records — the data-loss-safety wiring the production sweep relies on
(R3). A regression here would silently re-open the data-loss risk that the fakes can't
catch, so this is the guard for the real set-derivation.
"""

from __future__ import annotations

import json
from pathlib import Path

from dadaia_workspace.container import (
    _live_lifecycle_claims,
    _step_payload_reclaim_allow,
)
from dadaia_workspace.core.models.lifecycle import (
    LifecyclePhase,
    LifecycleRun,
    LifecycleRunStatus,
)
from dadaia_workspace.core.models.workflow_handoff import (
    RetentionMode,
    WorkflowStepConsumerRecord,
    WorkflowStepLedger,
    WorkflowStepRecord,
)
from dadaia_workspace.infrastructure.json_lifecycle_run_store import JsonLifecycleRunStore


def _workspace(tmp_path: Path) -> Path:
    # The retention providers go through build_lifecycle_run_store -> _guard_initialized,
    # which requires the spec_contexts.json marker to exist.
    states = tmp_path / ".dadaia" / "states"
    states.mkdir(parents=True)
    (states / "spec_contexts.json").write_text(json.dumps({"contexts": []}), encoding="utf-8")
    return tmp_path


def _payload_ref(run_id: str, step: str, attempt: int) -> str:
    return f".dadaia/runs/lifecycle/{run_id}/steps/{step}-attempt-{attempt}.step-payload.json"


def _record(
    run_id: str,
    step: str,
    *,
    mode: RetentionMode,
    consumed: bool,
) -> WorkflowStepRecord:
    consumptions: tuple[WorkflowStepConsumerRecord, ...] = ()
    if consumed:
        consumptions = (
            WorkflowStepConsumerRecord(
                consumer_step="downstream",
                consumer_attempt=0,
                consumed_at="2026-06-27T12:30:00Z",
            ),
        )
    return WorkflowStepRecord(
        run_id=run_id,
        producer_step=step,
        attempt=0,
        output_schema="release-scope-handoff-v1",
        payload_ref=_payload_ref(run_id, step, 0),
        content_hash="a" * 64,
        produced_at="2026-06-27T12:00:00Z",
        retention_mode=mode,
        declared_consumers=("downstream",),
        consumptions=consumptions,
    )


def _save(
    store: JsonLifecycleRunStore,
    run_id: str,
    status: LifecycleRunStatus,
    record: WorkflowStepRecord,
) -> None:
    store.save(
        LifecycleRun(
            run_id=run_id,
            context="dadaia-workspace",
            release_id="v0.1.30",
            command="release_definition",
            phase=LifecyclePhase.RELEASE_DEFINITION,
            status=status,
            current_step=record.producer_step,
            workflow_steps=WorkflowStepLedger(records=(record,)),
        )
    )


def test_reclaim_allow_and_live_claims_protect_live_promoted_and_keep_modes(
    tmp_path: Path,
) -> None:
    workspace = _workspace(tmp_path)
    store = JsonLifecycleRunStore(workspace)

    # LIVE (non-terminal) run, consumed_all delete-after-consumed payload.
    live = _record("run-live", "scope", mode=RetentionMode.DELETE_AFTER_CONSUMED, consumed=True)
    _save(store, "run-live", LifecycleRunStatus.RUNNING, live)

    # TERMINAL run, consumed_all delete-after-consumed → the ONLY reclaimable case.
    term_del = _record("run-term", "scope", mode=RetentionMode.DELETE_AFTER_CONSUMED, consumed=True)
    _save(store, "run-term", LifecycleRunStatus.COMPLETED, term_del)

    # TERMINAL run, consumed_all PROMOTE_TO_EVIDENCE → durable, never reclaimable.
    term_promo = _record(
        "run-promo", "verdict", mode=RetentionMode.PROMOTE_TO_EVIDENCE, consumed=True
    )
    _save(store, "run-promo", LifecycleRunStatus.COMPLETED, term_promo)

    # TERMINAL run, consumed_all KEEP_UNTIL_FAILURE_TTL → kept on the failure schedule,
    # never reclaimed by the consumed-TTL sweep (the is_cleanup_eligible retention-mode fix).
    term_keep = _record(
        "run-keep", "scope", mode=RetentionMode.KEEP_UNTIL_FAILURE_TTL, consumed=True
    )
    _save(store, "run-keep", LifecycleRunStatus.FAILED, term_keep)

    # TERMINAL run, delete-after-consumed but UNCONSUMED → required edge unfilled, not eligible.
    term_unconsumed = _record(
        "run-unc", "scope", mode=RetentionMode.DELETE_AFTER_CONSUMED, consumed=False
    )
    _save(store, "run-unc", LifecycleRunStatus.COMPLETED, term_unconsumed)

    allow = _step_payload_reclaim_allow(workspace)()
    claims = _live_lifecycle_claims(workspace)()

    # Only the terminal, consumed_all, delete-after-consumed payload is reclaim-eligible.
    assert term_del.payload_ref.lstrip("/") in allow
    # Live run's payload is NEVER eligible AND is explicitly claimed (defence in depth).
    assert live.payload_ref.lstrip("/") not in allow
    assert live.payload_ref.lstrip("/") in claims
    # Promoted evidence and keep-until-failure payloads survive (not in the allow set).
    assert term_promo.payload_ref.lstrip("/") not in allow
    assert term_keep.payload_ref.lstrip("/") not in allow
    # An unconsumed required payload is not eligible.
    assert term_unconsumed.payload_ref.lstrip("/") not in allow
    # Terminal-run payloads are not live-claimed.
    assert term_del.payload_ref.lstrip("/") not in claims
