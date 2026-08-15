"""FR10 (v0.1.65) legacy loader + SPEC v0.12.0 FR2/T-120-05 generic-engine coverage.

Intent: CONTRACT — v0.12.0 A2.2, A2.4

Bug ``backlog-doctor-yaml-parse-misdiagnosis``: an unquoted frontmatter value like
``source: text (note: more text)`` raises a ``yaml.ScannerError`` that
``_parse_frontmatter`` used to swallow — the whole frontmatter (including a perfectly
valid ``intents[]``) evaporated, and the doctor misdiagnosed the item as
``no intents[] declared``.

Contract fixed here (still true over the legacy per-entry model, T-120-05):

- the loader captures the parse failure in ``BacklogItem.frontmatter_error``
  (YAMLError message + problem-mark line/column when available);
- ``run_backlog_doctor``'s legacy split (:func:`doctor._split_legacy_frontmatter_errors`)
  emits a dedicated BL-SCHEMA ERROR ``frontmatter YAML parse error: <msg> (line <L>,
  column <C>)`` and EXCLUDES that item from the shared check engine, suppressing the
  downstream no-intents / unresolved-subject findings for it;
- well-formed files keep byte-identical findings (no regression).

**T-120-05 migration.** ``document.ActiveItem`` has no ``frontmatter_error`` concept (no
single YAML frontmatter blob in the new Markdown-bold-key shape — a malformed
``**Intents:**`` block is captured as ``intents_error`` instead, generically, by
:func:`doctor._check_schema` — A2.4). This module therefore now tests TWO things: the
legacy-only frontmatter-error split (still real, still wired, until T-120-08), and the
generic ``intents_error`` path shared by both models.
"""

from __future__ import annotations

from pathlib import Path

from dadaia_workspace.features.backlog.doctor import (
    BacklogDoctorCode,
    DoctorContext,
    Severity,
    _check_schema,
    _split_legacy_frontmatter_errors,
    run_checks,
)
from dadaia_workspace.features.backlog.document import ActiveItem
from dadaia_workspace.features.backlog.preview import load_backlog_items

#: The bug's repro frontmatter: the unquoted ``(note: ...)`` value is a YAML
#: ScannerError ("mapping values are not allowed here"), while ``intents[]`` is valid.
_REPRO_CONTENT = """---
status: candidate
source: text (note: more text)
intents:
  - subject:
      kind: code
      ref: pkg/mod.py#some_symbol
    change: extend
---

# Repro item
"""

_WELL_FORMED_CONTENT = """---
status: candidate
source: "text (note: more text)"
intents:
  - subject:
      kind: code
      ref: pkg/mod.py#some_symbol
    change: extend
---

# Well-formed item
"""


def _write_backlog(tmp_path: Path, name: str, content: str) -> Path:
    backlog = tmp_path / "backlog"
    backlog.mkdir(exist_ok=True)
    (backlog / name).write_text(content, encoding="utf-8")
    return backlog


def _ctx_with_bound(items: list) -> DoctorContext:  # type: ignore[type-arg]
    """Build a minimal ``DoctorContext`` with a synthetic bound map — no live registry,
    matching the pre-existing driving-fake style: parse failure or empty intents bind to
    nothing, an unresolved intent seeds a synthetic HALT message so the schema check's
    suppression behaviour is directly observable without standing up a real registry."""
    ctx = DoctorContext(items=items, registry=None, consumed={})  # type: ignore[arg-type]
    for item in items:
        ctx.bound[item.slug] = (
            {},
            ["unresolved: pkg/mod.py#some_symbol"] if item.intents else [],
        )
    return ctx


# ---------------------------------------------------------------------------
# Legacy loader: frontmatter_error capture (still real over the per-entry model)
# ---------------------------------------------------------------------------


def test_loader_captures_frontmatter_parse_error_with_line_and_column(tmp_path: Path) -> None:
    backlog = _write_backlog(tmp_path, "repro.md", _REPRO_CONTENT)
    items = load_backlog_items(backlog)
    assert len(items) == 1
    item = items[0]
    assert item.frontmatter_error is not None
    assert "(line 3, column" in item.frontmatter_error
    # The parse failure zeroes the frontmatter — no intents, no intents_error.
    assert item.intents == ()
    assert item.intents_error is None
    assert item.status is None


# ---------------------------------------------------------------------------
# Legacy split: dedicated finding + downstream suppression vs well-formed still flagged
# ---------------------------------------------------------------------------


def test_legacy_split_emits_parse_error_finding_and_excludes_item_from_engine(
    tmp_path: Path,
) -> None:
    backlog = _write_backlog(tmp_path, "repro.md", _REPRO_CONTENT)
    items = load_backlog_items(backlog)

    findings, clean_items = _split_legacy_frontmatter_errors(items)

    messages = [f.message for f in findings]
    parse_errors = [m for m in messages if m.startswith("frontmatter YAML parse error: ")]
    assert len(parse_errors) == 1, messages
    assert "(line 3, column" in parse_errors[0]
    assert all(f.code is BacklogDoctorCode.BL_SCHEMA for f in findings)
    assert all(f.severity is Severity.ERROR for f in findings)

    # The broken item never reaches the shared check engine — no downstream noise.
    assert clean_items == []


def test_legacy_split_leaves_well_formed_items_unaffected(tmp_path: Path) -> None:
    """A parse-error item's exclusion must not bleed into other items: a well-formed
    item with no intents still gets 'no intents[]' from the shared engine, and a
    well-formed item with an unresolved subject still surfaces it."""
    backlog = _write_backlog(
        tmp_path, "no-intents.md", "---\nstatus: candidate\n---\n\n# No intents\n"
    )
    items = load_backlog_items(backlog)
    findings, clean_items = _split_legacy_frontmatter_errors(items)
    assert findings == []
    assert len(clean_items) == 1
    engine_findings = run_checks(_ctx_with_bound(clean_items))
    assert any("no intents[] declared" in f.message for f in engine_findings)
    assert not any("frontmatter YAML parse error" in f.message for f in engine_findings)

    backlog2 = _write_backlog(tmp_path, "good.md", _WELL_FORMED_CONTENT)
    items2 = load_backlog_items(backlog2)
    findings2, clean_items2 = _split_legacy_frontmatter_errors(items2)
    assert findings2 == []
    engine_findings2 = run_checks(_ctx_with_bound(clean_items2))
    assert any("unresolved: pkg/mod.py#some_symbol" in f.message for f in engine_findings2)
    assert not any("frontmatter YAML parse error" in f.message for f in engine_findings2)


# ---------------------------------------------------------------------------
# A2.4 — the generic intents_error path (shared engine, both models) fires at ANY status
# ---------------------------------------------------------------------------


def test_generic_intents_error_fires_at_idea_status_document_model(tmp_path: Path) -> None:
    """A2.4: the malformed-``**Intents:**``-block diagnostic fires at ANY status,
    including ``idea`` — proven directly over ``document.ActiveItem`` (the new model),
    not just the legacy loader, confirming :func:`doctor._check_schema` is genuinely
    generic over both."""
    item = ActiveItem(
        slug="bad-structure-item",
        title="Bad structure",
        opened="2026-08-10",
        status="idea",
        description="d",
        provenance="operator request",
        intents=(),
        intents_error="malformed intents[] frontmatter: intents must be a list, got str",
    )
    ctx = DoctorContext(items=[item], registry=None, consumed={})  # type: ignore[arg-type]
    ctx.bound[item.slug] = ({}, [])
    findings = _check_schema(ctx)
    messages = [f.message for f in findings]
    assert any(m.startswith("malformed intents[] frontmatter: ") for m in messages)
    assert not any("no intents[] declared" in m for m in messages)
    assert not any("invalid status" in m for m in messages)
