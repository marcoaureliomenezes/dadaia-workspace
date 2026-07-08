"""FR10 (v0.1.65) — backlog doctor YAML parse misdiagnosis fix.

Bug ``backlog-doctor-yaml-parse-misdiagnosis``: an unquoted frontmatter value like
``source: text (note: more text)`` raises a ``yaml.ScannerError`` that
``_parse_frontmatter`` used to swallow — the whole frontmatter (including a perfectly
valid ``intents[]``) evaporated, and the doctor misdiagnosed the item as
``no intents[] declared``.

Contract fixed here:

- the loader captures the parse failure in ``BacklogItem.frontmatter_error``
  (YAMLError message + problem-mark line/column when available);
- ``_check_schema`` emits a dedicated BL-SCHEMA ERROR
  ``frontmatter YAML parse error: <msg> (line <L>, column <C>)`` and SUPPRESSES the
  downstream no-intents / unresolved-subject findings for that item;
- well-formed files keep byte-identical findings (no regression).
"""

from __future__ import annotations

from pathlib import Path

from dadaia_workspace.features.backlog.doctor import (
    BacklogDoctorCode,
    DoctorContext,
    _check_schema,
)
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


def _ctx(items: list) -> DoctorContext:  # type: ignore[type-arg]
    ctx = DoctorContext(items=items, registry=None, consumed={})  # type: ignore[arg-type]
    for item in items:
        # Simulate the doctor's binding step without a live registry: parse failure or
        # empty intents bind to nothing; seed a synthetic unresolved message so the
        # suppression behavior is observable.
        ctx.bound[item.slug] = ({}, ["unresolved: pkg/mod.py#some_symbol"] if item.intents else [])
    return ctx


# ---------------------------------------------------------------------------
# Loader: frontmatter_error capture
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


def test_loader_leaves_well_formed_items_untouched(tmp_path: Path) -> None:
    backlog = _write_backlog(tmp_path, "good.md", _WELL_FORMED_CONTENT)
    items = load_backlog_items(backlog)
    assert len(items) == 1
    item = items[0]
    assert item.frontmatter_error is None
    assert item.status == "candidate"
    assert len(item.intents) == 1
    assert item.intents[0].subject.ref == "pkg/mod.py#some_symbol"


# ---------------------------------------------------------------------------
# Doctor: dedicated finding + downstream suppression
# ---------------------------------------------------------------------------


def test_doctor_emits_parse_error_finding_not_no_intents(tmp_path: Path) -> None:
    backlog = _write_backlog(tmp_path, "repro.md", _REPRO_CONTENT)
    items = load_backlog_items(backlog)
    findings = _check_schema(_ctx(items))
    messages = [f.message for f in findings]
    parse_errors = [m for m in messages if m.startswith("frontmatter YAML parse error: ")]
    assert len(parse_errors) == 1, messages
    assert "(line 3, column" in parse_errors[0]
    assert all(f.code is BacklogDoctorCode.BL_SCHEMA for f in findings)
    # The misdiagnosis is gone: no downstream findings for the broken item.
    assert not any("no intents[] declared" in m for m in messages)
    assert not any("unresolved" in m for m in messages)
    assert not any("invalid status" in m for m in messages)


def test_doctor_still_flags_missing_intents_on_well_formed_item(tmp_path: Path) -> None:
    backlog = _write_backlog(
        tmp_path, "no-intents.md", "---\nstatus: candidate\n---\n\n# No intents\n"
    )
    items = load_backlog_items(backlog)
    findings = _check_schema(_ctx(items))
    assert any("no intents[] declared" in f.message for f in findings)
    assert not any("frontmatter YAML parse error" in f.message for f in findings)


def test_doctor_still_surfaces_unresolved_subjects_on_well_formed_item(tmp_path: Path) -> None:
    backlog = _write_backlog(tmp_path, "good.md", _WELL_FORMED_CONTENT)
    items = load_backlog_items(backlog)
    findings = _check_schema(_ctx(items))
    assert any("unresolved: pkg/mod.py#some_symbol" in f.message for f in findings)
