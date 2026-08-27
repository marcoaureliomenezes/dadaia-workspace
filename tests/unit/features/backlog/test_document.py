"""Unit tests for the single-source ``BACKLOG.md`` parser (SPEC v0.12.0 FR1, PLAN §5;
v0.5.0 FR5, A5.2/A5.3).

Intent: CONTRACT — v0.12.0 A1.1-A1.6; v0.5.0 A5.2, A5.3

One pure module, ``features/backlog/document.py``, parses ``BACKLOG.md`` into a typed
``BacklogDocument`` (``ACTIVE`` subsections + errors — the in-file ``## LEDGER`` section
and its ``LedgerRow`` model retired at v0.5.0 FR5; an exit now lives in
``backlog_histo.jsonl``, see :func:`remove_active_subsection`/:func:`backlog_exit`
below). Parsing is diagnostic, never throwing: every malformed piece is CAPTURED as a
located :class:`DocumentError` (section, slug, line, message), never raised. All roots
are injected (``backlog_dir``); no cwd reads.

Not wired to anything yet (T-120-04) — these tests exercise :func:`load_document`
directly over inline ``tmp_path`` fixtures, never the live CLI.
"""

from __future__ import annotations

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


def _write(tmp_path: Path, content: str) -> Path:
    backlog_dir = tmp_path / "backlog"
    backlog_dir.mkdir(parents=True, exist_ok=True)
    (backlog_dir / "BACKLOG.md").write_text(content, encoding="utf-8")
    return backlog_dir


# ── A1.1 — a well-formed document parses to N items, fields preserved ──────────────

_WELL_FORMED = """\
# BACKLOG

## ACTIVE

### widget-refactor
- **Title:** Refactor the widget
- **Opened:** 2026-08-10
- **Status:** idea
- **Description:** The widget needs a refactor.
- **Provenance:** operator request

### gadget-intents
- **Title:** Bind the gadget
- **Opened:** 2026-08-12
- **Status:** candidate
- **Description:** Gadget needs typed intents.
- **Provenance:** intake-report item 2-2 (approved 2026-08-15)
- **Intents:**
```yaml
- subject:
    kind: code
    ref: pkg/mod.py#Gadget
  change: extend Gadget
```
"""


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
    assert widget.line > 0

    gadget = by_slug["gadget-intents"]
    assert gadget.status == "candidate"
    assert gadget.provenance == "intake-report item 2-2 (approved 2026-08-15)"
    assert len(gadget.intents) == 1
    assert gadget.intents[0].subject.ref == "pkg/mod.py#Gadget"
    assert gadget.intents[0].change == "extend Gadget"
    assert gadget.intents_error is None


# ── A1.2 — an absent BACKLOG.md yields an empty model, not an error ─────────────────


def test_absent_backlog_md_yields_empty_model_not_error(tmp_path: Path) -> None:
    backlog_dir = tmp_path / "backlog"
    backlog_dir.mkdir()
    doc = load_document(backlog_dir)
    assert doc == BacklogDocument()
    assert doc.active == ()
    assert doc.errors == ()


def test_absent_backlog_dir_itself_yields_empty_model_not_error(tmp_path: Path) -> None:
    doc = load_document(tmp_path / "does-not-exist")
    assert doc == BacklogDocument()


# ── A1.3 — a subsection missing a required key: located error, parsing continues ────

_MISSING_KEY = """\
## ACTIVE

### broken-item
- **Title:** Broken
- **Opened:** 2026-08-10
- **Description:** Missing Status and Provenance.

### next-item
- **Title:** Fine
- **Opened:** 2026-08-11
- **Status:** idea
- **Description:** This one is fine.
- **Provenance:** operator request
"""


def test_subsection_missing_required_key_yields_located_error_and_continues(
    tmp_path: Path,
) -> None:
    backlog_dir = _write(tmp_path, _MISSING_KEY)
    doc = load_document(backlog_dir)

    schema_errors = [e for e in doc.errors if e.slug == "broken-item"]
    assert schema_errors, doc.errors
    assert all(isinstance(e, DocumentError) for e in schema_errors)
    messages = " ".join(e.message for e in schema_errors)
    assert "Status" in messages
    assert "Provenance" in messages
    assert all(e.line > 0 for e in schema_errors)

    # Parsing continues: the well-formed subsection after the broken one still parses.
    slugs = {item.slug for item in doc.active}
    assert "next-item" in slugs
    next_item = next(item for item in doc.active if item.slug == "next-item")
    assert next_item.status == "idea"


# ── A1.4 — a malformed **Intents:** block: located error, intents left empty, never raises ──

_BAD_INTENTS_YAML = """\
## ACTIVE

### bad-yaml-item
- **Title:** Bad YAML
- **Opened:** 2026-08-10
- **Status:** candidate
- **Description:** The intents block is not valid YAML.
- **Provenance:** operator request
- **Intents:**
```yaml
- subject: { kind: code, ref: pkg/m.py#X
  change: unterminated flow mapping
```
"""

_STRUCTURALLY_INVALID_INTENTS = """\
## ACTIVE

### bad-structure-item
- **Title:** Bad structure
- **Opened:** 2026-08-10
- **Status:** idea
- **Description:** The intents block is valid YAML but not a valid intents[] shape.
- **Provenance:** operator request
- **Intents:**
```yaml
just_a_string
```
"""


def test_malformed_intents_yaml_yields_located_error_never_raises(tmp_path: Path) -> None:
    backlog_dir = _write(tmp_path, _BAD_INTENTS_YAML)
    doc = load_document(backlog_dir)  # must never raise

    item = next(i for i in doc.active if i.slug == "bad-yaml-item")
    assert item.intents == ()
    assert item.intents_error is not None

    schema_errors = [e for e in doc.errors if e.slug == "bad-yaml-item"]
    assert schema_errors
    assert all(e.line > 0 for e in schema_errors)


def test_structurally_invalid_intents_at_idea_status_still_yields_located_error(
    tmp_path: Path,
) -> None:
    """A1.4: the malformed-block diagnostic fires at ANY status, including ``idea``
    (the FR5 status GATE only exempts the "no intents[] declared" / unresolved-subject
    findings — both doctor-level BL-SCHEMA concerns handled in T-120-05, not here)."""
    backlog_dir = _write(tmp_path, _STRUCTURALLY_INVALID_INTENTS)
    doc = load_document(backlog_dir)

    item = next(i for i in doc.active if i.slug == "bad-structure-item")
    assert item.intents == ()
    assert item.intents_error is not None
    assert any(e.slug == "bad-structure-item" for e in doc.errors)


# ── bug backlog-doctor-silent-on-duplicate-top-level-sections — a repeated top-level
# heading is a located DocumentError, and EVERY occurrence still parses (never just
# the first) ─────────────────────────────────────────────────────────────────────────
#
# Root cause (dd-bug-fix H1, confirmed by instrumentation): ``_top_level_sections()``
# used ``dict.setdefault`` to map a heading NAME to its body range — the first
# occurrence won and every later occurrence's body was silently discarded, so a
# duplicated ``## ACTIVE`` block (and any duplicate slug inside it) never reached
# ``load_document``'s caller at all. The document schema states exactly one top-level
# section (module docstring; v0.5.0 A5.2 retired the second, ``## LEDGER``), and the
# parser now says so itself.

_DUPLICATE_ACTIVE_HEADING_SAME_SLUG = """\
## ACTIVE

### dup-item
- **Title:** First
- **Opened:** 2026-08-10
- **Status:** idea
- **Description:** first copy.
- **Provenance:** operator request

## ACTIVE

### dup-item
- **Title:** Second
- **Opened:** 2026-08-10
- **Status:** idea
- **Description:** second copy, same slug.
- **Provenance:** operator request
"""


def test_duplicate_top_level_active_heading_yields_document_error_and_parses_both_bodies(
    tmp_path: Path,
) -> None:
    """Intent: CONTRACT — bug backlog-doctor-silent-on-duplicate-top-level-sections.

    A second ``## ACTIVE`` heading is a located :class:`DocumentError` (the document
    schema states exactly one top-level section) AND its body is still parsed — both
    ``dup-item`` subsections reach ``doc.active``, so a downstream duplicate-slug check
    can compare them instead of one being silently dropped."""
    backlog_dir = _write(tmp_path, _DUPLICATE_ACTIVE_HEADING_SAME_SLUG)
    doc = load_document(backlog_dir)

    duplicate_heading_errors = [
        e for e in doc.errors if "duplicate top-level section heading" in e.message
    ]
    assert len(duplicate_heading_errors) == 1, doc.errors
    assert "'ACTIVE'" in duplicate_heading_errors[0].message
    assert duplicate_heading_errors[0].line > 0

    dup_items = [item for item in doc.active if item.slug == "dup-item"]
    assert len(dup_items) == 2, (
        "both occurrences of the duplicated '## ACTIVE' block must parse — the second "
        f"must never be silently dropped: got {[i.title for i in doc.active]}"
    )
    titles = {item.title for item in dup_items}
    assert titles == {"First", "Second"}


# ── M1 (code-reviewer, v0.12.0 pre-PR) — section splitting is fence-aware ───────────
#
# Reproduces the reviewer's finding: a fenced ``## ``/``### `` line inside an ACTIVE
# subsection's body used to be read as REAL structure by ``_top_level_sections``/
# ``_SUBSECTION_RE``, silently truncating ``## ACTIVE`` (or splicing a phantom
# subsection) with ZERO diagnostics — a clean report over a shrunken model.

_FENCED_TOP_HEADING_IN_DESCRIPTION = """\
## ACTIVE

### item-one
- **Title:** Item one
- **Opened:** 2026-08-10
- **Status:** idea
- **Description:** Example of a nested heading in a fenced span:
```markdown
## Example heading
```
- **Provenance:** operator request

### item-two
- **Title:** Item two
- **Opened:** 2026-08-11
- **Status:** candidate
- **Description:** Defined after the fence — must survive (the reviewer's repro).
- **Provenance:** operator request
"""


def test_fenced_top_heading_inside_active_description_does_not_truncate_active_section(
    tmp_path: Path,
) -> None:
    """M1: a fenced ``## Example heading`` inside item-one's Description must not end
    the ``## ACTIVE`` body early — item-two (declared after the fence) must still
    parse, and the fenced line must never be read as a real top-level section."""
    backlog_dir = _write(tmp_path, _FENCED_TOP_HEADING_IN_DESCRIPTION)
    doc = load_document(backlog_dir)

    slugs = {item.slug for item in doc.active}
    assert slugs == {"item-one", "item-two"}, (
        "item-two must not be silently dropped by a fenced '##' line in item-one's body"
    )
    item_two = next(item for item in doc.active if item.slug == "item-two")
    assert item_two.status == "candidate"
    assert item_two.description.startswith("Defined after the fence")


_FENCED_SUBSECTION_HEADING_IN_DESCRIPTION = """\
## ACTIVE

### item-one
- **Title:** Item one
- **Opened:** 2026-08-10
- **Status:** idea
- **Description:** A fenced example that itself looks like a subsection heading:
```markdown
### phantom-slug
- **Title:** This is fenced content, not a real subsection.
```
- **Provenance:** operator request
"""


def test_fenced_subsection_heading_inside_description_does_not_spawn_phantom_item(
    tmp_path: Path,
) -> None:
    """M1: a fenced ``### phantom-slug`` line inside item-one's Description must not be
    read by ``_SUBSECTION_RE`` as a second, real ``### <slug>`` subsection."""
    backlog_dir = _write(tmp_path, _FENCED_SUBSECTION_HEADING_IN_DESCRIPTION)
    doc = load_document(backlog_dir)

    slugs = [item.slug for item in doc.active]
    assert slugs == ["item-one"], f"a fenced '###' line must never spawn a phantom item: {slugs}"


_NESTED_FENCE_WITH_LONGER_OUTER_FENCE = """\
## ACTIVE

### item-one
- **Title:** Item one
- **Opened:** 2026-08-10
- **Status:** idea
- **Description:** Shows a fenced example that itself contains a fence — the outer
  fence must be longer (CommonMark close-length rule) so the inner ``` doesn't
  prematurely close it:
````markdown
Some text, then a nested fence containing a heading line:
```yaml
## still fenced, still content
```
````
- **Provenance:** operator request

### item-two
- **Title:** Item two
- **Opened:** 2026-08-11
- **Status:** candidate
- **Description:** Defined after the nested/outer fence pair.
- **Provenance:** operator request
"""


def test_longer_outer_fence_is_not_closed_by_a_shorter_nested_fence(tmp_path: Path) -> None:
    """M1: a 4-backtick outer fence containing a nested 3-backtick fence (and a heading
    line inside it) must stay open across the whole nested span — the inner ``` must
    not close it early, and item-two after the whole span must still parse."""
    backlog_dir = _write(tmp_path, _NESTED_FENCE_WITH_LONGER_OUTER_FENCE)
    doc = load_document(backlog_dir)

    slugs = {item.slug for item in doc.active}
    assert slugs == {"item-one", "item-two"}
    item_two = next(item for item in doc.active if item.slug == "item-two")
    assert item_two.status == "candidate"


_UNCLOSED_FENCE_AT_EOF = """\
## ACTIVE

### item-one
- **Title:** Item one
- **Opened:** 2026-08-10
- **Status:** idea
- **Description:** An unclosed fence follows — a structural anomaly this parser
  cannot attribute to any section:
```markdown
this fence is never closed before end-of-file
- **Provenance:** operator request
"""


def test_unclosed_fence_at_eof_surfaces_a_diagnostic_never_a_silent_shrunken_model(
    tmp_path: Path,
) -> None:
    """M1 backstop: an unclosed fence swallows everything to EOF — the model shrinks,
    but ``load_document`` must NEVER return that shrunken model with zero errors.
    Diagnostic-never-throwing still holds: no exception escapes."""
    backlog_dir = _write(tmp_path, _UNCLOSED_FENCE_AT_EOF)
    doc = load_document(backlog_dir)  # must never raise

    assert doc.errors, "an unclosed fence at EOF must never yield a silently clean model"
    assert any("fence" in e.message.lower() for e in doc.errors)
    assert all(e.line > 0 for e in doc.errors)


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


# ── extra coverage: dataclass shapes stay importable/typed as PLAN §5 declares ──────


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
    assert item.line == 0


# ═════════════════════════════════════════════════════════════════════════════════
# FR1 (v0.4.2, D1) — backlog_new MOVES here: one feature owns the grammar for both
# reading and writing. The A3.1-A3.4 coverage below is relocated UNMODIFIED from
# tests/unit/features/spec_artifacts/test_new_artifacts.py (its pre-move home); the new
# A1.2 seam (write-then-verify) is a new test. v0.5.0 FR5/A5.2 retired the fence-aware
# insertion-point coverage (A1.1) along with the ``## LEDGER`` heading it located —
# ``backlog_new`` now appends unconditionally at end-of-file (there is nothing else to
# insert ahead of, in a single-section document).
# ═════════════════════════════════════════════════════════════════════════════════

from dadaia_workspace.features.backlog.document import backlog_new  # noqa: E402

# Intent: CONTRACT — v0.4.2 A3.1 (relocated from test_new_artifacts.py, v0.12.0 origin)


def test_backlog_new_on_absent_document_creates_section_and_one_subsection(
    tmp_path: Path,
) -> None:
    specs = tmp_path / "specs"
    specs.mkdir()
    # backlog/ deliberately NOT pre-created — auto-creation facet.

    result = backlog_new(specs, "cool-idea")

    target = specs / "backlog" / "BACKLOG.md"
    assert target.is_file(), "BACKLOG.md must be created (A3.1)"
    assert result.path == target
    assert result.created is True

    content = target.read_text(encoding="utf-8")
    assert content.count("## ACTIVE") == 1
    assert "### cool-idea" in content
    assert content.index("### cool-idea") > content.index("## ACTIVE")

    assert "- **Title:** cool-idea" in content
    assert "- **Status:** idea" in content
    assert "- **Provenance:**" in content
    from datetime import UTC, datetime

    today = datetime.now(tz=UTC).strftime("%Y-%m-%d")
    assert f"- **Opened:** {today}" in content

    # The intents teaching comment is preserved (SPEC FR3), as a commented block, not
    # a live `**Intents:**` binding — an `idea` stays doctor-clean with none.
    assert "<!--" in content and "-->" in content
    assert "**Intents:**" in content  # named inside the teaching comment
    for kind in ("code", "cli", "catalog", "doc", "invariant"):
        assert kind in content

    # The fresh subsection parses clean under the single-source document model.
    doc = load_document(specs / "backlog")
    assert doc.errors == ()
    assert len(doc.active) == 1
    assert doc.active[0].slug == "cool-idea"
    assert doc.active[0].status == "idea"
    assert doc.active[0].intents == ()


# Intent: CONTRACT — v0.4.2 A3.2/A1.7 (relocated from test_new_artifacts.py, v0.12.0 origin)


def test_backlog_new_append_leaves_every_other_byte_unchanged(tmp_path: Path) -> None:
    specs = tmp_path / "specs"
    specs.mkdir()
    backlog_new(specs, "first-idea")

    target = specs / "backlog" / "BACKLOG.md"
    before = target.read_text(encoding="utf-8")

    backlog_new(specs, "second-idea")
    after = target.read_text(encoding="utf-8")

    assert after != before
    assert after.startswith(before.rstrip("\n")), (
        "every byte of the original file must survive byte-for-byte, with the new "
        "subsection appended at end-of-file"
    )
    assert "### second-idea" in after
    assert "### first-idea" in after


# Intent: CONTRACT — v0.4.2 A3.3/A1.7 (relocated from test_new_artifacts.py, v0.12.0 origin)


def test_backlog_new_refuses_slug_already_in_active(tmp_path: Path) -> None:
    specs = tmp_path / "specs"
    specs.mkdir()
    backlog_new(specs, "cool-idea")

    with pytest.raises(FileExistsError, match=r"already exists"):
        backlog_new(specs, "cool-idea")


# Intent: CONTRACT — v0.4.2 A3.4/A1.7 (relocated from test_new_artifacts.py, v0.12.0 origin)


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
        # The post-write verify re-parse: lie — report no ACTIVE items at all, as a
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


# ── A1.5 — an unreadable BACKLOG.md diagnostic carries no absolute filesystem path.
# Intent: CONTRACT — v0.4.2 A1.5 ─────────────────────────────────────────────────────


def test_unreadable_backlog_md_diagnostic_carries_no_absolute_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    backlog_dir = tmp_path / "backlog"
    backlog_dir.mkdir()
    target = backlog_dir / "BACKLOG.md"
    target.write_text("## ACTIVE\n", encoding="utf-8")

    # Portable unreadability simulation (not `target.chmod(0o000)`): POSIX permission
    # bits are a platform no-op on Windows, so the chmod-based simulation never denies
    # the read there and the OSError-handling path in load_document goes unexercised
    # (bug: Windows CI green-lit a diagnostic path it never ran). Monkeypatching
    # ``Path.read_text`` to raise for this exact target exercises the same
    # `except OSError` branch identically on every platform. Matched by value equality
    # (`self == target`), not identity, because ``load_document`` builds its own
    # ``Path`` instance for the same file.
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
    assert "BACKLOG.md" in message


# ═════════════════════════════════════════════════════════════════════════════════
# FR11 (v0.4.2, GRILL P5/P6, D7) — the fence filter is bisect-based (not the
# O(headings × fences) rescan), and load_document pays PyYAML once through
# yaml.CSafeLoader-when-available (falling back to the pure-Python loader otherwise).
# No second parse mode is added (D7) — exactly one parse path exists (A11.4, covered by
# T-042-04's A1.6 zero-hit grep test, which already asserts no module outside this one
# compiles the backlog grammar).
# ═════════════════════════════════════════════════════════════════════════════════

# ── A11.1 — budget regression: a ~140 KB synthetic document parses well under one
# second. Intent: CONTRACT — v0.4.2 A11.1 ───────────────────────────────────────────


def _synthetic_backlog_document(n_items: int) -> str:
    """Build an N-subsection ``BACKLOG.md`` where every subsection's Description also
    quotes a small fenced example — the exact shape GRILL P5 measured as
    O(headings × fences): every ``### <slug>`` heading (a match) coexists with an
    unrelated fenced span (a range) it must be checked against."""
    parts = ["## ACTIVE\n\n"]
    for i in range(n_items):
        parts.append(
            f"### synthetic-item-{i}\n"
            f"- **Title:** Synthetic item {i}\n"
            f"- **Opened:** 2026-08-10\n"
            f"- **Status:** idea\n"
            f"- **Description:** budget-regression fixture with a fenced example:\n"
            f"```markdown\nsynthetic fenced content {i}\n```\n"
            f"- **Provenance:** operator request\n\n"
        )
    return "".join(parts)


def test_backlog_document_budget_140kb_parses_well_under_one_second(tmp_path: Path) -> None:
    import time

    text = _synthetic_backlog_document(565)  # ~140 KB
    size = len(text.encode("utf-8"))
    assert 120_000 < size < 160_000, f"fixture drifted outside the ~140 KB budget: {size} bytes"

    backlog_dir = _write(tmp_path, text)

    start = time.perf_counter()
    doc = load_document(backlog_dir)
    elapsed = time.perf_counter() - start

    assert doc.errors == ()
    assert len(doc.active) == 565
    # A budget, not a stopwatch (D7): generous headroom so this is not a flake
    # generator, while still catching a real algorithmic regression.
    assert elapsed < 1.0, f"140 KB document took {elapsed:.3f}s — budget is 1.0s"


# ── A11.3 — CSafeLoader absence is exercised (forced fallback) and yields identical
# results. Intent: CONTRACT — v0.4.2 A11.3 ──────────────────────────────────────────

_WITH_INTENTS = """\
## ACTIVE

### fallback-item
- **Title:** Fallback item
- **Opened:** 2026-08-10
- **Status:** candidate
- **Description:** Exercises the Intents YAML parse path under both loaders.
- **Provenance:** operator request
- **Intents:**
```yaml
- subject:
    kind: code
    ref: pkg/mod.py#Widget
  change: extend Widget
```
"""


def test_forced_safeloader_fallback_produces_identical_results(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A11.3: force the fallback (as if the C-accelerated ``CSafeLoader`` were
    unavailable) and assert the parse is identical to the default (``CSafeLoader``,
    when the environment has libyaml) path."""
    import dadaia_workspace.features.backlog.document as document_module

    backlog_dir = _write(tmp_path, _WITH_INTENTS)

    default_doc = load_document(backlog_dir)

    monkeypatch.setattr(document_module, "_YAML_LOADER", document_module.yaml.SafeLoader)
    fallback_doc = load_document(backlog_dir)

    assert fallback_doc == default_doc
    assert fallback_doc.errors == ()
    assert len(fallback_doc.active) == 1
    assert fallback_doc.active[0].intents[0].subject.ref == "pkg/mod.py#Widget"
    assert fallback_doc.active[0].intents[0].change == "extend Widget"


# ═════════════════════════════════════════════════════════════════════════════════
# v0.5.0 FR5, A5.3 — remove_active_subsection / backlog_exit: the writer's mirror
# image. An entry exit (any disposition) removes exactly one ``### <slug>`` ACTIVE
# subsection and appends exactly one histo record — proven by an executed fixture.
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


_ONE_ACTIVE_ITEM = """\
## ACTIVE

### going-away
- **Title:** Going away
- **Opened:** 2026-08-10
- **Status:** candidate
- **Description:** About to exit.
- **Provenance:** operator request
- **Intents:**
```yaml
- subject:
    kind: code
    ref: pkg/mod.py#Widget
  change: retire Widget
```

### staying-put
- **Title:** Staying put
- **Opened:** 2026-08-11
- **Status:** idea
- **Description:** Not touched by the exit.
- **Provenance:** operator request
"""


def test_remove_active_subsection_removes_exactly_one_and_returns_its_source(
    tmp_path: Path,
) -> None:
    specs = tmp_path / "specs"
    (specs / "backlog").mkdir(parents=True)
    (specs / "backlog" / "BACKLOG.md").write_text(_ONE_ACTIVE_ITEM, encoding="utf-8")

    removed = remove_active_subsection(specs, "going-away")

    assert removed.startswith("### going-away")
    assert "retire Widget" in removed

    doc = load_document(specs / "backlog")
    assert doc.errors == ()
    slugs = {item.slug for item in doc.active}
    assert slugs == {"staying-put"}, "only the named subsection is removed"


def test_remove_active_subsection_raises_for_an_unknown_slug(tmp_path: Path) -> None:
    specs = tmp_path / "specs"
    (specs / "backlog").mkdir(parents=True)
    (specs / "backlog" / "BACKLOG.md").write_text(_ONE_ACTIVE_ITEM, encoding="utf-8")

    with pytest.raises(KeyError):
        remove_active_subsection(specs, "does-not-exist")


def test_backlog_exit_removes_active_and_appends_exactly_one_histo_record(
    tmp_path: Path,
) -> None:
    """A5.3: an entry exit (any disposition) removes exactly one ``## ACTIVE``
    subsection and appends exactly one histo record — the executed fixture the
    acceptance criterion asks for."""
    specs = tmp_path / "specs"
    (specs / "backlog").mkdir(parents=True)
    (specs / "backlog" / "BACKLOG.md").write_text(_ONE_ACTIVE_ITEM, encoding="utf-8")

    store = _FakeHistoStore()
    record = backlog_exit(
        specs,
        "going-away",
        histo_store=store,
        disposition="DELIVERED",
        reason=None,
        release="v9.9.9",
        by="test-suite",
        ts="2026-08-27",
    )

    assert record.id == "going-away"
    assert record.disposition == "DELIVERED"
    assert record.release == "v9.9.9"
    assert record.entry_md is not None and record.entry_md.startswith("### going-away")

    stored = list(store.iter_records())
    assert len(stored) == 1
    assert stored[0].id == "going-away"

    doc = load_document(specs / "backlog")
    assert {item.slug for item in doc.active} == {"staying-put"}


def test_backlog_exit_twice_for_the_same_slug_is_structurally_impossible(
    tmp_path: Path,
) -> None:
    """BL-DUP's retirement rationale (v0.5.0 A5.2), proven: once a slug has exited,
    it no longer names a live ACTIVE subsection — a second exit attempt for the same
    slug fails at the removal step, never producing a second histo record."""
    specs = tmp_path / "specs"
    (specs / "backlog").mkdir(parents=True)
    (specs / "backlog" / "BACKLOG.md").write_text(_ONE_ACTIVE_ITEM, encoding="utf-8")

    store = _FakeHistoStore()
    backlog_exit(
        specs,
        "going-away",
        histo_store=store,
        disposition="DELIVERED",
        reason=None,
        release="v9.9.9",
        by="test-suite",
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
        )

    assert len(list(store.iter_records())) == 1
