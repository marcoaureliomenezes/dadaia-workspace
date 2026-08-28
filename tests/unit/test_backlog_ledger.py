"""Unit tests for the ``consumed_backlog`` ledger reader (SPEC §3.6, ADR-C; v0.5.0
T-050-13A, A5.5).

Intent: CONTRACT — v0.5.0 A5.5

BL-STALE keys on a **structured** ledger; ``read_consumed`` iterates an injected
:class:`~dadaia_workspace.core.protocols.record_store.RecordStore`
[``ConsumedBacklogHistoRecord``] — never a directory glob (T-050-13A relocated the 18
per-release ``consumed_backlog.json`` sidecars into one append-only file, before FR6
deletes the root archive tree those sidecars lived under). ``None`` (no store injected)
degrades to ``{}`` — never a false ERROR (acceptance §3.7.6, A5.5).

A fake, not a mock, satisfies the internal ``RecordStore`` Protocol dependency (this
workspace's own test-authoring convention) — see ``_FakeConsumedHistoStore``.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from pathlib import Path

import pytest

from dadaia_workspace.core.models.backlog import ConsumedBacklogHistoRecord
from dadaia_workspace.features.backlog.ledger import read_consumed

pytestmark = pytest.mark.unit


class _FakeConsumedHistoStore:
    """A minimal in-memory double satisfying
    :class:`~dadaia_workspace.core.protocols.record_store.RecordStore` for
    :class:`ConsumedBacklogHistoRecord`."""

    def __init__(self, records: list[ConsumedBacklogHistoRecord] | None = None) -> None:
        self._records = list(records or [])

    @property
    def path(self) -> Path:
        return Path("fake-consumed-backlog-histo.jsonl")

    def append(self, record: ConsumedBacklogHistoRecord) -> None:
        self._records.append(record)

    def iter_records(self) -> Iterator[ConsumedBacklogHistoRecord]:
        return iter(self._records)

    def update(
        self,
        record_id: str,
        mutate: Callable[[ConsumedBacklogHistoRecord], ConsumedBacklogHistoRecord],
    ) -> ConsumedBacklogHistoRecord:
        raise NotImplementedError


def _record(release: str, entries: list[dict[str, object]]) -> ConsumedBacklogHistoRecord:
    return ConsumedBacklogHistoRecord(id=release, consumed=entries)


def test_none_store_is_noop() -> None:
    """No store injected (never wired, or genuinely absent record) degrades to ``{}`` —
    never a false ERROR (A5.5's kept degrade-to-``{}`` behaviour)."""
    assert read_consumed(None) == {}


def test_empty_store_is_noop() -> None:
    assert read_consumed(_FakeConsumedHistoStore()) == {}


def test_single_multi_release_and_union_reads() -> None:
    single = _FakeConsumedHistoStore(
        [_record("v0.1.20", [{"slug": "old-feature", "shipped_anchors": ["a#X", "b#Y"]}])]
    )
    assert read_consumed(single) == {"old-feature": {"a#X", "b#Y"}}

    multi = _FakeConsumedHistoStore(
        [
            _record("v0.1.20", [{"slug": "feat-a", "shipped_anchors": ["a#X"]}]),
            _record("v0.1.21", [{"slug": "feat-b", "shipped_anchors": ["b#Y"]}]),
        ]
    )
    assert set(read_consumed(multi)) == {"feat-a", "feat-b"}

    # Same slug recorded by two different releases' records — anchors union.
    union = _FakeConsumedHistoStore(
        [
            _record("v0.1.20", [{"slug": "feat-a", "shipped_anchors": ["a#X"]}]),
            _record("v0.1.21", [{"slug": "feat-a", "shipped_anchors": ["a#Z"]}]),
        ]
    )
    assert read_consumed(union)["feat-a"] == {"a#X", "a#Z"}


def test_entry_without_anchors_tolerated() -> None:
    store = _FakeConsumedHistoStore([_record("v0.1.20", [{"slug": "feat-a"}])])
    assert read_consumed(store) == {"feat-a": set()}


def test_entry_without_slug_skipped() -> None:
    store = _FakeConsumedHistoStore([_record("v0.1.20", [{"shipped_anchors": ["a#X"]}])])
    assert read_consumed(store) == {}


def test_extra_entry_keys_are_ignored_not_fatal() -> None:
    """Every original ``consumed_backlog.json`` entry key survives the relocation
    (byte-lossless, A5.5) — ``read_consumed`` only consults ``slug``/``shipped_anchors``
    and tolerates any other key (e.g. ``note``, carried by several of the 18 relocated
    sidecars) without erroring."""
    store = _FakeConsumedHistoStore(
        [
            _record(
                "v0.1.57",
                [
                    {
                        "slug": "hard-remove-model-flag-across-run-verbs",
                        "shipped_anchors": [],
                        "note": "DELIVERED — v0.1.57 (archived at SHIP)",
                    }
                ],
            )
        ]
    )
    assert read_consumed(store) == {"hard-remove-model-flag-across-run-verbs": set()}
