"""Unit tests for the single-source ``BACKLOG.json`` reader/writer (operator ruling
2026-08-28: "BACKLOG.md e BACKLOG.json — estruturado"; schema: ``public/schemas/backlog/
backlog-v1.schema.json``).

Intent: CONTRACT — v0.12.0 A1.1-A1.6 (superseded shape); v0.5.0 A5.2, A5.3 (unchanged
semantics, new storage)

**Supersession (recorded, same pattern this module already used at the T-120-08
cutover — see ``tests/unit/features/backlog/test_frontmatter_yaml_parse_error.py``'s own
docstring for precedent).** The Markdown grammar (``## ACTIVE`` / ``### <slug>``
subsections, fenced ```yaml **Intents:** blocks, CommonMark fence-awareness, PyYAML
loader fallback) is retired outright — ``BACKLOG.md`` support is DELETED, not kept as a
fallback. Every test whose sole subject was that grammar (duplicate-heading detection,
fenced-heading-in-description, nested/unclosed fence handling, the CSafeLoader/SafeLoader
YAML-loader-fallback pair, the 140 KB fence-aware parse-budget test) is deleted with its
subject — JSON has no fence-ambiguity, no nested-heading-collision and needs no YAML
dependency for ``intents[]`` (a native JSON array now, parsed by the SAME
``core.models.backlog.parse_intents`` the old fenced-YAML block already fed). Replacement
coverage: a JSON-native duplicate-``id``-in-``active`` test, a malformed-document-shape
test (non-object/non-array), and a lighter N-item parse-budget test with the same intent.

One pure module, ``features/backlog/document.py``, parses ``BACKLOG.json`` into a typed
``BacklogDocument`` (``active`` items + errors). Parsing is diagnostic, never throwing:
every malformed piece is CAPTURED as a located :class:`DocumentError` (section, slug,
index, message), never raised. All roots are injected (``backlog_dir``); no cwd reads.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dadaia_workspace.features.backlog.document import (
    ActiveItem,
    BacklogDocument,
    DocumentError,
    load_document,
)

pytestmark = pytest.mark.unit


def _write(tmp_path: Path, document: dict[str, object]) -> Path:
    backlog_dir = tmp_path / "backlog"
    backlog_dir.mkdir(parents=True, exist_ok=True)
    (backlog_dir / "BACKLOG.json").write_text(json.dumps(document), encoding="utf-8")
    return backlog_dir


def _doc(active: list[dict[str, object]]) -> dict[str, object]:
    return {"schema": "backlog-v1", "active": active}


# ── A1.1 — a well-formed document parses to N items, fields preserved ──────────────

_WELL_FORMED = _doc(
    [
        {
            "id": "widget-refactor",
            "title": "Refactor the widget",
            "opened": "2026-08-10",
            "status": "idea",
            "description": "The widget needs a refactor.",
            "provenance": "operator request",
        },
        {
            "id": "gadget-intents",
            "title": "Bind the gadget",
            "opened": "2026-08-12",
            "status": "candidate",
            "description": "Gadget needs typed intents.",
            "provenance": "intake-report item 2-2 (approved 2026-08-15)",
            "intents": [
                {"subject": {"kind": "code", "ref": "pkg/mod.py#Gadget"}, "change": "extend Gadget"}
            ],
        },
    ]
)


def test_well_formed_document_parses_n_items_preserving_fields(tmp_path: Path) -> None:
    backlog_dir = _write(tmp_path, _WELL_FORMED)
    doc = load_document(backlog_dir)

    assert isinstance(doc, BacklogDocument)
    assert doc.errors == ()
    assert len(doc.active) == 2

    by_slug = {item.slug: item for item in doc.active}
    widget = by_slug["widget-refactor"]
    assert widget.title == "Refactor the widget"
    assert widget.opened == "2026-08-10"
    assert widget.status == "idea"
    assert widget.description == "The widget needs a refactor."
    assert widget.provenance == "operator request"
    assert widget.intents == ()
    assert widget.intents_error is None
    assert widget.index == 0

    gadget = by_slug["gadget-intents"]
    assert gadget.status == "candidate"
    assert gadget.provenance == "intake-report item 2-2 (approved 2026-08-15)"
    assert len(gadget.intents) == 1
    assert gadget.intents[0].subject.ref == "pkg/mod.py#Gadget"
    assert gadget.intents[0].change == "extend Gadget"
    assert gadget.intents_error is None
    assert gadget.index == 1


# ── A1.2 — an absent BACKLOG.json yields an empty model, not an error ───────────────


def test_absent_backlog_json_yields_empty_model_not_error(tmp_path: Path) -> None:
    backlog_dir = tmp_path / "backlog"
    backlog_dir.mkdir()
    doc = load_document(backlog_dir)
    assert doc == BacklogDocument()
    assert doc.active == ()
    assert doc.errors == ()


def test_absent_backlog_dir_itself_yields_empty_model_not_error(tmp_path: Path) -> None:
    doc = load_document(tmp_path / "does-not-exist")
    assert doc == BacklogDocument()


# ── A1.3 — an entry missing a required key: located error, parsing continues ────────

_MISSING_KEY = _doc(
    [
        {
            "id": "broken-item",
            "title": "Broken",
            "opened": "2026-08-10",
            "description": "Missing status and provenance.",
        },
        {
            "id": "next-item",
            "title": "Fine",
            "opened": "2026-08-11",
            "status": "idea",
            "description": "This one is fine.",
            "provenance": "operator request",
        },
    ]
)


def test_entry_missing_required_key_yields_located_error_and_continues(
    tmp_path: Path,
) -> None:
    backlog_dir = _write(tmp_path, _MISSING_KEY)
    doc = load_document(backlog_dir)

    schema_errors = [e for e in doc.errors if e.slug == "broken-item"]
    assert schema_errors, doc.errors
    assert all(isinstance(e, DocumentError) for e in schema_errors)
    messages = " ".join(e.message for e in schema_errors)
    assert "status" in messages
    assert "provenance" in messages
    assert all(e.index >= 0 for e in schema_errors)

    # Parsing continues: the well-formed entry after the broken one still parses.
    slugs = {item.slug for item in doc.active}
    assert "next-item" in slugs
    next_item = next(item for item in doc.active if item.slug == "next-item")
    assert next_item.status == "idea"


# ── A1.4 — a structurally invalid intents[] shape: located error, intents left empty,
# never raises ────────────────────────────────────────────────────────────────────────

_STRUCTURALLY_INVALID_INTENTS = _doc(
    [
        {
            "id": "bad-structure-item",
            "title": "Bad structure",
            "opened": "2026-08-10",
            "status": "idea",
            "description": "intents is valid JSON but not a valid intents[] shape.",
            "provenance": "operator request",
            "intents": "just_a_string",
        }
    ]
)


def test_structurally_invalid_intents_at_idea_status_still_yields_located_error(
    tmp_path: Path,
) -> None:
    """A1.4: the malformed-intents diagnostic fires at ANY status, including ``idea``
    (the FR5 status GATE only exempts the "no intents[] declared" / unresolved-subject
    findings — both doctor-level BL-SCHEMA concerns, not this parser's)."""
    backlog_dir = _write(tmp_path, _STRUCTURALLY_INVALID_INTENTS)
    doc = load_document(backlog_dir)  # must never raise

    item = next(i for i in doc.active if i.slug == "bad-structure-item")
    assert item.intents == ()
    assert item.intents_error is not None
    assert item.intents_error.startswith("malformed intents[] frontmatter:")
    assert any(e.slug == "bad-structure-item" for e in doc.errors)


# ── duplicate ``id`` within ``active`` — the JSON-native replacement for the retired
# same-slug-twice-in-ACTIVE / duplicate-top-level-heading checks ────────────────────

_DUPLICATE_ID = _doc(
    [
        {
            "id": "dup-item",
            "title": "First",
            "opened": "2026-08-10",
            "status": "idea",
            "description": "first copy.",
            "provenance": "operator request",
        },
        {
            "id": "dup-item",
            "title": "Second",
            "opened": "2026-08-10",
            "status": "idea",
            "description": "second copy, same id.",
            "provenance": "operator request",
        },
    ]
)


def test_duplicate_id_in_active_yields_document_error_and_both_still_parse(
    tmp_path: Path,
) -> None:
    """The JSON-native replacement for bug
    ``backlog-doctor-silent-on-duplicate-top-level-sections``: a duplicate ``id`` in
    ``active`` is a located :class:`DocumentError` AND both entries still parse — never
    silently dropped, so BL-SCHEMA can report it."""
    backlog_dir = _write(tmp_path, _DUPLICATE_ID)
    doc = load_document(backlog_dir)

    dup_errors = [e for e in doc.errors if "duplicate id" in e.message]
    assert len(dup_errors) == 1, doc.errors
    assert "'dup-item'" in dup_errors[0].message

    dup_items = [item for item in doc.active if item.slug == "dup-item"]
    assert len(dup_items) == 2, (
        "both entries with the duplicated id must parse — the second must never be "
        f"silently dropped: got {[i.title for i in doc.active]}"
    )
    titles = {item.title for item in dup_items}
    assert titles == {"First", "Second"}


# ── malformed document shape: never raises, always a located DocumentError ─────────


def test_malformed_json_yields_located_error_never_raises(tmp_path: Path) -> None:
    backlog_dir = tmp_path / "backlog"
    backlog_dir.mkdir(parents=True)
    (backlog_dir / "BACKLOG.json").write_text("{not valid json", encoding="utf-8")

    doc = load_document(backlog_dir)  # must never raise

    assert doc.active == ()
    assert doc.errors
    assert any("cannot parse" in e.message for e in doc.errors)


def test_document_not_a_json_object_yields_located_error(tmp_path: Path) -> None:
    backlog_dir = tmp_path / "backlog"
    backlog_dir.mkdir(parents=True)
    (backlog_dir / "BACKLOG.json").write_text("[1, 2, 3]", encoding="utf-8")

    doc = load_document(backlog_dir)

    assert doc.active == ()
    assert doc.errors
    assert any("JSON object" in e.message for e in doc.errors)


def test_active_field_not_an_array_yields_located_error(tmp_path: Path) -> None:
    backlog_dir = _write(tmp_path, {"schema": "backlog-v1", "active": "nope"})
    doc = load_document(backlog_dir)

    assert doc.active == ()
    assert doc.errors
    assert any("JSON array" in e.message for e in doc.errors)


def test_active_entry_not_an_object_yields_located_error_and_continues(
    tmp_path: Path,
) -> None:
    backlog_dir = _write(
        tmp_path,
        {
            "schema": "backlog-v1",
            "active": [
                "not-an-object",
                {
                    "id": "fine-item",
                    "title": "Fine",
                    "opened": "2026-08-10",
                    "status": "idea",
                    "description": "d",
                    "provenance": "operator request",
                },
            ],
        },
    )
    doc = load_document(backlog_dir)

    assert any("must be a JSON object" in e.message for e in doc.errors)
    slugs = {item.slug for item in doc.active}
    assert "fine-item" in slugs


# ── A1.6 — the module imports nothing from cli or hooks ─────────────────────────────
#
# The former third leg ("...or infrastructure") is RETIRED by ADR-0001 (accepted):
# the features-no-infrastructure import-linter contract this per-module substring
# check hand-duplicated is deleted from setup.cfg — this module now legitimately
# imports its sole concrete infrastructure adapter directly
# (infrastructure.jsonl_record_store.JsonlRecordStore, backlog_exit's histo_store
# type). cli/hooks independence is untouched by that ADR and still has no global
# import-linter contract behind it, so this narrowed probe stays the one thing that
# catches a features -> cli/hooks edge here.


def test_module_imports_nothing_from_cli_or_hooks() -> None:
    import inspect

    import dadaia_workspace.features.backlog.document as document_module

    source = inspect.getsource(document_module)
    for forbidden in ("dadaia_workspace.cli", "dadaia_workspace.hooks"):
        assert forbidden not in source, f"document.py must not import {forbidden}"


# ── extra coverage: dataclass shapes stay importable/typed ──────────────────────────


def test_active_item_dataclass_shape() -> None:
    item = ActiveItem(
        slug="y",
        title="Y",
        opened="2026-01-01",
        status="idea",
        description="d",
        provenance="operator request",
    )
    assert item.intents == ()
    assert item.intents_error is None
    assert item.index == 0


# ── A1.5 — an unreadable BACKLOG.json diagnostic carries no absolute filesystem path.
# Intent: CONTRACT — v0.4.2 A1.5 ─────────────────────────────────────────────────────


def test_unreadable_backlog_json_diagnostic_carries_no_absolute_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    backlog_dir = tmp_path / "backlog"
    backlog_dir.mkdir()
    target = backlog_dir / "BACKLOG.json"
    target.write_text(json.dumps({"schema": "backlog-v1", "active": []}), encoding="utf-8")

    # Portable unreadability simulation (not `target.chmod(0o000)`): POSIX permission
    # bits are a platform no-op on Windows. Monkeypatching ``Path.read_text`` to raise
    # for this exact target exercises the same `except OSError` branch identically on
    # every platform. Matched by value equality (`self == target`), not identity,
    # because ``load_document`` builds its own ``Path`` instance for the same file.
    real_read_text = Path.read_text

    def _read_text_denied(self: Path, *args: object, **kwargs: object) -> str:
        if self == target:
            raise PermissionError(13, "Permission denied", str(self))
        return real_read_text(self, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(Path, "read_text", _read_text_denied)

    doc = load_document(backlog_dir)

    assert doc.errors, "an unreadable file must surface a diagnostic, never raise"
    message = doc.errors[0].message
    assert str(backlog_dir) not in message, f"diagnostic leaked an absolute path: {message!r}"
    assert str(target) not in message, f"diagnostic leaked an absolute path: {message!r}"
    assert "BACKLOG.json" in message


# ── budget regression: an N-item document parses well under one second. Intent:
# CONTRACT — v0.4.2 A11.1 (lighter, JSON-native replacement) ────────────────────────


def _synthetic_backlog_document(n_items: int) -> dict[str, object]:
    return _doc(
        [
            {
                "id": f"synthetic-item-{i}",
                "title": f"Synthetic item {i}",
                "opened": "2026-08-10",
                "status": "idea",
                "description": "budget-regression fixture " * 10,
                "provenance": "operator request",
            }
            for i in range(n_items)
        ]
    )


def test_backlog_document_1000_items_parses_well_under_one_second(tmp_path: Path) -> None:
    import time

    backlog_dir = _write(tmp_path, _synthetic_backlog_document(1000))

    start = time.perf_counter()
    doc = load_document(backlog_dir)
    elapsed = time.perf_counter() - start

    assert doc.errors == ()
    assert len(doc.active) == 1000
    # A budget, not a stopwatch (D7): generous headroom so this is not a flake
    # generator, while still catching a real algorithmic regression.
    assert elapsed < 1.0, f"1000-item document took {elapsed:.3f}s — budget is 1.0s"
