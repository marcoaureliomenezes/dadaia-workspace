"""Workflow-step handoff doctor (v0.1.30 Item 5 / T-30-D-08 / A26).

Pins A26: the doctor fails on orphan, malformed, stale, undeclared, and
unconsumed-required workflow-step payloads, and reports ``ok`` when the ledger and the
on-disk data plane are coherent. Built on the real ``WorkflowHandoffResolver.produce`` +
``JsonLifecycleRunStore`` so payloads land on disk under ``.dadaia/runs/lifecycle/``.

CRITICAL: the promote_to_evidence terminal exemption (v0.1.71 on-disk healing) AND its
delete_after_consumed control — exemption without its control is a hole.
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import os
from pathlib import Path

import pytest

from dadaia_workspace.core.models.hygiene import SlopPolicy
from dadaia_workspace.core.models.lifecycle import (
    LifecyclePhase,
    LifecycleRun,
    LifecycleRunStatus,
)
from dadaia_workspace.core.models.workflow_handoff import RetentionMode
from dadaia_workspace.features.lifecycle.workflow_handoff_doctor import (
    WorkflowHandoffDoctor,
    WorkflowHandoffFindingKind,
)
from dadaia_workspace.features.lifecycle.workflow_handoffs import WorkflowHandoffResolver
from dadaia_workspace.infrastructure.json_lifecycle_run_store import JsonLifecycleRunStore
from dadaia_workspace.infrastructure.runtime_files import FilesystemRuntimeFileAdapter

NOW = dt.datetime(2026, 6, 27, 12, 0, tzinfo=dt.UTC)


def _workspace(tmp_path: Path) -> Path:
    (tmp_path / ".dadaia" / "states").mkdir(parents=True)
    (tmp_path / ".dadaia" / "states" / "spec_contexts.json").write_text("{}", encoding="utf-8")
    (tmp_path / "repos").mkdir()
    return tmp_path


def _resolver(tmp_path: Path) -> WorkflowHandoffResolver:
    return WorkflowHandoffResolver(
        run_store=JsonLifecycleRunStore(tmp_path),
        payload_writer=FilesystemRuntimeFileAdapter(tmp_path),
        clock=lambda: "2026-06-27T12:00:00Z",
    )


def _run(status: LifecycleRunStatus = LifecycleRunStatus.RUNNING) -> LifecycleRun:
    return LifecycleRun(
        run_id="run-1",
        context="dadaia-workspace",
        release_id="v0.1.30",
        command="release_definition",
        phase=LifecyclePhase.RELEASE_DEFINITION,
        status=status,
        current_step="release_scope",
        idempotency_key="run-1",
    )


def _doctor(tmp_path: Path, *, now: dt.datetime = NOW) -> WorkflowHandoffDoctor:
    return WorkflowHandoffDoctor(tmp_path, JsonLifecycleRunStore(tmp_path), now=now)


def _kinds(report) -> set[WorkflowHandoffFindingKind]:  # type: ignore[no-untyped-def]
    return {f.kind for f in report.findings}


# --- ① ok-on-coherent + orphan/malformed/undeclared param -------------------------------


@pytest.mark.parametrize("case_id", ["ok", "orphan", "malformed", "undeclared"])
def test_finding_kind_bites_matrix(tmp_path: Path, case_id: str) -> None:
    if case_id == "ok":
        _workspace(tmp_path)
        resolver = _resolver(tmp_path)
        resolver.produce(
            _run(),
            producer_step="release_scope",
            attempt=0,
            output_schema="release-scope-handoff-v1",
            payload={"summary": "scope"},
        )
        ok_report = _doctor(tmp_path).run()
        assert ok_report.ok is True
        assert ok_report.findings == ()
    elif case_id == "orphan":
        _workspace(tmp_path)
        resolver = _resolver(tmp_path)
        _run_result, record = resolver.produce(
            _run(),
            producer_step="release_scope",
            attempt=0,
            output_schema="release-scope-handoff-v1",
            payload={"summary": "scope"},
        )
        (tmp_path / record.payload_ref).unlink()
        report = _doctor(tmp_path).run()
        assert report.ok is False
        assert WorkflowHandoffFindingKind.ORPHAN in _kinds(report)
    elif case_id == "malformed":
        _workspace(tmp_path)
        # No ledger; just a garbage on-disk payload.
        JsonLifecycleRunStore(tmp_path).save(_run())
        steps = tmp_path / ".dadaia" / "runs" / "lifecycle" / "run-1" / "steps"
        steps.mkdir(parents=True)
        (steps / "bad-attempt-0.step-payload.json").write_text("{not json", encoding="utf-8")
        report = _doctor(tmp_path).run()
        assert report.ok is False
        assert WorkflowHandoffFindingKind.MALFORMED in _kinds(report)
    else:  # undeclared
        _workspace(tmp_path)
        JsonLifecycleRunStore(tmp_path).save(_run())
        steps = tmp_path / ".dadaia" / "runs" / "lifecycle" / "run-1" / "steps"
        steps.mkdir(parents=True)
        # Valid JSON object but no matching ledger record.
        (steps / "ghost-attempt-0.step-payload.json").write_text('{"x": 1}', encoding="utf-8")
        report = _doctor(tmp_path).run()
        assert report.ok is False
        assert WorkflowHandoffFindingKind.UNDECLARED in _kinds(report)


# --- ② stale-past-TTL + unconsumed-required-on-terminal ---------------------------------


def test_stale_past_ttl_and_unconsumed_required_on_terminal(tmp_path: Path) -> None:
    _workspace(tmp_path)
    stale_resolver = _resolver(tmp_path)
    # Produce a delete-after-consumed payload with one consumer, then fully consume it.
    run, record = stale_resolver.produce(
        _run(),
        producer_step="release_scope",
        attempt=0,
        output_schema="release-scope-handoff-v1",
        payload={"summary": "scope"},
        declared_consumers=("spec_create",),
        retention_mode=RetentionMode.DELETE_AFTER_CONSUMED,
    )
    stale_resolver.record_consumption(
        run,
        producer_step="release_scope",
        producer_attempt=0,
        consumer_step="spec_create",
        consumer_attempt=0,
    )
    # Age the on-disk payload past the consumed TTL (tmp_ttl_seconds).
    old = (NOW - dt.timedelta(seconds=SlopPolicy().tmp_ttl_seconds + 99)).timestamp()
    os.utime(tmp_path / record.payload_ref, (old, old))
    stale_report = _doctor(tmp_path).run()
    assert stale_report.ok is False
    assert WorkflowHandoffFindingKind.STALE in _kinds(stale_report)

    unconsumed_root = tmp_path / "unconsumed"
    _workspace(unconsumed_root)
    unconsumed_resolver = _resolver(unconsumed_root)
    # A producer with a declared consumer that never consumes; the run is terminal.
    unconsumed_run, _ = unconsumed_resolver.produce(
        _run(),
        producer_step="release_scope",
        attempt=0,
        output_schema="release-scope-handoff-v1",
        payload={"summary": "scope"},
        declared_consumers=("spec_create",),
    )
    terminal = dataclasses.replace(unconsumed_run, status=LifecycleRunStatus.COMPLETED)
    JsonLifecycleRunStore(unconsumed_root).save(terminal)
    unconsumed_report = _doctor(unconsumed_root).run()
    assert unconsumed_report.ok is False
    assert WorkflowHandoffFindingKind.UNCONSUMED_REQUIRED in _kinds(unconsumed_report)


# --- promote_to_evidence exemption + its delete_after_consumed control -----------------


def test_promote_to_evidence_exempt_delete_after_consumed_control_still_flags(
    tmp_path: Path,
) -> None:
    """v0.1.71 FR4: reproduces bug ``handoffs-doctor-blocks-terminal-promote-to-evidence``:
    a terminal APPROVED implementation-review verdict payload has
    retention_mode=PROMOTE_TO_EVIDENCE + declared_consumers=(implement) and is never
    consumed — because it is promoted to evidence, not consumed. It must NOT be flagged
    unconsumed_required (heals pre-fix runs on disk with no migration). FR4.2 control: the
    exemption is scoped to PROMOTE_TO_EVIDENCE — a terminal delete_after_consumed required
    payload that was never consumed still flags."""
    _workspace(tmp_path)
    exempt_resolver = _resolver(tmp_path)
    exempt_run, _ = exempt_resolver.produce(
        _run(),
        producer_step="review_qa",
        attempt=0,
        output_schema="qa-review-handoff-v1",
        payload={"verdict": "APPROVED", "summary": "approved", "blocking": []},
        declared_consumers=("implement",),
        retention_mode=RetentionMode.PROMOTE_TO_EVIDENCE,
    )
    exempt_terminal = dataclasses.replace(exempt_run, status=LifecycleRunStatus.COMPLETED)
    JsonLifecycleRunStore(tmp_path).save(exempt_terminal)
    exempt_report = _doctor(tmp_path).run()
    assert exempt_report.ok is True, [f.to_dict() for f in exempt_report.findings]
    assert WorkflowHandoffFindingKind.UNCONSUMED_REQUIRED not in _kinds(exempt_report)

    control_root = tmp_path / "control"
    _workspace(control_root)
    control_resolver = _resolver(control_root)
    control_run, _ = control_resolver.produce(
        _run(),
        producer_step="release_scope",
        attempt=0,
        output_schema="release-scope-handoff-v1",
        payload={"summary": "scope"},
        declared_consumers=("spec_create",),
        retention_mode=RetentionMode.DELETE_AFTER_CONSUMED,
    )
    control_terminal = dataclasses.replace(control_run, status=LifecycleRunStatus.COMPLETED)
    JsonLifecycleRunStore(control_root).save(control_terminal)
    control_report = _doctor(control_root).run()
    assert WorkflowHandoffFindingKind.UNCONSUMED_REQUIRED in _kinds(control_report)


# --- v0.1.71 FR2: --context/--release-id are REAL run filters, scoping runs AND disk scan --


def _run_in(run_id: str, context: str, release_id: str) -> LifecycleRun:
    return LifecycleRun(
        run_id=run_id,
        context=context,
        release_id=release_id,
        command="release_definition",
        phase=LifecyclePhase.RELEASE_DEFINITION,
        status=LifecycleRunStatus.COMPLETED,
        current_step="release_scope",
        idempotency_key=run_id,
    )


def test_context_filter_scopes_runs_and_disk_scan_to_matched_runs_only(tmp_path: Path) -> None:
    """A context/release filter narrows the report AND the on-disk scan to the matched
    runs — an unconsumed_required defect in another context's run is excluded, and that
    other run's on-disk payload is NOT mis-flagged ``undeclared`` against the narrowed
    ledger."""
    _workspace(tmp_path)
    resolver = _resolver(tmp_path)
    # Target run (dd-chain-capture/v0.2.0): coherent.
    tgt, _ = resolver.produce(
        _run_in("run-target", "dd-chain-capture", "v0.2.0"),
        producer_step="release_scope",
        attempt=0,
        output_schema="release-scope-handoff-v1",
        payload={"summary": "ok"},
    )
    JsonLifecycleRunStore(tmp_path).save(
        dataclasses.replace(tgt, status=LifecycleRunStatus.COMPLETED)
    )
    # Foreign run (other context): has a genuine unconsumed_required defect.
    other, _ = resolver.produce(
        _run_in("run-other", "some-other-context", "v9.9.9"),
        producer_step="release_scope",
        attempt=0,
        output_schema="release-scope-handoff-v1",
        payload={"summary": "defect"},
        declared_consumers=("spec_create",),
    )
    JsonLifecycleRunStore(tmp_path).save(
        dataclasses.replace(other, status=LifecycleRunStatus.COMPLETED)
    )

    # Unfiltered: the foreign defect is visible.
    assert WorkflowHandoffFindingKind.UNCONSUMED_REQUIRED in _kinds(_doctor(tmp_path).run())

    # Filtered to the target: clean, and no ``undeclared`` from the foreign payload.
    scoped = WorkflowHandoffDoctor(
        tmp_path,
        JsonLifecycleRunStore(tmp_path),
        now=NOW,
        context="dd-chain-capture",
        release_id="v0.2.0",
    ).run()
    assert scoped.ok is True, [f.to_dict() for f in scoped.findings]
