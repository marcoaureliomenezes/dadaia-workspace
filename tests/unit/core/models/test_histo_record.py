"""The ONE history-record shape and the ONE terminal vocabulary (0.4.7 FR7, T-047-03).

Intent: CONTRACT — T-047-03 (SPEC 0.4.7 FR7): `HistoRecord` round-trips the seven
fields every `_histo.jsonl` line carries, and `TERMINAL_DISPOSITIONS` is the single
lowercase vocabulary the per-ledger subsets are drawn from.
Size: SMALL — pure in-memory dataclass round-trip, no I/O.
"""

from __future__ import annotations

import pytest

from dadaia_workspace.core.models.bugs import TERMINAL_EVENTS
from dadaia_workspace.core.models.histo import (
    AUDITS_HISTO_DISPOSITIONS,
    BACKLOG_HISTO_DISPOSITIONS,
    BUGS_DISPOSITIONS,
    RELEASES_HISTO_DISPOSITIONS,
    TERMINAL_DISPOSITIONS,
    HistoRecord,
)

_RECORD = HistoRecord(
    id="push-range-denylist-scan",
    ts="2026-08-14",
    disposition="delivered",
    release="0.4.6",
    reason=None,
    summary="shipped in the v0.9.0 push-gate work",
    entry={"id": "push-range-denylist-scan", "status": "picked"},
)


def test_round_trip_preserves_every_field() -> None:
    assert HistoRecord.from_dict(_RECORD.to_dict()) == _RECORD


def test_to_dict_carries_exactly_the_seven_keys() -> None:
    assert set(_RECORD.to_dict()) == {
        "id",
        "ts",
        "disposition",
        "release",
        "reason",
        "summary",
        "entry",
    }


def test_nullable_fields_round_trip_as_null() -> None:
    record = HistoRecord(
        id="x",
        ts="2026-09-12T00:00:00Z",
        disposition="rejected",
        release=None,
        reason=None,
        summary=None,
        entry=None,
    )
    assert record.to_dict()["entry"] is None
    assert HistoRecord.from_dict(record.to_dict()) == record


def test_from_dict_refuses_a_record_missing_a_required_field() -> None:
    raw = _RECORD.to_dict()
    del raw["disposition"]
    with pytest.raises(ValueError):
        HistoRecord.from_dict(raw)


def test_terminal_vocabulary_is_five_lowercase_words() -> None:
    assert TERMINAL_DISPOSITIONS == (
        "delivered",
        "resolved",
        "superseded",
        "deferred",
        "rejected",
    )


@pytest.mark.parametrize(
    "subset",
    [
        BACKLOG_HISTO_DISPOSITIONS,
        BUGS_DISPOSITIONS,
        AUDITS_HISTO_DISPOSITIONS,
        RELEASES_HISTO_DISPOSITIONS,
    ],
)
def test_every_per_ledger_subset_is_drawn_from_the_one_vocabulary(subset: tuple[str, ...]) -> None:
    assert set(subset) <= set(TERMINAL_DISPOSITIONS)
    assert subset == tuple(w for w in TERMINAL_DISPOSITIONS if w in set(subset))


def test_the_bugs_subset_is_the_bug_ledger_terminal_vocabulary() -> None:
    """One constant, not two: `core.models.bugs.TERMINAL_EVENTS` IS this subset."""
    assert frozenset(BUGS_DISPOSITIONS) == TERMINAL_EVENTS
