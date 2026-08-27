"""``BugRecord`` — one record per bug, immutable core, mutable governance (v0.5.0 FR2).

Intent: CONTRACT — A2.1, A2.2(a), A2.2(b), A2.10, A2.11, A2.12 (T-050-07; the ruling
this file proves is AR-1, ``specs/releases/0.5.0/reviews/S1-AR1-ruling.md``).

Size: SMALL — pure-function/dataclass unit tests, no I/O beyond reading the packaged
schema fixture (tests are exempt from the ``core`` file-I/O purity ratchet;
``core/models/bugs.py`` itself never does — see its module docstring). The in-place
rewrite (A2.2c), refuse-stale (A2.9) and redaction-on-both-write-paths (A2.6) contract
tests live in ``tests/unit/infrastructure/test_jsonl_record_store.py`` since they
exercise the generic store, not this model in isolation.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator

from dadaia_workspace.core.models.bugs import (
    BugRecord,
    BugRecordImmutableFieldError,
    BugRecordWriteOnceFieldSetError,
)

_REPO_ROOT = Path(__file__).resolve().parents[4]
_SCHEMA_PATH = (
    _REPO_ROOT / "dadaia_workspace" / "public" / "schemas" / "bugs" / "bug-record-v1.schema.json"
)
_CORE_MODELS_DIR = _REPO_ROOT / "dadaia_workspace" / "core" / "models"

#: Every write-once field (v0.5.0 FR2) — includes the restored FR23 evidence triple
#: plus ``diff_direction`` (A2.11) alongside ``root_cause``/``solution``/
#: ``superseded_by``/``migration_note``.
_WRITE_ONCE_FIELDS = (
    "root_cause",
    "solution",
    "evidence_loop",
    "evidence_seam",
    "evidence_diff",
    "diff_direction",
    "superseded_by",
    "migration_note",
)


def _schema() -> dict[str, Any]:
    return json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))  # type: ignore[no-any-return]


def _sample_record(**overrides: object) -> BugRecord:
    base: dict[str, object] = {
        "id": "sample-bug",
        "ts": "2026-08-27T12:00:00Z",
        "reported_by": "software-engineer",
        "title": "sample bug",
        "severity": "MEDIUM",
        "surface": "bugs",
        "component": "features/bugs/service.py#BugService",
        "context": "dadaia-workspace",
        "symptom": "something broke",
        "repro": "run the thing",
        "expected": "it should not break",
    }
    base.update(overrides)
    return BugRecord(**base)  # type: ignore[arg-type]


# --- A2.2(a) — immutable core -------------------------------------------------------


@pytest.mark.parametrize("field_name", ["id", "title", "severity", "component"])
def test_immutable_core_field_refused_when_changed_through_apply_update(
    field_name: str,
) -> None:
    """A change to an immutable-core field's VALUE is refused at the update seam; a
    re-assertion of its OWN current value is a harmless no-op (not blanket refusal of
    the key appearing in ``changes`` — only a genuine change is refused)."""
    record = _sample_record()
    current = getattr(record, field_name)

    same_value = record.apply_governance_update({field_name: current})
    assert same_value == record

    with pytest.raises(BugRecordImmutableFieldError):
        record.apply_governance_update({field_name: f"{current}-changed"})


# --- A2.2(b) / A2.11 — write-once ----------------------------------------------------


@pytest.mark.parametrize("field_name", _WRITE_ONCE_FIELDS)
def test_write_once_field_settable_once_then_refused_on_differing_second_write(
    field_name: str,
) -> None:
    """A write-once field is absent (``None``) on a freshly registered record, settable
    exactly once, and a SECOND write with a DIFFERENT value is refused at the seam — a
    second write with the SAME value is a no-op, not a violation (A2.2b). The FR23
    evidence triple (``evidence_loop``/``evidence_seam``/``evidence_diff``) and
    ``diff_direction`` follow the identical mechanic (A2.11 — restored, not
    re-invented)."""
    record = _sample_record()
    assert getattr(record, field_name) is None

    first_write = record.apply_governance_update({field_name: "first-value"})
    assert getattr(first_write, field_name) == "first-value"

    same_value_again = first_write.apply_governance_update({field_name: "first-value"})
    assert getattr(same_value_again, field_name) == "first-value"

    with pytest.raises(BugRecordWriteOnceFieldSetError):
        first_write.apply_governance_update({field_name: "second-value"})


def test_evidence_triple_and_diff_direction_declared_write_once_in_schema() -> None:
    """A2.11: the FR23 evidence triple and ``diff_direction`` exist in
    ``bug-record-v1.schema.json``, each carrying ``x-mutability: write-once`` — the
    schema half of "restored, not re-invented" (fold 3, software-architect change 2)."""
    schema = _schema()
    properties = schema["properties"]
    assert isinstance(properties, dict)
    for name in ("evidence_loop", "evidence_seam", "evidence_diff", "diff_direction"):
        assert properties[name]["x-mutability"] == "write-once", name


# --- A2.1 / A2.10 — schema-documented categories, zero hand-kept mirror ------------


def _module_level_string_collection_offenses(source: str, filename: str) -> list[str]:
    """Return a description per module-level ``Tuple``/``List``/``Set`` LITERAL DISPLAY
    (not a computed expression — e.g. a function call — which is exactly the derived
    shape this file uses instead) whose elements are all string constants, excluding
    dunder names (``__all__`` is a legitimate export list, not a field-name mirror).

    This is the exact shape of the retired ``_OPTIONAL_STR_FIELDS: tuple[str, ...] = (
    "title", "severity", ...)`` — a hand-authored collection of property names that
    must be remembered and kept in sync with the schema by hand, which is what twice
    missed a newly added free-text field (T-043-23 -> T-044-62). A module-level name
    bound to a FUNCTION CALL result (e.g. ``_dataclass_field_names(BugRecord, ...)``)
    is NOT flagged — its contents are derived fresh from the dataclass's own field
    declarations every time, so it can never silently drift the way a literal can.
    """
    tree = ast.parse(source, filename=filename)
    offenses: list[str] = []
    for node in tree.body:
        if not isinstance(node, ast.Assign | ast.AnnAssign):
            continue
        value = node.value
        if value is None or not isinstance(value, ast.Tuple | ast.List | ast.Set):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        names = [t.id for t in targets if isinstance(t, ast.Name)]
        if any(name.startswith("__") and name.endswith("__") for name in names):
            continue
        if not value.elts:
            continue
        if all(isinstance(elt, ast.Constant) and isinstance(elt.value, str) for elt in value.elts):
            offenses.append(f"{filename}:{node.lineno} {names}")
    return offenses


def test_field_categories_documented_in_schema_match_dataclass_with_no_hand_kept_mirror() -> None:
    """A2.1: the three-category split is documented PER PROPERTY in
    ``bug-record-v1.schema.json`` (``x-mutability``), and every property is accounted
    for. A2.10: ``core/models/{bugs,findings,release_events}.py`` declare ZERO
    module-level tuple/list/set literal of property names — ``findings.py``/
    ``release_events.py`` do not exist yet at this fold (globbed, not hand-listed)."""
    schema = _schema()
    Draft202012Validator.check_schema(schema)
    properties = schema["properties"]
    assert isinstance(properties, dict)

    schema_categories = {name: spec["x-mutability"] for name, spec in properties.items()}
    assert set(schema_categories.values()) == {
        "immutable-core",
        "write-once",
        "mutable-governance",
    }

    dataclass_categories = {
        f.name: f.metadata.get("category") for f in __import__("dataclasses").fields(BugRecord)
    }
    assert schema_categories == dataclass_categories, (
        "bug-record-v1.schema.json's x-mutability must match BugRecord's own "
        "per-field category metadata exactly — the schema is the documented source "
        "(A2.1); the dataclass is its zero-I/O runtime mirror"
    )

    offenses: list[str] = []
    for candidate in sorted(_CORE_MODELS_DIR.glob("*.py")):
        if candidate.name not in {"bugs.py", "findings.py", "release_events.py"}:
            continue
        source = candidate.read_text(encoding="utf-8")
        offenses.extend(
            _module_level_string_collection_offenses(source, str(candidate.relative_to(_REPO_ROOT)))
        )
    assert not offenses, (
        "hand-kept module-level field-name mirror(s) found (A2.10 forbids them; the "
        f"field set must be read from the schema): {offenses}"
    )


# --- A2.12 — surface enum, one source ------------------------------------------------


def test_surface_enum_equals_on_disk_feature_packages() -> None:
    """A2.12: the schema ``surface`` enum's FEATURE arm equals the
    ``dadaia_workspace/features/<name>/`` packages on disk (glob, 24 at this fold),
    plus the 7 fixed non-feature members (``core``/``infrastructure``/``cli``/
    ``hooks``/``tests``/``public-assets``/``unknown``).

    Compared against the ON-DISK package list, NOT ``setup.cfg``'s
    ``[importlinter:contract:features-no-cross-feature]`` ``modules =`` list: that list
    is 20 entries today (``capabilities``/``certification``/``reconcile``/``tmp_gc``
    missing) and is completed to the full 24 by T-050-29 — asserting against it here
    would go RED for a gap this task does not own. Once T-050-29 lands, a SEPARATE
    assertion (there, not here) equates ``setup.cfg`` to this same on-disk list.
    """
    schema = _schema()
    enum_values = set(schema["properties"]["surface"]["enum"])

    features_dir = _REPO_ROOT / "dadaia_workspace" / "features"
    on_disk_packages = {
        p.name
        for p in features_dir.iterdir()
        if p.is_dir() and p.name != "__pycache__" and (p / "__init__.py").is_file()
    }
    assert len(on_disk_packages) == 24

    non_feature_members = {
        "core",
        "infrastructure",
        "cli",
        "hooks",
        "tests",
        "public-assets",
        "unknown",
    }
    assert enum_values == on_disk_packages | non_feature_members
    assert len(enum_values) == 31
