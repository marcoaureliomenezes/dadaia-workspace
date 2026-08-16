"""Unit tests for the single-source ``BACKLOG.md`` parser (SPEC v0.12.0 FR1, PLAN §5).

Intent: CONTRACT — v0.12.0 A1.1-A1.6

One pure module, ``features/backlog/document.py``, parses ``BACKLOG.md`` into a typed
``BacklogDocument`` (``ACTIVE`` subsections + ``LEDGER`` rows). Parsing is diagnostic,
never throwing: every malformed piece is CAPTURED as a located :class:`DocumentError`
(section, slug, line, message), never raised. All roots are injected (``backlog_dir``);
no cwd reads.

Not wired to anything yet (T-120-04) — these tests exercise :func:`load_document`
directly over inline ``tmp_path`` fixtures, never the live CLI.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.features.backlog.document import (
    ActiveItem,
    BacklogDocument,
    DocumentError,
    LedgerRow,
    load_document,
)

pytestmark = pytest.mark.unit


def _write(tmp_path: Path, content: str) -> Path:
    backlog_dir = tmp_path / "backlog"
    backlog_dir.mkdir(parents=True, exist_ok=True)
    (backlog_dir / "BACKLOG.md").write_text(content, encoding="utf-8")
    return backlog_dir


# ── A1.1 — a well-formed document parses to N items + M rows, fields preserved ──────

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

## LEDGER

- old-feature · DELIVERED · v0.9.0 · 2026-06-01
- rejected-idea · REJECTED · not worth pursuing · 2026-05-10
"""


def test_well_formed_document_parses_n_items_and_m_rows_preserving_fields(
    tmp_path: Path,
) -> None:
    backlog_dir = _write(tmp_path, _WELL_FORMED)
    doc = load_document(backlog_dir)

    assert isinstance(doc, BacklogDocument)
    assert doc.errors == ()
    assert len(doc.active) == 2
    assert len(doc.ledger) == 2

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

    rows_by_slug = {row.slug: row for row in doc.ledger}
    old = rows_by_slug["old-feature"]
    assert old.disposition == "DELIVERED"
    assert old.release_or_reason == "v0.9.0"
    assert old.date == "2026-06-01"
    assert old.line > 0

    rejected = rows_by_slug["rejected-idea"]
    assert rejected.disposition == "REJECTED"
    assert rejected.release_or_reason == "not worth pursuing"


# ── A1.2 — an absent BACKLOG.md yields an empty model, not an error ─────────────────


def test_absent_backlog_md_yields_empty_model_not_error(tmp_path: Path) -> None:
    backlog_dir = tmp_path / "backlog"
    backlog_dir.mkdir()
    doc = load_document(backlog_dir)
    assert doc == BacklogDocument()
    assert doc.active == ()
    assert doc.ledger == ()
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

## LEDGER
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

## LEDGER
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

## LEDGER
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


# ── A1.5 — a LEDGER line off-grammar or with an unknown disposition: located error ──

_BAD_LEDGER = """\
## ACTIVE

## LEDGER

- good-slug · DELIVERED · v0.9.0 · 2026-06-01
- too-few-fields · DELIVERED · v0.9.0
- unknown-token-slug · MAYBE · v0.9.0 · 2026-06-01
"""


def test_ledger_line_off_grammar_or_unknown_disposition_yields_located_error(
    tmp_path: Path,
) -> None:
    backlog_dir = _write(tmp_path, _BAD_LEDGER)
    doc = load_document(backlog_dir)

    good_slugs = {row.slug for row in doc.ledger}
    assert good_slugs == {"good-slug"}

    error_lines = {e.line for e in doc.errors}
    assert len(error_lines) == 2  # too-few-fields + unknown-token-slug
    assert all(isinstance(e, DocumentError) for e in doc.errors)
    assert all(e.section == "LEDGER" for e in doc.errors)


@pytest.mark.parametrize(
    "token",
    ["DELIVERED", "SUPERSEDED", "RESOLVED", "CONSUMED", "DEFERRED", "REJECTED"],
)
def test_every_canonical_disposition_token_accepted(tmp_path: Path, token: str) -> None:
    content = f"## ACTIVE\n\n## LEDGER\n\n- some-slug · {token} · v0.9.0 · 2026-06-01\n"
    backlog_dir = _write(tmp_path, content)
    doc = load_document(backlog_dir)
    assert len(doc.ledger) == 1
    assert doc.ledger[0].disposition == token
    assert doc.errors == ()


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

## LEDGER
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
    # A truncation this parser cannot attribute would previously vanish with zero
    # errors AND zero LEDGER (since '## LEDGER' itself would be swallowed by the same
    # bug). Confirm the real '## LEDGER' heading is still found, not phantom-shadowed.
    assert doc.ledger == ()  # no rows declared, but the section itself parsed (not an error)


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

## LEDGER
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

## LEDGER
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

## LEDGER
"""


def test_unclosed_fence_at_eof_surfaces_a_diagnostic_never_a_silent_shrunken_model(
    tmp_path: Path,
) -> None:
    """M1 backstop: an unclosed fence swallows everything to EOF (including the real
    '## LEDGER' heading) — the model shrinks, but ``load_document`` must NEVER return
    that shrunken model with zero errors. Diagnostic-never-throwing still holds: no
    exception escapes."""
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


def test_ledger_row_and_active_item_dataclass_shapes() -> None:
    row = LedgerRow(
        slug="x", disposition="DELIVERED", release_or_reason="v0.1.0", date="2026-01-01", line=1
    )
    assert row.slug == "x"
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
