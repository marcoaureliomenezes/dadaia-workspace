"""Unit tests for SpecsDoctor ledger invariants + identity-coherence backstop.

Release v0.1.10 / T-010-14 (R6b). Ledger invariants plus a lease<->session coherence
backstop, each with an ERROR/WARNING code following the SPEC-DOC-NNN convention:

- SPEC-DOC-024 — phase<->markers coherence (ACTIVE.md phase vs TASKS markers).
- SPEC-DOC-006 (extended) — CLOSURE-before-archive, recursive into nested archive dirs.
- SPEC-DOC-026 — unique release ids across releases/ u _archive/releases/ (recursive),
  WARN for documented legacy nested dirs.
- SPEC-DOC-027 — naming canon ``^v\\d+\\.\\d+\\.\\d+$`` for release dirs, legacy WARN
  (ADR-9 permanent allowlist, forward-enforced).
- SPEC-DOC-028 — constitution file-ref resolution (WARN on a missing repo file).
- SPEC-DOC-029 — lease<->session coherence backstop, CRITICAL: the ADR-11/B3 three-state
  triage (stale-dead WARN / live-incoherent ERROR forgery / coherent silent).
- SPEC-DOC-030 — specs/audits/ naming canon.
- SPEC-DOC-031 — consumed-backlog disposition drift.
- SPEC-DOC-032 — bug status-token canon.

CRITICAL: DOC-029's live-incoherent ERROR (forgery wording) and the composed
stale-pidless-plus-fresh-READ-bind B3 repro are kept verbatim — the severity split
(live-ERROR vs stale-WARN) is the operator contract this invariant exists to protect,
and the composition-root pid-probe seam test is kept as a named architectural guard.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from dadaia_workspace.features.spec_context import session_identity
from dadaia_workspace.features.specs import Severity, SpecsDoctor, SpecsDoctorIssue

MINIMAL_MEMORY_PRODUCT_INDEX_MD = """\
---
slug: index
title: Product Index
category: product
tldr: 'Product catalog entry point.'
summary: 'Product catalog entry point.'
tags: []
agent_tier: self-pull
token_estimate: 20
last_updated: '2026-06-01'
release_origin: test-release
---

## Catalog

Feature atoms.
"""

MINIMAL_MEMORY_ATOM_MD = """\
---
slug: {slug}
title: {title}
category: core
tldr: 'tldr.'
summary: 'summary.'
tags: []
agent_tier: self-pull
token_estimate: 20
last_updated: '2026-06-01'
release_origin: test-release
---

## Heading

Body.
"""

_CLOSURE_MD = """\
# Closure

## Summary
Done.

## Validations
| Check | Command | Result |
|---|---|---|
| pytest | pytest | green |

## Drifts
None.

## Memory updates
None.
"""

_FORGERY_TOKEN = "forgery"
_STALE_REMEDIATION_TOKENS = ("dadaia doctor --fix", "dadaia lock steal")

_DOCTOR_MODULE_NAMES = (
    "doctor",
    "doctor_types",
    "doctor_common",
    "doctor_structural",
    "doctor_memory",
    "doctor_release",
    "doctor_closure_audit",
    "doctor_governance",
    "doctor_coherence",
)


@pytest.fixture(autouse=True)
def _skip_memory_lint_subprocess(monkeypatch: pytest.MonkeyPatch) -> None:
    """v0.1.55 FR1: LINT-1 moved off the coordinator into ``doctor_memory.MemoryValidator``."""
    from dadaia_workspace.features.specs.doctor_memory import MemoryValidator

    monkeypatch.setattr(MemoryValidator, "check_lint1_memory_atoms", lambda self: [])


def _make_clean_specs_tree(root: Path, release_id: str = "v0.1.10") -> Path:
    """A minimal but ledger-valid specs/ tree."""
    specs = root / "specs"
    (specs / "memory" / "product").mkdir(parents=True)
    (specs / "releases" / release_id).mkdir(parents=True)
    (specs / "_archive" / "releases").mkdir(parents=True)
    (specs / "backlog").mkdir(parents=True)

    (specs / "constitution.md").write_text("# Constitution\n\nThe laws.\n", encoding="utf-8")
    (specs / "memory" / "product" / "index.md").write_text(
        MINIMAL_MEMORY_PRODUCT_INDEX_MD, encoding="utf-8"
    )
    for slug, title in (
        ("architecture", "Architecture"),
        ("tech-stack", "Tech Stack"),
        ("quality-assurance", "Quality Assurance"),
    ):
        (specs / "memory" / f"{slug}.md").write_text(
            MINIMAL_MEMORY_ATOM_MD.format(slug=slug, title=title), encoding="utf-8"
        )

    (specs / "releases" / "ACTIVE.md").write_text(
        f"release: {release_id}\nphase: IMPLEMENTATION\n", encoding="utf-8"
    )
    spec_md = "# Spec\n\n> **Status:** Aprovado\n> **Created:** 2026-06-09\n\nContent.\n"
    plan_md = "# Plan\n\n> **Status:** Aprovado\n\nShort.\n"
    tasks_md = "# Tasks\n\n> **Status:** Aprovado\n\n- [-] T1 something\n- [ ] T2 other\n"
    (specs / "releases" / release_id / "SPEC.md").write_text(spec_md, encoding="utf-8")
    (specs / "releases" / release_id / "PLAN.md").write_text(plan_md, encoding="utf-8")
    (specs / "releases" / release_id / "TASKS.md").write_text(tasks_md, encoding="utf-8")
    return specs


def _set_active(specs: Path, release_id: str, phase: str) -> None:
    (specs / "releases" / "ACTIVE.md").write_text(
        f"release: {release_id}\nphase: {phase}\n", encoding="utf-8"
    )


def _write_tasks(specs: Path, release_id: str, body: str) -> None:
    (specs / "releases" / release_id / "TASKS.md").write_text(
        f"# Tasks\n\n> **Status:** Aprovado\n\n{body}\n", encoding="utf-8"
    )


def _codes(issues: list[SpecsDoctorIssue]) -> set[str]:
    return {i.code for i in issues}


def _by_code(issues: list[SpecsDoctorIssue], code: str) -> list[SpecsDoctorIssue]:
    return [i for i in issues if i.code == code]


def _write_backlog_entry(specs: Path, slug: str, status_line: str) -> None:
    (specs / "backlog").mkdir(parents=True, exist_ok=True)
    (specs / "backlog" / f"{slug}.md").write_text(
        f"# {slug}\n\n**Status:** {status_line}\n\nBody.\n", encoding="utf-8"
    )


def _write_archived_closure(specs: Path, release_id: str, body: str) -> None:
    rel = specs / "_archive" / "releases" / release_id
    rel.mkdir(parents=True, exist_ok=True)
    (rel / "CLOSURE.md").write_text(body, encoding="utf-8")


def _write_bug(specs: Path, slug: str, status: str, extra: str = "") -> None:
    (specs / "bugs").mkdir(parents=True, exist_ok=True)
    (specs / "bugs" / f"{slug}.md").write_text(
        f"---\nname: {slug}\nstatus: {status}\nsession_id: null\n{extra}---\n\n**Symptom:** x.\n",
        encoding="utf-8",
    )


def _strip_pid_from_lock_record(state_dir: Path, ctx: str) -> None:
    """Reduce the genuine ``<ctx>.lock.json`` to the legacy pre-``pid`` record shape."""
    import json

    record_path = state_dir / "states" / "ctx_locks" / f"{ctx}.lock.json"
    data = json.loads(record_path.read_text(encoding="utf-8"))
    data.pop("pid", None)
    record_path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _seed_lock_record(
    workspace: Path,
    ctx: str,
    session_id: str,
    *,
    clock: object = None,
    pid: int = 4242,
) -> None:
    """Plant a raw ``<ctx>.lock.json`` — v0.1.76 T-3 successor to ``lease.acquire``.

    ``lease.acquire`` is DELETED (the acquisition/CAS machinery it belonged to is gone);
    this doctor-coherence backstop diagnoses whatever residual record exists on disk, so
    seeding one directly (matching the schema ``acquire`` used to write) is the faithful
    fixture successor — the coherence check itself is unaffected by how the record landed.
    """
    import json
    from datetime import UTC, datetime

    now = (clock() if callable(clock) else datetime.now(tz=UTC)).isoformat()
    lock_dir = workspace / ".dadaia" / "states" / "ctx_locks"
    lock_dir.mkdir(parents=True, exist_ok=True)
    record = {
        "context": ctx,
        "release": "rel-1",
        "session_id": session_id,
        "mode": "IMPLEMENTATION",
        "pid": pid,
        "acquired_at": now,
        "heartbeat": now,
        "ttl": 120,
    }
    (lock_dir / f"{ctx}.lock.json").write_text(json.dumps(record, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# Sad matrix: each broken fixture fires its code (DOC-024/006/026/027/028/030/031/032)
# ---------------------------------------------------------------------------


def test_sad_matrix(tmp_path: Path) -> None:
    # DOC-024: phase=SPEC but TASKS are an [x]-majority (the live audit incident).
    specs_a = _make_clean_specs_tree(tmp_path)
    _set_active(specs_a, "v0.1.10", "SPEC")
    _write_tasks(specs_a, "v0.1.10", "- [x] T1 done\n- [x] T2 done\n- [ ] T3 open\n")
    assert "SPEC-DOC-024" in _codes(SpecsDoctor(specs_a).check())

    # DOC-024: phase=CLOSURE but a non-[x] task remains.
    specs_b = _make_clean_specs_tree(tmp_path.parent / (tmp_path.name + "-024b"))
    _set_active(specs_b, "v0.1.10", "CLOSURE")
    _write_tasks(specs_b, "v0.1.10", "- [x] T1 done\n- [-] T2 in-progress\n")
    assert "SPEC-DOC-024" in _codes(SpecsDoctor(specs_b).check())

    # DOC-006 (extended, recursive): nested archived release dir with no CLOSURE.md.
    specs_c = _make_clean_specs_tree(tmp_path.parent / (tmp_path.name + "-006"))
    nested = specs_c / "_archive" / "releases" / "v0.2.0" / "milestone-1"
    nested.mkdir(parents=True)
    (nested / "SPEC.md").write_text("# Spec\n\n> **Status:** Aprovado\n", encoding="utf-8")
    (nested / "TASKS.md").write_text("# Tasks\n\n> **Status:** Aprovado\n", encoding="utf-8")
    (specs_c / "_archive" / "releases" / "v0.2.0" / "CLOSURE.md").write_text(
        _CLOSURE_MD, encoding="utf-8"
    )
    doc006 = _by_code(SpecsDoctor(specs_c).check(), "SPEC-DOC-006")
    assert any("milestone-1" in (i.path or "") for i in doc006)

    # DOC-026: duplicate release id across releases/ and _archive/releases/ -> ERROR.
    specs_d = _make_clean_specs_tree(tmp_path.parent / (tmp_path.name + "-026"))
    dup = specs_d / "_archive" / "releases" / "v0.1.10"
    dup.mkdir(parents=True)
    (dup / "CLOSURE.md").write_text(_CLOSURE_MD, encoding="utf-8")
    doc026 = _by_code(SpecsDoctor(specs_d).check(), "SPEC-DOC-026")
    assert any(i.severity == Severity.ERROR for i in doc026)

    # DOC-027: non-SemVer active release dir -> ERROR.
    specs_e = _make_clean_specs_tree(
        tmp_path.parent / (tmp_path.name + "-027"), release_id="my-feature-v1"
    )
    doc027 = _by_code(SpecsDoctor(specs_e).check(), "SPEC-DOC-027")
    assert any(i.severity == Severity.ERROR for i in doc027)

    # DOC-028: dangling constitution file ref -> WARNING.
    specs_f = _make_clean_specs_tree(tmp_path.parent / (tmp_path.name + "-028"))
    (specs_f / "constitution.md").write_text(
        "# Constitution\n\nSee `does/not/exist.py` for details.\n", encoding="utf-8"
    )
    doc028 = _by_code(SpecsDoctor(specs_f, repo_root=specs_f.parent).check(), "SPEC-DOC-028")
    assert doc028 and all(i.severity == Severity.WARNING for i in doc028)

    # DOC-030: non-conforming new audit dir -> WARNING.
    specs_g = _make_clean_specs_tree(tmp_path.parent / (tmp_path.name + "-030"))
    (specs_g / "audits" / "2026-07-01T000000Z").mkdir(parents=True)
    doc030 = _by_code(SpecsDoctor(specs_g).check(), "SPEC-DOC-030")
    assert doc030 and all(i.severity == Severity.WARNING for i in doc030)

    # DOC-031: non-terminal backlog referenced in an archived CLOSURE -> WARNING with
    # the reconciled BL-SCHEMA remediation text (bare terminal token, not "TOKEN — vX.Y.Z").
    specs_h = _make_clean_specs_tree(tmp_path.parent / (tmp_path.name + "-031"))
    _write_backlog_entry(specs_h, "feat-consumed-thing", "PICKED — blocked on operator grill")
    _write_archived_closure(
        specs_h,
        "v0.0.9",
        "# Closure\n\n## Bug dispositions\n\n"
        "Source: `specs/backlog/feat-consumed-thing.md` — delivered, accepted.\n",
    )
    doc031 = _by_code(SpecsDoctor(specs_h).check(), "SPEC-DOC-031")
    assert doc031 and all(i.severity == Severity.WARNING for i in doc031)
    text031 = " ".join(i.description for i in doc031)
    assert "feat-consumed-thing" in text031 and "v0.0.9" in text031
    assert "status: delivered" in text031
    assert "delivered_in" in text031
    assert "_archive" in text031
    assert "BL-SCHEMA" in text031 and "Do NOT" in text031

    # DOC-032: legacy non-canonical bug status -> WARNING.
    specs_i = _make_clean_specs_tree(tmp_path.parent / (tmp_path.name + "-032"))
    _write_bug(specs_i, "some-old-bug", "Fixed")
    doc032 = _by_code(SpecsDoctor(specs_i).check(), "SPEC-DOC-032")
    assert doc032 and all(i.severity == Severity.WARNING for i in doc032)
    assert "Fixed" in " ".join(i.description for i in doc032)


# ---------------------------------------------------------------------------
# Silent matrix: coherent/terminal/allowlisted/grandfathered/skipped aggregates
# ---------------------------------------------------------------------------


def test_silent_matrix(tmp_path: Path) -> None:
    # DOC-024: coherent phase/markers.
    specs_a = _make_clean_specs_tree(tmp_path)
    assert "SPEC-DOC-024" not in _codes(SpecsDoctor(specs_a).check())
    specs_a2 = _make_clean_specs_tree(tmp_path.parent / (tmp_path.name + "-024ok"))
    _set_active(specs_a2, "v0.1.10", "CLOSURE")
    _write_tasks(specs_a2, "v0.1.10", "- [x] T1 done\n- [x] T2 done\n")
    assert "SPEC-DOC-024" not in _codes(SpecsDoctor(specs_a2).check())

    # DOC-006: properly closed archived release -> silent.
    specs_c = _make_clean_specs_tree(tmp_path.parent / (tmp_path.name + "-006ok"))
    arch_c = specs_c / "_archive" / "releases" / "v0.0.9"
    arch_c.mkdir(parents=True)
    (arch_c / "CLOSURE.md").write_text(_CLOSURE_MD, encoding="utf-8")
    assert "SPEC-DOC-006" not in _codes(SpecsDoctor(specs_c).check())

    # DOC-026: distinct release ids -> silent.
    specs_d = _make_clean_specs_tree(tmp_path.parent / (tmp_path.name + "-026ok"))
    arch_d = specs_d / "_archive" / "releases" / "v0.1.9"
    arch_d.mkdir(parents=True)
    (arch_d / "CLOSURE.md").write_text(_CLOSURE_MD, encoding="utf-8")
    assert "SPEC-DOC-026" not in _codes(SpecsDoctor(specs_d).check())

    # DOC-027: SemVer-clean dirs -> silent; allowlisted legacy names -> silent.
    specs_e = _make_clean_specs_tree(tmp_path.parent / (tmp_path.name + "-027ok"))
    arch_e = specs_e / "_archive" / "releases" / "v0.1.9"
    arch_e.mkdir(parents=True)
    (arch_e / "CLOSURE.md").write_text(_CLOSURE_MD, encoding="utf-8")
    assert "SPEC-DOC-027" not in _codes(SpecsDoctor(specs_e).check())

    # DOC-028: resolvable ref + no-repo-root no-op -> silent.
    specs_f1 = _make_clean_specs_tree(tmp_path.parent / (tmp_path.name + "-028ok"))
    (specs_f1.parent / "real_file.py").write_text("# ok\n", encoding="utf-8")
    (specs_f1 / "constitution.md").write_text(
        "# Constitution\n\nSee `real_file.py` for details.\n", encoding="utf-8"
    )
    assert "SPEC-DOC-028" not in _codes(SpecsDoctor(specs_f1, repo_root=specs_f1.parent).check())
    specs_f2 = _make_clean_specs_tree(tmp_path.parent / (tmp_path.name + "-028noop"))
    (specs_f2 / "constitution.md").write_text(
        "# Constitution\n\nSee `does/not/exist.py`.\n", encoding="utf-8"
    )
    assert "SPEC-DOC-028" not in _codes(SpecsDoctor(specs_f2).check())  # no repo_root

    # DOC-030: canonical/grandfathered dirs + absent audits/ -> silent.
    specs_g1 = _make_clean_specs_tree(tmp_path.parent / (tmp_path.name + "-030ok"))
    (specs_g1 / "audits" / "20260701T000000Z-abcd1234").mkdir(parents=True)
    assert "SPEC-DOC-030" not in _codes(SpecsDoctor(specs_g1).check())
    specs_g2 = _make_clean_specs_tree(tmp_path.parent / (tmp_path.name + "-030gf"))
    for name in (
        "2026-06-09T075056Z",
        "2026-06-10T010550Z",
        "2026-06-10T052944Z",
        "2026-06-10T140553Z",
        "_archive",
    ):
        (specs_g2 / "audits" / name).mkdir(parents=True)
    assert "SPEC-DOC-030" not in _codes(SpecsDoctor(specs_g2).check())
    specs_g3 = _make_clean_specs_tree(tmp_path.parent / (tmp_path.name + "-030absent"))
    assert not (specs_g3 / "audits").exists()
    assert "SPEC-DOC-030" not in _codes(SpecsDoctor(specs_g3).check())

    # DOC-031: legitimate return (Backlog returns section), terminal-and-referenced,
    # never-referenced-open, and aggregate files skipped -> all silent.
    specs_h1 = _make_clean_specs_tree(tmp_path.parent / (tmp_path.name + "-031returns"))
    _write_backlog_entry(specs_h1, "newly-returned-item", "CANDIDATE — not picked")
    _write_archived_closure(
        specs_h1,
        "v0.0.7",
        "# Closure\n\n## Backlog returns\n\n"
        "- `specs/backlog/newly-returned-item.md` ← registered for a future release.\n",
    )
    assert "SPEC-DOC-031" not in _codes(SpecsDoctor(specs_h1).check())

    specs_h2 = _make_clean_specs_tree(tmp_path.parent / (tmp_path.name + "-031terminal"))
    _write_backlog_entry(specs_h2, "shipped-thing", "DELIVERED — v0.0.9 (see CLOSURE)")
    _write_archived_closure(
        specs_h2,
        "v0.0.9",
        "# Closure\n\n## Dispositions\n\nSource: `specs/backlog/shipped-thing.md` delivered.\n",
    )
    assert "SPEC-DOC-031" not in _codes(SpecsDoctor(specs_h2).check())

    specs_h3 = _make_clean_specs_tree(tmp_path.parent / (tmp_path.name + "-031open"))
    _write_backlog_entry(specs_h3, "brand-new-idea", "OPEN — never picked")
    _write_archived_closure(specs_h3, "v0.0.9", "# Closure\n\nUnrelated content.\n")
    assert "SPEC-DOC-031" not in _codes(SpecsDoctor(specs_h3).check())

    specs_h4 = _make_clean_specs_tree(tmp_path.parent / (tmp_path.name + "-031aggregate"))
    (specs_h4 / "backlog" / "candidates.md").write_text(
        "## Candidatas ativas\n\n- thing — x (owner: a, contexto: b)\n", encoding="utf-8"
    )
    _write_archived_closure(specs_h4, "v0.0.9", "# Closure\n\nReferences candidates here.\n")
    assert "SPEC-DOC-031" not in _codes(SpecsDoctor(specs_h4).check())

    # DOC-032: canonical statuses (case-insensitive), README skip, absent bugs/ dir,
    # and the live-tree superseded_by fix shape -> all silent.
    for idx, status in enumerate(("Open", "Closed", "open", "closed", "CLOSED")):
        # Dir name carries an index, not the status: case-variant statuses collide
        # on the case-insensitive filesystems of the macOS/Windows CI runners.
        specs_i = _make_clean_specs_tree(tmp_path.parent / (tmp_path.name + f"-032-{idx}"))
        _write_bug(specs_i, "well-formed-bug", status)
        assert "SPEC-DOC-032" not in _codes(SpecsDoctor(specs_i).check())
    specs_i2 = _make_clean_specs_tree(tmp_path.parent / (tmp_path.name + "-032readme"))
    (specs_i2 / "bugs").mkdir(parents=True, exist_ok=True)
    (specs_i2 / "bugs" / "README.md").write_text("# Bugs\n\nstatus: whatever\n", encoding="utf-8")
    assert "SPEC-DOC-032" not in _codes(SpecsDoctor(specs_i2).check())
    specs_i3 = _make_clean_specs_tree(tmp_path.parent / (tmp_path.name + "-032dup"))
    _write_bug(
        specs_i3,
        "duplicate-bug",
        "Closed",
        extra="superseded_by: canonical-bug\nrejected_reason: marked duplicate\n",
    )
    assert "SPEC-DOC-032" not in _codes(SpecsDoctor(specs_i3).check())


# ---------------------------------------------------------------------------
# DOC-026/027 legacy-nested + allowlist forward-enforcement — 1 combined test
# ---------------------------------------------------------------------------


def test_legacy_nested_and_allowlist_forward_enforcement(tmp_path: Path) -> None:
    # DOC-026: legacy nested milestone collision -> WARNING (never ERROR).
    specs_a = _make_clean_specs_tree(tmp_path)
    real = specs_a / "_archive" / "releases" / "v0.1.9"
    real.mkdir(parents=True)
    (real / "CLOSURE.md").write_text(_CLOSURE_MD, encoding="utf-8")
    nested = specs_a / "_archive" / "releases" / "v0.2.0" / "v0.1.9"
    nested.mkdir(parents=True)
    (nested / "SPEC.md").write_text("# Spec\n\n> **Status:** Aprovado\n", encoding="utf-8")
    (specs_a / "_archive" / "releases" / "v0.2.0" / "CLOSURE.md").write_text(
        _CLOSURE_MD, encoding="utf-8"
    )
    doc026 = _by_code(SpecsDoctor(specs_a).check(), "SPEC-DOC-026")
    assert doc026 and all(i.severity == Severity.WARNING for i in doc026)

    # DOC-027: unlisted legacy archive dir -> WARNING.
    specs_b = _make_clean_specs_tree(tmp_path.parent / (tmp_path.name + "-027unlisted"))
    legacy = specs_b / "_archive" / "releases" / "some-unlisted-legacy-name-v1"
    legacy.mkdir(parents=True)
    (legacy / "CLOSURE.md").write_text(_CLOSURE_MD, encoding="utf-8")
    doc027_unlisted = _by_code(SpecsDoctor(specs_b).check(), "SPEC-DOC-027")
    assert doc027_unlisted and all(i.severity == Severity.WARNING for i in doc027_unlisted)

    # DOC-027: every enumerated ADR-9 allowlisted legacy dir -> silent.
    specs_c = _make_clean_specs_tree(tmp_path.parent / (tmp_path.name + "-027allowlisted"))
    for allowlisted_name in (
        "ctx-inject-v2-drift-fix-v1",
        "memory-markdown-source-v1",
        "v0.1.4.1",
        "v0.1.4.2",
        "v0.1.4.3",
        "v0.1.4.3-report-retention",
        "v0.1.4.4",
        "v0.1.4.5",
        "v0.1.4.6",
    ):
        legacy_c = specs_c / "_archive" / "releases" / allowlisted_name
        legacy_c.mkdir(parents=True)
        (legacy_c / "CLOSURE.md").write_text(_CLOSURE_MD, encoding="utf-8")
    assert "SPEC-DOC-027" not in _codes(SpecsDoctor(specs_c).check())

    # DOC-027: forward enforcement — a NEW non-canon dir still WARNs alongside an
    # allowlisted one; the allowlist NEVER silences the live releases/ tree.
    specs_d = _make_clean_specs_tree(tmp_path.parent / (tmp_path.name + "-027forward"))
    allowed = specs_d / "_archive" / "releases" / "v0.1.4.6"
    allowed.mkdir(parents=True)
    (allowed / "CLOSURE.md").write_text(_CLOSURE_MD, encoding="utf-8")
    bad = specs_d / "_archive" / "releases" / "brand-new-non-canon-dir"
    bad.mkdir(parents=True)
    (bad / "CLOSURE.md").write_text(_CLOSURE_MD, encoding="utf-8")
    doc027_forward = _by_code(SpecsDoctor(specs_d).check(), "SPEC-DOC-027")
    assert any("brand-new-non-canon-dir" in (i.path or "") for i in doc027_forward)
    assert not any("v0.1.4.6" in (i.path or "") for i in doc027_forward)

    specs_e = _make_clean_specs_tree(
        tmp_path.parent / (tmp_path.name + "-027live"), release_id="v0.1.4.6"
    )
    doc027_live = _by_code(SpecsDoctor(specs_e).check(), "SPEC-DOC-027")
    assert any(i.severity == Severity.ERROR for i in doc027_live)


# ---------------------------------------------------------------------------
# DOC-029 three-state triage — CRITICAL. Kept named: live-incoherent ERROR w/
# forgery wording, the composed stale-pidless+fresh-READ-bind B3 repro, and the
# composition-root pid-probe seam guard. Remaining states (basic incoherent,
# coherent, noop-without-state-dir, coherent-live) merged into one param.
# ---------------------------------------------------------------------------


def test_live_incoherent_lease_reports_doc_029_error_with_forgery_wording(
    tmp_path: Path,
) -> None:
    """A LIVE lock holder whose identity genuinely diverges from the incumbent ptr /
    session record => ERR with forgery wording (the only state where it is permitted)."""
    specs = _make_clean_specs_tree(tmp_path)
    state_dir = tmp_path / ".dadaia"
    ctx = "ctx-live"

    _seed_lock_record(tmp_path, ctx, "sessForgedLive")
    session_identity.set_incumbent(tmp_path, ctx, "sessOther")
    session_identity.write_session(tmp_path, "sessOther", {"session_id": "sessOther"})

    issues = SpecsDoctor(
        specs,
        workspace_state_dir=state_dir,
        pid_probe=lambda _pid: True,  # the holder is genuinely alive
    ).check()
    doc_029 = _by_code(issues, "SPEC-DOC-029")
    assert doc_029, [i.to_dict() for i in issues]
    assert all(i.severity == Severity.ERROR for i in doc_029)
    text = " ".join(i.description for i in doc_029).lower()
    assert _FORGERY_TOKEN in text, text


def test_stale_pidless_lease_with_fresh_read_bind_warns_not_err(tmp_path: Path) -> None:
    """Named composed integration test (AC-W1-03 / bug B3 repro steps 1-4, end-to-end).

    A residual lease record ~36h old (heartbeat far past TTL) is planted directly, reduced
    to the legacy pid-LESS shape, a new session runs a READ bind (incumbent ptr + session
    record re-point), then doctor runs. Expected: WARN (never ERR), naming the reclaim
    command, NO forgery wording.
    """
    specs = _make_clean_specs_tree(tmp_path)
    state_dir = tmp_path / ".dadaia"
    ctx = "consumer-ctx"

    stale_clock = lambda: datetime.now(tz=UTC) - timedelta(hours=36)  # noqa: E731
    _seed_lock_record(tmp_path, ctx, "sessDead", clock=stale_clock)
    _strip_pid_from_lock_record(state_dir, ctx)

    session_identity.set_incumbent(tmp_path, ctx, "sessFreshRead")
    session_identity.write_session(
        tmp_path, "sessFreshRead", {"session_id": "sessFreshRead", "mode": "read"}
    )

    issues = SpecsDoctor(specs, workspace_state_dir=state_dir).check()

    doc_029 = _by_code(issues, "SPEC-DOC-029")
    assert doc_029, [i.to_dict() for i in issues]
    assert all(i.severity == Severity.WARNING for i in doc_029)
    text = " ".join(i.description for i in doc_029)
    assert any(tok in text for tok in _STALE_REMEDIATION_TOKENS), text
    full_output = " ".join(i.description for i in issues)
    assert _FORGERY_TOKEN not in full_output.lower(), full_output
    assert all(i.severity != Severity.ERROR for i in doc_029)


def test_doctor_pid_probe_seam_is_composition_root_wired_not_feature_import() -> None:
    """The doctor pid-probe seam is an injected ``__init__`` parameter (composition-root
    wired, like ``workspace_state_dir``) — ``features/specs/doctor.py`` must NOT import the
    infrastructure process-probe adapter directly (import-linter / ADR layering law)."""
    import importlib
    import inspect

    sig = inspect.signature(SpecsDoctor.__init__)
    assert "pid_probe" in sig.parameters, "SpecsDoctor must accept an injected pid_probe seam"

    for name in _DOCTOR_MODULE_NAMES:
        mod = importlib.import_module(f"dadaia_workspace.features.specs.{name}")
        src = inspect.getsource(mod)
        assert "process_probe_adapter" not in src, (
            f"{mod.__name__} must not import the infrastructure process-probe adapter; "
            "the probe is composition-root-wired via the pid_probe parameter."
        )


def test_doc029_remaining_states_matrix(tmp_path: Path) -> None:
    """Basic incoherent (via a planted lock record), coherent, no-op-without-state-dir,
    and coherent-live states — the rest of the DOC-029 state space."""
    # Basic incoherent: lock-holder S1 vs incumbent/session S2 -> ERROR.
    specs_a = _make_clean_specs_tree(tmp_path)
    state_dir_a = tmp_path / ".dadaia"
    ctx_a = "ctx-a"
    _seed_lock_record(tmp_path, ctx_a, "sessForged")
    session_identity.set_incumbent(tmp_path, ctx_a, "sessS2")
    session_identity.write_session(tmp_path, "sessS2", {"session_id": "sessS2"})
    issues_a = SpecsDoctor(specs_a, workspace_state_dir=state_dir_a).check()
    doc029_a = _by_code(issues_a, "SPEC-DOC-029")
    assert doc029_a and all(i.severity == Severity.ERROR for i in doc029_a)
    assert all((i.path or "").endswith(f"{ctx_a}.lock.json") for i in doc029_a)

    # Coherent via a planted lock record -> silent.
    specs_b = _make_clean_specs_tree(tmp_path.parent / (tmp_path.name + "-029coherent"))
    state_dir_b = tmp_path.parent / (tmp_path.name + "-029coherent") / ".dadaia"
    ctx_b = "ctx-b"
    ws_b = tmp_path.parent / (tmp_path.name + "-029coherent")
    _seed_lock_record(ws_b, ctx_b, "sessS1")
    session_identity.write_session(ws_b, "sessS1", {"session_id": "sessS1"})
    issues_b = SpecsDoctor(specs_b, workspace_state_dir=state_dir_b).check()
    assert "SPEC-DOC-029" not in _codes(issues_b)

    # No-op without a workspace state dir (default construction).
    specs_c = _make_clean_specs_tree(tmp_path.parent / (tmp_path.name + "-029noop"))
    assert "SPEC-DOC-029" not in _codes(SpecsDoctor(specs_c).check())

    # Coherent live lease (with a probe wired) -> silent.
    specs_d = _make_clean_specs_tree(tmp_path.parent / (tmp_path.name + "-029coherentlive"))
    ws_d = tmp_path.parent / (tmp_path.name + "-029coherentlive")
    ctx_d = "ctx-coherent"
    _seed_lock_record(ws_d, ctx_d, "sessS1")
    session_identity.write_session(ws_d, "sessS1", {"session_id": "sessS1"})
    issues_d = SpecsDoctor(
        specs_d, workspace_state_dir=ws_d / ".dadaia", pid_probe=lambda _pid: True
    ).check()
    assert "SPEC-DOC-029" not in _codes(issues_d)
