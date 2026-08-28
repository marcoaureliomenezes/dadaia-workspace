"""``BugService.archive`` — A2.8, rewritten onto ``RecordStore.remove`` at the S1 FR23
firing (amendment A1, `specs/releases/0.5.0/reviews/S1-FR23-firing.md` §3): a second,
unsealed raw-file rewrite is replaced by the SAME refuse-stale seam ``apply_update``
already uses.

Intent: CONTRACT — 0.5.0 A2.8, S1 FR23 firing A1. Size: SMALL — real ``tmp_path``
filesystem, no subprocess/network.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from dadaia_workspace.core.models.bugs import BugRecord
from dadaia_workspace.features.bugs.service import BugService

from ._bug_record_helpers import bug_archive_store, bug_record_store

_TS_OLD = "2026-01-01T00:00:00Z"
_TS_RECENT = "2026-08-20T00:00:00Z"
_NOW = datetime(2026, 8, 27, tzinfo=UTC)


def _record(bug_id: str, *, status: str = "open", ts: str = _TS_OLD) -> BugRecord:
    return BugRecord(
        id=bug_id,
        ts=ts,
        reported_by="software-engineer",
        title="t",
        severity="HIGH",
        surface="bugs",
        component="c",
        context="dadaia-workspace",
        symptom="s",
        repro="r",
        expected="e",
        status=status,
    )


def _service(tmp_path: Path) -> BugService:
    return BugService(bug_record_store(tmp_path), archive_store=bug_archive_store(tmp_path))


def test_archive_requires_an_archive_store() -> None:
    service = BugService(bug_record_store(Path("/tmp/does-not-matter")))
    try:
        service.archive()
    except ValueError as exc:
        assert "archive_store" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_archive_moves_eligible_terminal_records_and_keeps_the_rest(tmp_path: Path) -> None:
    store = bug_record_store(tmp_path)
    store.append(_record("old-resolved", status="resolved", ts=_TS_OLD))
    store.append(_record("recent-resolved", status="resolved", ts=_TS_RECENT))
    store.append(_record("still-open", status="open", ts=_TS_OLD))
    service = _service(tmp_path)

    result = service.archive(now=_NOW)

    assert result.archived == 1
    assert result.kept == 2
    live_ids = {r.id for r in store.iter_records()}
    assert live_ids == {"recent-resolved", "still-open"}
    archived_ids = {r.id for r in bug_archive_store(tmp_path).iter_records()}
    assert archived_ids == {"old-resolved"}


def test_archive_is_a_noop_when_nothing_is_eligible(tmp_path: Path) -> None:
    store = bug_record_store(tmp_path)
    store.append(_record("still-open", status="open", ts=_TS_OLD))
    service = _service(tmp_path)

    result = service.archive(now=_NOW)

    assert result.archived == 0
    assert result.kept == 1
    assert [r.id for r in store.iter_records()] == ["still-open"]


def test_archive_with_an_absent_ledger_is_a_clean_noop(tmp_path: Path) -> None:
    service = _service(tmp_path)

    result = service.archive(now=_NOW)

    assert result.archived == 0
    assert result.kept == 0


def test_archive_second_run_with_nothing_newly_eligible_is_byte_identical(
    tmp_path: Path,
) -> None:
    """Idempotent (module docstring's own claim): a second run with nothing newly
    eligible never touches either file."""
    store = bug_record_store(tmp_path)
    store.append(_record("old-resolved", status="resolved", ts=_TS_OLD))
    store.append(_record("still-open", status="open", ts=_TS_OLD))
    service = _service(tmp_path)

    first = service.archive(now=_NOW)
    live_bytes_after_first = store.path.read_bytes()
    archive_bytes_after_first = bug_archive_store(tmp_path).path.read_bytes()

    second = service.archive(now=_NOW)

    assert first.archived == 1
    assert second.archived == 0
    assert second.kept == 1
    assert store.path.read_bytes() == live_bytes_after_first
    assert bug_archive_store(tmp_path).path.read_bytes() == archive_bytes_after_first
