"""Integration tests for the BL-SCHEMA/DUP/CONFLICT/STALE checks over the single-source
``BACKLOG.md`` document model (SPEC v0.12.0 FR2, ADR D8, PLAN §6, §8).

Intent: CONTRACT — v0.12.0 A2.1-A2.8, A2.9(-adjacent), A3.5, A5.6

The four BL-* checks are exercised by a **single parameterized** test (one fixture
matrix) — NOT four copy-pasted functions (SPEC §3.8 #8). A planted violation per check
ERRORs; a clean tree passes (no findings). Roots injected over a ``tmp_path`` fixture.

Most tests below drive :func:`document.load_document` + :func:`doctor.run_checks`
DIRECTLY over inline ``BACKLOG.md`` fixtures — fine-grained control over the check
engine, independent of the CLI wiring. ``_CHECKS``, ``Finding``, ``Severity`` and the
message texts are the SAME symbols the CLI-facing :func:`doctor.run_backlog_doctor`
uses — this is the same engine, fed the same (fixture-built) item source by hand. The
final section proves the wiring itself: :func:`run_backlog_doctor` (wired to
:func:`document.load_document` since the T-120-08 cutover) and ``specs doctor``'s
backlog-surface checks agree on the same tree (A5.6), and a freshly authored
``backlog_new`` subsection passes both out of the box (A3.5).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dadaia_workspace.features.backlog.doctor import (
    BacklogDoctorCode,
    DoctorContext,
    Finding,
    Severity,
    run_checks,
)
from dadaia_workspace.features.backlog.document import load_document
from dadaia_workspace.features.backlog.ledger import read_consumed
from dadaia_workspace.features.backlog.preview import bound_anchor_changes
from dadaia_workspace.features.backlog.subject_registry import build_registry

pytestmark = pytest.mark.integration

# A minimal source root the registry scans for code anchors.
_SOURCE = "class Widget:\n    pass\n\n\nclass Gadget:\n    pass\n"

_ACTIVE_SUBSECTION = """\
### {slug}
- **Title:** {title}
- **Opened:** 2026-08-10
- **Status:** {status}
- **Description:** {slug} needs a change.
- **Provenance:** operator request
{intents_block}
"""


def _intents_block(ref: str, change: str) -> str:
    return (
        "- **Intents:**\n```yaml\n"
        f"- subject:\n    kind: code\n    ref: {ref}\n  change: {change}\n```\n"
    )


def _build_roots(tmp_path: Path) -> tuple[Path, Path]:
    specs = tmp_path / "specs"
    (specs / "backlog").mkdir(parents=True)
    (specs / "memory" / "product").mkdir(parents=True)
    (specs / "memory" / "product" / "catalog.json").write_text(
        json.dumps({"features": [{"slug": "alpha-feature"}]}), encoding="utf-8"
    )
    src = tmp_path / "src"
    (src / "pkg").mkdir(parents=True)
    (src / "pkg" / "m.py").write_text(_SOURCE, encoding="utf-8")
    return specs, src


def _write_backlog_md(specs: Path, active_body: str, ledger_body: str = "") -> None:
    text = f"## ACTIVE\n\n{active_body}\n## LEDGER\n\n{ledger_body}"
    (specs / "backlog" / "BACKLOG.md").write_text(text, encoding="utf-8")


def _run(specs: Path, src: Path, archive_root: Path | None = None) -> list[Finding]:
    document = load_document(specs / "backlog")
    registry = build_registry(
        source_root=src,
        catalog_path=specs / "memory" / "product" / "catalog.json",
        alias_map_path=specs / "no-aliases.txt",
        specs_dir=specs,
        cli_anchors=frozenset(),
    )
    consumed = read_consumed(archive_root if archive_root is not None else specs / "_archive")
    ctx = DoctorContext(
        items=list(document.active),
        registry=registry,
        consumed=consumed,
        ledger=document.ledger,
        document_errors=document.errors,
    )
    for item in document.active:
        ctx.bound[item.slug] = bound_anchor_changes(item, registry)
    return run_checks(ctx)


# ── A2.1 — a clean consolidated BACKLOG.md yields zero findings, exit 0 ─────────────


def test_clean_document_yields_zero_findings(tmp_path: Path) -> None:
    specs, src = _build_roots(tmp_path)
    active = _ACTIVE_SUBSECTION.format(
        slug="clean-one",
        title="Clean one",
        status="idea",
        intents_block="",
    ) + _ACTIVE_SUBSECTION.format(
        slug="clean-two",
        title="Clean two",
        status="candidate",
        intents_block=_intents_block("pkg/m.py#Widget", "tweak Widget"),
    )
    _write_backlog_md(specs, active)
    findings = _run(specs, src)
    assert findings == [], [f.to_dict() for f in findings]


# ── A2.2 — a subsection missing a required key fires exactly one BL-SCHEMA ERROR ────


def test_missing_required_key_fires_exactly_one_bl_schema_naming_slug(tmp_path: Path) -> None:
    specs, src = _build_roots(tmp_path)
    active = (
        "### broken-item\n"
        "- **Title:** Broken\n"
        "- **Opened:** 2026-08-10\n"
        "- **Description:** Missing Status and Provenance.\n\n"
    )
    _write_backlog_md(specs, active)
    findings = _run(specs, src)
    schema_findings = [f for f in findings if f.slug == "broken-item"]
    assert len(schema_findings) == 1, [f.to_dict() for f in findings]
    assert schema_findings[0].code is BacklogDoctorCode.BL_SCHEMA
    assert schema_findings[0].severity is Severity.ERROR
    assert "Status" in schema_findings[0].message
    assert "Provenance" in schema_findings[0].message


# ── A2.3 — candidate with no Intents fires BL-SCHEMA; idea does not (FR5 preserved) ──


def test_candidate_with_no_intents_fires_but_idea_does_not(tmp_path: Path) -> None:
    specs, src = _build_roots(tmp_path)
    active = _ACTIVE_SUBSECTION.format(
        slug="candidate-no-intents", title="Cand", status="candidate", intents_block=""
    )
    _write_backlog_md(specs, active)
    findings = _run(specs, src)
    assert any(
        f.code is BacklogDoctorCode.BL_SCHEMA and "no intents[] declared" in f.message
        for f in findings
    ), [f.to_dict() for f in findings]

    specs2, src2 = _build_roots(tmp_path / "idea-case")
    active2 = _ACTIVE_SUBSECTION.format(
        slug="idea-no-intents", title="Idea", status="idea", intents_block=""
    )
    _write_backlog_md(specs2, active2)
    findings2 = _run(specs2, src2)
    assert findings2 == [], [f.to_dict() for f in findings2]


# ── A2.4 — a malformed intents YAML block fires BL-SCHEMA at ANY status ─────────────


def test_malformed_intents_yaml_fires_at_any_status_including_idea(tmp_path: Path) -> None:
    specs, src = _build_roots(tmp_path)
    active = (
        "### bad-intents\n"
        "- **Title:** Bad\n"
        "- **Opened:** 2026-08-10\n"
        "- **Status:** idea\n"
        "- **Description:** malformed intents block.\n"
        "- **Provenance:** operator request\n"
        "- **Intents:**\n```yaml\njust_a_string\n```\n\n"
    )
    _write_backlog_md(specs, active)
    findings = _run(specs, src)
    assert any(
        f.code is BacklogDoctorCode.BL_SCHEMA
        and f.message.startswith("malformed intents[] frontmatter: ")
        for f in findings
    ), [f.to_dict() for f in findings]


# ── A2.5 — a slug repeated in ACTIVE fires BL-DUP; divergent anchors fire BL-CONFLICT ──


def test_duplicate_slug_in_active_fires_bl_dup(tmp_path: Path) -> None:
    specs, src = _build_roots(tmp_path)
    one = _ACTIVE_SUBSECTION.format(
        slug="dup-slug",
        title="One",
        status="candidate",
        intents_block=_intents_block("pkg/m.py#Widget", "first"),
    )
    two = _ACTIVE_SUBSECTION.format(
        slug="dup-slug",
        title="Two",
        status="candidate",
        intents_block=_intents_block("pkg/m.py#Gadget", "second"),
    )
    _write_backlog_md(specs, one + two)
    findings = _run(specs, src)
    dup = [f for f in findings if f.code is BacklogDoctorCode.BL_DUP]
    assert any("more than once in ACTIVE" in f.message for f in dup), [
        f.to_dict() for f in findings
    ]


def test_same_anchor_same_change_fires_bl_dup_pairwise(tmp_path: Path) -> None:
    specs, src = _build_roots(tmp_path)
    active = _ACTIVE_SUBSECTION.format(
        slug="dup-a",
        title="A",
        status="candidate",
        intents_block=_intents_block("pkg/m.py#Widget", "refactor Widget"),
    ) + _ACTIVE_SUBSECTION.format(
        slug="dup-b",
        title="B",
        status="candidate",
        intents_block=_intents_block("pkg/m.py#Widget", "refactor Widget"),
    )
    _write_backlog_md(specs, active)
    findings = _run(specs, src)
    assert any(f.code is BacklogDoctorCode.BL_DUP for f in findings), [
        f.to_dict() for f in findings
    ]


def test_divergent_anchor_change_fires_bl_conflict(tmp_path: Path) -> None:
    specs, src = _build_roots(tmp_path)
    active = _ACTIVE_SUBSECTION.format(
        slug="twin-d",
        title="D",
        status="candidate",
        intents_block=_intents_block("pkg/m.py#Widget", "change to D"),
    ) + _ACTIVE_SUBSECTION.format(
        slug="twin-e",
        title="E",
        status="candidate",
        intents_block=_intents_block("pkg/m.py#Widget", "change to E"),
    )
    _write_backlog_md(specs, active)
    findings = _run(specs, src)
    assert any(f.code is BacklogDoctorCode.BL_CONFLICT for f in findings), [
        f.to_dict() for f in findings
    ]


# ── A2.6 — an ACTIVE item whose slug carries a LEDGER line fires BL-STALE ───────────


def test_active_slug_also_in_ledger_fires_bl_stale(tmp_path: Path) -> None:
    specs, src = _build_roots(tmp_path)
    active = _ACTIVE_SUBSECTION.format(
        slug="shipped-but-still-active",
        title="Shipped",
        status="candidate",
        intents_block=_intents_block("pkg/m.py#Widget", "already shipped"),
    )
    ledger = "- shipped-but-still-active · DELIVERED · v0.11.0 · 2026-08-01\n"
    _write_backlog_md(specs, active, ledger)
    findings = _run(specs, src)
    stale = [f for f in findings if f.code is BacklogDoctorCode.BL_STALE]
    assert any(f.slug == "shipped-but-still-active" for f in stale), [f.to_dict() for f in findings]


def test_slug_only_in_ledger_fires_nothing(tmp_path: Path) -> None:
    specs, src = _build_roots(tmp_path)
    ledger = "- long-gone · DELIVERED · v0.9.0 · 2026-06-01\n"
    _write_backlog_md(specs, "", ledger)
    findings = _run(specs, src)
    assert findings == [], [f.to_dict() for f in findings]


def test_active_item_with_own_terminal_status_fires_bl_stale(tmp_path: Path) -> None:
    """The third BL-STALE ORed condition (ADR D8): an ACTIVE item's own ``Status`` is
    itself one of the six canonical terminal disposition tokens."""
    specs, src = _build_roots(tmp_path)
    active = _ACTIVE_SUBSECTION.format(
        slug="mis-statused",
        title="Mis-statused",
        status="DELIVERED",
        intents_block=_intents_block("pkg/m.py#Widget", "already shipped"),
    )
    _write_backlog_md(specs, active)
    findings = _run(specs, src)
    stale = [f for f in findings if f.code is BacklogDoctorCode.BL_STALE]
    assert any(f.slug == "mis-statused" for f in stale), [f.to_dict() for f in findings]


def test_deferred_active_status_fires_bl_stale(tmp_path: Path) -> None:
    """Bug ``backlog-doctor-rejects-deferred-status-documented-by-skill`` (T-044-34) —
    the literal repro from the report: an ACTIVE entry with ``Status: deferred``.
    ``deferred`` IS one of the six canonical terminal disposition tokens
    (``core.models.backlog.TERMINAL_DISPOSITION_TOKENS``), so BL-STALE firing here is the
    correct, decided behaviour — not the bug. The statement that was actually wrong was
    ``dd-backlog-definition`` SKILL.md listing ``deferred`` as a live ACTIVE status; see
    ``tests/contract/test_backlog_status_vocabulary_contract.py`` for that half."""
    specs, src = _build_roots(tmp_path)
    active = _ACTIVE_SUBSECTION.format(
        slug="prematurely-deferred",
        title="Prematurely deferred",
        status="deferred",
        intents_block=_intents_block("pkg/m.py#Widget", "still needs a home"),
    )
    _write_backlog_md(specs, active)
    findings = _run(specs, src)
    stale = [f for f in findings if f.code is BacklogDoctorCode.BL_STALE]
    assert any(f.slug == "prematurely-deferred" for f in stale), [f.to_dict() for f in findings]


# ── A2.7 — an ACTIVE item whose slug appears in an archived consumed_backlog.json ───


def test_slug_in_archived_consumed_ledger_fires_bl_stale(tmp_path: Path) -> None:
    specs, src = _build_roots(tmp_path)
    active = _ACTIVE_SUBSECTION.format(
        slug="shipped-feature",
        title="Shipped feature",
        status="candidate",
        intents_block=_intents_block("pkg/m.py#Widget", "already shipped"),
    )
    _write_backlog_md(specs, active)
    archive = specs / "_archive" / "v0.1.20"
    archive.mkdir(parents=True)
    (archive / "consumed_backlog.json").write_text(
        json.dumps(
            {"release": "v0.1.20", "consumed": [{"slug": "shipped-feature", "shipped_anchors": []}]}
        ),
        encoding="utf-8",
    )
    findings = _run(specs, src)
    stale = [f for f in findings if f.code is BacklogDoctorCode.BL_STALE]
    assert any(f.slug == "shipped-feature" for f in stale), [f.to_dict() for f in findings]


def test_no_archived_ledger_is_a_noop_for_that_condition(tmp_path: Path) -> None:
    specs, src = _build_roots(tmp_path)
    active = _ACTIVE_SUBSECTION.format(
        slug="live-feature",
        title="Live",
        status="candidate",
        intents_block=_intents_block("pkg/m.py#Widget", "still live"),
    )
    _write_backlog_md(specs, active)
    findings = _run(specs, src)
    assert not any(f.code is BacklogDoctorCode.BL_STALE for f in findings), [
        f.to_dict() for f in findings
    ]


# ── A2.8 — an absent BACKLOG.md yields zero findings and exit 0 ─────────────────────


def test_absent_backlog_md_yields_zero_findings(tmp_path: Path) -> None:
    specs, src = _build_roots(tmp_path)
    # No BACKLOG.md written at all.
    findings = _run(specs, src)
    assert findings == [], [f.to_dict() for f in findings]


# ── T-120-08 cutover — run_backlog_doctor (CLI-facing) reads the document model ─────


def _run_wired(specs: Path, src: Path) -> list[Finding]:
    """Drive the CLI-facing :func:`run_backlog_doctor` directly — the live wiring
    proven end to end, not the hand-built ``_run`` helper above."""
    from dadaia_workspace.features.backlog.doctor import run_backlog_doctor

    return run_backlog_doctor(
        specs_dir=specs,
        source_root=src,
        catalog_path=specs / "memory" / "product" / "catalog.json",
        alias_map_path=specs / "no-aliases.txt",
        archive_root=specs / "_archive",
        cli_anchors=frozenset(),
    )


def test_run_backlog_doctor_reads_the_single_source_document(tmp_path: Path) -> None:
    """T-120-08 cutover: the CLI-facing ``run_backlog_doctor`` reads
    ``specs/backlog/BACKLOG.md`` through :func:`document.load_document` — a clean
    document yields zero findings through the wired entry point."""
    specs, src = _build_roots(tmp_path)
    active = _ACTIVE_SUBSECTION.format(
        slug="wired-clean", title="Wired", status="idea", intents_block=""
    )
    _write_backlog_md(specs, active)
    findings = _run_wired(specs, src)
    assert findings == [], [f.to_dict() for f in findings]


def test_run_backlog_doctor_absent_document_is_a_clean_noop(tmp_path: Path) -> None:
    """A2.8 over the wired entry point: no BACKLOG.md ⇒ zero findings, not an error."""
    specs, src = _build_roots(tmp_path)
    findings = _run_wired(specs, src)
    assert findings == [], [f.to_dict() for f in findings]


# ── bug backlog-doctor-silent-on-duplicate-top-level-sections — end-to-end through the
# wired CLI-facing entry point ───────────────────────────────────────────────────────


def test_duplicated_active_and_ledger_sections_fire_bl_schema_and_bl_dup_and_are_never_clean(
    tmp_path: Path,
) -> None:
    """Intent: CONTRACT — bug backlog-doctor-silent-on-duplicate-top-level-sections.

    The exact reported repro through the wired, CLI-facing entry point: a BACKLOG.md
    whose preamble+ACTIVE block was accidentally duplicated (two '## ACTIVE' headings,
    two '## LEDGER' headings, the same slug present in both ACTIVE copies and the same
    slug present in both LEDGER copies). Expected (bug ticket, verbatim): a BL-SCHEMA
    error for each repeated top-level section heading, and a BL-DUP error for the slug
    duplicated in ACTIVE (and in LEDGER) — never a clean report."""
    specs, src = _build_roots(tmp_path)
    text = (
        "## ACTIVE\n\n"
        + _ACTIVE_SUBSECTION.format(slug="dup-item", title="First", status="idea", intents_block="")
        + "\n## LEDGER\n\n"
        + "- old-one · DELIVERED · v0.9.0 · 2026-06-01\n\n"
        + "## ACTIVE\n\n"
        + _ACTIVE_SUBSECTION.format(
            slug="dup-item", title="Second", status="idea", intents_block=""
        )
        + "\n## LEDGER\n\n"
        + "- old-one · DELIVERED · v0.9.0 · 2026-06-01\n"
    )
    (specs / "backlog" / "BACKLOG.md").write_text(text, encoding="utf-8")

    findings = _run_wired(specs, src)
    errors = [f for f in findings if f.severity is Severity.ERROR]
    assert errors, "a duplicated-section BACKLOG.md must never report clean"

    schema_findings = [
        f
        for f in findings
        if f.code is BacklogDoctorCode.BL_SCHEMA
        and "duplicate top-level section heading" in f.message
    ]
    assert len(schema_findings) == 2, [f.to_dict() for f in findings]
    assert any("'ACTIVE'" in f.message for f in schema_findings), [f.to_dict() for f in findings]
    assert any("'LEDGER'" in f.message for f in schema_findings), [f.to_dict() for f in findings]

    dup_findings = [f for f in findings if f.code is BacklogDoctorCode.BL_DUP]
    assert any(
        f.slug == "dup-item" and "more than once in ACTIVE" in f.message for f in dup_findings
    ), [f.to_dict() for f in findings]
    assert any(
        f.slug == "old-one" and "more than once in LEDGER" in f.message for f in dup_findings
    ), [f.to_dict() for f in findings]


# ── A3.5 — a freshly authored subsection is clean under BOTH doctors ────────────────


def test_freshly_authored_subsection_is_clean_under_both_doctors(tmp_path: Path) -> None:
    """A3.5 (R-13, the producer-passes-its-own-validator rule): ``backlog_new``'s
    freshly appended ACTIVE subsection is ``backlog doctor``-clean AND ``specs
    doctor``-clean out of the box — proven over the real writer + both live doctors,
    not fixtures hand-built to match the parser."""
    from dadaia_workspace.features.backlog.document import backlog_new
    from dadaia_workspace.features.specs import SpecsDoctor

    specs, src = _build_roots(tmp_path)
    backlog_new(specs, "fresh-entry")

    findings = _run_wired(specs, src)
    assert findings == [], [f.to_dict() for f in findings]

    issues = SpecsDoctor(specs).check()
    backlog_issues = [i for i in issues if i.code in {"SPEC-DOC-031", "SPEC-DOC-035"}]
    assert backlog_issues == [], [i.to_dict() for i in backlog_issues]


# ── A5.6 — the two doctors agree: never contradict on the same tree (R-13) ─────────


def test_two_doctors_agree_on_clean_and_violation_trees(tmp_path: Path) -> None:
    """A5.6: ``backlog doctor`` and ``specs doctor`` never contradict on the same tree.
    (a) a clean ``BACKLOG.md`` is accepted by both. (b) a planted ACTIVE-schema
    violation is rejected by ``backlog doctor`` (BL-SCHEMA ERROR) while ``specs
    doctor``'s backlog-surface checks (SPEC-DOC-031/035) stay silent on it — nothing
    consumed, no loose file — so neither doctor contradicts the other."""
    from dadaia_workspace.features.specs import SpecsDoctor

    def _backlog_surface_issues(specs: Path) -> list[object]:
        return [i for i in SpecsDoctor(specs).check() if i.code in {"SPEC-DOC-031", "SPEC-DOC-035"}]

    # (a) clean tree — both doctors accept.
    specs_a, src_a = _build_roots(tmp_path / "clean")
    active = _ACTIVE_SUBSECTION.format(
        slug="agree-clean", title="Clean", status="idea", intents_block=""
    )
    _write_backlog_md(specs_a, active)
    assert _run_wired(specs_a, src_a) == []
    assert _backlog_surface_issues(specs_a) == []

    # (b) a planted ACTIVE-schema violation — backlog doctor rejects (ERROR); specs
    # doctor's backlog-surface checks stay silent.
    specs_b, src_b = _build_roots(tmp_path / "violation")
    (specs_b / "backlog" / "BACKLOG.md").write_text(
        "## ACTIVE\n\n### broken\n- **Title:** Broken\n- **Opened:** 2026-08-10\n"
        "- **Description:** missing Status and Provenance.\n\n## LEDGER\n",
        encoding="utf-8",
    )
    findings_b = _run_wired(specs_b, src_b)
    errors = [f for f in findings_b if f.severity is Severity.ERROR]
    assert errors and errors[0].code is BacklogDoctorCode.BL_SCHEMA
    assert _backlog_surface_issues(specs_b) == []
