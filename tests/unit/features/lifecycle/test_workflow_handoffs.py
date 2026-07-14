"""Unit tests for the workflow-step handoff resolver (v0.1.30 Item 5 / T-30-D-03).

These pin the queue-semantics contract over an in-memory fake writer + a real
JsonLifecycleRunStore under ``tmp_path`` — hermetic, no real workspace touched.

Acceptance coverage:
- A19 — ``resolve_required`` resolves the EXACT (run, producer step, attempt), not "latest".
- A20 — a missing/malformed required payload raises (the workflow BLOCKS).
- A22 — consumption transitions produced -> consumed_partial -> consumed_all; cleanup
  eligibility flips only after every declared consumer acked.
- A25 — the resolver never uses a filename glob; the lookup is the addressable ledger key.

CRITICAL: immutable data plane — content-hash tamper detection and exact-attempt
addressing must survive.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from dadaia_workspace.core.models.lifecycle import (
    AgentRunResult,
    AgentRunStatus,
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
    durable_payload_from_result,
)
from dadaia_workspace.infrastructure.json_lifecycle_run_store import JsonLifecycleRunStore


class _FakeWriter:
    """In-memory immutable step-payload writer keyed by (run, step, attempt)."""

    def __init__(self) -> None:
        self.files: dict[str, str] = {}
        self.worker_outputs: set[str] = set()

    def write_step_payload(
        self, *, run_id: str, producer_step: str, attempt: int, content: str
    ) -> StepPayloadRef:
        ref = f".dadaia/runs/lifecycle/{run_id}/steps/{producer_step}-attempt-{attempt}.step-payload.json"
        self.files[ref] = content
        return StepPayloadRef(
            payload_ref=ref, content_hash=hashlib.sha256(content.encode("utf-8")).hexdigest()
        )

    def read_step_payload(self, payload_ref: str) -> str | None:
        return self.files.get(payload_ref)

    def purge_step_payloads(
        self, run_id: str, producer_steps: frozenset[str] | set[str] | None = None
    ) -> int:
        zone = f".dadaia/runs/lifecycle/{run_id}/steps/"
        doomed = [
            ref
            for ref in self.files
            if ref.startswith(zone)
            and (
                producer_steps is None
                or ref.rsplit("/", 1)[-1].rsplit("-attempt-", 1)[0] in producer_steps
            )
        ]
        for ref in doomed:
            del self.files[ref]
        return len(doomed)

    def purge_worker_outputs(self, refs: tuple[str, ...]) -> int:
        removed = 0
        for ref in refs:
            if ref in self.worker_outputs:
                self.worker_outputs.remove(ref)
                removed += 1
        return removed


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


# --- ① produce: envelope+ledger+persist + idempotent consumption + digest is compact ----


def test_produce_envelope_ledger_persist_and_digest_compact(tmp_path: Path) -> None:
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

    # idempotent consumption + digest render.
    digest_writer = _FakeWriter()
    digest_resolver = _resolver(tmp_path / "digest", digest_writer)
    digest_run = _run()
    digest_run, _ = digest_resolver.produce(
        digest_run,
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
    resolved = digest_resolver.resolve_required(digest_run, producer_step="qa", attempt=1)
    digest = WorkflowHandoffResolver.render_digest(resolved)
    assert "qa#1" in digest
    assert "verdict: REJECTED" in digest
    assert "tests missing" in digest
    assert "[HIGH] no coverage for resume" in digest
    # The digest is NOT the raw serialised payload object.
    assert json.dumps(resolved.payload) not in digest

    idem_writer = _FakeWriter()
    idem_resolver = _resolver(tmp_path / "idem", idem_writer)
    idem_run = _run()
    idem_run, _ = idem_resolver.produce(
        idem_run,
        producer_step="release_scope",
        attempt=0,
        output_schema="release-scope-handoff-v1",
        payload={"summary": "scope"},
        declared_consumers=("spec_create",),
    )
    idem_run = idem_resolver.record_consumption(
        idem_run,
        producer_step="release_scope",
        producer_attempt=0,
        consumer_step="spec_create",
        consumer_attempt=0,
    )
    again = idem_resolver.record_consumption(
        idem_run,
        producer_step="release_scope",
        producer_attempt=0,
        consumer_step="spec_create",
        consumer_attempt=0,
    )
    idem_record = again.workflow_steps.find("release_scope", 0)
    assert idem_record is not None
    assert len(idem_record.consumptions) == 1


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


# --- consumption transitions (A22) ------------------------------------------------


def test_consumption_transitions_produced_partial_all_and_promoted_never_eligible(
    tmp_path: Path,
) -> None:
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

    # A PROMOTE_TO_EVIDENCE payload never becomes cleanup-eligible, even fully consumed.
    promote_writer = _FakeWriter()
    promote_resolver = _resolver(tmp_path / "promote", promote_writer)
    promote_run = _run()
    promote_run, _ = promote_resolver.produce(
        promote_run,
        producer_step="spec_qa_review",
        attempt=0,
        output_schema="qa-review-handoff-v1",
        payload={"verdict": "APPROVED"},
        declared_consumers=("plan_create",),
        retention_mode=RetentionMode.PROMOTE_TO_EVIDENCE,
    )
    promote_run = promote_resolver.record_consumption(
        promote_run,
        producer_step="spec_qa_review",
        producer_attempt=0,
        consumer_step="plan_create",
        consumer_attempt=0,
    )
    promote_record = promote_run.workflow_steps.find("spec_qa_review", 0)
    assert promote_record is not None
    assert promote_record.consumption_state() is WorkflowStepConsumptionState.CONSUMED_ALL
    assert not promote_record.is_cleanup_eligible(), (
        "promoted evidence survives despite consumed_all"
    )


# --- ② failure param: schema-invalid / unknown schema / missing record / missing file / --
#     hash-mismatch tamper / missing producer


def test_failure_matrix_raises_table(tmp_path: Path) -> None:
    schema_invalid_resolver = _resolver(tmp_path / "schema-invalid", _FakeWriter())
    with pytest.raises(MalformedHandoffError):
        schema_invalid_resolver.produce(
            _run(),
            producer_step="release_scope",
            attempt=0,
            output_schema="release-scope-handoff-v1",
            payload={"no_summary": "x"},
        )

    unknown_schema_resolver = _resolver(tmp_path / "unknown-schema", _FakeWriter())
    with pytest.raises(PayloadSchemaUnknownError):
        unknown_schema_resolver.produce(
            _run(),
            producer_step="release_scope",
            attempt=0,
            output_schema="not-a-real-schema-v9",
            payload={"summary": "x"},
        )

    missing_record_resolver = _resolver(tmp_path / "missing-record", _FakeWriter())
    with pytest.raises(RequiredHandoffMissingError):
        missing_record_resolver.resolve_required(_run(), producer_step="qa", attempt=0)

    missing_file_writer = _FakeWriter()
    missing_file_resolver = _resolver(tmp_path / "missing-file", missing_file_writer)
    mf_run, mf_record = missing_file_resolver.produce(
        _run(),
        producer_step="qa",
        attempt=0,
        output_schema="qa-review-handoff-v1",
        payload={"verdict": "APPROVED"},
    )
    # Simulate the data-plane file vanishing under the ledger.
    del missing_file_writer.files[mf_record.payload_ref]
    with pytest.raises(MalformedHandoffError):
        missing_file_resolver.resolve_required(mf_run, producer_step="qa", attempt=0)

    tamper_writer = _FakeWriter()
    tamper_resolver = _resolver(tmp_path / "tamper", tamper_writer)
    tamper_run, tamper_record = tamper_resolver.produce(
        _run(),
        producer_step="qa",
        attempt=0,
        output_schema="qa-review-handoff-v1",
        payload={"verdict": "APPROVED"},
    )
    tamper_writer.files[tamper_record.payload_ref] = tamper_writer.files[
        tamper_record.payload_ref
    ].replace("APPROVED", "REJECTED")
    with pytest.raises(MalformedHandoffError):
        tamper_resolver.resolve_required(tamper_run, producer_step="qa", attempt=0)


@pytest.mark.parametrize(
    ("output_schema", "payload"),
    [
        ("audit-scope-handoff-v1", {"summary": "audit_scope"}),
        (
            "audit-findings-handoff-v1",
            {
                "summary": "looks fine",
                "verdict": "APPROVED",
                "verdict_reason": "looks fine",
                "findings": [],
            },
        ),
        ("audit-disposition-handoff-v1", {"summary": "triage"}),
    ],
)
def test_audit_payload_schemas_reject_transport_only_fallbacks(
    tmp_path: Path, output_schema: str, payload: dict[str, object]
) -> None:
    resolver = _resolver(tmp_path / output_schema, _FakeWriter())

    with pytest.raises(MalformedHandoffError):
        resolver.produce(
            _run(),
            producer_step="audit",
            attempt=0,
            output_schema=output_schema,
            payload=payload,
        )


def test_audit_payload_schemas_accept_complete_domain_contracts(tmp_path: Path) -> None:
    resolver = _resolver(tmp_path, _FakeWriter())
    run = _run()
    run, _ = resolver.produce(
        run,
        producer_step="audit_scope",
        attempt=0,
        output_schema="audit-scope-handoff-v1",
        payload={
            "summary": "Bound architecture drift.",
            "audit_question": "Does the replay API match its memory contract?",
            "lenses": [{"name": "architecture", "rationale": "Contract fidelity."}],
            "surfaces": ["src/games.py"],
            "acceptance_criteria": [
                {"lens": "architecture", "pass_condition": "No duplicated rules."}
            ],
        },
    )
    run, _ = resolver.produce(
        run,
        producer_step="drift_scan",
        attempt=0,
        output_schema="audit-findings-handoff-v1",
        payload={
            "summary": "One drift found.",
            "verdict": "REJECTED",
            "verdict_reason": "The implementation duplicates a rule.",
            "lens_results": [
                {
                    "lens": "architecture",
                    "status": "FAIL",
                    "evidence": ["src/games.py:10"],
                }
            ],
            "findings": [
                {
                    "id": "duplicate-rule",
                    "severity": "HIGH",
                    "message": "Rule duplicated.",
                    "surface": "src/games.py",
                    "evidence": "src/games.py:10",
                }
            ],
        },
    )
    run, _ = resolver.produce(
        run,
        producer_step="triage",
        attempt=0,
        output_schema="audit-disposition-handoff-v1",
        payload={
            "summary": "Routed the finding.",
            "source_verdict": "REJECTED",
            "dispositions": [
                {
                    "finding_id": "duplicate-rule",
                    "disposition": "bug",
                    "route": "specs/bugs via dadaia bugs append",
                    "severity": "HIGH",
                    "evidence": "src/games.py:10",
                }
            ],
        },
    )

    assert len(run.workflow_steps) == 3


def test_audit_scope_digest_preserves_bounded_execution_contract(tmp_path: Path) -> None:
    resolver = _resolver(tmp_path, _FakeWriter())
    run, _ = resolver.produce(
        _run(),
        producer_step="audit_scope",
        attempt=0,
        output_schema="audit-scope-handoff-v1",
        payload={
            "summary": "Bound replay drift.",
            "audit_question": "Does replay preserve engine rules?",
            "lenses": [{"name": "architecture", "rationale": "Rule ownership."}],
            "surfaces": ["src/games.py", "tests/test_games.py"],
            "acceptance_criteria": [
                {"lens": "architecture", "pass_condition": "One transition path."}
            ],
        },
    )

    digest = WorkflowHandoffResolver.render_digest(
        resolver.resolve_required(run, producer_step="audit_scope", attempt=0)
    )

    assert "audit_question: Does replay preserve engine rules?" in digest
    assert "lenses: architecture" in digest
    assert "src/games.py" in digest
    assert "architecture: One transition path." in digest


def test_audit_findings_digest_preserves_identity_surface_and_evidence(tmp_path: Path) -> None:
    resolver = _resolver(tmp_path, _FakeWriter())
    run, _ = resolver.produce(
        _run(),
        producer_step="drift_scan",
        attempt=0,
        output_schema="audit-findings-handoff-v1",
        payload={
            "summary": "One drift found.",
            "verdict": "REJECTED",
            "verdict_reason": "Architecture drift.",
            "lens_results": [
                {
                    "lens": "architecture",
                    "status": "FAIL",
                    "evidence": ["src/games.py:10"],
                }
            ],
            "findings": [
                {
                    "id": "duplicate-rule",
                    "severity": "HIGH",
                    "message": "Rule duplicated.",
                    "surface": "src/games.py",
                    "evidence": "src/games.py:10",
                }
            ],
        },
    )

    digest = WorkflowHandoffResolver.render_digest(
        resolver.resolve_required(run, producer_step="drift_scan", attempt=0)
    )

    assert "[HIGH] Rule duplicated. (id: duplicate-rule)" in digest
    assert "surface: src/games.py" in digest
    assert "evidence: src/games.py:10" in digest

    missing_producer_resolver = _resolver(tmp_path / "missing-producer", _FakeWriter())
    with pytest.raises(RequiredHandoffMissingError):
        missing_producer_resolver.record_consumption(
            _run(),
            producer_step="ghost",
            producer_attempt=0,
            consumer_step="spec_create",
            consumer_attempt=0,
        )


def test_durable_payload_promotes_domain_handoff_without_temp_self_ref() -> None:
    temp_ref = ".dadaia/tmp/lifecycle-worker/demo/release-scope.step-output.json"
    result = AgentRunResult(
        status=AgentRunStatus.SUCCEEDED,
        summary="codex exec completed",
        artifact_refs=(temp_ref,),
        domain_payload={
            "schema": "agent-run-result-v1",
            "artifact_refs": [temp_ref],
            "artifact": {"type": "report", "path": temp_ref},
            "handoff": {
                "summary": "Bound one authoritative backlog item.",
                "picked_items": {"backlog": ["specs/backlog/replay.md"]},
                "open_questions": [],
            },
        },
    )

    payload = durable_payload_from_result(result, fallback_summary="release_scope", is_review=False)

    assert payload == {
        "summary": "Bound one authoritative backlog item.",
        "picked_items": {"backlog": ["specs/backlog/replay.md"]},
        "open_questions": [],
    }
    assert temp_ref not in json.dumps(payload)


def test_durable_payload_keeps_real_artifact_and_review_verdict() -> None:
    temp_ref = ".dadaia/tmp/lifecycle-worker/demo/review.step-output.json"
    result = AgentRunResult(
        status=AgentRunStatus.SUCCEEDED,
        summary="review complete",
        artifact_refs=(temp_ref,),
        structured_output={
            "verdict": "REJECTED",
            "verdict_reason": "coverage gap",
            "findings": json.dumps(
                [{"severity": "HIGH", "message": "missing replay rejection case"}]
            ),
        },
        domain_payload={
            "schema": "agent-run-result-v1",
            "artifact": {"type": "report", "path": "specs/reviews/qa.json"},
        },
    )

    payload = durable_payload_from_result(result, fallback_summary="review_qa", is_review=True)

    assert payload["verdict"] == "REJECTED"
    assert payload["verdict_reason"] == "coverage gap"
    assert payload["artifact_refs"] == ["specs/reviews/qa.json"]
    assert payload["findings"] == [{"severity": "HIGH", "message": "missing replay rejection case"}]


def test_durable_payload_summarizes_top_level_domain_and_drops_temp_artifact() -> None:
    temp_ref = ".dadaia/tmp/lifecycle-worker/demo/scope.step-output.json"
    result = AgentRunResult(
        status=AgentRunStatus.SUCCEEDED,
        summary="codex exec completed",
        artifact_refs=(temp_ref,),
        domain_payload={
            "schema": "agent-run-result-v1",
            "artifact": {"type": "report", "path": temp_ref},
            "release_scope": {
                "core_problem": "Replay outcomes need an explicit adapter contract.",
                "picked_items": {"backlog": ["specs/backlog/replay.md"]},
            },
        },
    )

    payload = durable_payload_from_result(result, fallback_summary="release_scope", is_review=False)

    assert payload["summary"] == "Replay outcomes need an explicit adapter contract."
    assert "artifact" not in payload
    assert temp_ref not in json.dumps(payload)


def test_durable_payload_prefers_structured_domain_contract_over_transport_findings() -> None:
    temp_ref = ".dadaia/tmp/lifecycle-worker/demo/drift.step-output.json"
    exact_finding = {
        "id": "memory-drift",
        "severity": "MEDIUM",
        "message": "Memory is stale.",
        "surface": "specs/memory/architecture.md",
        "evidence": "specs/memory/architecture.md:10",
    }
    result = AgentRunResult(
        status=AgentRunStatus.SUCCEEDED,
        summary="audit rejected",
        artifact_refs=(temp_ref,),
        structured_output={
            "verdict": "REJECTED",
            "verdict_reason": "Memory drift.",
        },
        domain_payload={
            "schema": "agent-run-result-v1",
            "artifact_refs": [temp_ref],
            "verdict": "REJECTED",
            "findings": [{"severity": "MEDIUM", "message": "presentation-only finding"}],
            "structured_output": {
                "summary": "One memory drift found.",
                "verdict": "REJECTED",
                "verdict_reason": "Memory drift.",
                "lens_results": [
                    {
                        "lens": "architecture",
                        "status": "FAIL",
                        "evidence": ["specs/memory/architecture.md:10"],
                    }
                ],
                "findings": [exact_finding],
            },
        },
    )

    payload = durable_payload_from_result(result, fallback_summary="drift_scan", is_review=True)

    assert payload["summary"] == "One memory drift found."
    assert payload["lens_results"] == [
        {
            "lens": "architecture",
            "status": "FAIL",
            "evidence": ["specs/memory/architecture.md:10"],
        }
    ]
    assert payload["findings"] == [exact_finding]
    assert "presentation-only" not in json.dumps(payload)


def test_reset_run_zone_purges_ledger_and_exact_worker_outputs(tmp_path: Path) -> None:
    writer = _FakeWriter()
    resolver = _resolver(tmp_path, writer)
    run, _ = resolver.produce(
        _run(),
        producer_step="release_scope",
        attempt=0,
        output_schema="release-scope-handoff-v1",
        payload={"summary": "old scope"},
    )
    assert run.workflow_steps.find("release_scope", 0) is not None
    worker_ref = ".dadaia/tmp/lifecycle-worker/demo/scope.step-output.json"
    writer.worker_outputs.add(worker_ref)

    removed = resolver.reset_run_zone("run-1", worker_output_refs=(worker_ref,))

    assert removed == 2
    assert writer.files == {}
    assert writer.worker_outputs == set()
