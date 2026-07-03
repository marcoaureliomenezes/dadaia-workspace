"""Unit tests for SpecsDoctor ledger invariants + identity-coherence backstop.

Release v0.1.10 / T-010-14 (R6b). Five new ledger invariants plus a lease↔session
coherence backstop, each with an ERROR/WARNING code following the SPEC-DOC-NNN
convention:

- SPEC-DOC-024 — phase↔markers coherence (ACTIVE.md phase vs TASKS markers).
- SPEC-DOC-006 (extended) — CLOSURE-before-archive, recursive into nested archive dirs.
- SPEC-DOC-026 — unique release ids across releases/ ∪ _archive/releases/ (recursive),
  WARN for documented legacy nested dirs (the v0.2.0/v0.1.{6..9} milestone collision).
- SPEC-DOC-027 — naming canon ``^v\\d+\\.\\d+\\.\\d+$`` for release dirs, legacy WARN.
- SPEC-DOC-028 — constitution file-ref resolution (WARN on a missing repo file).
- SPEC-DOC-029 — lease↔session coherence backstop (no-op unless a workspace state
  dir is injected; otherwise delegates to ``session_identity.coherence`` over the
  genuine ``<ctx>.lock.json`` records production writes, reporting any three-source
  divergence between the lease holder, the incumbent pointer, and the session record).

Each invariant has one failing fixture (the violation fires the code) and one passing
fixture (a clean tree does NOT fire the code).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.features.spec_context import lease, session_identity
from dadaia_workspace.features.specs import Severity, SpecsDoctor, SpecsDoctorIssue

_REPO_ROOT = Path(__file__).parent.parent.parent.parent.parent

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


@pytest.fixture(autouse=True)
def _skip_memory_lint_subprocess(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep these unit tests focused on in-process structural checks.

    v0.1.55 FR1: LINT-1 moved off the coordinator into ``doctor_memory.MemoryValidator``;
    stub its public method so the coordinator's ``check()`` never shells out.
    """
    from dadaia_workspace.features.specs.doctor_memory import MemoryValidator

    monkeypatch.setattr(MemoryValidator, "check_lint1_memory_atoms", lambda self: [])


def _make_clean_specs_tree(root: Path, release_id: str = "v0.1.10") -> Path:
    """A minimal but ledger-valid specs/ tree.

    Default release id is SemVer-clean so the naming-canon invariant does not fire,
    phase is IMPLEMENTATION with an approved Aprovado TASKS carrying a reserved marker.
    """
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


# ──────────────────────────────────────────────────────────────────────────────
# Invariant 1 — SPEC-DOC-024 phase↔markers coherence
# ──────────────────────────────────────────────────────────────────────────────


def test_phase_spec_with_all_done_markers_reports_doc_024(tmp_path: Path) -> None:
    """phase=SPEC but TASKS are an [x]-majority → SPEC-DOC-024 (the live audit incident)."""
    specs = _make_clean_specs_tree(tmp_path)
    _set_active(specs, "v0.1.10", "SPEC")
    _write_tasks(specs, "v0.1.10", "- [x] T1 done\n- [x] T2 done\n- [ ] T3 open\n")
    issues = SpecsDoctor(specs).check()
    assert "SPEC-DOC-024" in _codes(issues)


def test_phase_closure_with_open_task_reports_doc_024(tmp_path: Path) -> None:
    """phase=CLOSURE but a non-[x] task remains → SPEC-DOC-024."""
    specs = _make_clean_specs_tree(tmp_path)
    _set_active(specs, "v0.1.10", "CLOSURE")
    _write_tasks(specs, "v0.1.10", "- [x] T1 done\n- [-] T2 in-progress\n")
    issues = SpecsDoctor(specs).check()
    assert "SPEC-DOC-024" in _codes(issues)


def test_phase_implementation_without_aprovado_tasks_reports_doc_024(tmp_path: Path) -> None:
    """phase=IMPLEMENTATION but TASKS is not Aprovado → SPEC-DOC-024."""
    specs = _make_clean_specs_tree(tmp_path)
    _set_active(specs, "v0.1.10", "IMPLEMENTATION")
    (specs / "releases" / "v0.1.10" / "TASKS.md").write_text(
        "# Tasks\n\n> **Status:** Draft\n\n- [ ] T1\n", encoding="utf-8"
    )
    issues = SpecsDoctor(specs).check()
    assert "SPEC-DOC-024" in _codes(issues)


def test_coherent_phase_markers_does_not_report_doc_024(tmp_path: Path) -> None:
    """A coherent IMPLEMENTATION tree (Aprovado TASKS, not all done) → no SPEC-DOC-024."""
    specs = _make_clean_specs_tree(tmp_path)
    issues = SpecsDoctor(specs).check()
    assert "SPEC-DOC-024" not in _codes(issues)


def test_coherent_closure_all_done_does_not_report_doc_024(tmp_path: Path) -> None:
    """phase=CLOSURE with every task [x] → no SPEC-DOC-024."""
    specs = _make_clean_specs_tree(tmp_path)
    _set_active(specs, "v0.1.10", "CLOSURE")
    _write_tasks(specs, "v0.1.10", "- [x] T1 done\n- [x] T2 done\n")
    issues = SpecsDoctor(specs).check()
    assert "SPEC-DOC-024" not in _codes(issues)


# ──────────────────────────────────────────────────────────────────────────────
# Invariant 2 — SPEC-DOC-006 (extended) CLOSURE-before-archive, recursive
# ──────────────────────────────────────────────────────────────────────────────


def test_nested_archive_release_without_closure_reports_doc_006(tmp_path: Path) -> None:
    """A nested archived release dir (release artifacts, no CLOSURE.md) → SPEC-DOC-006.

    The pre-existing SPEC-DOC-006 only iterated the top level of _archive/releases/;
    the extension recurses so nested legacy milestone dirs are also covered.
    """
    specs = _make_clean_specs_tree(tmp_path)
    nested = specs / "_archive" / "releases" / "v0.2.0" / "milestone-1"
    nested.mkdir(parents=True)
    (nested / "SPEC.md").write_text("# Spec\n\n> **Status:** Aprovado\n", encoding="utf-8")
    (nested / "TASKS.md").write_text("# Tasks\n\n> **Status:** Aprovado\n", encoding="utf-8")
    # parent v0.2.0 itself is a closed release
    (specs / "_archive" / "releases" / "v0.2.0" / "CLOSURE.md").write_text(
        _CLOSURE_MD, encoding="utf-8"
    )
    issues = SpecsDoctor(specs).check()
    doc_006 = _by_code(issues, "SPEC-DOC-006")
    assert any("milestone-1" in (i.path or "") for i in doc_006), [i.to_dict() for i in doc_006]


def test_top_level_archive_release_without_closure_reports_doc_006(tmp_path: Path) -> None:
    """Top-level archived release with artifacts but no CLOSURE.md → SPEC-DOC-006."""
    specs = _make_clean_specs_tree(tmp_path)
    arch = specs / "_archive" / "releases" / "v0.0.9"
    arch.mkdir(parents=True)
    (arch / "SPEC.md").write_text("# Spec\n\n> **Status:** Aprovado\n", encoding="utf-8")
    issues = SpecsDoctor(specs).check()
    assert "SPEC-DOC-006" in _codes(issues)


def test_archive_release_with_closure_does_not_report_doc_006(tmp_path: Path) -> None:
    """A properly-closed archived release (CLOSURE.md present + sections) → no SPEC-DOC-006."""
    specs = _make_clean_specs_tree(tmp_path)
    arch = specs / "_archive" / "releases" / "v0.0.9"
    arch.mkdir(parents=True)
    (arch / "CLOSURE.md").write_text(_CLOSURE_MD, encoding="utf-8")
    issues = SpecsDoctor(specs).check()
    assert "SPEC-DOC-006" not in _codes(issues)


# ──────────────────────────────────────────────────────────────────────────────
# Invariant 3 — SPEC-DOC-026 unique release ids across releases ∪ _archive (recursive)
# ──────────────────────────────────────────────────────────────────────────────


def test_duplicate_release_id_top_level_reports_doc_026_error(tmp_path: Path) -> None:
    """The same release id in releases/ and _archive/releases/ (both real, non-legacy)
    → SPEC-DOC-026 ERROR."""
    specs = _make_clean_specs_tree(tmp_path)
    dup = specs / "_archive" / "releases" / "v0.1.10"
    dup.mkdir(parents=True)
    (dup / "CLOSURE.md").write_text(_CLOSURE_MD, encoding="utf-8")
    issues = SpecsDoctor(specs).check()
    doc_026 = _by_code(issues, "SPEC-DOC-026")
    assert any(i.severity == Severity.ERROR for i in doc_026), [i.to_dict() for i in doc_026]


def test_legacy_nested_duplicate_release_id_reports_doc_026_warning(tmp_path: Path) -> None:
    """The v0.2.0/v0.1.9 nested legacy milestone colliding with the real v0.1.9 archive
    → SPEC-DOC-026 WARNING (documented legacy until T-010-15 renames it), never ERROR."""
    specs = _make_clean_specs_tree(tmp_path)
    real = specs / "_archive" / "releases" / "v0.1.9"
    real.mkdir(parents=True)
    (real / "CLOSURE.md").write_text(_CLOSURE_MD, encoding="utf-8")
    nested = specs / "_archive" / "releases" / "v0.2.0" / "v0.1.9"
    nested.mkdir(parents=True)
    (nested / "SPEC.md").write_text("# Spec\n\n> **Status:** Aprovado\n", encoding="utf-8")
    (specs / "_archive" / "releases" / "v0.2.0" / "CLOSURE.md").write_text(
        _CLOSURE_MD, encoding="utf-8"
    )
    issues = SpecsDoctor(specs).check()
    doc_026 = _by_code(issues, "SPEC-DOC-026")
    assert doc_026, "expected SPEC-DOC-026 WARNING for legacy nested collision"
    assert all(i.severity == Severity.WARNING for i in doc_026), [i.to_dict() for i in doc_026]


def test_unique_release_ids_does_not_report_doc_026(tmp_path: Path) -> None:
    """Distinct release ids across releases + archive → no SPEC-DOC-026."""
    specs = _make_clean_specs_tree(tmp_path)
    arch = specs / "_archive" / "releases" / "v0.1.9"
    arch.mkdir(parents=True)
    (arch / "CLOSURE.md").write_text(_CLOSURE_MD, encoding="utf-8")
    issues = SpecsDoctor(specs).check()
    assert "SPEC-DOC-026" not in _codes(issues)


# ──────────────────────────────────────────────────────────────────────────────
# Invariant 4 — SPEC-DOC-027 naming canon ^v\d+\.\d+\.\d+$
# ──────────────────────────────────────────────────────────────────────────────


def test_non_semver_active_release_dir_reports_doc_027(tmp_path: Path) -> None:
    """A non-SemVer active release dir name → SPEC-DOC-027 ERROR."""
    specs = _make_clean_specs_tree(tmp_path, release_id="my-feature-v1")
    issues = SpecsDoctor(specs).check()
    doc_027 = _by_code(issues, "SPEC-DOC-027")
    assert any(i.severity == Severity.ERROR for i in doc_027), [i.to_dict() for i in doc_027]


def test_unlisted_legacy_archive_non_semver_dir_reports_doc_027_warning(tmp_path: Path) -> None:
    """A NON-allowlisted legacy archived non-SemVer dir → SPEC-DOC-027 WARNING, never ERROR.

    Uses a synthetic name that is NOT in the SPEC-DOC-027 permanent allowlist
    (ADR-9), so forward enforcement for new/unrecognised legacy dirs is intact.
    """
    specs = _make_clean_specs_tree(tmp_path)
    legacy = specs / "_archive" / "releases" / "some-unlisted-legacy-name-v1"
    legacy.mkdir(parents=True)
    (legacy / "CLOSURE.md").write_text(_CLOSURE_MD, encoding="utf-8")
    issues = SpecsDoctor(specs).check()
    doc_027 = _by_code(issues, "SPEC-DOC-027")
    assert doc_027, "expected SPEC-DOC-027 WARNING for unlisted legacy archive dir"
    assert all(i.severity == Severity.WARNING for i in doc_027), [i.to_dict() for i in doc_027]


@pytest.mark.parametrize(
    "allowlisted_name",
    [
        "ctx-inject-v2-drift-fix-v1",
        "memory-markdown-source-v1",
        "v0.1.4.1",
        "v0.1.4.2",
        "v0.1.4.3",
        "v0.1.4.3-report-retention",
        "v0.1.4.4",
        "v0.1.4.5",
        "v0.1.4.6",
    ],
)
def test_allowlisted_legacy_archive_dir_is_silent_doc_027(
    tmp_path: Path, allowlisted_name: str
) -> None:
    """An enumerated permanent-allowlist legacy archive dir → no SPEC-DOC-027 (ADR-9).

    The frozen-history `_archive` names are documented in source and never renamed;
    the doctor stays silent for exactly these names.
    """
    specs = _make_clean_specs_tree(tmp_path)
    legacy = specs / "_archive" / "releases" / allowlisted_name
    legacy.mkdir(parents=True)
    (legacy / "CLOSURE.md").write_text(_CLOSURE_MD, encoding="utf-8")
    issues = SpecsDoctor(specs).check()
    assert "SPEC-DOC-027" not in _codes(issues), [
        i.to_dict() for i in _by_code(issues, "SPEC-DOC-027")
    ]


def test_allowlist_does_not_silence_synthetic_new_bad_dir_doc_027(tmp_path: Path) -> None:
    """The allowlist is name-exact: a NEW non-canon dir still WARNs even alongside
    an allowlisted dir (forward enforcement intact, ADR-9)."""
    specs = _make_clean_specs_tree(tmp_path)
    allowed = specs / "_archive" / "releases" / "v0.1.4.6"
    allowed.mkdir(parents=True)
    (allowed / "CLOSURE.md").write_text(_CLOSURE_MD, encoding="utf-8")
    bad = specs / "_archive" / "releases" / "brand-new-non-canon-dir"
    bad.mkdir(parents=True)
    (bad / "CLOSURE.md").write_text(_CLOSURE_MD, encoding="utf-8")
    issues = SpecsDoctor(specs).check()
    doc_027 = _by_code(issues, "SPEC-DOC-027")
    assert any("brand-new-non-canon-dir" in (i.path or "") for i in doc_027), [
        i.to_dict() for i in doc_027
    ]
    assert not any("v0.1.4.6" in (i.path or "") for i in doc_027), [i.to_dict() for i in doc_027]


def test_allowlist_does_not_silence_live_release_tree_doc_027(tmp_path: Path) -> None:
    """The allowlist only applies to archived dirs: an allowlisted name appearing in the
    LIVE releases/ tree born after the canon still ERRORs (forward enforcement, ADR-9)."""
    specs = _make_clean_specs_tree(tmp_path, release_id="v0.1.4.6")
    issues = SpecsDoctor(specs).check()
    doc_027 = _by_code(issues, "SPEC-DOC-027")
    assert any(i.severity == Severity.ERROR for i in doc_027), [i.to_dict() for i in doc_027]


def test_semver_release_dirs_do_not_report_doc_027(tmp_path: Path) -> None:
    """SemVer-clean dirs in releases/ + archive → no SPEC-DOC-027."""
    specs = _make_clean_specs_tree(tmp_path)
    arch = specs / "_archive" / "releases" / "v0.1.9"
    arch.mkdir(parents=True)
    (arch / "CLOSURE.md").write_text(_CLOSURE_MD, encoding="utf-8")
    issues = SpecsDoctor(specs).check()
    assert "SPEC-DOC-027" not in _codes(issues)


# ──────────────────────────────────────────────────────────────────────────────
# Invariant 5 — SPEC-DOC-028 constitution file-ref resolution
# ──────────────────────────────────────────────────────────────────────────────


def test_constitution_dangling_file_ref_reports_doc_028(tmp_path: Path) -> None:
    """A path-like backtick ref in constitution.md that does not resolve → SPEC-DOC-028 WARN."""
    specs = _make_clean_specs_tree(tmp_path)
    # repo_root is tmp_path (specs lives at tmp_path/specs)
    (specs / "constitution.md").write_text(
        "# Constitution\n\nSee `does/not/exist.py` for details.\n", encoding="utf-8"
    )
    issues = SpecsDoctor(specs, repo_root=tmp_path).check()
    doc_028 = _by_code(issues, "SPEC-DOC-028")
    assert doc_028, [i.to_dict() for i in issues]
    assert all(i.severity == Severity.WARNING for i in doc_028)


def test_constitution_resolvable_file_ref_does_not_report_doc_028(tmp_path: Path) -> None:
    """A path-like ref that resolves against repo root → no SPEC-DOC-028."""
    specs = _make_clean_specs_tree(tmp_path)
    (tmp_path / "real_file.py").write_text("# ok\n", encoding="utf-8")
    (specs / "constitution.md").write_text(
        "# Constitution\n\nSee `real_file.py` for details.\n", encoding="utf-8"
    )
    issues = SpecsDoctor(specs, repo_root=tmp_path).check()
    assert "SPEC-DOC-028" not in _codes(issues)


def test_constitution_ref_resolution_noop_without_repo_root(tmp_path: Path) -> None:
    """Without a repo_root the file-ref check is a safe no-op (cannot resolve repo paths)."""
    specs = _make_clean_specs_tree(tmp_path)
    (specs / "constitution.md").write_text(
        "# Constitution\n\nSee `does/not/exist.py`.\n", encoding="utf-8"
    )
    issues = SpecsDoctor(specs).check()  # no repo_root
    assert "SPEC-DOC-028" not in _codes(issues)


# ──────────────────────────────────────────────────────────────────────────────
# Backstop — SPEC-DOC-029 lease↔session coherence
# ──────────────────────────────────────────────────────────────────────────────


def test_incoherent_lease_session_via_production_writers_reports_doc_029(
    tmp_path: Path,
) -> None:
    """A deliberately incoherent lease↔session pair, created on disk via the PRODUCTION
    writers (``lease.acquire`` + ``session_identity`` writers), makes the doctor flag
    SPEC-DOC-029.

    Production sequence reproduced:

    1. ``lease.acquire`` writes the genuine ``<ctx>.lock.json`` record (holder = ``S1``)
       and the incumbent ``<ctx>.ptr`` (= ``S1``).
    2. The incumbent pointer is then drifted to ``S2`` (``set_incumbent``) and a session
       record is written for ``S2`` (``write_session``) — the out-of-band drift the
       D-2 backstop exists to catch.

    Result: lock-holder = ``S1`` while incumbent-ptr/session-record = ``S2`` — three-source
    divergence → SPEC-DOC-029 fires on the real ``<ctx>.lock.json`` artifact.
    """
    specs = _make_clean_specs_tree(tmp_path)
    state_dir = tmp_path / ".dadaia"
    ctx = "ctx-a"

    # Production writer #1: the real lease record + incumbent ptr, both naming S1.
    lease.acquire(tmp_path, ctx, "sessS1", "rel-1", "implementation")
    # v0.1.50 FR2 (holder-confirmation): a REAL acquire leaves same-CAS index
    # evidence, so ptr drift alone is no longer forgery. Forge the record
    # out-of-band (no index entry) to reproduce the true 029 ERROR shape.
    rec = lease.read_record(tmp_path, ctx)
    assert rec is not None
    rec["session_id"] = "sessForged"
    lease._write_record(lease._record_path(tmp_path, ctx), rec)
    # Production writer #2: drift the incumbent ptr to S2 and persist S2's session record.
    session_identity.set_incumbent(tmp_path, ctx, "sessS2")
    session_identity.write_session(tmp_path, "sessS2", {"session_id": "sessS2"})

    issues = SpecsDoctor(specs, workspace_state_dir=state_dir).check()
    doc_029 = [i for i in issues if i.code == "SPEC-DOC-029"]
    assert doc_029, [i.to_dict() for i in issues]
    assert all(i.severity == Severity.ERROR for i in doc_029)
    # The reported artifact is the REAL record name production writes, not a fabrication.
    assert all(i.path.endswith(f"{ctx}.lock.json") for i in doc_029)


def test_coherent_lease_session_via_production_writers_does_not_report_doc_029(
    tmp_path: Path,
) -> None:
    """A coherent lease↔session state created via the production writers → no SPEC-DOC-029.

    ``lease.acquire`` writes the lock record + incumbent ptr (both = ``S1``); the matching
    session record for ``S1`` is then persisted. All three sources name ``S1`` → coherent.
    """
    specs = _make_clean_specs_tree(tmp_path)
    state_dir = tmp_path / ".dadaia"
    ctx = "ctx-a"

    lease.acquire(tmp_path, ctx, "sessS1", "rel-1", "implementation")
    session_identity.write_session(tmp_path, "sessS1", {"session_id": "sessS1"})

    issues = SpecsDoctor(specs, workspace_state_dir=state_dir).check()
    assert "SPEC-DOC-029" not in _codes(issues)


def test_lease_coherence_is_noop_without_workspace_state_dir(tmp_path: Path) -> None:
    """Default construction (pure module) → backstop is a no-op, never fires."""
    specs = _make_clean_specs_tree(tmp_path)
    issues = SpecsDoctor(specs).check()
    assert "SPEC-DOC-029" not in _codes(issues)


# ──────────────────────────────────────────────────────────────────────────────
# SPEC-DOC-029 three-state triage — T-011-03 (bug B3:
# doctor-stale-lease-misdiagnosed-as-forgery)
#
# (a) TTL-expired + dead/unprobeable holder  ⇒ WARN "stale lease ... safe to reclaim"
# (b) live holder + genuine incoherence       ⇒ ERR (forgery wording ONLY here)
# (c) coherent                                ⇒ silent
# ──────────────────────────────────────────────────────────────────────────────

from datetime import UTC, datetime, timedelta  # noqa: E402

# v0.1.55 FR1: the pid_probe seam logic (check_lease_session_coherence) moved off the coordinator
# into doctor_coherence. The process-probe-adapter-avoidance assertion is re-widened across the
# coordinator AND every decomposed sibling (built lazily to avoid mid-file import churn) so it
# cannot silently narrow to coordinator-only.
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

_FORGERY_TOKEN = "forgery"
_STALE_REMEDIATION_TOKENS = ("dadaia doctor --fix", "dadaia lock steal")


def _strip_pid_from_lock_record(state_dir: Path, ctx: str) -> None:
    """Reduce the genuine ``<ctx>.lock.json`` to the legacy pre-``pid`` record shape.

    The record is still produced by the production writer (``lease.acquire``); this only
    removes the ``pid`` field to reproduce the EXACT pre-pid legacy shape observed in the
    bug (a record that predates the ``pid`` field), so the pid-veto degrades to TTL-only.
    """
    import json

    record_path = state_dir / "states" / "ctx_locks" / f"{ctx}.lock.json"
    data = json.loads(record_path.read_text(encoding="utf-8"))
    data.pop("pid", None)
    record_path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def test_stale_dead_holder_lease_reports_doc_029_warning_with_remediation(
    tmp_path: Path,
) -> None:
    """State (a): a TTL-expired lock record whose holder is dead/unprobeable ⇒ WARN.

    The lease is acquired ~36 h ago (heartbeat far past the 120 s TTL); no live pid_probe
    is wired (default ``None``), so the record degrades to the TTL verdict (stale/dead).
    The incumbent ptr / session record are coherently re-bound to a *fresh* session — the
    out-of-band lock holder is just the stale, never-GC'd lease. Doctor must WARN
    ("stale lease ... safe to reclaim") with a remediation command, never ERR / forgery.
    """
    specs = _make_clean_specs_tree(tmp_path)
    state_dir = tmp_path / ".dadaia"
    ctx = "ctx-stale"

    stale_clock = lambda: datetime.now(tz=UTC) - timedelta(hours=36)  # noqa: E731
    lease.acquire(tmp_path, ctx, "sessOld", "rel-1", "implementation", clock=stale_clock)
    # Fresh READ bind: incumbent ptr + session record re-point to a new live session.
    session_identity.set_incumbent(tmp_path, ctx, "sessNew")
    session_identity.write_session(tmp_path, "sessNew", {"session_id": "sessNew"})

    issues = SpecsDoctor(specs, workspace_state_dir=state_dir).check()
    doc_029 = _by_code(issues, "SPEC-DOC-029")
    assert doc_029, [i.to_dict() for i in issues]
    assert all(i.severity == Severity.WARNING for i in doc_029)
    text = " ".join(i.description for i in doc_029)
    assert "stale lease" in text.lower()
    assert "safe to reclaim" in text.lower()
    assert any(tok in text for tok in _STALE_REMEDIATION_TOKENS)
    assert _FORGERY_TOKEN not in text.lower()
    # No ERROR-class SPEC-DOC-029 at all.
    assert all(i.severity == Severity.WARNING for i in doc_029)


def test_stale_pidless_lease_with_fresh_read_bind_warns_not_err(tmp_path: Path) -> None:
    """Named composed integration test (AC-W1-03 / bug B3 repro steps 1–4, end-to-end).

    Built entirely via the PRODUCTION writers:

    1. A session acquires the lease in IMPLEMENTATION mode (genuine ``<ctx>.lock.json`` +
       incumbent ptr), ~36 h ago — heartbeat far past TTL. The record is then reduced to
       the legacy pid-LESS shape (the exact pre-pid record observed in the bug).
    2. The harness session ended without release; TTL expired; no GC reclaimed the file.
    3. A new session runs a READ bind: incumbent ptr + session record re-point to the new
       session (production ``set_incumbent`` + ``write_session``).
    4. ``specs doctor`` runs over this state.

    Expected (the bug's Expected section): WARN — not ERR — naming the reclaim command,
    overall exit 0 (no other ERR), and NO forgery wording in the output.
    """
    specs = _make_clean_specs_tree(tmp_path)
    state_dir = tmp_path / ".dadaia"
    ctx = "consumer-ctx"

    # Step 1 — genuine lease + ptr, ~36 h old, then reduced to the legacy pid-less shape.
    stale_clock = lambda: datetime.now(tz=UTC) - timedelta(hours=36)  # noqa: E731
    lease.acquire(tmp_path, ctx, "sessDead", "rel-1", "implementation", clock=stale_clock)
    _strip_pid_from_lock_record(state_dir, ctx)

    # Step 3 — fresh READ bind re-points incumbent ptr + session record to the new session.
    session_identity.set_incumbent(tmp_path, ctx, "sessFreshRead")
    session_identity.write_session(
        tmp_path, "sessFreshRead", {"session_id": "sessFreshRead", "mode": "read"}
    )

    # Step 4 — run doctor (probe seam left at default None ⇒ pid-less ⇒ TTL verdict = dead).
    issues = SpecsDoctor(specs, workspace_state_dir=state_dir).check()

    doc_029 = _by_code(issues, "SPEC-DOC-029")
    assert doc_029, [i.to_dict() for i in issues]
    # WARN, not ERR.
    assert all(i.severity == Severity.WARNING for i in doc_029)
    # Remediation command named.
    text = " ".join(i.description for i in doc_029)
    assert any(tok in text for tok in _STALE_REMEDIATION_TOKENS), text
    # No forgery wording anywhere in the doctor output.
    full_output = " ".join(i.description for i in issues)
    assert _FORGERY_TOKEN not in full_output.lower(), full_output
    # Overall exit 0 — no ERROR-class issue introduced by this stale lease.
    assert all(i.severity != Severity.ERROR for i in doc_029)


def test_live_incoherent_lease_reports_doc_029_error_with_forgery_wording(
    tmp_path: Path,
) -> None:
    """State (b): a LIVE lock holder whose identity genuinely diverges from the incumbent
    ptr / session record ⇒ ERR with forgery wording (the only state where it is permitted).

    ``lease.acquire`` writes a TTL-fresh record stamped with THIS test process's pid (alive),
    so the holder is live; the incumbent ptr is then drifted to a different session — genuine
    three-source incoherence on a live holder = the forgery the backstop exists to catch.
    """
    specs = _make_clean_specs_tree(tmp_path)
    state_dir = tmp_path / ".dadaia"
    ctx = "ctx-live"

    # Live holder: fresh acquire (heartbeat now, pid = this process, alive). Wire a probe
    # so the live pid is honoured even if TTL math is borderline. v0.1.50 FR2: forge
    # the holder sid out-of-band (no same-CAS index entry) — a confirmed holder with
    # ptr drift is coherent now; only the evidence-less shape is forgery.
    lease.acquire(tmp_path, ctx, "sessLive", "rel-1", "implementation")
    rec = lease.read_record(tmp_path, ctx)
    assert rec is not None
    rec["session_id"] = "sessForgedLive"
    lease._write_record(lease._record_path(tmp_path, ctx), rec)
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


def test_coherent_live_lease_reports_no_doc_029(tmp_path: Path) -> None:
    """State (c): a coherent live lease ⇒ silent (no SPEC-DOC-029 at all)."""
    specs = _make_clean_specs_tree(tmp_path)
    state_dir = tmp_path / ".dadaia"
    ctx = "ctx-coherent"

    lease.acquire(tmp_path, ctx, "sessS1", "rel-1", "implementation")
    session_identity.write_session(tmp_path, "sessS1", {"session_id": "sessS1"})

    issues = SpecsDoctor(specs, workspace_state_dir=state_dir, pid_probe=lambda _pid: True).check()
    assert "SPEC-DOC-029" not in _codes(issues)


def test_doctor_pid_probe_seam_is_composition_root_wired_not_feature_import() -> None:
    """The doctor pid-probe seam is an injected ``__init__`` parameter (composition-root
    wired, like ``workspace_state_dir``) — ``features/specs/doctor.py`` must NOT import the
    infrastructure process-probe adapter directly (import-linter / ADR layering law).
    """
    import importlib
    import inspect

    sig = inspect.signature(SpecsDoctor.__init__)
    assert "pid_probe" in sig.parameters, "SpecsDoctor must accept an injected pid_probe seam"

    # Re-widened (v0.1.55 FR1): the coordinator AND every decomposed validator/leaf module must
    # be free of the infrastructure process-probe adapter — the probe is composition-root-wired
    # via the pid_probe parameter. Asserting over the coordinator alone would silently pass now
    # that the lease/session coherence logic lives in doctor_coherence.
    for name in _DOCTOR_MODULE_NAMES:
        mod = importlib.import_module(f"dadaia_workspace.features.specs.{name}")
        src = inspect.getsource(mod)
        assert "process_probe_adapter" not in src, (
            f"{mod.__name__} must not import the infrastructure process-probe adapter; "
            "the probe is composition-root-wired via the pid_probe parameter."
        )


# ──────────────────────────────────────────────────────────────────────────────
# SPEC-DOC-030 — specs/audits/ naming canon (constitution §8 collision-safe naming)
# ──────────────────────────────────────────────────────────────────────────────


def test_non_conforming_new_audit_dir_reports_doc_030_warning(tmp_path: Path) -> None:
    """A new audit dir not matching <YYYYMMDDTHHMMSSZ>-<sid8> → SPEC-DOC-030 WARNING."""
    specs = _make_clean_specs_tree(tmp_path)
    (specs / "audits" / "2026-07-01T000000Z").mkdir(parents=True)
    issues = SpecsDoctor(specs).check()
    doc_030 = _by_code(issues, "SPEC-DOC-030")
    assert doc_030, [i.to_dict() for i in issues]
    assert all(i.severity == Severity.WARNING for i in doc_030)
    assert all(i.path.endswith("2026-07-01T000000Z") for i in doc_030)


def test_conforming_audit_dir_does_not_report_doc_030(tmp_path: Path) -> None:
    """A canonical <YYYYMMDDTHHMMSSZ>-<sid8> dir → silent."""
    specs = _make_clean_specs_tree(tmp_path)
    (specs / "audits" / "20260701T000000Z-abcd1234").mkdir(parents=True)
    issues = SpecsDoctor(specs).check()
    assert "SPEC-DOC-030" not in _codes(issues)


def test_grandfathered_audit_dir_does_not_report_doc_030(tmp_path: Path) -> None:
    """The four §8-amendment grandfathered dirs + _archive → silent."""
    specs = _make_clean_specs_tree(tmp_path)
    for name in (
        "2026-06-09T075056Z",
        "2026-06-10T010550Z",
        "2026-06-10T052944Z",
        "2026-06-10T140553Z",
        "_archive",
    ):
        (specs / "audits" / name).mkdir(parents=True)
    issues = SpecsDoctor(specs).check()
    assert "SPEC-DOC-030" not in _codes(issues)


def test_audit_naming_check_silent_when_audits_dir_absent(tmp_path: Path) -> None:
    """No audits/ dir → the check is a safe no-op."""
    specs = _make_clean_specs_tree(tmp_path)
    assert not (specs / "audits").exists()
    issues = SpecsDoctor(specs).check()
    assert "SPEC-DOC-030" not in _codes(issues)


# ──────────────────────────────────────────────────────────────────────────────
# Clean tree sanity — no new ERROR codes on a coherent ledger
# ──────────────────────────────────────────────────────────────────────────────


def test_clean_ledger_tree_has_no_new_errors(tmp_path: Path) -> None:
    specs = _make_clean_specs_tree(tmp_path)
    issues = SpecsDoctor(specs).check()
    new_codes = {"SPEC-DOC-024", "SPEC-DOC-026", "SPEC-DOC-027", "SPEC-DOC-028", "SPEC-DOC-029"}
    errors = [i for i in issues if i.severity == Severity.ERROR and i.code in new_codes]
    assert errors == [], [i.to_dict() for i in errors]


# ──────────────────────────────────────────────────────────────────────────────
# SPEC-DOC-031 — consumed-backlog disposition drift (T-011-10, bug B1 half (b))
#
# A specs/backlog/<slug>.md whose Status line is an ADR-11 NON-TERMINAL token
# ({OPEN, PICKED, CANDIDATE}, case-insensitive prefix match) AND whose slug/ID
# appears in an ARCHIVED release CLOSURE.md/SPEC.md (specs/_archive/releases/*/),
# EXCLUDING matches inside "Backlog returns" sections ⇒ WARN (never ERR; ADR-6 —
# slug mention ≠ consumption is the false-positive class that keeps it WARN).
# ──────────────────────────────────────────────────────────────────────────────


def _write_backlog_entry(specs: Path, slug: str, status_line: str) -> None:
    (specs / "backlog").mkdir(parents=True, exist_ok=True)
    (specs / "backlog" / f"{slug}.md").write_text(
        f"# {slug}\n\n**Status:** {status_line}\n\nBody.\n", encoding="utf-8"
    )


def _write_archived_closure(specs: Path, release_id: str, body: str) -> None:
    rel = specs / "_archive" / "releases" / release_id
    rel.mkdir(parents=True, exist_ok=True)
    (rel / "CLOSURE.md").write_text(body, encoding="utf-8")


def test_nonterminal_backlog_referenced_in_archived_closure_reports_doc_031_warning(
    tmp_path: Path,
) -> None:
    """Picked/consumed backlog whose status is still non-terminal ⇒ SPEC-DOC-031 WARN."""
    specs = _make_clean_specs_tree(tmp_path)
    _write_backlog_entry(specs, "feat-consumed-thing", "PICKED — blocked on operator grill")
    _write_archived_closure(
        specs,
        "v0.0.9",
        "# Closure\n\n## Bug dispositions\n\n"
        "Source: `specs/backlog/feat-consumed-thing.md` — delivered, accepted.\n",
    )
    issues = SpecsDoctor(specs).check()
    doc_031 = _by_code(issues, "SPEC-DOC-031")
    assert doc_031, [i.to_dict() for i in issues]
    assert all(i.severity == Severity.WARNING for i in doc_031)
    text = " ".join(i.description for i in doc_031)
    assert "feat-consumed-thing" in text
    # The finding text must cite the ADR-6 false-positive reasoning (why it stays WARN).
    assert "v0.0.9" in text
    assert all(i.path.endswith("feat-consumed-thing.md") for i in doc_031)
    # W1-10 (T-47-19): remediation text is reconciled with BL-SCHEMA vocabulary — it must
    # recommend a BARE terminal token + optional delivered_in + archive move, and must
    # explicitly warn AGAINST the BL-SCHEMA-rejected 'TOKEN — vX.Y.Z' status form.
    assert "status: delivered" in text  # bare terminal token BL-SCHEMA accepts
    assert "delivered_in" in text  # optional release field, not part of the status token
    assert "_archive" in text  # archive move per SPEC-DOC-035
    assert "BL-SCHEMA" in text and "Do NOT" in text  # explicit rejected-form warning


def test_open_backlog_referenced_in_archived_spec_reports_doc_031_warning(
    tmp_path: Path,
) -> None:
    """An OPEN backlog slug sourced in an archived SPEC also drifts ⇒ WARN."""
    specs = _make_clean_specs_tree(tmp_path)
    _write_backlog_entry(specs, "open-but-sourced", "OPEN — filed for intake only")
    rel = specs / "_archive" / "releases" / "v0.0.8"
    rel.mkdir(parents=True, exist_ok=True)
    (rel / "SPEC.md").write_text(
        "# Spec\n\n## 4. Product Deltas\n\nSource: `specs/backlog/open-but-sourced.md`\n",
        encoding="utf-8",
    )
    (rel / "CLOSURE.md").write_text("# Closure\n\nDone.\n", encoding="utf-8")
    issues = SpecsDoctor(specs).check()
    doc_031 = _by_code(issues, "SPEC-DOC-031")
    assert doc_031, [i.to_dict() for i in issues]
    assert all(i.severity == Severity.WARNING for i in doc_031)
    assert any("open-but-sourced" in i.description for i in doc_031)


def test_backlog_slug_only_in_backlog_returns_section_is_silent(tmp_path: Path) -> None:
    """Negative fixture (ADR-6): a slug appearing ONLY inside a ``## Backlog returns``
    section of an archived CLOSURE is a legitimate return (the slug is being ADDED, not
    consumed) ⇒ SPEC-DOC-031 must stay silent."""
    specs = _make_clean_specs_tree(tmp_path)
    _write_backlog_entry(specs, "newly-returned-item", "CANDIDATE — not picked")
    _write_archived_closure(
        specs,
        "v0.0.7",
        "# Closure\n\n## Backlog returns\n\n"
        "- `specs/backlog/newly-returned-item.md` ← registered for a future release.\n",
    )
    issues = SpecsDoctor(specs).check()
    assert "SPEC-DOC-031" not in _codes(issues)


def test_terminal_backlog_referenced_in_archived_closure_is_silent(tmp_path: Path) -> None:
    """A DELIVERED (terminal) backlog entry referenced in an archived CLOSURE is correctly
    dispositioned ⇒ no SPEC-DOC-031 WARN."""
    specs = _make_clean_specs_tree(tmp_path)
    _write_backlog_entry(specs, "shipped-thing", "DELIVERED — v0.0.9 (see CLOSURE)")
    _write_archived_closure(
        specs,
        "v0.0.9",
        "# Closure\n\n## Dispositions\n\nSource: `specs/backlog/shipped-thing.md` delivered.\n",
    )
    issues = SpecsDoctor(specs).check()
    assert "SPEC-DOC-031" not in _codes(issues)


def test_nonterminal_backlog_not_in_any_archive_is_silent(tmp_path: Path) -> None:
    """A genuinely open backlog item never referenced by an archived release ⇒ silent."""
    specs = _make_clean_specs_tree(tmp_path)
    _write_backlog_entry(specs, "brand-new-idea", "OPEN — never picked")
    _write_archived_closure(specs, "v0.0.9", "# Closure\n\nUnrelated content.\n")
    issues = SpecsDoctor(specs).check()
    assert "SPEC-DOC-031" not in _codes(issues)


def test_doc_031_skips_candidates_and_ideas_aggregate_files(tmp_path: Path) -> None:
    """The free-form aggregate files (candidates.md / ideas.md / README.md) are not
    per-slug backlog entries and must never trigger SPEC-DOC-031."""
    specs = _make_clean_specs_tree(tmp_path)
    (specs / "backlog" / "candidates.md").write_text(
        "## Candidatas ativas\n\n- thing — x (owner: a, contexto: b)\n", encoding="utf-8"
    )
    _write_archived_closure(specs, "v0.0.9", "# Closure\n\nReferences candidates here.\n")
    issues = SpecsDoctor(specs).check()
    assert "SPEC-DOC-031" not in _codes(issues)


# ──────────────────────────────────────────────────────────────────────────────
# SPEC-DOC-032 — bug status-token canon (T-011-10, bug B1 half (b))
#
# A specs/bugs/<slug>.md whose frontmatter ``status:`` is outside the ADR-11 bug
# canon {Open, Closed} ⇒ WARN (guards regressions of the legacy Fixed/resolved drift).
# ──────────────────────────────────────────────────────────────────────────────


def _write_bug(specs: Path, slug: str, status: str, extra: str = "") -> None:
    (specs / "bugs").mkdir(parents=True, exist_ok=True)
    (specs / "bugs" / f"{slug}.md").write_text(
        f"---\nname: {slug}\nstatus: {status}\nsession_id: null\n{extra}---\n\n**Symptom:** x.\n",
        encoding="utf-8",
    )


def test_bug_with_noncanonical_status_reports_doc_032_warning(tmp_path: Path) -> None:
    """A bug carrying a legacy ``Fixed`` token ⇒ SPEC-DOC-032 WARN."""
    specs = _make_clean_specs_tree(tmp_path)
    _write_bug(specs, "some-old-bug", "Fixed")
    issues = SpecsDoctor(specs).check()
    doc_032 = _by_code(issues, "SPEC-DOC-032")
    assert doc_032, [i.to_dict() for i in issues]
    assert all(i.severity == Severity.WARNING for i in doc_032)
    text = " ".join(i.description for i in doc_032)
    assert "Fixed" in text
    assert all(i.path.endswith("some-old-bug.md") for i in doc_032)


def test_bug_with_rejected_status_reports_doc_032_warning(tmp_path: Path) -> None:
    """``Rejected`` is outside the {Open, Closed} canon ⇒ WARN (the duplicate/rejected bug
    should be ``Closed`` + ``superseded_by:``)."""
    specs = _make_clean_specs_tree(tmp_path)
    _write_bug(specs, "rejected-dup-bug", "Rejected", extra="rejected_reason: duplicate of x\n")
    issues = SpecsDoctor(specs).check()
    doc_032 = _by_code(issues, "SPEC-DOC-032")
    assert doc_032, [i.to_dict() for i in issues]
    assert all(i.severity == Severity.WARNING for i in doc_032)


@pytest.mark.parametrize("status", ["Open", "Closed", "open", "closed", "CLOSED"])
def test_bug_with_canonical_status_is_silent(tmp_path: Path, status: str) -> None:
    """{Open, Closed} (case-insensitive) ⇒ silent."""
    specs = _make_clean_specs_tree(tmp_path)
    _write_bug(specs, "well-formed-bug", status)
    issues = SpecsDoctor(specs).check()
    assert "SPEC-DOC-032" not in _codes(issues)


def test_doc_032_skips_readme_and_silent_when_bugs_dir_absent(tmp_path: Path) -> None:
    """README.md is skipped; absent bugs/ dir ⇒ no-op."""
    specs = _make_clean_specs_tree(tmp_path)
    (specs / "bugs").mkdir(parents=True, exist_ok=True)
    (specs / "bugs" / "README.md").write_text("# Bugs\n\nstatus: whatever\n", encoding="utf-8")
    issues = SpecsDoctor(specs).check()
    assert "SPEC-DOC-032" not in _codes(issues)


def test_closed_bug_with_superseded_by_is_silent(tmp_path: Path) -> None:
    """A duplicate normalized to ``Closed`` + ``superseded_by:`` (the live-tree fix shape)
    ⇒ silent."""
    specs = _make_clean_specs_tree(tmp_path)
    _write_bug(
        specs,
        "duplicate-bug",
        "Closed",
        extra="superseded_by: canonical-bug\nrejected_reason: marked duplicate\n",
    )
    issues = SpecsDoctor(specs).check()
    assert "SPEC-DOC-032" not in _codes(issues)
