"""``JsonlRecordStore`` — the generic "one record per id" store (v0.5.0 FR2, AR-1
ruling answer (b), ``specs/releases/0.5.0/reviews/S1-AR1-ruling.md`` §2).

Intent: CONTRACT — A2.2(c), A2.6, A2.9 (T-050-07).

Size: SMALL — real ``tmp_path`` filesystem, no subprocess/network. Exercises the store
generically through ``BugRecord`` (the one concrete model this release lands) and the
``container.build_bug_record_store`` composition seam, which ``features/bugs/service.py``
now reads/writes through (T-050-08 — D-F "switch"). The store's physical file is still
``bugs.jsonl`` (T-050-08) — FR3/T-050-10 renames it to ``BUGS.jsonl`` once the physical
migration lands; ``build_bug_record_store`` takes a ``specs_dir`` directly, never a
``workspace_root``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from dadaia_workspace import container
from dadaia_workspace.core.models.bugs import BugRecord, redactable_property_names
from dadaia_workspace.core.protocols.record_store import StaleRecordWriteError
from dadaia_workspace.infrastructure.jsonl_record_store import JsonlRecordStore

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SCHEMA_PATH = (
    _REPO_ROOT / "dadaia_workspace" / "public" / "schemas" / "bugs" / "bug-record-v1.schema.json"
)


def _schema() -> dict[str, Any]:
    return json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))  # type: ignore[no-any-return]


def _sample_record(record_id: str, **overrides: object) -> BugRecord:
    base: dict[str, object] = {
        "id": record_id,
        "ts": "2026-08-27T12:00:00Z",
        "reported_by": "software-engineer",
        "title": f"title for {record_id}",
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


def _store(tmp_path: Path) -> JsonlRecordStore[BugRecord]:
    return JsonlRecordStore(
        tmp_path / "BUGS.jsonl", to_dict=BugRecord.to_dict, from_dict=BugRecord.from_dict
    )


# --- A2.2(c) — governance update rewrites the line in place, byte-identical elsewhere --


def test_governance_update_rewrites_one_line_in_place_byte_identical_elsewhere(
    tmp_path: Path,
) -> None:
    """The store's ``update`` touches ONLY the matching line; every other line is
    copied through verbatim (never re-serialized), so it is byte-identical after the
    rewrite. Exercised through ``container.build_bug_record_store`` so the composition
    seam this task adds is proven, not merely the class in isolation."""
    store = container.build_bug_record_store(tmp_path)
    store_path = tmp_path / "bugs" / "bugs.jsonl"
    store.append(_sample_record("bug-a"))
    store.append(_sample_record("bug-b"))
    store.append(_sample_record("bug-c"))

    before_lines = store_path.read_text(encoding="utf-8").split("\n")
    assert len(before_lines) == 4  # 3 records + trailing empty split

    updated = store.update(
        "bug-b", lambda record: record.apply_governance_update({"status": "resolved"})
    )
    assert updated.status == "resolved"

    after_lines = store_path.read_text(encoding="utf-8").split("\n")
    assert after_lines[0] == before_lines[0]  # bug-a untouched
    assert after_lines[2] == before_lines[2]  # bug-c untouched
    assert after_lines[3] == before_lines[3] == ""  # trailing newline preserved
    assert after_lines[1] != before_lines[1]  # bug-b is the one line that changed
    assert json.loads(after_lines[1])["status"] == "resolved"


# --- A2.9 — refuse a stale rewrite, never clobber it ---------------------------------


def test_update_refuses_stale_rewrite_when_file_changed_since_read(tmp_path: Path) -> None:
    """Re-reads the file immediately before the atomic rewrite; when it changed since
    the record was read, refuses (``StaleRecordWriteError``) rather than clobbering a
    write it never saw — the file is left exactly as the concurrent writer left it,
    never corrupted (A2.9, one race semantics: refuse-stale, caller retries)."""
    store = container.build_bug_record_store(tmp_path)
    store_path = tmp_path / "bugs" / "bugs.jsonl"
    store.append(_sample_record("race-bug"))
    original_bytes = store_path.read_bytes()

    def _mutate(record: BugRecord) -> BugRecord:
        # Simulate a second writer racing between `update`'s initial read and its
        # pre-write re-read — the only hook point available from inside one call.
        store_path.write_text(store_path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
        return record.apply_governance_update({"status": "resolved"})

    with pytest.raises(StaleRecordWriteError):
        store.update("race-bug", _mutate)

    assert store_path.read_bytes() == original_bytes + b"\n"


# --- A2.6 — redaction is schema-derived and covers both write paths ------------------


def test_redaction_is_schema_derived_and_covers_both_write_paths(tmp_path: Path) -> None:
    """A NEW free-text property added to a schema FIXTURE (an in-memory dict — no file
    edited) is picked up by :func:`redactable_property_names` with NO code changed
    anywhere, proving the derivation is genuinely schema-driven. Separately, the SAME
    ``BugRecord.redact()`` seam scrubs a real denylist term on BOTH the append path and
    the in-place update path, through the generic store."""
    schema = _schema()
    baseline_fields = set(redactable_property_names(schema))
    assert "id" not in baseline_fields
    assert "ts" not in baseline_fields
    assert "reported_by" not in baseline_fields

    extended_schema = {
        **schema,
        "properties": {
            **schema["properties"],
            "extra_free_text_field": {"type": "string"},
        },
    }
    extended_fields = set(redactable_property_names(extended_schema))
    assert extended_fields == baseline_fields | {"extra_free_text_field"}

    denylist = (("SECRET-TOKEN", "test-term"),)
    store = _store(tmp_path)
    record = _sample_record("leaky-bug", component="leaked SECRET-TOKEN in the log", cause=None)

    # append path
    store.append(record.redact(denylist))
    appended = next(store.iter_records())
    assert "SECRET-TOKEN" not in appended.component
    assert "[REDACTED-TERM]" in appended.component

    # in-place update path
    updated = store.update(
        "leaky-bug",
        lambda current: current.apply_governance_update(
            {"cause": "root SECRET-TOKEN exposure"}
        ).redact(denylist),
    )
    assert updated.cause is not None
    assert "SECRET-TOKEN" not in updated.cause
    assert "[REDACTED-TERM]" in updated.cause
