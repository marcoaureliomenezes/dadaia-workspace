"""The ONE history-record shape and the ONE terminal vocabulary (0.4.7 FR7, T-047-03).

Intent: CONTRACT — T-047-03 (SPEC 0.4.7 FR7): `HistoRecord.from_dict` reads the seven
fields every `_histo.jsonl` line carries; `TERMINAL_DISPOSITIONS` is the one vocabulary.
Size: SMALL — in-memory parsing.
"""

from __future__ import annotations

import pytest

from dadaia_workspace.core.models.histo import TERMINAL_DISPOSITIONS, HistoRecord

_RAW: dict[str, object] = {
    "id": "x", "ts": "2026-09-12", "disposition": "rejected", "release": None,
    "reason": None, "summary": None, "entry": None,
}  # fmt: skip


def test_from_dict_reads_the_seven_fields_and_refuses_a_missing_one() -> None:
    record = HistoRecord.from_dict(_RAW)
    assert (record.id, record.disposition, record.entry) == ("x", "rejected", None)
    with pytest.raises(ValueError):
        HistoRecord.from_dict({k: v for k, v in _RAW.items() if k != "disposition"})


def test_terminal_vocabulary_is_five_lowercase_words() -> None:
    assert TERMINAL_DISPOSITIONS == ("delivered", "resolved", "superseded", "deferred", "rejected")
