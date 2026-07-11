"""v0.1.78 T-C / FR-C — ONE canonical cleanup contract (bug
``split-cleanup-engines-strand-stale-step-payloads``).

Before the fix, ``LifecycleHygieneService.cleanup()`` (the engine behind both
``dadaia lifecycle hygiene clean`` AND the preflight remediation printed for
``"hygiene cleanup candidates present"``) scanned ONLY ``SlopPolicy.safe_zones``
(reports/handoff/tmp) — it never saw ``.dadaia/runs/lifecycle/<run>/steps/`` payloads.
``RetentionSweep`` (``dadaia lifecycle clean``, a DIFFERENT command) DOES cover
``.dadaia/runs`` via ``_swept_zones``. So a workflow-step payload the handoffs doctor
flagged as STALE (past its consumed-TTL) survived the operator's OFFICIAL, printed
remediation — the classic "doctor says X, remediation cannot fix X" hole.

Fix: ``LifecycleHygieneService.cleanup()`` now ALSO reclaims stale, cleanup-eligible
workflow-step payloads (delegating to the exact same TTL + liveness + important-ref
guard the retention sweep already enforces for that zone), so the ONE printed
remediation command actually clears what the doctor flags.
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import os
from pathlib import Path

from dadaia_workspace.core.models.hygiene import SlopPolicy
from dadaia_workspace.core.models.lifecycle import (
    LifecyclePhase,
    LifecycleRun,
    LifecycleRunStatus,
)
from dadaia_workspace.core.models.workflow_handoff import RetentionMode
from dadaia_workspace.features.lifecycle.hygiene import LifecycleHygieneService
from dadaia_workspace.features.lifecycle.workflow_handoff_doctor import WorkflowHandoffDoctor
from dadaia_workspace.features.lifecycle.workflow_handoffs import WorkflowHandoffResolver
from dadaia_workspace.infrastructure.json_lifecycle_run_store import JsonLifecycleRunStore
from dadaia_workspace.infrastructure.runtime_files import FilesystemRuntimeFileAdapter

NOW = dt.datetime(2026, 7, 11, 12, 0, tzinfo=dt.UTC)


def _workspace(tmp_path: Path) -> Path:
    (tmp_path / ".dadaia" / "states").mkdir(parents=True)
    (tmp_path / ".dadaia" / "states" / "spec_contexts.json").write_text("{}", encoding="utf-8")
    (tmp_path / "repos").mkdir()
    return tmp_path


def _resolver(tmp_path: Path) -> WorkflowHandoffResolver:
    return WorkflowHandoffResolver(
        run_store=JsonLifecycleRunStore(tmp_path),
        payload_writer=FilesystemRuntimeFileAdapter(tmp_path),
        clock=lambda: "2026-07-11T12:00:00Z",
    )


def _run() -> LifecycleRun:
    return LifecycleRun(
        run_id="run-1",
        context="dadaia-workspace",
        release_id="v0.1.78",
        command="release_definition",
        phase=LifecyclePhase.RELEASE_DEFINITION,
        status=LifecycleRunStatus.RUNNING,
        current_step="release_scope",
        idempotency_key="run-1",
    )


def _produce_stale_consumed_payload(tmp_path: Path) -> Path:
    """Reproduce the exact remote-reported shape: a fully-consumed delete_after_consumed
    step payload, aged past the consumed TTL — the doctor flags it STALE."""
    resolver = _resolver(tmp_path)
    run, record = resolver.produce(
        _run(),
        producer_step="release_scope",
        attempt=0,
        output_schema="release-scope-handoff-v1",
        payload={"summary": "scope"},
        declared_consumers=("spec_create",),
        retention_mode=RetentionMode.DELETE_AFTER_CONSUMED,
    )
    run = resolver.record_consumption(
        run,
        producer_step="release_scope",
        producer_attempt=0,
        consumer_step="spec_create",
        consumer_attempt=0,
    )
    # Terminal — a live run's payloads must never be reclaimed (the liveness gate stays).
    terminal = dataclasses.replace(run, status=LifecycleRunStatus.COMPLETED)
    JsonLifecycleRunStore(tmp_path).save(terminal)
    old = (NOW - dt.timedelta(seconds=SlopPolicy().tmp_ttl_seconds + 99)).timestamp()
    payload_path = tmp_path / record.payload_ref
    os.utime(payload_path, (old, old))
    return payload_path


def test_doctor_flags_stale_payload_official_remediation_reclaims_it_doctor_clean(
    tmp_path: Path,
) -> None:
    """RED (pre-fix): doctor flags STALE; ``hygiene clean --apply`` does not touch the
    file (it never scanned ``.dadaia/runs`` at all) — the payload survives, doctor still
    flags it. GREEN (post-fix): the SAME ``hygiene clean --apply`` reclaims it and the
    doctor goes clean afterward — the official printed remediation actually works.
    """
    _workspace(tmp_path)
    payload_path = _produce_stale_consumed_payload(tmp_path)
    assert payload_path.is_file()

    pre_report = WorkflowHandoffDoctor(tmp_path, JsonLifecycleRunStore(tmp_path), now=NOW).run()
    assert pre_report.ok is False, "fixture must reproduce the doctor-flags-it precondition"

    # The OFFICIAL remediation: hygiene clean --apply (what preflight prints, what the
    # operator is told to run).
    service = LifecycleHygieneService(tmp_path, now=NOW, run_store=JsonLifecycleRunStore(tmp_path))
    result = service.cleanup(dry_run=False)

    assert not payload_path.exists(), (
        "the official hygiene-clean remediation must reclaim a stale, fully-consumed, "
        "terminal-run step payload — this is exactly the split-cleanup-engines hole"
    )
    reclaimed_refs = {str(p.relative_to(tmp_path)) for p in result.deleted_paths}
    assert any("steps" in ref for ref in reclaimed_refs), result.deleted_paths

    post_report = WorkflowHandoffDoctor(tmp_path, JsonLifecycleRunStore(tmp_path), now=NOW).run()
    assert post_report.ok is True, post_report.findings


def test_dry_run_previews_the_stale_payload_without_deleting(tmp_path: Path) -> None:
    """dry-run (the default) previews the reclaim without touching the filesystem —
    ``hygiene status``/``hygiene clean`` (no ``--apply``) stay side-effect-free."""
    _workspace(tmp_path)
    payload_path = _produce_stale_consumed_payload(tmp_path)

    service = LifecycleHygieneService(tmp_path, now=NOW, run_store=JsonLifecycleRunStore(tmp_path))
    result = service.cleanup(dry_run=True)

    assert payload_path.is_file(), "dry-run must never delete"
    candidate_paths = {c.path for c in result.candidates}
    assert any("steps" in path for path in candidate_paths), result.candidates


def test_live_run_step_payload_is_never_reclaimed_by_hygiene_clean(tmp_path: Path) -> None:
    """The liveness gate is preserved: a NON-terminal run's step payload is never reclaimed
    even past TTL — a live worker's mid-flight payload must survive."""
    _workspace(tmp_path)
    resolver = _resolver(tmp_path)
    run, record = resolver.produce(
        _run(),  # status RUNNING — never saved as terminal
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
    old = (NOW - dt.timedelta(seconds=SlopPolicy().tmp_ttl_seconds + 99)).timestamp()
    payload_path = tmp_path / record.payload_ref
    os.utime(payload_path, (old, old))

    service = LifecycleHygieneService(tmp_path, now=NOW, run_store=JsonLifecycleRunStore(tmp_path))
    service.cleanup(dry_run=False)

    assert payload_path.is_file(), "a live (non-terminal) run's step payload must survive"


def test_no_run_store_wired_is_byte_identical_back_compat(tmp_path: Path) -> None:
    """A ``LifecycleHygieneService`` constructed with NO ``run_store`` (every pre-v0.1.78
    call site, and any future caller that genuinely has none) never discovers step-payload
    candidates — additive-optional, not a silent behavior change for existing callers."""
    _workspace(tmp_path)
    payload_path = _produce_stale_consumed_payload(tmp_path)

    service = LifecycleHygieneService(tmp_path, now=NOW)  # no run_store
    result = service.cleanup(dry_run=False)

    assert payload_path.is_file(), "no run_store wired => no step-payload reclaim at all"
    assert not any("steps" in c.path for c in result.candidates)
