"""RED tests — the append path enforces the SAME stream-coherence invariant the doctor
diagnoses (bugs bugs-append-accepts-second-terminal-event and
bugs-append-allows-terminal-event-without-reported).

Bug class: the one-terminal invariant lived only in the specs doctor's fold — a
diagnostic gate with no enforced counterpart (the exact class the v0.1.72 law forbids).
The authority now lives once in ``core.models.bugs.advance_coherence``; the doctor folds
history through it to DIAGNOSE, ``BugService.append_event`` folds through it to REFUSE.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dadaia_workspace.core.models.bugs import BugEvent, advance_coherence
from dadaia_workspace.features.bugs.service import BugService
from dadaia_workspace.infrastructure.jsonl_bug_store import JsonlBugStore


def _event(bug_id: str, event: str, *, ts: str = "2026-08-11T10:00:00Z") -> BugEvent:
    extra: dict[str, str] = {}
    if event == "reported":
        extra = {"title": f"title {bug_id}", "severity": "MEDIUM"}
    if event == "resolved":
        extra = {"release": "v0.5.0", "evidence": "executed-path repro plus fix proof"}
    if event in {"deferred", "rejected"}:
        extra = {"reason": "test rationale"}
    if event == "superseded":
        extra = {"superseded_by": "other-slug"}
    return BugEvent(bug_id=bug_id, event=event, ts=ts, reported_by="software-engineer", **extra)  # type: ignore[arg-type]


def _service(tmp_path: Path) -> BugService:
    return BugService(JsonlBugStore(tmp_path / "bugs"))


def test_second_terminal_event_is_refused(tmp_path: Path) -> None:
    svc = _service(tmp_path)
    svc.append_event(_event("b1", "reported"))
    svc.append_event(_event("b1", "resolved"))
    with pytest.raises(ValueError, match="at most one terminal"):
        svc.append_event(_event("b1", "rejected"))
    # Nothing was written for the refused event.
    events = list(JsonlBugStore(tmp_path / "bugs").iter_events())
    assert [e.event for e in events] == ["reported", "resolved"]


def test_terminal_without_reported_is_refused(tmp_path: Path) -> None:
    svc = _service(tmp_path)
    with pytest.raises(ValueError, match="must open with 'reported'"):
        svc.append_event(_event("never-reported", "resolved"))
    assert list(JsonlBugStore(tmp_path / "bugs").iter_events()) == []


def test_reopen_clears_terminal_and_allows_new_terminal(tmp_path: Path) -> None:
    svc = _service(tmp_path)
    svc.append_event(_event("b1", "reported"))
    svc.append_event(_event("b1", "resolved"))
    svc.append_event(_event("b1", "reported"))  # legitimate reopen
    svc.append_event(_event("b1", "deferred"))  # coherent second stream terminal
    events = list(JsonlBugStore(tmp_path / "bugs").iter_events())
    assert [e.event for e in events] == ["reported", "resolved", "reported", "deferred"]


def test_archived_annotation_is_never_refused(tmp_path: Path) -> None:
    svc = _service(tmp_path)
    svc.append_event(_event("b1", "reported"))
    svc.append_event(_event("b1", "resolved"))
    svc.append_event(_event("b1", "archived"))  # non-terminal annotation, always coherent


def test_historical_incoherence_never_blocks_other_streams(tmp_path: Path) -> None:
    """Append-only history is never rewritten: the two historical SPEC-DOC-033 ledger
    errors must not make the store refuse coherent NEW events for other bug_ids."""
    bugs_dir = tmp_path / "bugs"
    bugs_dir.mkdir(parents=True)
    rows = [
        _event("ghost", "resolved").to_dict(),  # historical terminal-without-reported
        _event("ok-bug", "reported").to_dict(),
    ]
    (bugs_dir / "bugs.jsonl").write_text(
        "".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8"
    )
    svc = _service(tmp_path)
    svc.append_event(_event("ok-bug", "resolved"))  # coherent — must not raise
    # But the incoherent bug_id itself stays terminal-folded: a SECOND terminal on it
    # is still refused (history advanced the fold, exactly as the doctor folds it).
    with pytest.raises(ValueError, match="at most one terminal"):
        svc.append_event(_event("ghost", "rejected"))


def test_refusal_message_is_the_doctor_message(tmp_path: Path) -> None:
    """One authority, two consumers: the service's refusal text is the exact clause the
    doctor embeds in its SPEC-DOC-033 finding — the gates cannot diverge."""
    seen: set[str] = set()
    terminated: set[str] = set()
    assert advance_coherence("b1", "reported", seen, terminated) is None
    assert advance_coherence("b1", "resolved", seen, terminated) is None
    doctor_clause = advance_coherence("b1", "rejected", seen, terminated)
    svc = _service(tmp_path)
    svc.append_event(_event("b1", "reported"))
    svc.append_event(_event("b1", "resolved"))
    with pytest.raises(ValueError) as exc_info:
        svc.append_event(_event("b1", "rejected"))
    assert str(exc_info.value) == doctor_clause
