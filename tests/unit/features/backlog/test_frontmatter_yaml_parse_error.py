"""SPEC v0.12.0 FR2/A2.4 — the generic ``intents_error`` path fires at ANY status.

Intent: CONTRACT — v0.12.0 A2.4

Bug ``backlog-doctor-yaml-parse-misdiagnosis`` (v0.1.65, FR10): historically, an unquoted
frontmatter value like ``source: text (note: more text)`` raised a ``yaml.ScannerError``
that the legacy per-entry loader (``preview._parse_frontmatter``) used to swallow — the
whole frontmatter (including a perfectly valid ``intents[]``) evaporated, and the doctor
misdiagnosed the item as ``no intents[] declared``.

**T-120-08 supersession (recorded).** The legacy per-entry loader
(``preview.load_backlog_items``/``BacklogItem``/``_parse_frontmatter``) and the doctor's
legacy-only split (``doctor._split_legacy_frontmatter_errors``) were retired at the
T-120-08 cutover — the single-source ``BACKLOG.md`` model has no monolithic YAML
frontmatter blob to fail parsing; a malformed ``**Intents:**`` fenced block is captured
generically as ``ActiveItem.intents_error`` instead, by :func:`doctor._check_schema` (A2.4).
This module's three legacy-loader-specific tests
(``test_loader_captures_frontmatter_parse_error_with_line_and_column``,
``test_legacy_split_emits_parse_error_finding_and_excludes_item_from_engine``,
``test_legacy_split_leaves_well_formed_items_unaffected``) are deleted as a recorded
supersession — their subject (the legacy loader + legacy split) no longer exists.
Replacement coverage: A2.4 (malformed ``**Intents:**`` fires at ANY status, including
``idea``) is covered end-to-end over the real document model by
``tests/integration/test_backlog_doctor.py::test_malformed_intents_yaml_fires_at_any_status_including_idea``;
this module keeps the one test below, which drives ``doctor._check_schema`` directly over
a synthetic ``ActiveItem`` — narrower, faster coverage of the same contract.
"""

from __future__ import annotations

from dadaia_workspace.features.backlog.doctor import DoctorContext, _check_schema
from dadaia_workspace.features.backlog.document import ActiveItem


def test_generic_intents_error_fires_at_idea_status_document_model() -> None:
    """A2.4: the malformed-``**Intents:**``-block diagnostic fires at ANY status,
    including ``idea`` — proven directly over ``document.ActiveItem``, the single
    reading model, confirming :func:`doctor._check_schema` never re-gates it by status."""
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
