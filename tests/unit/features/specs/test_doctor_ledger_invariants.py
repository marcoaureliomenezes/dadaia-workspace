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
  dir is injected; otherwise validates the holder session record exists).

Each invariant has one failing fixture (the violation fires the code) and one passing
fixture (a clean tree does NOT fire the code).
"""

from __future__ import annotations

from pathlib import Path

import pytest

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
    """Keep these unit tests focused on in-process structural checks."""
    monkeypatch.setattr(SpecsDoctor, "_check_lint1_memory_atoms", lambda self: [])


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


def test_legacy_archive_non_semver_dir_reports_doc_027_warning(tmp_path: Path) -> None:
    """A legacy archived non-SemVer release dir → SPEC-DOC-027 WARNING, never ERROR."""
    specs = _make_clean_specs_tree(tmp_path)
    legacy = specs / "_archive" / "releases" / "ctx-inject-v2-drift-fix-v1"
    legacy.mkdir(parents=True)
    (legacy / "CLOSURE.md").write_text(_CLOSURE_MD, encoding="utf-8")
    issues = SpecsDoctor(specs).check()
    doc_027 = _by_code(issues, "SPEC-DOC-027")
    assert doc_027, "expected SPEC-DOC-027 WARNING for legacy archive dir"
    assert all(i.severity == Severity.WARNING for i in doc_027), [i.to_dict() for i in doc_027]


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


def _seed_lock(state_dir: Path, ctx: str, session_id: str) -> Path:
    import json

    locks = state_dir / "states" / "ctx_locks"
    locks.mkdir(parents=True)
    lock = locks / f"{ctx}.lock"
    lock.write_text(json.dumps({"session_id": session_id, "context": ctx}), encoding="utf-8")
    return lock


def test_lease_without_session_record_reports_doc_029(tmp_path: Path) -> None:
    """A lock naming a holder session whose session record is absent → SPEC-DOC-029."""
    specs = _make_clean_specs_tree(tmp_path)
    state_dir = tmp_path / ".dadaia"
    _seed_lock(state_dir, "ctx-a", "sess_ghost1")
    (state_dir / "sessions").mkdir(parents=True)  # no sess_ghost1.json
    issues = SpecsDoctor(specs, workspace_state_dir=state_dir).check()
    assert "SPEC-DOC-029" in _codes(issues)


def test_lease_with_session_record_does_not_report_doc_029(tmp_path: Path) -> None:
    """A lock whose holder session record exists → no SPEC-DOC-029."""
    specs = _make_clean_specs_tree(tmp_path)
    state_dir = tmp_path / ".dadaia"
    _seed_lock(state_dir, "ctx-a", "sess_real01")
    sessions = state_dir / "sessions"
    sessions.mkdir(parents=True)
    (sessions / "sess_real01.json").write_text('{"session_id": "sess_real01"}', encoding="utf-8")
    issues = SpecsDoctor(specs, workspace_state_dir=state_dir).check()
    assert "SPEC-DOC-029" not in _codes(issues)


def test_lease_coherence_is_noop_without_workspace_state_dir(tmp_path: Path) -> None:
    """Default construction (pure module) → backstop is a no-op, never fires."""
    specs = _make_clean_specs_tree(tmp_path)
    issues = SpecsDoctor(specs).check()
    assert "SPEC-DOC-029" not in _codes(issues)


# ──────────────────────────────────────────────────────────────────────────────
# Clean tree sanity — no new ERROR codes on a coherent ledger
# ──────────────────────────────────────────────────────────────────────────────


def test_clean_ledger_tree_has_no_new_errors(tmp_path: Path) -> None:
    specs = _make_clean_specs_tree(tmp_path)
    issues = SpecsDoctor(specs).check()
    new_codes = {"SPEC-DOC-024", "SPEC-DOC-026", "SPEC-DOC-027", "SPEC-DOC-028", "SPEC-DOC-029"}
    errors = [i for i in issues if i.severity == Severity.ERROR and i.code in new_codes]
    assert errors == [], [i.to_dict() for i in errors]
