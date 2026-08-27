"""Integration tests for the BL-SCHEMA/CONFLICT/STALE checks over the single-source
``BACKLOG.md`` document model (SPEC v0.12.0 FR2, ADR D8, PLAN §6, §8; v0.5.0 FR5, A5.2).

Intent: CONTRACT — v0.12.0 A2.1-A2.4, A2.6-A2.8, A3.5, A5.6; v0.5.0 A5.2, A5.5-adjacent

**BL-DUP is DELETED (v0.5.0 A5.2), not disabled** — see ``dadaia_workspace.features.
backlog.doctor``'s module docstring for the structural argument (a duplicate exit is
impossible once ``BACKLOG.md`` holds only ``## ACTIVE`` and every exit lands as one
append-only, slug-keyed ``backlog_histo.jsonl`` record). The two BL-DUP-subject tests
this file used to carry — ``test_duplicate_slug_in_active_fires_bl_dup``
(same-slug-twice-in-ACTIVE) and ``test_same_anchor_same_change_fires_bl_dup_pairwise``
(classifier ``DUPLICATE`` verdict) — are deleted with their subject (qa-engineer
test-minimization verdict, ``specs/releases/0.5.0/reviews/
qa-engineer-test-minimization-review.md:221``: "BL-DUP rule + tests — structurally
impossible, deleted not disabled"), replaced by BL-STALE's new histo-backed condition
(``test_active_slug_with_histo_record_fires_bl_stale`` /
``test_no_histo_store_supplied_is_a_noop_for_that_condition``) and a BL-SCHEMA-only
version of the duplicate-top-level-heading regression this file also carried.

The three BL-* checks are exercised by a **single parameterized** test (one fixture
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
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest

from dadaia_workspace.core.models.backlog import BacklogHistoRecord
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


class _FakeHistoStore:
    """A minimal in-memory double satisfying
    :class:`~dadaia_workspace.core.protocols.record_store.RecordStore` for
    :class:`BacklogHistoRecord` — a fake, not a mock, per this workspace's own
    test-authoring convention (internal Protocol dependency)."""

    def __init__(self, records: list[BacklogHistoRecord] | None = None) -> None:
        self._records = list(records or [])

    @property
    def path(self) -> Path:
        return Path("fake-backlog-histo.jsonl")

    def append(self, record: BacklogHistoRecord) -> None:
        self._records.append(record)

    def iter_records(self) -> Iterator[BacklogHistoRecord]:
        return iter(self._records)

    def update(
        self, record_id: str, mutate: Callable[[BacklogHistoRecord], BacklogHistoRecord]
    ) -> BacklogHistoRecord:
        raise NotImplementedError


def _histo_record(slug: str, *, disposition: str = "DELIVERED") -> BacklogHistoRecord:
    return BacklogHistoRecord(
        id=slug,
        ts="2026-08-01",
        disposition=disposition,
        reason=None,
        release="v0.11.0",
        by="test-suite",
        entry_md=None,
        entry_md_source=None,
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


def _write_backlog_md(specs: Path, active_body: str) -> None:
    text = f"## ACTIVE\n\n{active_body}"
    (specs / "backlog" / "BACKLOG.md").write_text(text, encoding="utf-8")


def _run(
    specs: Path,
    src: Path,
    archive_root: Path | None = None,
    histo_store: _FakeHistoStore | None = None,
) -> list[Finding]:
    document = load_document(specs / "backlog")
    registry = build_registry(
        source_root=src,
        catalog_path=specs / "memory" / "product" / "catalog.json",
        alias_map_path=specs / "no-aliases.txt",
        specs_dir=specs,
        cli_anchors=frozenset(),
    )
    consumed = read_consumed(archive_root if archive_root is not None else specs / "_archive")
    histo_slugs = (
        frozenset(record.id for record in histo_store.iter_records())
        if histo_store is not None
        else frozenset()
    )
    ctx = DoctorContext(
        items=list(document.active),
        registry=registry,
        consumed=consumed,
        histo_slugs=histo_slugs,
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


# ── v0.5.0 A5.2 — divergent anchors still fire BL-CONFLICT (BL-DUP retired) ─────────


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


def test_bl_dup_code_no_longer_exists(tmp_path: Path) -> None:
    """A5.2, proven negatively: the exact same-anchor+same-change fixture that used to
    fire BL-DUP now fires NOTHING — the check code is gone, not silenced (the
    classifier's own ``DUPLICATE`` verdict is unchanged, ``classifier.py`` is out of
    this task's write set; this doctor simply never asks for it any more)."""
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
    assert "BL-DUP" not in {f.code.value for f in findings}, [f.to_dict() for f in findings]
    assert not hasattr(BacklogDoctorCode, "BL_DUP")


# ── A2.6/v0.5.0 A5.2 — an ACTIVE item whose slug already has a histo record fires
# BL-STALE (the retired in-document LEDGER condition's replacement) ─────────────────


def test_active_slug_with_histo_record_fires_bl_stale(tmp_path: Path) -> None:
    specs, src = _build_roots(tmp_path)
    active = _ACTIVE_SUBSECTION.format(
        slug="shipped-but-still-active",
        title="Shipped",
        status="candidate",
        intents_block=_intents_block("pkg/m.py#Widget", "already shipped"),
    )
    _write_backlog_md(specs, active)
    store = _FakeHistoStore([_histo_record("shipped-but-still-active")])
    findings = _run(specs, src, histo_store=store)
    stale = [f for f in findings if f.code is BacklogDoctorCode.BL_STALE]
    assert any(f.slug == "shipped-but-still-active" for f in stale), [f.to_dict() for f in findings]
    assert any("backlog_histo.jsonl" in f.message for f in stale)


def test_no_histo_store_supplied_is_a_noop_for_that_condition(tmp_path: Path) -> None:
    """No ``histo_store`` (the CLI-unwired default) degrades to a no-op — mirrors
    ``read_consumed``'s absent-ledger no-op, never a false ERROR."""
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
        slug="live-feature-2",
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


def test_run_backlog_doctor_default_histo_store_is_a_noop(tmp_path: Path) -> None:
    """``run_backlog_doctor``'s ``histo_store`` parameter defaults to ``None`` — the
    live CLI callsite (unmodified by this task, out of its write set) stays a clean
    no-op for the histo BL-STALE condition until it is wired, exactly like the
    pre-existing ``consumed_backlog.json`` no-op behaviour."""
    specs, src = _build_roots(tmp_path)
    active = _ACTIVE_SUBSECTION.format(
        slug="terminal-status-only",
        title="Terminal by its own Status",
        status="DELIVERED",
        intents_block=_intents_block("pkg/m.py#Widget", "shipped"),
    )
    _write_backlog_md(specs, active)
    findings = _run_wired(specs, src)
    # Condition (c) — own terminal Status — still fires with no histo_store at all.
    stale = [f for f in findings if f.code is BacklogDoctorCode.BL_STALE]
    assert any(f.slug == "terminal-status-only" for f in stale), [f.to_dict() for f in findings]


# ── bug backlog-doctor-silent-on-duplicate-top-level-sections — end-to-end through the
# wired CLI-facing entry point (v0.5.0 A5.2: BL-SCHEMA only now, BL-DUP retired) ────


def test_duplicated_active_sections_fire_bl_schema_and_are_never_clean(
    tmp_path: Path,
) -> None:
    """Intent: CONTRACT — bug backlog-doctor-silent-on-duplicate-top-level-sections.

    The exact reported repro through the wired, CLI-facing entry point, adjusted for
    the single-section document (v0.5.0 A5.2 — the fixture's duplicated ``## LEDGER``
    half retired with the section itself): two ``## ACTIVE`` headings, the same slug
    present in both copies. Expected: one BL-SCHEMA error for the repeated heading —
    never a clean report."""
    specs, src = _build_roots(tmp_path)
    text = (
        "## ACTIVE\n\n"
        + _ACTIVE_SUBSECTION.format(slug="dup-item", title="First", status="idea", intents_block="")
        + "\n## ACTIVE\n\n"
        + _ACTIVE_SUBSECTION.format(
            slug="dup-item", title="Second", status="idea", intents_block=""
        )
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
    assert len(schema_findings) == 1, [f.to_dict() for f in findings]
    assert "'ACTIVE'" in schema_findings[0].message


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
        "- **Description:** missing Status and Provenance.\n",
        encoding="utf-8",
    )
    findings_b = _run_wired(specs_b, src_b)
    errors = [f for f in findings_b if f.severity is Severity.ERROR]
    assert errors and errors[0].code is BacklogDoctorCode.BL_SCHEMA
    assert _backlog_surface_issues(specs_b) == []
