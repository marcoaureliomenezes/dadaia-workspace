"""``AdrRecord`` — one record per architecture decision (v0.5.0 specs-canon closure,
operator ruling 2026-08-28).

Intent: CONTRACT — v0.5.0 specs-canon closure

Size: SMALL — pure-function/dataclass unit tests, no I/O.
"""

from __future__ import annotations

import pytest

from dadaia_workspace.core.models.adr import AdrRecord


def _sample_record(**overrides: object) -> AdrRecord:
    base: dict[str, object] = {
        "id": "0001",
        "ts": "2026-08-28T12:00:00Z",
        "title": "Features depend on ports, not adapters",
        "status": "proposed",
        "context": "Features need I/O but must stay unit-testable without real I/O.",
        "decision": "We will define a Protocol per I/O boundary and inject an adapter.",
        "consequences": "+ testable with fakes\n- one extra indirection layer",
    }
    base.update(overrides)
    return AdrRecord(**base)  # type: ignore[arg-type]


def test_optional_fields_default_to_none() -> None:
    record = _sample_record()
    assert record.measured_by is None
    assert record.supersedes is None
    assert record.amends is None


def test_to_dict_from_dict_round_trip_is_lossless() -> None:
    record = _sample_record(measured_by="tests/contract/test_x.py", supersedes="0002")
    raw = record.to_dict()
    restored = AdrRecord.from_dict(raw)
    assert restored == record


def test_to_dict_always_emits_every_field_even_when_none() -> None:
    record = _sample_record()
    raw = record.to_dict()
    assert raw["measured_by"] is None
    assert raw["supersedes"] is None
    assert raw["amends"] is None
    assert set(raw) == {
        "id",
        "ts",
        "title",
        "status",
        "context",
        "decision",
        "consequences",
        "measured_by",
        "supersedes",
        "amends",
    }


@pytest.mark.parametrize(
    "field_name", ["id", "ts", "title", "status", "context", "decision", "consequences"]
)
def test_from_dict_raises_on_missing_required_field(field_name: str) -> None:
    raw = _sample_record().to_dict()
    del raw[field_name]
    with pytest.raises(ValueError, match=field_name):
        AdrRecord.from_dict(raw)


def test_from_dict_raises_on_wrong_typed_optional_field() -> None:
    raw = _sample_record().to_dict()
    raw["measured_by"] = 12345
    with pytest.raises(ValueError, match="measured_by"):
        AdrRecord.from_dict(raw)


def test_from_dict_tolerates_a_null_optional_field() -> None:
    raw = _sample_record(measured_by="x").to_dict()
    raw["measured_by"] = None
    restored = AdrRecord.from_dict(raw)
    assert restored.measured_by is None
