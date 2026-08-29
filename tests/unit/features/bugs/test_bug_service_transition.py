"""``BugService.transition`` — the ONE governance-write seam a status change goes
through (v0.5.1 K5 deepening, AS-16): dispatches a verb to the matching
:class:`~dadaia_workspace.core.models.bugs.BugRecord` transition method, called
INSIDE the record-store's atomic update.

Intent: CONTRACT — v0.5.1 K5. Size: SMALL — real ``tmp_path`` filesystem, no
subprocess/network.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.core.models.bugs import BugRecord, IncompleteTransitionError
from dadaia_workspace.features.bugs.service import BugService

from ._bug_record_helpers import bug_record_store


def _record(bug_id: str) -> BugRecord:
    return BugRecord(
        id=bug_id,
        ts="2026-08-27T00:00:00Z",
        reported_by="software-engineer",
        title="t",
        severity="HIGH",
        surface="bugs",
        component="c",
        context="dadaia-workspace",
        symptom="s",
        repro="r",
        expected="e",
    )


def _service(tmp_path: Path) -> BugService:
    return BugService(bug_record_store(tmp_path))


def test_transition_resolve_dispatches_to_the_matching_record_method(tmp_path: Path) -> None:
    service = _service(tmp_path)
    service.register(
        bug_id="a",
        ts="2026-08-27T00:00:00Z",
        reported_by="software-engineer",
        title="t",
        severity="HIGH",
        surface="bugs",
        component="c",
        context="dadaia-workspace",
        symptom="s",
        repro="r",
        expected="e",
    )

    updated = service.transition(
        "a",
        "resolve",
        cause="c",
        caused_by="none",
        resolved_release="v0.5.1",
        solution="s",
        evidence_loop="el",
        evidence_seam="es",
        evidence_diff="net-negative: deleted more than added",
        diff_direction="net-negative",
    )

    assert updated.status == "resolved"
    stored = next(r for r in service.status(include_closed=True) if r.id == "a")
    assert stored.status == "resolved"


def test_transition_refuses_an_unknown_verb(tmp_path: Path) -> None:
    service = _service(tmp_path)
    service.register(
        bug_id="a",
        ts="2026-08-27T00:00:00Z",
        reported_by="software-engineer",
        title="t",
        severity="HIGH",
        surface="bugs",
        component="c",
        context="dadaia-workspace",
        symptom="s",
        repro="r",
        expected="e",
    )

    with pytest.raises(ValueError, match="unknown bug-record transition verb"):
        service.transition("a", "close")


def test_transition_refusal_never_reaches_the_store(tmp_path: Path) -> None:
    """An IncompleteTransitionError raises INSIDE ``mutate()``, before
    ``RecordStore.update`` ever touches disk — the record stays open, byte-identical."""
    service = _service(tmp_path)
    service.register(
        bug_id="a",
        ts="2026-08-27T00:00:00Z",
        reported_by="software-engineer",
        title="t",
        severity="HIGH",
        surface="bugs",
        component="c",
        context="dadaia-workspace",
        symptom="s",
        repro="r",
        expected="e",
    )
    before = bug_record_store(tmp_path).path.read_text(encoding="utf-8")

    with pytest.raises(IncompleteTransitionError):
        service.transition("a", "resolve")  # every required field missing

    after = bug_record_store(tmp_path).path.read_text(encoding="utf-8")
    assert after == before
    assert service.status(include_closed=True)[0].status == "open"
