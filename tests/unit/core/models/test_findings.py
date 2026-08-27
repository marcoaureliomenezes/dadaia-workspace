"""``FindingRecord`` — one record per audit finding, immutable core, mutable governance
(v0.5.0 FR13, D5, D11).

Intent: CONTRACT — A13.1 (T-050-23; the ruling this file proves is the fold-3
`software-architect` correction of A13.4, ``specs/releases/0.5.0/SPEC.md`` FR13).

Size: SMALL — pure-function/dataclass unit tests, no I/O beyond reading the packaged
schema fixture (tests are exempt from the ``core`` file-I/O purity ratchet;
``core/models/findings.py`` itself never does — see its module docstring).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator

from dadaia_workspace.core.models.findings import (
    FindingRecord,
    FindingRecordImmutableFieldError,
)

_REPO_ROOT = Path(__file__).resolve().parents[4]
_SCHEMA_PATH = (
    _REPO_ROOT
    / "dadaia_workspace"
    / "public"
    / "schemas"
    / "audits"
    / "finding-record-v1.schema.json"
)


def _schema() -> dict[str, Any]:
    return json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))  # type: ignore[no-any-return]


def _sample_record(**overrides: object) -> FindingRecord:
    base: dict[str, object] = {
        "id": "20260101-sample-F001",
        "pillar": "bugs",
        "severity": "HIGH",
        "refs": ("some/path.py:10", "some-bug-id"),
        "claim": "a one-sentence claim",
        "evidence": "git show <sha> --stat -> 1 file changed",
    }
    base.update(overrides)
    return FindingRecord(**base)  # type: ignore[arg-type]


# --- immutable-core -------------------------------------------------------------------


@pytest.mark.parametrize("field_name", ["id", "pillar", "severity", "claim", "evidence"])
def test_immutable_core_field_refused_when_changed_through_apply_update(
    field_name: str,
) -> None:
    """A change to an immutable-core field's VALUE is refused at the update seam; a
    re-assertion of its OWN current value is a harmless no-op (mirrors
    ``BugRecord``'s A2.2(a) — only a genuine change is refused)."""
    record = _sample_record()
    current = getattr(record, field_name)

    same_value = record.apply_governance_update({field_name: current})
    assert same_value == record

    with pytest.raises(FindingRecordImmutableFieldError):
        record.apply_governance_update({field_name: f"{current}-changed"})


def test_refs_immutable_core_field_refused_when_changed() -> None:
    """``refs`` is a tuple, not a string — the same immutable-core refusal applies."""
    record = _sample_record()

    same_value = record.apply_governance_update({"refs": record.refs})
    assert same_value == record

    with pytest.raises(FindingRecordImmutableFieldError):
        record.apply_governance_update({"refs": (*record.refs, "extra-ref")})


# --- mutable-governance — always settable, no write-once category ---------------------


def test_governance_fields_default_open_and_null_on_a_freshly_appended_record() -> None:
    """A finding is appended with ``disposition: "open"`` and ``release``/``reason``
    both absent (``None``) — mirrors the schema's ``"as appended"`` example."""
    record = _sample_record()
    assert record.disposition == "open"
    assert record.release is None
    assert record.reason is None


def test_governance_fields_are_rewritten_in_place_any_number_of_times() -> None:
    """Unlike ``BugRecord``'s write-once evidence fields, a finding's governance
    triple (``disposition``/``release``/``reason``) may be set, and then changed
    again, freely — the remediation release dispositions it, but nothing refuses a
    second dispositioning rewrite (e.g. ``open`` -> ``deferred`` -> ``fixed``)."""
    record = _sample_record()

    deferred = record.apply_governance_update(
        {"disposition": "deferred", "release": None, "reason": "picked for a later release"}
    )
    assert deferred.disposition == "deferred"
    assert deferred.reason == "picked for a later release"

    fixed = deferred.apply_governance_update(
        {
            "disposition": "fixed",
            "release": "0.6.0",
            "reason": "one render path; regression test at the formatter seam",
        }
    )
    assert fixed.disposition == "fixed"
    assert fixed.release == "0.6.0"
    # Every immutable-core field survives both rewrites, byte-identical.
    for name in ("id", "pillar", "severity", "refs", "claim", "evidence"):
        assert getattr(fixed, name) == getattr(record, name)


def test_apply_governance_update_rejects_an_unknown_field_name() -> None:
    record = _sample_record()
    with pytest.raises(ValueError, match="unknown finding-record field"):
        record.apply_governance_update({"not_a_real_field": "x"})


# --- to_dict / from_dict round trip ----------------------------------------------------


def test_to_dict_from_dict_round_trip_is_lossless() -> None:
    record = _sample_record(disposition="fixed", release="0.6.0", reason="done")
    raw = record.to_dict()
    assert raw["refs"] == list(record.refs)  # JSON has no tuple; serialized as a list
    restored = FindingRecord.from_dict(raw)
    assert restored == record


def test_from_dict_raises_on_missing_required_field() -> None:
    raw = _sample_record().to_dict()
    del raw["claim"]
    with pytest.raises(ValueError, match="claim"):
        FindingRecord.from_dict(raw)


def test_from_dict_raises_when_refs_is_not_a_non_empty_array_of_strings() -> None:
    raw = _sample_record().to_dict()
    raw["refs"] = []
    with pytest.raises(ValueError, match="refs"):
        FindingRecord.from_dict(raw)


# --- A13.1 — schema-documented categories, zero hand-kept mirror ----------------------


def test_field_categories_documented_in_schema_match_dataclass_with_no_hand_kept_mirror() -> None:
    """A13.1: the two-category split (``immutable-core``/``mutable-governance``) is
    documented PER PROPERTY in ``finding-record-v1.schema.json`` (``x-mutability``),
    and every property is accounted for; the dataclass's own ``field(metadata=...)``
    matches it exactly, with zero second, hand-kept mirror (A2.10, reused from
    ``BugRecord``'s own contract)."""
    schema = _schema()
    Draft202012Validator.check_schema(schema)
    properties = schema["properties"]
    assert isinstance(properties, dict)

    schema_categories = {name: spec["x-mutability"] for name, spec in properties.items()}
    assert set(schema_categories.values()) == {"immutable-core", "mutable-governance"}

    dataclass_categories = {
        f.name: f.metadata.get("category") for f in __import__("dataclasses").fields(FindingRecord)
    }
    assert schema_categories == dataclass_categories, (
        "finding-record-v1.schema.json's x-mutability must match FindingRecord's own "
        "per-field category metadata exactly — the schema is the documented source "
        "(A13.1); the dataclass is its zero-I/O runtime mirror"
    )
