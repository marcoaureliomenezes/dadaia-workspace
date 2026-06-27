"""Unit tests for the workflow-step handoff ledger models (v0.1.30 Item 5 / T-30-D-01).

The headline guard is **A27 back-compat**: an old ``LifecycleRun`` record written before
``workflow_steps`` existed must still load (→ empty ledger), and a new record must
round-trip its ledger byte-for-byte. This SAFETY test is landed BEFORE the producer code
that writes ledger entries, per the operator-approved Wave-D order.
"""

from __future__ import annotations

from dadaia_workspace.core.models.lifecycle import (
    LifecyclePhase,
    LifecycleRun,
    LifecycleRunStatus,
)
from dadaia_workspace.core.models.workflow_handoff import (
    RetentionMode,
    WorkflowStepConsumerRecord,
    WorkflowStepConsumptionState,
    WorkflowStepLedger,
    WorkflowStepRecord,
)


def _record(
    *,
    producer_step: str = "release_scope",
    attempt: int = 0,
    declared_consumers: tuple[str, ...] = ("spec_create",),
    consumptions: tuple[WorkflowStepConsumerRecord, ...] = (),
    retention_mode: RetentionMode = RetentionMode.DELETE_AFTER_CONSUMED,
) -> WorkflowStepRecord:
    return WorkflowStepRecord(
        run_id="run-1",
        producer_step=producer_step,
        attempt=attempt,
        output_schema="release-scope-handoff-v1",
        payload_ref=f".dadaia/runs/lifecycle/run-1/steps/001-{producer_step}-attempt-{attempt}.step-payload.json",
        content_hash="a" * 64,
        produced_at="2026-06-27T12:00:00Z",
        retention_mode=retention_mode,
        declared_consumers=declared_consumers,
        consumptions=consumptions,
    )


def _base_run_dict() -> dict[str, object]:
    """An old-shape persisted run dict with NO ``workflow_steps`` key (pre-v0.1.30)."""
    return {
        "run_id": "run-1",
        "context": "dadaia-workspace",
        "release_id": "v0.1.29",
        "command": "release_definition",
        "phase": LifecyclePhase.RELEASE_DEFINITION.value,
        "status": LifecycleRunStatus.RUNNING.value,
        "current_step": "release_scope",
        "expected_artifacts": [],
        "idempotency_key": "run-1",
        "blocked": None,
        "injected_context": [],
        "workflow_policy": None,
        # deliberately NO "workflow_steps" key — this is an old record.
    }


# --- A27: back-compat round-trip --------------------------------------------------


def test_old_lifecycle_run_without_workflow_steps_loads_as_empty_ledger() -> None:
    """A27: an old record (no ``workflow_steps`` key) loads → empty ledger, never raises."""
    old = _base_run_dict()
    assert "workflow_steps" not in old

    run = LifecycleRun.from_dict(old)

    assert isinstance(run.workflow_steps, WorkflowStepLedger)
    assert len(run.workflow_steps) == 0
    assert run.workflow_steps.to_list() == []


def test_new_lifecycle_run_round_trips_its_workflow_step_ledger() -> None:
    """A27: a new record with a populated ledger round-trips through to_dict/from_dict."""
    consumed = WorkflowStepConsumerRecord(
        consumer_step="spec_create", consumer_attempt=0, consumed_at="2026-06-27T12:05:00Z"
    )
    ledger = WorkflowStepLedger(
        records=(
            _record(producer_step="release_scope", attempt=0, consumptions=(consumed,)),
            _record(producer_step="spec_create", attempt=0, declared_consumers=()),
        )
    )
    run = LifecycleRun(
        run_id="run-1",
        context="dadaia-workspace",
        release_id="v0.1.30",
        command="release_definition",
        phase=LifecyclePhase.RELEASE_DEFINITION,
        status=LifecycleRunStatus.RUNNING,
        current_step="spec_create",
        workflow_steps=ledger,
    )

    restored = LifecycleRun.from_dict(run.to_dict())

    assert restored.workflow_steps.to_list() == ledger.to_list()
    assert restored == run
    # The serialised form carries the additive key.
    assert "workflow_steps" in run.to_dict()


def test_lifecycle_run_default_workflow_steps_is_empty_ledger() -> None:
    """A LifecycleRun constructed without a ledger defaults to an empty one (additive)."""
    run = LifecycleRun(
        run_id="r",
        context="c",
        release_id="v",
        command="release_definition",
        phase=LifecyclePhase.RELEASE_DEFINITION,
        status=LifecycleRunStatus.RUNNING,
        current_step="s",
    )
    assert len(run.workflow_steps) == 0


# --- consumption state derivation (A22) -------------------------------------------


def test_consumption_state_is_produced_when_no_consumer_acked() -> None:
    record = _record(declared_consumers=("spec_create", "plan_create"))
    assert record.consumption_state() is WorkflowStepConsumptionState.PRODUCED
    assert not record.is_cleanup_eligible()


def test_consumption_state_is_partial_when_some_consumers_acked() -> None:
    acked = WorkflowStepConsumerRecord(
        consumer_step="spec_create", consumer_attempt=0, consumed_at="2026-06-27T12:05:00Z"
    )
    record = _record(declared_consumers=("spec_create", "plan_create"), consumptions=(acked,))
    assert record.consumption_state() is WorkflowStepConsumptionState.CONSUMED_PARTIAL
    assert not record.is_cleanup_eligible()


def test_consumption_state_is_all_when_every_declared_consumer_acked() -> None:
    acks = (
        WorkflowStepConsumerRecord(
            consumer_step="spec_create", consumer_attempt=0, consumed_at="t1"
        ),
        WorkflowStepConsumerRecord(
            consumer_step="plan_create", consumer_attempt=0, consumed_at="t2"
        ),
    )
    record = _record(declared_consumers=("spec_create", "plan_create"), consumptions=acks)
    assert record.consumption_state() is WorkflowStepConsumptionState.CONSUMED_ALL
    assert record.is_cleanup_eligible()


def test_payload_with_no_declared_consumers_is_never_auto_consumed_all() -> None:
    record = _record(declared_consumers=())
    assert record.consumption_state() is WorkflowStepConsumptionState.PRODUCED
    assert not record.is_cleanup_eligible()


def test_promote_to_evidence_is_never_cleanup_eligible_even_when_consumed_all() -> None:
    acked = WorkflowStepConsumerRecord(
        consumer_step="spec_create", consumer_attempt=0, consumed_at="t"
    )
    record = _record(
        declared_consumers=("spec_create",),
        consumptions=(acked,),
        retention_mode=RetentionMode.PROMOTE_TO_EVIDENCE,
    )
    assert record.consumption_state() is WorkflowStepConsumptionState.CONSUMED_ALL
    assert not record.is_cleanup_eligible(), "promoted evidence is durable, never reclaimed"


# --- with_consumption idempotency -------------------------------------------------


def test_with_consumption_appends_and_is_idempotent_per_step_attempt() -> None:
    record = _record(declared_consumers=("spec_create",))
    ack = WorkflowStepConsumerRecord(
        consumer_step="spec_create", consumer_attempt=0, consumed_at="t"
    )
    once = record.with_consumption(ack)
    twice = once.with_consumption(ack)
    assert len(once.consumptions) == 1
    assert twice is once, "re-recording the same (step, attempt) is a no-op"


def test_with_consumption_distinguishes_attempts() -> None:
    """Different attempts of the same consumer step are distinct consumptions (A24)."""
    record = _record(declared_consumers=("implement",))
    a0 = WorkflowStepConsumerRecord(consumer_step="implement", consumer_attempt=0, consumed_at="t0")
    a1 = WorkflowStepConsumerRecord(consumer_step="implement", consumer_attempt=1, consumed_at="t1")
    updated = record.with_consumption(a0).with_consumption(a1)
    assert len(updated.consumptions) == 2


# --- ledger lookups (A19 exact-by-attempt) ----------------------------------------


def test_ledger_find_resolves_exact_step_and_attempt() -> None:
    ledger = WorkflowStepLedger(
        records=(
            _record(producer_step="qa", attempt=0),
            _record(producer_step="qa", attempt=1),
        )
    )
    found = ledger.find("qa", 1)
    assert found is not None
    assert found.key == ("run-1", "qa", 1)
    assert ledger.find("qa", 2) is None


def test_ledger_latest_attempt_returns_highest_attempt() -> None:
    ledger = WorkflowStepLedger(
        records=(
            _record(producer_step="qa", attempt=0),
            _record(producer_step="qa", attempt=2),
            _record(producer_step="qa", attempt=1),
        )
    )
    latest = ledger.latest_attempt("qa")
    assert latest is not None
    assert latest.attempt == 2
    assert ledger.latest_attempt("missing") is None


def test_ledger_upsert_replaces_by_key_and_preserves_order() -> None:
    ledger = WorkflowStepLedger(records=(_record(producer_step="qa", attempt=0),))
    replacement = _record(producer_step="qa", attempt=0, declared_consumers=("implement",))
    updated = ledger.upsert(replacement)
    assert len(updated) == 1
    found = updated.find("qa", 0)
    assert found is not None
    assert found.declared_consumers == ("implement",)
    # upsert of a new key appends
    appended = updated.upsert(_record(producer_step="spec", attempt=0))
    assert len(appended) == 2


def test_ledger_round_trips_through_list_form() -> None:
    ledger = WorkflowStepLedger(
        records=(_record(producer_step="qa", attempt=0), _record(producer_step="spec", attempt=0))
    )
    assert WorkflowStepLedger.from_list(ledger.to_list()).to_list() == ledger.to_list()
