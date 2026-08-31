"""The doctor rule registry — ONE ordered table (F012, 20260830 audit).

Check order, fix dispatch and the ``--fix`` CLI help all derive from :data:`RULES`.
Before this table, ``SpecsDoctor.check()`` was a hand-wired 40-line call list,
``fix()`` a hand-kept if/elif over seven code literals, and the CLI help text a third
hand-written copy that was wrong at HEAD (it claimed TREE-3 fixable — it is not — and
omitted six codes that are). One registry; the three projections cannot drift again.

The order is the pre-decomposition interleaved order 1:1 — the golden lock
(``test_doctor_golden``) pins the rendered output byte-identically.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from dadaia_workspace.features.specs.doctor_types import SpecsDoctorIssue

if TYPE_CHECKING:
    from dadaia_workspace.features.specs.doctor import SpecsDoctor
    from dadaia_workspace.features.specs.specs_tree import SpecsTree

__all__ = ["FIX_BY_CODE", "RULES", "Rule", "render_fix_help"]


@dataclass(frozen=True)
class Rule:
    """One doctor rule family: which codes it emits, how to run it, how to fix one."""

    codes: tuple[str, ...]
    run: Callable[[SpecsDoctor, SpecsTree], list[SpecsDoctorIssue]]
    fix: Callable[[SpecsDoctor, SpecsDoctorIssue], None] | None = None
    fix_help: str | None = None


RULES: tuple[Rule, ...] = (
    Rule(("SPEC-DOC-001",), lambda d, t: d._coherence.check_constitution()),
    Rule(
        ("SPEC-DOC-002", "SPEC-DOC-002L", "SPEC-DOC-008"),
        lambda d, t: d._memory.check_memory_files(),
    ),
    Rule(
        ("MEM-PLACEHOLDER-1",),
        lambda d, t: d._memory.check_placeholder_atoms(),
        fix=lambda d, i: d._memory.fix_placeholder_atom(i),
        fix_help="remove unfilled placeholder atoms from old scaffolds",
    ),
    Rule(("AGENTS-PLACEHOLDER-1",), lambda d, t: d._memory.check_tests_agents_placeholder()),
    Rule(("SPEC-DOC-003", "SPEC-DOC-009"), lambda d, t: d._release.check_active_md()),
    Rule(("SPEC-DOC-004",), lambda d, t: d._release.check_active_release_artifacts()),
    Rule(("SPEC-DOC-005",), lambda d, t: d._release.check_plan_line_limit()),
    Rule(("SPEC-DOC-007",), lambda d, t: d._closure_audit.check_no_orphan_specs()),
    Rule(("SPEC-DOC-010",), lambda d, t: d._memory.check_memory_atomicity()),
    Rule(("TREE-1",), lambda d, t: d._structural.check_tree1_foundation()),
    Rule(
        ("REPO-DADAIA-1",),
        lambda d, t: d._structural.check_repo_dadaia1(),
        fix=lambda d, i: d._structural.fix_repo_dadaia1(i),
        fix_help="quarantine an in-repo .dadaia/ directory",
    ),
    Rule(("TREE-2",), lambda d, t: d._structural.check_tree2_root_spec_md()),
    Rule(("TREE-3",), lambda d, t: d._structural.check_tree3_memory_md()),
    Rule(
        ("TREE-4",),
        lambda d, t: d._structural.check_tree4_required_dirs(),
        fix=lambda d, i: d._structural.fix_tree4(i),
        fix_help="create missing required dirs with their AGENTS.md",
    ),
    Rule(
        ("TREE-5",),
        lambda d, t: d._structural.check_tree5_agents_md(),
        fix=lambda d, i: d._structural.fix_tree5(i),
        fix_help="refresh a superseded, uncustomised law projection",
    ),
    Rule(("TREE-5M",), lambda d, t: d._structural.check_memory_agents_md()),
    Rule(("TREE-7",), lambda d, t: d._structural.check_tree7_bug_session_id()),
    Rule(
        ("TREE-8",),
        lambda d, t: d._structural.check_tree8_canon_root(),
        fix=lambda d, i: d._structural.fix_tree8(i),
        fix_help="remove a stray non-canon root entry or dotfile",
    ),
    Rule(("CAT-1",), lambda d, t: d._memory.check_cat1_catalog_sync()),
    Rule(("LINT-1",), lambda d, t: d._memory.check_lint1_memory_atoms()),
    Rule(("MEM-DRIFT-1",), lambda d, t: d._memory.check_mem_drift1_features_package_map()),
    Rule(("SPECS-VERSION",), lambda d, t: d._coherence.check_specs_pattern_version()),
    Rule(("SPEC-DOC-024",), lambda d, t: d._release.check_phase_markers_coherence()),
    Rule(("SPEC-DOC-026",), lambda d, t: d._release.check_unique_release_ids()),
    Rule(("SPEC-DOC-027",), lambda d, t: d._release.check_release_naming_canon()),
    Rule(("SPEC-DOC-028",), lambda d, t: d._coherence.check_constitution_file_refs()),
    Rule(("SPEC-DOC-030",), lambda d, t: d._closure_audit.check_audits_naming_canon()),
    Rule(("SPEC-DOC-031",), lambda d, t: d._governance.check_consumed_backlog_disposition()),
    Rule(("SPEC-DOC-033",), lambda d, t: d._governance.check_bugs_jsonl_invariant()),
    Rule(
        ("SPEC-DOC-034",),
        lambda d, t: d._closure_audit.check_archive_dirs_exist(),
        fix=lambda d, i: d._closure_audit.fix_archive_dir(i),
        fix_help="create a missing _archive directory",
    ),
    Rule(("SPEC-DOC-035",), lambda d, t: d._governance.check_unarchived_terminal_backlog()),
    Rule(("SPEC-DOC-036",), lambda d, t: d._closure_audit.check_audit_disposition()),
    Rule(("SPEC-DOC-037",), lambda d, t: d._coherence.check_constitution_no_runtime_enum()),
    Rule(("SPEC-DOC-038",), lambda d, t: d._closure_audit.check_loose_undisposed_audits()),
    Rule(("SPEC-DOC-039",), lambda d, t: d._release.check_partial_archived_release_dirs()),
    Rule(("SPEC-DOC-041",), lambda d, t: d._governance.check_bug_archive_overdue()),
    Rule(
        ("SPEC-DOC-044",),
        lambda d, t: d._release.check_stale_verdicts(head_sha=d.head_sha, parent_sha=d.parent_sha),
        fix=lambda d, i: d._release.fix_stale_verdict(i),
        fix_help="delete a stale (non-head, non-parent) security verdict",
    ),
    Rule(
        ("SPEC-DOC-045",),
        lambda d, t: d._release.check_pyproject_version_matches_release(d.repo_root),
    ),
)

#: code -> Rule, for every rule that carries a fix — the ONE fix dispatch table.
FIX_BY_CODE: dict[str, Rule] = {
    code: rule for rule in RULES if rule.fix is not None for code in rule.codes
}


def render_fix_help() -> str:
    """The ``--fix`` CLI help, derived from the registry (never hand-kept again)."""
    parts = "; ".join(f"{'/'.join(r.codes)}: {r.fix_help}" for r in RULES if r.fix is not None)
    return (
        f"Apply auto-fixes for fixable issues ({parts}). "
        "Every other invariant is warn/report-only and never auto-fixed. "
        "After fixing, re-checks and reports residual issues."
    )
