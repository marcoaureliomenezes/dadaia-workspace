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
from dadaia_workspace.core.kernel_tunables import (
    AUDIT_SCRIPT,
    BACKLOG_SCRIPT,
    DADAIA_BIN,
    MEMORY_SCRIPT,
)
from dadaia_workspace.features.specs import doctor_adr
from dadaia_workspace.features.specs.doctor_types import SpecsDoctorIssue
from dadaia_workspace.features.specs.release_tree import (
    release_memory_issues,
    release_tree_issues,
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
    fix_help: str | None = None,
) -> SpecsRule:
    """Bind ``section="specs"`` once instead of on every row."""
    return Rule(codes, SECTION, run, fix, fix_help)


RULES: tuple[SpecsRule, ...] = (
    _rule(
        ("SPEC-DOC-001",),
        lambda d: d._coherence.check_constitution(),
        fix_help="printf '%s\\n' '## <missing section>' >> specs/constitution.md",
    ),
    _rule(
        ("SPEC-DOC-002", "SPEC-DOC-002L", "SPEC-DOC-008"),
        lambda d: d._memory.check_memory_files(),
        fix_help="printf '%s\\n' '# <title>' >> specs/memory/<document>.md",
    ),
    _rule(
        ("MEM-PLACEHOLDER-1",),
        lambda d: d._memory.check_placeholder_atoms(),
        fix=lambda d, i: d._memory.fix_placeholder_atom(i),
        fix_help=f"{DADAIA_BIN} doctor --fix",
    ),
    _rule(
        ("AGENTS-PLACEHOLDER-1",),
        lambda d: d._memory.check_tests_agents_placeholder(),
        # No fix line: filling a project's own test rules is judgment, and `>` would
        # overwrite the operator's file. WARNING-only, so the run never exits 1 on it.
    ),
    _rule(
        (
            "SPEC-DOC-003",
            "SPEC-DOC-009",
        ),
        lambda d: d._release.check_active_md(),
        fix_help="git rm specs/ACTIVE.md",
    ),
    _rule(
        ("SPEC-DOC-004",),
        lambda d: d._release.check_active_release_artifacts(),
        fix_help=(
            "sed -i '\\|\\*\\*Status:\\*\\*|d' specs/releases/<id>/<document>.md && "
            "printf '%s\\n' '**Status:** <Approved|In review|Draft>' "
            ">> specs/releases/<id>/<document>.md"
        ),
    ),
    _rule(
        ("SPEC-DOC-005",),
        lambda d: d._release.check_plan_line_limit(),
        # No fix line: an over-long PLAN is split, and truncating it at the limit
        # deletes the plan's tail. WARNING-only (see check_plan_line_limit).
    ),
    _rule(
        ("SPEC-DOC-007",),
        lambda d: d._closure_audit.check_no_orphan_specs(),
        fix_help="git rm <orphan path>",
    ),
    _rule(
        ("SPEC-DOC-010",),
        lambda d: d._memory.check_memory_atomicity(),
        # No fix line: where an atom's history belongs is judgment, and truncating at
        # the heading deletes it. WARNING-only here; LINT-1 still errors on the same
        # atom, so the invariant keeps its exit-1 home.
    ),
    _rule(
        ("TREE-1",),
        lambda d: d._structural.check_tree1_foundation(),
        fix_help=f"{DADAIA_BIN} specs upgrade --specs-dir <specs>",
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
        fix_help="printf '%s\\n' '# <title>' >> specs/memory/<document>.md",
    ),
    _rule(
        ("TREE-4",),
        lambda d: d._structural.check_tree4_required_dirs(),
        fix=lambda d, i: d._structural.fix_tree4(i),
        fix_help=f"{DADAIA_BIN} doctor --fix",
    ),
    _rule(
        ("TREE-5",),
        lambda d: d._structural.check_tree5_agents_md(),
        fix=lambda d, i: d._structural.fix_tree5(i),
        fix_help=f"{DADAIA_BIN} doctor --fix",
    ),
    _rule(
        ("TREE-7",),
        lambda d: d._structural.check_tree7_bug_session_id(),
        fix_help="sed -i 's/<session id>/<redacted>/g' specs/bugs/BUGS.jsonl",
    ),
    _rule(
        ("TREE-8",),
        lambda d: d._structural.check_tree8_canon_root(),
        fix=lambda d, i: d._structural.fix_tree8(i),
        fix_help=f"{DADAIA_BIN} doctor --fix",
    ),
    _rule(
        ("CAT-1",),
        lambda d: d._memory.check_cat1_catalog_sync(),
        fix_help=f"{MEMORY_SCRIPT} catalog generate --specs <specs>",
    ),
    _rule(
        ("LINT-1",),
        lambda d: d._memory.check_lint1_memory_atoms(),
        fix_help="sed -i '2i <field>: <value>' <atom>",
    ),
    _rule(
        ("MEM-DRIFT-1",),
        lambda d: d._memory.check_mem_drift1_features_package_map(),
        fix_help="sed -i 's|<stale package line>|<package on disk>|' specs/memory/ARCHITECTURE.md",
    ),
    _rule(
        ("ADR-SUPERSEDED-CITATION",),
        lambda d: doctor_adr.superseded_adr_citations(d.specs_dir, d.public_dir),
        fix_help="sed -i 's|ADR: <superseded id>|ADR: <successor id>|' <citing file>",
    ),
    _rule(
        ("MEM-DRIFT-2",),
        lambda d: d._memory.check_mem_drift2_citations(
            repo_root=d.repo_root, command_paths=d.command_paths
        ),
        fix_help="sed -i 's|<dead citation>|<what exists today>|' <memory atom>",
    ),
    _rule(
        ("FIXED-1", "FIXED-2"),
        lambda d: d._memory.check_fixed_sections(d.public_dir),
        fix=lambda d, i: d._memory.fix_fixed_section(i, d.public_dir),
        fix_help=f"{DADAIA_BIN} doctor --fix",
    ),
    _rule(
        ("SPECS-VERSION",),
        lambda d: d._coherence.check_specs_pattern_version(),
        fix_help=f"{DADAIA_BIN} specs upgrade --specs-dir <specs>",
    ),
    _rule(
        ("SPEC-DOC-024",),
        lambda d: d._release.check_phase_markers_coherence(),
        fix_help="sed -i 's/<stale phase marker>/<_RELEASE.json phase>/' <document>",
    ),
    _rule(
        ("SPEC-DOC-026",),
        lambda d: d._release.check_unique_release_ids(),
        fix_help="git mv specs/releases/<duplicated> specs/releases/<id>",
    ),
    _rule(
        ("SPEC-DOC-027",),
        lambda d: d._release.check_release_naming_canon(),
        fix_help="git mv <release-dir> <release-dir-parent>/<M.m.p>",
    ),
    _rule(
        ("SPEC-DOC-028",),
        lambda d: d._coherence.check_constitution_file_refs(),
        fix_help="sed -i '\\|<dangling reference>|d' specs/constitution.md",
    ),
    _rule(
        ("SPEC-DOC-030",),
        lambda d: d._closure_audit.check_audits_naming_canon(),
        fix_help="git mv specs/audits/<name> specs/audits/<YYYYMMDD>-<slug>",
    ),
    _rule(
        ("SPEC-DOC-033",),
        lambda d: d._governance.check_bugs_jsonl_invariant(),
        fix_help="python3 .agents/skills/dd-bug-resolution/scripts/bugs.py update <bug-id> --set <field>=<value>",
    ),
    _rule(
        ("SPEC-DOC-034",),
        lambda d: d._closure_audit.check_archive_dirs_exist(),
        fix=lambda d, i: d._closure_audit.fix_archive_dir(i),
        fix_help=f"{DADAIA_BIN} doctor --fix",
    ),
    _rule(
        ("SPEC-DOC-035",),
        lambda d: d._governance.check_unarchived_terminal_backlog(),
        fix_help=(
            f"{BACKLOG_SCRIPT} exit <slug> --disposition <disposition> <--release id|--reason why>"
        ),
    ),
    _rule(
        ("SPEC-DOC-036",),
        lambda d: d._closure_audit.check_audit_disposition(),
        fix_help=(
            f"{AUDIT_SCRIPT} disposition <audit> <finding-id> "
            "--disposition resolved --release <release>"
        ),
    ),
    _rule(
        ("SPEC-DOC-037",),
        lambda d: d._coherence.check_constitution_no_runtime_enum(),
        fix_help="sed -i '\\|<enum line>|d' specs/constitution.md",
    ),
    _rule(
        ("SPEC-DOC-038",),
        lambda d: d._closure_audit.check_loose_undisposed_audits(),
        fix_help=f"{AUDIT_SCRIPT} close <audit> --sha <sha>",
    ),
    _rule(
        ("SPEC-DOC-041",),
        lambda d: d._governance.check_bug_archive_overdue(),
        fix_help="python3 .agents/skills/dd-bug-resolution/scripts/bugs.py archive",
    ),
    _rule(
        ("SPEC-DOC-047",),
        lambda d: d._release.check_no_memory_task(),
        fix_help="sed -i '\\|<memory task line>|d' specs/releases/<id>/TASKS.md",
    ),
    _rule(
        ("SPEC-DOC-048",),
        lambda d: d._release.check_spec_origin(d._governance.known_bug_ids),
        fix_help=(
            "sed -i '\\|^\\*\\*Opened:\\*\\*|a **Origin:** operator-demand' "
            "specs/releases/<id>/SPEC.md"
        ),
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
        fix_help=(
            "python3 .agents/skills/dd-release-implementation/scripts/release.py memory "
            "--reviewed <slugs> --changed <slugs>"
        ),
    ),
    _rule(
        ("SPEC-DOC-046",),
        lambda d: d._release.check_release_state_filename(),
        fix=lambda d, i: d._release.fix_release_state_filename(i),
        fix_help=f"{DADAIA_BIN} doctor --fix",
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
