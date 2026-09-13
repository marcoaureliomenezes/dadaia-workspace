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
from typing import TYPE_CHECKING

from dadaia_workspace.core.doctor_rules import Rule
from dadaia_workspace.features.specs.doctor_types import SpecsDoctorIssue
from dadaia_workspace.features.specs.release_tree import release_tree_issues

if TYPE_CHECKING:
    from dadaia_workspace.features.specs.doctor import SpecsDoctor

__all__ = ["FIX_BY_CODE", "RULES", "SpecsRule", "render_fix_help"]

#: This section's binding of the one record: rules run over the ``SpecsDoctor``
#: coordinator and emit ``SpecsDoctorIssue``.
type SpecsRule = Rule[SpecsDoctor, SpecsDoctorIssue]

SECTION = "specs"


def _rule(
    codes: tuple[str, ...],
    run: Callable[[SpecsDoctor], list[SpecsDoctorIssue]],
    fix: Callable[[SpecsDoctor, SpecsDoctorIssue], None] | None = None,
    fix_help: str | None = None,
) -> SpecsRule:
    """Bind ``section="specs"`` once instead of on every row."""
    return Rule(codes, SECTION, run, fix, fix_help)


RULES: tuple[SpecsRule, ...] = (
    _rule(
        ("SPEC-DOC-001",),
        lambda d: d._coherence.check_constitution(),
        fix_help="edit specs/constitution.md to carry every section the canon declares",
    ),
    _rule(
        ("SPEC-DOC-002", "SPEC-DOC-002L", "SPEC-DOC-008"),
        lambda d: d._memory.check_memory_files(),
        fix_help="author the missing memory document under specs/memory/",
    ),
    _rule(
        ("MEM-PLACEHOLDER-1",),
        lambda d: d._memory.check_placeholder_atoms(),
        fix=lambda d, i: d._memory.fix_placeholder_atom(i),
        fix_help="remove unfilled placeholder atoms from old scaffolds",
    ),
    _rule(
        ("AGENTS-PLACEHOLDER-1",),
        lambda d: d._memory.check_tests_agents_placeholder(),
        fix_help="replace the scaffold placeholder in tests/AGENTS.md with the repo's own test rules",
    ),
    _rule(
        (
            "SPEC-DOC-003",
            "SPEC-DOC-009",
        ),
        lambda d: d._release.check_active_md(),
        fix_help="delete the retired ACTIVE.md — the live release is _RELEASE.json's phase",
    ),
    _rule(
        ("SPEC-DOC-004",),
        lambda d: d._release.check_active_release_artifacts(),
        fix_help="author the missing SPEC.md/PLAN.md/TASKS.md at the live release root",
    ),
    _rule(
        ("SPEC-DOC-005",),
        lambda d: d._release.check_plan_line_limit(),
        fix_help="cut PLAN.md back under its line limit",
    ),
    _rule(
        ("SPEC-DOC-007",),
        lambda d: d._closure_audit.check_no_orphan_specs(),
        fix_help="delete the orphan specs file or attach it to a release",
    ),
    _rule(
        ("SPEC-DOC-010",),
        lambda d: d._memory.check_memory_atomicity(),
        fix_help="split the oversized memory atom into one subject per file",
    ),
    _rule(
        ("TREE-1",),
        lambda d: d._structural.check_tree1_foundation(),
        fix_help=".dadaia/.venv/bin/dadaia specs upgrade --context <ctx>",
    ),
    _rule(
        ("TREE-2",),
        lambda d: d._structural.check_tree2_root_spec_md(),
        fix_help="author the root spec document the canon declares",
    ),
    _rule(
        ("TREE-3",),
        lambda d: d._structural.check_tree3_memory_md(),
        fix_help="author specs/memory/ARCHITECTURE.md, QUALITY.md and TECHSTACK.md",
    ),
    _rule(
        ("TREE-4",),
        lambda d: d._structural.check_tree4_required_dirs(),
        fix=lambda d, i: d._structural.fix_tree4(i),
        fix_help="create missing required dirs with their AGENTS.md",
    ),
    _rule(
        ("TREE-5",),
        lambda d: d._structural.check_tree5_agents_md(),
        fix=lambda d, i: d._structural.fix_tree5(i),
        fix_help="refresh a superseded, uncustomised law projection",
    ),
    _rule(
        ("TREE-7",),
        lambda d: d._structural.check_tree7_bug_session_id(),
        fix_help="redact the session id from the named bug record in specs/bugs/BUGS.jsonl",
    ),
    _rule(
        ("TREE-8",),
        lambda d: d._structural.check_tree8_canon_root(),
        fix=lambda d, i: d._structural.fix_tree8(i),
        fix_help="remove a stray non-canon root entry or dotfile",
    ),
    _rule(
        ("CAT-1",),
        lambda d: d._memory.check_cat1_catalog_sync(),
        fix_help="regenerate specs/memory/product/catalog.json from the atoms on disk",
    ),
    _rule(
        ("LINT-1",),
        lambda d: d._memory.check_lint1_memory_atoms(),
        fix_help="repair the atom's frontmatter — exactly slug, title, category, tldr, summary, tags",
    ),
    _rule(
        ("MEM-DRIFT-1",),
        lambda d: d._memory.check_mem_drift1_features_package_map(),
        fix_help="update specs/memory/ARCHITECTURE.md's package map to the packages on disk",
    ),
    _rule(
        ("FIXED-1", "FIXED-2"),
        lambda d: d._memory.check_fixed_sections(d.public_dir),
        fix=lambda d, i: d._memory.fix_fixed_section(i, d.public_dir),
        fix_help="insert or refresh the workspace's fixed law sections",
    ),
    _rule(
        ("SPECS-VERSION",),
        lambda d: d._coherence.check_specs_pattern_version(),
        fix_help=".dadaia/.venv/bin/dadaia specs upgrade --context <ctx>",
    ),
    _rule(
        ("SPEC-DOC-024",),
        lambda d: d._release.check_phase_markers_coherence(),
        fix_help="align the phase markers with _RELEASE.json's phase",
    ),
    _rule(
        ("SPEC-DOC-026",),
        lambda d: d._release.check_unique_release_ids(),
        fix_help="rename the duplicated release directory to its own id",
    ),
    _rule(
        ("SPEC-DOC-027",),
        lambda d: d._release.check_release_naming_canon(),
        fix_help="rename the release directory to bare SemVer M.m.p",
    ),
    _rule(
        ("SPEC-DOC-028",),
        lambda d: d._coherence.check_constitution_file_refs(),
        fix_help="repair or delete the dangling file reference in specs/constitution.md",
    ),
    _rule(
        ("SPEC-DOC-030",),
        lambda d: d._closure_audit.check_audits_naming_canon(),
        fix_help="rename the audit directory to <YYYYMMDD>-<slug>",
    ),
    _rule(
        ("SPEC-DOC-033",),
        lambda d: d._governance.check_bugs_jsonl_invariant(),
        fix_help="repair the named record in specs/bugs/BUGS.jsonl against specs/bugs/AGENTS.md",
    ),
    _rule(
        ("SPEC-DOC-034",),
        lambda d: d._closure_audit.check_archive_dirs_exist(),
        fix=lambda d, i: d._closure_audit.fix_archive_dir(i),
        fix_help="create a missing _archive directory",
    ),
    _rule(
        ("SPEC-DOC-035",),
        lambda d: d._governance.check_unarchived_terminal_backlog(),
        fix_help="archive the terminal backlog entry — .dadaia/.venv/bin/dadaia backlog archive",
    ),
    _rule(
        ("SPEC-DOC-036",),
        lambda d: d._closure_audit.check_audit_disposition(),
        fix_help="disposition every finding in the audit's FINDINGS.jsonl",
    ),
    _rule(
        ("SPEC-DOC-037",),
        lambda d: d._coherence.check_constitution_no_runtime_enum(),
        fix_help="remove the runtime enum from specs/constitution.md — the code owns it",
    ),
    _rule(
        ("SPEC-DOC-038",),
        lambda d: d._closure_audit.check_loose_undisposed_audits(),
        fix_help="disposition the loose audit, then delete its directory",
    ),
    _rule(
        ("SPEC-DOC-039",),
        lambda d: d._release.check_partial_archived_release_dirs(),
        fix_help="complete or delete the partially archived release directory",
    ),
    _rule(
        ("SPEC-DOC-041",),
        lambda d: d._governance.check_bug_archive_overdue(),
        fix_help="archive the overdue bugs — .dadaia/.venv/bin/dadaia bugs archive",
    ),
    _rule(
        ("SPEC-DOC-044",),
        lambda d: d._release.check_stale_verdicts(live_shas=d.live_shas),
        fix=lambda d, i: d._release.fix_stale_verdict(i),
        fix_help="delete a stale security verdict (names no live sha: head, first parent, develop tip)",
    ),
    _rule(
        ("SPEC-DOC-045",),
        lambda d: d._release.check_pyproject_version_matches_release(d.repo_root),
        fix_help="set pyproject.toml's version to the live release id",
    ),
    _rule(
        ("SPEC-DOC-047",),
        lambda d: d._release.check_no_memory_task(),
        fix_help="move the memory work out of TASKS.md — it is closure procedure",
    ),
    _rule(
        (
            "RELEASE-TREE-SCHEMA",
            "RELEASE-TREE-PARSE",
            "RELEASE-TREE-TS-ORDER",
            "RELEASE-TREE-PHASE",
            "RELEASE-TREE-ARCHIVED",
            "RELEASE-TREE-TRIO",
            "RELEASE-TREE-STATE-MISSING",
        ),
        lambda d: release_tree_issues(d.specs_dir),
        fix_help="repair the release state document against specs/releases/AGENTS.md",
    ),
    _rule(
        ("SPEC-DOC-046",),
        lambda d: d._release.check_release_state_filename(),
        fix=lambda d, i: d._release.fix_release_state_filename(i),
        fix_help="rename a legacy RELEASE.json to the canonical _RELEASE.json",
    ),
)

#: code -> Rule, for every rule that carries a fix — the ONE fix dispatch table.
FIX_BY_CODE: dict[str, SpecsRule] = {
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
