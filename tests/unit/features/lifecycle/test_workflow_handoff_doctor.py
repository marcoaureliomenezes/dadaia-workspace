"""Workflow-step handoff doctor (v0.1.30 Item 5 / T-30-D-08 / A26).

Pins A26: the doctor fails on orphan, malformed, stale, undeclared, and
unconsumed-required workflow-step payloads, and reports ``ok`` when the ledger and the
on-disk data plane are coherent. Built on the real ``WorkflowHandoffResolver.produce`` +
``JsonLifecycleRunStore`` so payloads land on disk under ``.dadaia/runs/lifecycle/``.
"""

from __future__ import annotations

import dataclasses
import datetime as dt
from pathlib import Path

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


# --- ok ---------------------------------------------------------------------------


def test_doctor_ok_on_coherent_ledger(tmp_path: Path) -> None:
    _workspace(tmp_path)
    resolver = _resolver(tmp_path)
    run, _ = resolver.produce(
        _run(),
        producer_step="release_scope",
        attempt=0,
        output_schema="release-scope-handoff-v1",
        payload={"summary": "scope"},
    )
    report = _doctor(tmp_path).run()
    assert report.ok is True
    assert report.findings == ()


# --- orphan -----------------------------------------------------------------------


def test_doctor_flags_orphan_when_payload_file_missing(tmp_path: Path) -> None:
    _workspace(tmp_path)
    resolver = _resolver(tmp_path)
    run, record = resolver.produce(
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


# --- malformed --------------------------------------------------------------------


def test_doctor_flags_malformed_on_disk_payload(tmp_path: Path) -> None:
    _workspace(tmp_path)
    # No ledger; just a garbage on-disk payload.
    JsonLifecycleRunStore(tmp_path).save(_run())
    steps = tmp_path / ".dadaia" / "runs" / "lifecycle" / "run-1" / "steps"
    steps.mkdir(parents=True)
    (steps / "bad-attempt-0.step-payload.json").write_text("{not json", encoding="utf-8")
    report = _doctor(tmp_path).run()
    assert report.ok is False
    assert WorkflowHandoffFindingKind.MALFORMED in _kinds(report)


# --- undeclared -------------------------------------------------------------------


def test_doctor_flags_undeclared_on_disk_payload(tmp_path: Path) -> None:
    _workspace(tmp_path)
    JsonLifecycleRunStore(tmp_path).save(_run())
    steps = tmp_path / ".dadaia" / "runs" / "lifecycle" / "run-1" / "steps"
    steps.mkdir(parents=True)
    # Valid JSON object but no matching ledger record.
    (steps / "ghost-attempt-0.step-payload.json").write_text('{"x": 1}', encoding="utf-8")
    report = _doctor(tmp_path).run()
    assert report.ok is False
    assert WorkflowHandoffFindingKind.UNDECLARED in _kinds(report)


# --- stale ------------------------------------------------------------------------


def test_doctor_flags_stale_consumed_all_past_ttl(tmp_path: Path) -> None:
    import os

    _workspace(tmp_path)
    resolver = _resolver(tmp_path)
    # Produce a delete-after-consumed payload with one consumer, then fully consume it.
    run, record = resolver.produce(
        _run(),
        producer_step="release_scope",
        attempt=0,
        output_schema="release-scope-handoff-v1",
        payload={"summary": "scope"},
        declared_consumers=("spec_create",),
        retention_mode=RetentionMode.DELETE_AFTER_CONSUMED,
    )
    resolver.record_consumption(
        run,
        producer_step="release_scope",
        producer_attempt=0,
        consumer_step="spec_create",
        consumer_attempt=0,
    )
    # Age the on-disk payload past the consumed TTL (tmp_ttl_seconds).
    old = (NOW - dt.timedelta(seconds=SlopPolicy().tmp_ttl_seconds + 99)).timestamp()
    os.utime(tmp_path / record.payload_ref, (old, old))
    report = _doctor(tmp_path).run()
    assert report.ok is False
    assert WorkflowHandoffFindingKind.STALE in _kinds(report)


# --- unconsumed-required ----------------------------------------------------------


def test_doctor_flags_unconsumed_required_on_terminal_run(tmp_path: Path) -> None:
    _workspace(tmp_path)
    resolver = _resolver(tmp_path)
    # A producer with a declared consumer that never consumes; the run is terminal.
    run, _ = resolver.produce(
        _run(),
        producer_step="release_scope",
        attempt=0,
        output_schema="release-scope-handoff-v1",
        payload={"summary": "scope"},
        declared_consumers=("spec_create",),
    )
    terminal = dataclasses.replace(run, status=LifecycleRunStatus.COMPLETED)
    JsonLifecycleRunStore(tmp_path).save(terminal)
    report = _doctor(tmp_path).run()
    assert report.ok is False
    assert WorkflowHandoffFindingKind.UNCONSUMED_REQUIRED in _kinds(report)
