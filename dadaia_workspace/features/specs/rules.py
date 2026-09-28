"""The doctor rule registry — ONE ordered table (F012, 20260830 audit).

Check order, fix dispatch and the ``--fix`` CLI help all derive from :data:`RULES`.
Before this table, ``SpecsDoctor.check()`` was a hand-wired 40-line call list,
``fix()`` a hand-kept if/elif over seven code literals, and the CLI help text a third
hand-written copy that was wrong at HEAD (it claimed TREE-3 fixable — it is not — and
omitted six codes that are). One registry; the three projections cannot drift again.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from dadaia_workspace.core.doctor_rules import Rule
from dadaia_workspace.features.specs import doctor_adr
from dadaia_workspace.features.specs.doctor_types import SpecsDoctorIssue
from dadaia_workspace.features.specs.release_tree import (
    release_memory_issues,
    release_tree_issues,
)
from dadaia_workspace.infrastructure.ledger_scripts import (
    AUDIT_SCRIPT,
    BACKLOG_SCRIPT,
    BUGS_SCRIPT,
    RELEASE_SCRIPT,
)

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
    fix_help: str | tuple[str, ...] | None = None,
) -> SpecsRule:
    """Bind ``section="specs"`` once instead of on every row."""
    return Rule(codes, SECTION, run, fix, fix_help)


RULES: tuple[SpecsRule, ...] = (
    _rule(
        ("SPEC-DOC-001",),
        lambda d: d._coherence.check_constitution(),
        fix_help="Operator action: restore <specs>/constitution.md, then commit.",
    ),
    _rule(
        ("SPEC-DOC-002", "SPEC-DOC-002L"),
        lambda d: d._memory.check_memory_files(),
    ),
    _rule(
        ("MEM-PLACEHOLDER-1",),
        lambda d: d._memory.check_placeholder_atoms(),
        fix=lambda d, i: d._memory.fix_placeholder_atom(i),
        fix_help=("doctor", "--fix"),
    ),
    _rule(
        ("AGENTS-PLACEHOLDER-1",),
        lambda d: d._memory.check_tests_agents_placeholder(),
        # No fix line: filling a project's own test rules is judgment, and `>` would
        # overwrite the operator's file. WARNING-only, so the run never exits 1 on it.
    ),
    _rule(
        ("SPEC-DOC-003",),
        lambda d: d._release.check_active_md(),
        fix_help="Operator action: correct the live _RELEASE.json under <specs>/releases, then commit.",
    ),
    _rule(
        ("SPEC-DOC-004",),
        lambda d: d._release.check_active_release_artifacts(),
    ),
    _rule(
        ("SPEC-DOC-005",),
        lambda d: d._release.check_plan_line_limit(),
        # No fix line: an over-long PLAN is split, and truncating it at the limit
        # deletes the plan's tail. WARNING-only (see check_plan_line_limit).
    ),
    _rule(
        ("TREE-2",),
        lambda d: d._structural.check_tree2_root_spec_md(),
        # No fix line: reclassifying a root SPEC.md needs operator consent (the check's
        # own docstring). WARNING-only.
    ),
    _rule(
        ("TREE-3",),
        lambda d: d._structural.check_tree3_memory_md(),
        fix=lambda d, i: d._structural.fix_tree3(i),
        fix_help=("doctor", "--fix"),
    ),
    _rule(
        ("TREE-4",),
        lambda d: d._structural.check_tree4_required_dirs(),
        fix=lambda d, i: d._structural.fix_tree4(i),
        fix_help=("doctor", "--fix"),
    ),
    _rule(
        ("TREE-5",),
        lambda d: d._structural.check_tree5_agents_md(),
        fix=lambda d, i: d._structural.fix_tree5(i),
        fix_help=("doctor", "--fix"),
    ),
    _rule(
        ("TREE-7",),
        lambda d: d._structural.check_tree7_bug_session_id(),
        fix_help="sed -i 's/<session id>/<redacted>/g' specs/bugs/BUGS.jsonl",
    ),
    _rule(
        ("TREE-8",),
        lambda d: d._structural.check_tree8_canon_root(),
    ),
    _rule(
        ("LINT-1",),
        lambda d: d._memory.check_lint1_memory_atoms(),
    ),
    _rule(
        ("MEM-DRIFT-1",),
        lambda d: d._memory.check_mem_drift1_features_package_map(),
    ),
    _rule(
        ("ADR-SUPERSEDED-CITATION",),
        lambda d: doctor_adr.superseded_adr_citations(d.specs_dir, d.public_dir),
        fix_help="Operator action: cite the successor recorded in <specs>/ADRs/decisions.jsonl instead, then commit.",
    ),
    _rule(
        ("MEM-DRIFT-2",),
        lambda d: d._memory.check_mem_drift2_citations(
            repo_root=d.repo_root, command_paths=d.command_paths
        ),
    ),
    _rule(
        ("FIXED-1", "FIXED-2"),
        lambda d: d._memory.check_fixed_sections(d.public_dir),
        fix=lambda d, i: d._memory.fix_fixed_section(i, d.public_dir),
        fix_help=("doctor", "--fix"),
    ),
    _rule(
        ("SPECS-VERSION",),
        lambda d: d._coherence.check_specs_pattern_version(),
        fix_help=("specs", "upgrade", "--specs-dir", "<specs>"),
    ),
    _rule(
        ("GITFLOW-1",),
        lambda d: d._coherence.check_gitflow(),
        # No flag: `specs init` keeps a valid block, else writes the detected gitflow.
        fix_help=("specs", "init", "--specs-dir", "<specs>"),
    ),
    _rule(
        ("SPEC-DOC-024",),
        lambda d: d._release.check_phase_markers_coherence(),
        fix_help="Operator action: reconcile the live phase with its TASKS.md under <specs>/releases, then commit.",
    ),
    _rule(
        ("SPEC-DOC-026",),
        lambda d: d._release.check_unique_release_ids(),
        fix_help="Operator action: rename one of the duplicated dirs under <specs>/releases, then commit.",
    ),
    _rule(
        ("SPEC-DOC-027",),
        lambda d: d._release.check_release_naming_canon(),
        fix_help="Operator action: rename the release dir under <specs>/releases to its M.m.p id, then commit.",
    ),
    _rule(
        ("SPEC-DOC-030",),
        lambda d: d._closure_audit.check_audits_naming_canon(),
    ),
    _rule(
        ("SPEC-DOC-034",),
        lambda d: d._closure_audit.check_archive_dirs_exist(),
        fix=lambda d, i: d._closure_audit.fix_archive_dir(i),
        fix_help=("doctor", "--fix"),
    ),
    _rule(
        ("SPEC-DOC-035",),
        lambda d: d._governance.check_unarchived_terminal_backlog(),
        fix_help=(
            f"{BACKLOG_SCRIPT.invocation} exit <slug> --disposition <disposition> <--release id|--reason why>"
        ),
    ),
    _rule(
        ("SPEC-DOC-036",),
        lambda d: d._closure_audit.check_audit_disposition(),
        fix_help=(
            f"{AUDIT_SCRIPT.invocation} disposition <audit> <finding-id> "
            "--disposition resolved --release <release>"
        ),
    ),
    _rule(
        ("SPEC-DOC-038",),
        lambda d: d._closure_audit.check_loose_undisposed_audits(),
        fix_help=f"{AUDIT_SCRIPT.invocation} close <audit> --sha <sha>",
    ),
    _rule(
        ("SPEC-DOC-041",),
        lambda d: d._governance.check_bug_archive_overdue(),
        fix_help=f"{BUGS_SCRIPT.invocation} archive --specs <specs>",
    ),
    _rule(
        ("SPEC-DOC-047",),
        lambda d: d._release.check_no_memory_task(),
        fix_help="Operator action: drop the memory task from the live TASKS.md under <specs>/releases, then commit.",
    ),
    _rule(
        ("SPEC-DOC-048",),
        lambda d: d._release.check_spec_origin(d._governance.known_bug_ids),
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
        fix_help="sed -i 's|<invalid value>|<canonical value>|' specs/releases/<id>/_RELEASE.json",
    ),
    _rule(
        ("RELEASE-TREE-MEMORY",),
        lambda d: release_memory_issues(d.specs_dir),
        fix_help=(f"{RELEASE_SCRIPT.invocation} memory --reviewed <slugs> --changed <slugs>"),
    ),
)

#: code -> Rule, for every rule that carries a fix — the ONE fix dispatch table.
FIX_BY_CODE: dict[str, SpecsRule] = {
    code: rule for rule in RULES if rule.fix is not None for code in rule.codes
}


def render_fix_help() -> str:
    """The ``--fix`` CLI help, derived from the registry (never hand-kept again).

    The CODES only: ``fix_help`` is the ONE executable remediation command (0.4.7 FR2),
    not a description, and every auto-fixable rule's command is this very flag."""
    parts = ", ".join("/".join(r.codes) for r in RULES if r.fix is not None)
    return (
        f"Apply auto-fixes for fixable issues ({parts}). "
        "Every other invariant is warn/report-only and never auto-fixed. "
        "After fixing, re-checks and reports residual issues."
    )
