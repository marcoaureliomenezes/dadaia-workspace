"""A bug cannot be closed if nobody ever opened it.

Bug ``r19-bugs-resolved-event-accepted-without-prior-reported`` (consumer-side validator,
R19/R-06): the ledger accepted a ``resolved`` event for a ``bug_id`` with no ``reported``
before it, and folded it into the resolved count. The ledger's whole purpose is to be the
evidence trail, and an entry with no opening event is the one shape that cannot be
evidence of anything.

The operator harm is sharper than the accounting: a mistyped ``--bug-id`` on a close
silently mints a PHANTOM resolved bug instead of saying the id is unknown — so the real
bug stays open while the typo looks like progress. That is not hypothetical; this session
appended dozens of resolution events by hand.

The rule lives in the SERVICE because the CLI used to write straight to the store and
bypass it — the same two-writers shape already fixed for ``settings.json``.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.core.exceptions import DadaiaError
from dadaia_workspace.core.models.bugs import BugEvent
from dadaia_workspace.features.bugs.service import BugService
from dadaia_workspace.infrastructure.jsonl_bug_store import JsonlBugStore

pytestmark = pytest.mark.unit


def _service(tmp_path: Path) -> BugService:
    return BugService(JsonlBugStore(tmp_path / "bugs"))


def _reported(bug_id: str) -> BugEvent:
    return BugEvent(
        bug_id=bug_id,
        event="reported",
        ts="2026-07-29T00:00:00Z",
        reported_by="test",
        title="t",
        severity="LOW",
        surface="s",
        component="c",
        context="ctx",
        tags=("t",),
        symptom="sy",
        repro="r",
        expected="e",
        notes="n",
    )


def _resolved(bug_id: str) -> BugEvent:
    return BugEvent(
        bug_id=bug_id,
        event="resolved",
        ts="2026-07-29T00:01:00Z",
        reported_by="test",
        title="t",
        severity="LOW",
        surface="s",
        component="c",
        context="ctx",
        tags=("t",),
        symptom="sy",
        repro="r",
        expected="e",
        notes="n",
        release="0.4.2",
        evidence="evidence long enough to satisfy the resolution law",
    )


@pytest.mark.parametrize("terminal", ["resolved", "superseded", "deferred", "rejected"])
def test_a_terminal_event_without_a_reported_is_refused(tmp_path: Path, terminal: str) -> None:
    service = _service(tmp_path)
    event = _resolved("never-opened")
    object.__setattr__(event, "event", terminal)

    with pytest.raises(DadaiaError, match="never-opened"):
        service.append_event(event)


def test_the_refusal_points_at_the_likely_typo(tmp_path: Path) -> None:
    service = _service(tmp_path)
    with pytest.raises(DadaiaError) as excinfo:
        service.append_event(_resolved("typo-in-the-slug"))
    assert "typo" in str(excinfo.value), (
        "the message must name the likely cause; an unknown id on a CLOSE is almost "
        "always a mistyped slug, and saying so is what saves the real bug"
    )


def test_the_normal_lifecycle_still_works(tmp_path: Path) -> None:
    """Guard: refusing orphans must not refuse the path everyone actually uses."""
    service = _service(tmp_path)
    service.append_event(_reported("real"))
    service.append_event(_resolved("real"))
    assert [s.bug_id for s in service.status(include_closed=True)] == ["real"]
