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
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest

from dadaia_workspace.core.models.backlog import BacklogHistoRecord
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


# ── A1.6 — the module imports nothing from cli, infrastructure or hooks ─────────────


def test_module_imports_nothing_from_cli_infrastructure_or_hooks() -> None:
    import inspect

    import dadaia_workspace.features.backlog.document as document_module

    source = inspect.getsource(document_module)
    for forbidden in (
        "dadaia_workspace.cli",
        "dadaia_workspace.infrastructure",
        "dadaia_workspace.hooks",
    ):
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


# ═════════════════════════════════════════════════════════════════════════════════
# backlog_new — the single writer, now emitting BACKLOG.json.
# ═════════════════════════════════════════════════════════════════════════════════

from dadaia_workspace.features.backlog.document import backlog_new  # noqa: E402

# Intent: CONTRACT — v0.4.2 A3.1 (relocated); JSON-native shape


def test_backlog_new_on_absent_document_creates_document_and_one_entry(
    tmp_path: Path,
) -> None:
    specs = tmp_path / "specs"
    specs.mkdir()
    # backlog/ deliberately NOT pre-created — auto-creation facet.

    result = backlog_new(specs, "cool-idea")

    target = specs / "backlog" / "BACKLOG.json"
    assert target.is_file(), "BACKLOG.json must be created (A3.1)"
    assert result.path == target
    assert result.created is True

    raw = json.loads(target.read_text(encoding="utf-8"))
    assert raw["schema"] == "backlog-v1"
    assert len(raw["active"]) == 1
    entry = raw["active"][0]
    assert entry["id"] == "cool-idea"
    assert entry["title"] == "cool-idea"
    assert entry["status"] == "idea"
    assert entry["provenance"]
    from datetime import UTC, datetime

    today = datetime.now(tz=UTC).strftime("%Y-%m-%d")
    assert entry["opened"] == today

    # The fresh entry parses clean under the single-source document model.
    doc = load_document(specs / "backlog")
    assert doc.errors == ()
    assert len(doc.active) == 1
    assert doc.active[0].slug == "cool-idea"
    assert doc.active[0].status == "idea"
    assert doc.active[0].intents == ()


# Intent: CONTRACT — v0.4.2 A3.2/A1.7 (relocated); JSON-native shape


def test_backlog_new_append_leaves_the_first_entry_intact(tmp_path: Path) -> None:
    specs = tmp_path / "specs"
    specs.mkdir()
    backlog_new(specs, "first-idea")

    target = specs / "backlog" / "BACKLOG.json"
    before = json.loads(target.read_text(encoding="utf-8"))

    backlog_new(specs, "second-idea")
    after = json.loads(target.read_text(encoding="utf-8"))

    assert len(after["active"]) == 2
    assert after["active"][0] == before["active"][0], "the first entry survives untouched"
    ids = {e["id"] for e in after["active"]}
    assert ids == {"first-idea", "second-idea"}


# Intent: CONTRACT — v0.4.2 A3.3/A1.7 (relocated)


def test_backlog_new_refuses_slug_already_in_active(tmp_path: Path) -> None:
    specs = tmp_path / "specs"
    specs.mkdir()
    backlog_new(specs, "cool-idea")

    with pytest.raises(FileExistsError, match=r"already exists"):
        backlog_new(specs, "cool-idea")


# Intent: CONTRACT — v0.4.2 A3.4/A1.7 (relocated)


def test_backlog_new_invalid_slug_refused_with_unchanged_message(tmp_path: Path) -> None:
    specs = tmp_path / "specs"
    specs.mkdir()
    with pytest.raises(ValueError, match=r"Invalid slug"):
        backlog_new(specs, "Not-A-Valid-Slug")


# ── A1.2 — write-then-verify: raise when a re-parse of the fresh write is missing the
# slug. Intent: SENTINEL — write-then-verify ────────────────────────────────────────


def test_backlog_new_raises_when_reparse_of_own_write_lacks_the_fresh_slug(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A1.2: every write verifies itself by re-parsing its own output. This defensive
    seam has no organic trigger under a correct implementation (a validated slug always
    round-trips), so it is exercised by making the re-parse itself lie — the same
    technique a silent-corruption bug would need to slip past undetected."""
    import dadaia_workspace.features.backlog.document as document_module

    specs = tmp_path / "specs"
    specs.mkdir()

    real_load_document = document_module.load_document
    calls = {"n": 0}

    def _lying_load_document(backlog_dir: Path) -> BacklogDocument:
        calls["n"] += 1
        if calls["n"] == 1:
            # The pre-write slug-membership check: behave normally (empty tree).
            return real_load_document(backlog_dir)
        # The post-write verify re-parse: lie — report no active items at all, as a
        # silent-write-loss bug would look from the caller's side.
        return BacklogDocument()

    monkeypatch.setattr(document_module, "load_document", _lying_load_document)

    with pytest.raises(RuntimeError, match=r"re-parse"):
        document_module.backlog_new(specs, "verify-me")


# ── A1.4 — ``_SLUG_RE.fullmatch``: a trailing newline is refused. Intent: CONTRACT —
# v0.4.2 A1.4 ────────────────────────────────────────────────────────────────────────


def test_backlog_new_rejects_slug_with_trailing_newline(tmp_path: Path) -> None:
    specs = tmp_path / "specs"
    specs.mkdir()
    with pytest.raises(ValueError, match=r"Invalid slug"):
        backlog_new(specs, "valid-slug\n")


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


# ═════════════════════════════════════════════════════════════════════════════════
# v0.5.0 FR5, A5.3 — remove_active_subsection / backlog_exit: the writer's mirror
# image. An entry exit (any disposition) removes exactly one ``active[]`` entry and
# appends exactly one histo record — proven by an executed fixture.
# ═════════════════════════════════════════════════════════════════════════════════

from dadaia_workspace.features.backlog.document import (  # noqa: E402
    backlog_exit,
    remove_active_subsection,
)


class _FakeHistoStore:
    """A minimal in-memory double satisfying
    :class:`~dadaia_workspace.core.protocols.record_store.RecordStore` for
    :class:`BacklogHistoRecord` — a fake, not a mock (internal Protocol dependency),
    per this workspace's own test-authoring convention."""

    def __init__(self) -> None:
        self._records: dict[str, BacklogHistoRecord] = {}

    @property
    def path(self) -> Path:
        return Path("fake-backlog-histo.jsonl")

    def append(self, record: BacklogHistoRecord) -> None:
        assert record.id not in self._records, f"duplicate append for {record.id!r}"
        self._records[record.id] = record

    def iter_records(self) -> Iterator[BacklogHistoRecord]:
        return iter(self._records.values())

    def update(
        self, record_id: str, mutate: Callable[[BacklogHistoRecord], BacklogHistoRecord]
    ) -> BacklogHistoRecord:
        current = self._records[record_id]
        updated = mutate(current)
        self._records[record_id] = updated
        return updated


_TWO_ACTIVE_ITEMS = _doc(
    [
        {
            "id": "going-away",
            "title": "Going away",
            "opened": "2026-08-10",
            "status": "candidate",
            "description": "About to exit.",
            "provenance": "operator request",
            "intents": [
                {"subject": {"kind": "code", "ref": "pkg/mod.py#Widget"}, "change": "retire Widget"}
            ],
        },
        {
            "id": "staying-put",
            "title": "Staying put",
            "opened": "2026-08-11",
            "status": "idea",
            "description": "Not touched by the exit.",
            "provenance": "operator request",
        },
    ]
)


def test_remove_active_subsection_removes_exactly_one_and_returns_its_source(
    tmp_path: Path,
) -> None:
    specs = tmp_path / "specs"
    (specs / "backlog").mkdir(parents=True)
    (specs / "backlog" / "BACKLOG.json").write_text(json.dumps(_TWO_ACTIVE_ITEMS), encoding="utf-8")

    removed = remove_active_subsection(specs, "going-away")

    assert '"id": "going-away"' in removed
    assert "retire Widget" in removed

    doc = load_document(specs / "backlog")
    assert doc.errors == ()
    slugs = {item.slug for item in doc.active}
    assert slugs == {"staying-put"}, "only the named entry is removed"


def test_remove_active_subsection_raises_for_an_unknown_slug(tmp_path: Path) -> None:
    specs = tmp_path / "specs"
    (specs / "backlog").mkdir(parents=True)
    (specs / "backlog" / "BACKLOG.json").write_text(json.dumps(_TWO_ACTIVE_ITEMS), encoding="utf-8")

    with pytest.raises(KeyError):
        remove_active_subsection(specs, "does-not-exist")


def test_backlog_exit_removes_active_and_appends_exactly_one_histo_record(
    tmp_path: Path,
) -> None:
    """A5.3: an entry exit (any disposition) removes exactly one ``active[]`` entry
    and appends exactly one histo record — the executed fixture the acceptance
    criterion asks for."""
    specs = tmp_path / "specs"
    (specs / "backlog").mkdir(parents=True)
    (specs / "backlog" / "BACKLOG.json").write_text(json.dumps(_TWO_ACTIVE_ITEMS), encoding="utf-8")

    store = _FakeHistoStore()
    record = backlog_exit(
        specs,
        "going-away",
        histo_store=store,
        disposition="DELIVERED",
        reason=None,
        release="v9.9.9",
        by="test-suite",
        denylist_terms=(),
        ts="2026-08-27",
    )

    assert record.id == "going-away"
    assert record.disposition == "DELIVERED"
    assert record.release == "v9.9.9"
    assert record.entry_md is not None and '"id": "going-away"' in record.entry_md

    stored = list(store.iter_records())
    assert len(stored) == 1
    assert stored[0].id == "going-away"

    doc = load_document(specs / "backlog")
    assert {item.slug for item in doc.active} == {"staying-put"}


def test_backlog_exit_twice_for_the_same_slug_is_structurally_impossible(
    tmp_path: Path,
) -> None:
    """BL-DUP's retirement rationale (v0.5.0 A5.2), proven: once a slug has exited,
    it no longer names a live ``active[]`` entry — a second exit attempt for the same
    slug fails at the removal step, never producing a second histo record."""
    specs = tmp_path / "specs"
    (specs / "backlog").mkdir(parents=True)
    (specs / "backlog" / "BACKLOG.json").write_text(json.dumps(_TWO_ACTIVE_ITEMS), encoding="utf-8")

    store = _FakeHistoStore()
    backlog_exit(
        specs,
        "going-away",
        histo_store=store,
        disposition="DELIVERED",
        reason=None,
        release="v9.9.9",
        by="test-suite",
        denylist_terms=(),
    )

    with pytest.raises(KeyError):
        backlog_exit(
            specs,
            "going-away",
            histo_store=store,
            disposition="DELIVERED",
            reason=None,
            release="v9.9.9",
            by="test-suite",
            denylist_terms=(),
        )

    assert len(list(store.iter_records())) == 1


# ═════════════════════════════════════════════════════════════════════════════════
# bug backlog-histo-writer-skips-write-time-denylist-redaction — backlog_exit must
# thread an injected operator denylist through BacklogHistoRecord.redact() BEFORE
# appending, exactly as BugService.register/apply_update already do (SPEC v0.4.5
# FR6/T-045-19). Before the fix: an entry_md snapshot carrying a denylisted term is
# appended RAW, caught only later at the push gate.
# ═════════════════════════════════════════════════════════════════════════════════

_ACTIVE_ITEM_WITH_DENYLISTED_TERM = _doc(
    [
        {
            "id": "leaky-exit",
            "title": "Leaky exit",
            "opened": "2026-08-10",
            "status": "candidate",
            "description": "See .dadaia/reports/acme-corp-games/qa-engineer/report.html for detail.",
            "provenance": "operator request",
        }
    ]
)


def test_backlog_exit_masks_a_denylisted_term_in_entry_md_before_append(
    tmp_path: Path,
) -> None:
    """The RED test (bug backlog-histo-writer-skips-write-time-denylist-redaction):
    ``backlog_exit`` threads its ``denylist_terms`` parameter through
    ``BacklogHistoRecord.redact()`` before the record ever reaches the injected
    store — the SAME write-time seam ``BugService.register`` already enforces."""
    specs = tmp_path / "specs"
    (specs / "backlog").mkdir(parents=True)
    (specs / "backlog" / "BACKLOG.json").write_text(
        json.dumps(_ACTIVE_ITEM_WITH_DENYLISTED_TERM), encoding="utf-8"
    )

    store = _FakeHistoStore()
    record = backlog_exit(
        specs,
        "leaky-exit",
        histo_store=store,
        disposition="DELIVERED",
        reason=None,
        release="v9.9.9",
        by="test-suite",
        ts="2026-08-27",
        denylist_terms=(("acme-corp", "private project/person identifier"),),
    )

    assert record.entry_md is not None
    assert "acme-corp" not in record.entry_md.lower()
    assert "[REDACTED-TERM]" in record.entry_md

    persisted = list(store.iter_records())[0]
    assert persisted.entry_md is not None
    assert "acme-corp" not in persisted.entry_md.lower()


def test_backlog_exit_with_empty_denylist_terms_stays_byte_identical_to_pre_fix(
    tmp_path: Path,
) -> None:
    """A6.3-class sibling guarantee: ``backlog_exit`` called with an explicit empty
    ``denylist_terms=()`` (F-13, T-050-36 security review: the parameter is REQUIRED,
    no default) behaves exactly as before the fix — the removed entry's snapshot is
    appended verbatim, byte-identical."""
    specs = tmp_path / "specs"
    (specs / "backlog").mkdir(parents=True)
    (specs / "backlog" / "BACKLOG.json").write_text(
        json.dumps(_ACTIVE_ITEM_WITH_DENYLISTED_TERM), encoding="utf-8"
    )

    store = _FakeHistoStore()
    record = backlog_exit(
        specs,
        "leaky-exit",
        histo_store=store,
        disposition="DELIVERED",
        reason=None,
        release="v9.9.9",
        by="test-suite",
        denylist_terms=(),
        ts="2026-08-27",
    )

    assert record.entry_md is not None
    assert "acme-corp-games" in record.entry_md
