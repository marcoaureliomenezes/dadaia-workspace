"""Unit tests for the workflow-step handoff resolver (v0.1.30 Item 5 / T-30-D-03).

These pin the queue-semantics contract over an in-memory fake writer + a real
JsonLifecycleRunStore under ``tmp_path`` — hermetic, no real workspace touched.

Acceptance coverage:
- A19 — ``resolve_required`` resolves the EXACT (run, producer step, attempt), not "latest".
- A20 — a missing/malformed required payload raises (the workflow BLOCKS).
- A22 — consumption transitions produced → consumed_partial → consumed_all; cleanup
  eligibility flips only after every declared consumer acked.
- A25 — the resolver never uses a filename glob; the lookup is the addressable ledger key.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dadaia_workspace.core.models.lifecycle import (
    LifecyclePhase,
    LifecycleRun,
    LifecycleRunStatus,
)
from dadaia_workspace.core.models.workflow_handoff import (
    RetentionMode,
    WorkflowStepConsumptionState,
)
from dadaia_workspace.features.lifecycle.workflow_handoffs import (
    MalformedHandoffError,
    PayloadSchemaUnknownError,
    RequiredHandoffMissingError,
    StepPayloadRef,
    WorkflowHandoffResolver,
)
from dadaia_workspace.infrastructure.json_lifecycle_run_store import JsonLifecycleRunStore


class _FakeWriter:
    """In-memory immutable step-payload writer keyed by (run, step, attempt)."""

    def __init__(self) -> None:
        self.files: dict[str, str] = {}

    def write_step_payload(
        self, *, run_id: str, producer_step: str, attempt: int, content: str
    ) -> StepPayloadRef:
        import hashlib

        ref = f".dadaia/runs/lifecycle/{run_id}/steps/{producer_step}-attempt-{attempt}.step-payload.json"
        self.files[ref] = content
        return StepPayloadRef(
            payload_ref=ref, content_hash=hashlib.sha256(content.encode("utf-8")).hexdigest()
        )

    def read_step_payload(self, payload_ref: str) -> str | None:
        return self.files.get(payload_ref)


_T = "2026-06-27T12:00:00Z"


def _clock() -> str:
    return _T


def _store(tmp_path: Path) -> JsonLifecycleRunStore:
    # Build a minimal initialized-workspace skeleton so the store accepts tmp_path.
    (tmp_path / ".dadaia" / "states").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".dadaia" / "states" / "spec_contexts.json").write_text("{}", encoding="utf-8")
    (tmp_path / "repos").mkdir(exist_ok=True)
    return JsonLifecycleRunStore(tmp_path)


def _run() -> LifecycleRun:
    return LifecycleRun(
        run_id="run-1",
        context="dadaia-workspace",
        release_id="v0.1.30",
        command="release_definition",
        phase=LifecyclePhase.RELEASE_DEFINITION,
        status=LifecycleRunStatus.RUNNING,
        current_step="release_scope",
        idempotency_key="run-1",
    )


def _resolver(tmp_path: Path, writer: _FakeWriter) -> WorkflowHandoffResolver:
    return WorkflowHandoffResolver(run_store=_store(tmp_path), payload_writer=writer, clock=_clock)


# --- produce + persist (A18/A21) --------------------------------------------------


def test_produce_writes_immutable_payload_and_records_ledger_entry(tmp_path: Path) -> None:
    writer = _FakeWriter()
    resolver = _resolver(tmp_path, writer)
    run, record = resolver.produce(
        _run(),
        producer_step="release_scope",
        attempt=0,
        output_schema="release-scope-handoff-v1",
        payload={"summary": "scope locked"},
        declared_consumers=("spec_create",),
    )
    assert len(run.workflow_steps) == 1
    assert record.key == ("run-1", "release_scope", 0)
    assert record.payload_ref in writer.files
    # The on-disk envelope wraps the payload under the addressable key.
    envelope = json.loads(writer.files[record.payload_ref])
    assert envelope["schema_version"] == "workflow-step-payload-v1"
    assert envelope["producer_step"] == "release_scope"
    assert envelope["attempt"] == 0
    assert envelope["payload"] == {"summary": "scope locked"}
    # Persisted to the run store.
    reloaded = resolver._run_store.load("run-1")  # type: ignore[attr-defined]
    assert reloaded is not None
    assert reloaded.workflow_steps.find("release_scope", 0) is not None


def test_produce_rejects_payload_failing_named_schema(tmp_path: Path) -> None:
    resolver = _resolver(tmp_path, _FakeWriter())
    with pytest.raises(MalformedHandoffError):
        resolver.produce(
            _run(),
            producer_step="release_scope",
            attempt=0,
            output_schema="release-scope-handoff-v1",
            payload={"no_summary": "x"},
        )


def test_produce_rejects_unknown_output_schema(tmp_path: Path) -> None:
    resolver = _resolver(tmp_path, _FakeWriter())
    with pytest.raises(PayloadSchemaUnknownError):
        resolver.produce(
            _run(),
            producer_step="release_scope",
            attempt=0,
            output_schema="not-a-real-schema-v9",
            payload={"summary": "x"},
        )


# --- resolve_required exact-by-attempt (A19/A25) ----------------------------------


def test_resolve_required_resolves_exact_attempt_not_latest(tmp_path: Path) -> None:
    """A19: implement#2 must consume qa#1, NOT qa#0 / latest filename."""
    writer = _FakeWriter()
    resolver = _resolver(tmp_path, writer)
    run = _run()
    run, _ = resolver.produce(
        run,
        producer_step="qa",
        attempt=0,
        output_schema="qa-review-handoff-v1",
        payload={"verdict": "REJECTED", "verdict_reason": "first round failed"},
    )
    run, _ = resolver.produce(
        run,
        producer_step="qa",
        attempt=1,
        output_schema="qa-review-handoff-v1",
        payload={"verdict": "REJECTED", "verdict_reason": "second round failed"},
    )
    resolved = resolver.resolve_required(run, producer_step="qa", attempt=1)
    assert resolved.record.attempt == 1
    assert resolved.payload["verdict_reason"] == "second round failed"
    # The exact attempt 0 is independently resolvable — the ledger keys by attempt.
    earlier = resolver.resolve_required(run, producer_step="qa", attempt=0)
    assert earlier.payload["verdict_reason"] == "first round failed"


def test_resolve_required_missing_record_blocks(tmp_path: Path) -> None:
    resolver = _resolver(tmp_path, _FakeWriter())
    with pytest.raises(RequiredHandoffMissingError):
        resolver.resolve_required(_run(), producer_step="qa", attempt=0)


def test_resolve_required_missing_file_blocks(tmp_path: Path) -> None:
    writer = _FakeWriter()
    resolver = _resolver(tmp_path, writer)
    run, record = resolver.produce(
        _run(),
        producer_step="qa",
        attempt=0,
        output_schema="qa-review-handoff-v1",
        payload={"verdict": "APPROVED"},
    )
    # Simulate the data-plane file vanishing under the ledger.
    del writer.files[record.payload_ref]
    with pytest.raises(MalformedHandoffError):
        resolver.resolve_required(run, producer_step="qa", attempt=0)


def test_resolve_required_mutated_payload_blocks_on_hash_mismatch(tmp_path: Path) -> None:
    """A20 + immutability: a tampered payload fails the content-hash check."""
    writer = _FakeWriter()
    resolver = _resolver(tmp_path, writer)
    run, record = resolver.produce(
        _run(),
        producer_step="qa",
        attempt=0,
        output_schema="qa-review-handoff-v1",
        payload={"verdict": "APPROVED"},
    )
    writer.files[record.payload_ref] = writer.files[record.payload_ref].replace(
        "APPROVED", "REJECTED"
    )
    with pytest.raises(MalformedHandoffError):
        resolver.resolve_required(run, producer_step="qa", attempt=0)


# --- consumption transitions (A22) ------------------------------------------------


def test_consumption_transitions_produced_partial_all(tmp_path: Path) -> None:
    writer = _FakeWriter()
    resolver = _resolver(tmp_path, writer)
    run = _run()
    run, _ = resolver.produce(
        run,
        producer_step="release_scope",
        attempt=0,
        output_schema="release-scope-handoff-v1",
        payload={"summary": "scope"},
        declared_consumers=("spec_create", "plan_create"),
    )
    assert (
        run.workflow_steps.find("release_scope", 0).consumption_state()  # type: ignore[union-attr]
        is WorkflowStepConsumptionState.PRODUCED
    )
    run = resolver.record_consumption(
        run,
        producer_step="release_scope",
        producer_attempt=0,
        consumer_step="spec_create",
        consumer_attempt=0,
    )
    record = run.workflow_steps.find("release_scope", 0)
    assert record is not None
    assert record.consumption_state() is WorkflowStepConsumptionState.CONSUMED_PARTIAL
    assert not record.is_cleanup_eligible()
    run = resolver.record_consumption(
        run,
        producer_step="release_scope",
        producer_attempt=0,
        consumer_step="plan_create",
        consumer_attempt=0,
    )
    record = run.workflow_steps.find("release_scope", 0)
    assert record is not None
    assert record.consumption_state() is WorkflowStepConsumptionState.CONSUMED_ALL
    assert record.is_cleanup_eligible()


def test_record_consumption_is_idempotent(tmp_path: Path) -> None:
    writer = _FakeWriter()
    resolver = _resolver(tmp_path, writer)
    run = _run()
    run, _ = resolver.produce(
        run,
        producer_step="release_scope",
        attempt=0,
        output_schema="release-scope-handoff-v1",
        payload={"summary": "scope"},
        declared_consumers=("spec_create",),
    )
    run = resolver.record_consumption(
        run,
        producer_step="release_scope",
        producer_attempt=0,
        consumer_step="spec_create",
        consumer_attempt=0,
    )
    again = resolver.record_consumption(
        run,
        producer_step="release_scope",
        producer_attempt=0,
        consumer_step="spec_create",
        consumer_attempt=0,
    )
    record = again.workflow_steps.find("release_scope", 0)
    assert record is not None
    assert len(record.consumptions) == 1


def test_record_consumption_missing_producer_blocks(tmp_path: Path) -> None:
    resolver = _resolver(tmp_path, _FakeWriter())
    with pytest.raises(RequiredHandoffMissingError):
        resolver.record_consumption(
            _run(),
            producer_step="ghost",
            producer_attempt=0,
            consumer_step="spec_create",
            consumer_attempt=0,
        )


def test_promote_to_evidence_payload_never_cleanup_eligible(tmp_path: Path) -> None:
    writer = _FakeWriter()
    resolver = _resolver(tmp_path, writer)
    run = _run()
    run, _ = resolver.produce(
        run,
        producer_step="spec_qa_review",
        attempt=0,
        output_schema="qa-review-handoff-v1",
        payload={"verdict": "APPROVED"},
        declared_consumers=("plan_create",),
        retention_mode=RetentionMode.PROMOTE_TO_EVIDENCE,
    )
    run = resolver.record_consumption(
        run,
        producer_step="spec_qa_review",
        producer_attempt=0,
        consumer_step="plan_create",
        consumer_attempt=0,
    )
    record = run.workflow_steps.find("spec_qa_review", 0)
    assert record is not None
    assert record.consumption_state() is WorkflowStepConsumptionState.CONSUMED_ALL
    assert not record.is_cleanup_eligible(), "promoted evidence survives despite consumed_all"


# --- compact digest (not raw JSON) ------------------------------------------------


def test_render_digest_is_compact_and_omits_raw_json(tmp_path: Path) -> None:
    writer = _FakeWriter()
    resolver = _resolver(tmp_path, writer)
    run = _run()
    run, _ = resolver.produce(
        run,
        producer_step="qa",
        attempt=1,
        output_schema="qa-review-handoff-v1",
        payload={
            "verdict": "REJECTED",
            "verdict_reason": "tests missing",
            "summary": "qa round 2",
            "findings": [{"severity": "HIGH", "message": "no coverage for resume"}],
        },
    )
    resolved = resolver.resolve_required(run, producer_step="qa", attempt=1)
    digest = WorkflowHandoffResolver.render_digest(resolved)
    assert "qa#1" in digest
    assert "verdict: REJECTED" in digest
    assert "tests missing" in digest
    assert "[HIGH] no coverage for resume" in digest
    # The digest is NOT the raw serialised payload object.
    assert json.dumps(resolved.payload) not in digest
