"""SpecsDoctor — thin coordinator for SDD release-lifecycle structural validation.

v0.1.55 FR1 decomposed the former 2,830-line god module into a thin ``SpecsDoctor``
coordinator (this file) that **owns check()/fix() ORDER** and delegates all LOGIC to six
single-responsibility validator siblings plus two shared leaf modules:

  * ``doctor_types``     — ``Severity`` / ``SpecsDoctorIssue`` / ``_MemoryMdSummary``
  * ``doctor_common``    — cross-validator pure helpers (``read_active_md`` + release-dir discovery)
  * ``doctor_structural``   — TREE-1..7 + TREE-5M spec-tree invariants; ``fix_tree4``
  * ``doctor_memory``       — memory files/atomicity, CAT-1, LINT-1 (holds the lazy
                              ``infrastructure.subprocess_runner`` import)
  * ``doctor_release``      — ACTIVE.md, release artifacts, SemVer + ledger invariants
  * ``doctor_closure_audit``— archive closures, orphan specs, audit disposition; ``fix_archive_dir``
  * ``doctor_governance``   — single-source backlog invariants, bug status/JSONL
  * ``doctor_coherence``    — constitution and pattern-version coherence

The coordinator owns ORDER: ``check()`` invokes the validators' public methods in the exact
original interleaved sequence (families interleave — coherence→memory→release→…→governance→
closure→coherence), and ``fix()`` dispatches by issue code. It imports NEITHER ``spec_context``
NOR ``infrastructure.subprocess_runner`` (R-1 cap invariant): v0.1.76 T-4 retired the former
``pid_probe``/``workspace_state_dir`` seam along with SPEC-DOC-029 (see ``doctor_coherence.py``),
so the coordinator holds no ``spec_context`` cross-feature edge at all — not even via a typed
leaf seam. Behavior is byte-identical to the pre-split module (golden lock
``tests/unit/features/specs/test_doctor_golden.py``).

Pure module — no I/O outside the supplied specs_dir / public_dir. No external dependencies.
"""

from __future__ import annotations

from pathlib import Path

from dadaia_workspace.core.protocols.process_runner import ProcessRunner
from dadaia_workspace.features.specs.doctor_closure_audit import ClosureAuditValidator
from dadaia_workspace.features.specs.doctor_coherence import CoherenceValidator
from dadaia_workspace.features.specs.doctor_governance import GovernanceValidator
from dadaia_workspace.features.specs.doctor_memory import MemoryValidator
from dadaia_workspace.features.specs.doctor_release import ReleaseValidator
from dadaia_workspace.features.specs.doctor_structural import StructuralValidator
from dadaia_workspace.features.specs.doctor_types import SpecsDoctorIssue


class SpecsDoctor:
    """Diagnose specs/ structure under SDD release-lifecycle.

    Thin coordinator: owns the ``check()``/``fix()`` ORDER and delegates all LOGIC to the six
    validator siblings (each independently testable). The public surface — the ``__init__``
    signature, ``check()``, ``fix()``, and every issue code — is byte-identical to the
    pre-decomposition module.

    Args:
        specs_dir: Path to the ``specs/`` directory.
        public_dir: Optional path to ``dadaia_workspace/public/``. When provided,
            the TREE-3/TREE-4/TREE-5 auto-fix + drift-detect features are available
            (templates loaded from ``public_dir/templates/``).
            When *not* provided the TREE checks still run but TREE-3 fix and TREE-5
            hash comparison are skipped (issue is still emitted, fix is no-op).
    """

    def __init__(
        self,
        specs_dir: Path,
        public_dir: Path | None = None,
        templates_dir: Path | None = None,
        process_runner: ProcessRunner | None = None,
        repo_root: Path | None = None,
    ) -> None:
        self.specs_dir = Path(specs_dir)
        self.public_dir: Path | None = Path(public_dir) if public_dir is not None else None
        # repo_root: when supplied, the constitution file-ref invariant (SPEC-DOC-028)
        # resolves path-like references against it. None → that check is a no-op.
        self.repo_root: Path | None = Path(repo_root) if repo_root is not None else None
        # templates_dir is resolved from public_dir if not explicitly supplied.
        if templates_dir is not None:
            self._templates_dir: Path | None = Path(templates_dir)
        elif self.public_dir is not None:
            candidate = self.public_dir / "templates"
            self._templates_dir = candidate if candidate.is_dir() else None
        else:
            self._templates_dir = None

        # Scaffold source dir (for TREE-4 README content).
        if self.public_dir is not None:
            scaffold_candidate = self.public_dir / "scaffold"
            self._scaffold_dir: Path | None = (
                scaffold_candidate if scaffold_candidate.is_dir() else None
            )
        else:
            self._scaffold_dir = None

        # ProcessRunner: injected for tests/DI; lazily resolved to the infra adapter in
        # production when not provided (the memory validator holds the lazy import).
        self._process_runner: ProcessRunner | None = process_runner

        # Build the six validators (each independently testable). The coordinator owns the
        # config resolution; validators own their family LOGIC and family-local helpers.
        self._structural = StructuralValidator(
            self.specs_dir, self._scaffold_dir, self._templates_dir
        )
        self._memory = MemoryValidator(self.specs_dir, self._process_runner)
        self._release = ReleaseValidator(self.specs_dir)
        self._closure_audit = ClosureAuditValidator(self.specs_dir)
        self._governance = GovernanceValidator(self.specs_dir, self.public_dir)
        self._coherence = CoherenceValidator(
            self.specs_dir,
            self.public_dir,
            self.repo_root,
        )

    def check(self) -> list[SpecsDoctorIssue]:
        """Run every structural check in the EXACT original interleaved order.

        The coordinator owns ORDER; each validator owns its family LOGIC. This sequence is the
        pre-decomposition l.566-615 order 1:1 — the golden lock pins it byte-identically.
        """
        issues: list[SpecsDoctorIssue] = []
        issues.extend(self._coherence.check_constitution())
        issues.extend(self._memory.check_memory_files())
        issues.extend(self._memory.check_placeholder_atoms())  # MEM-PLACEHOLDER-1
        issues.extend(self._memory.check_tests_agents_placeholder())  # AGENTS-PLACEHOLDER-1
        issues.extend(self._release.check_active_md())
        issues.extend(self._release.check_active_release_artifacts())
        issues.extend(self._release.check_plan_line_limit())
        issues.extend(self._closure_audit.check_archive_closures())
        issues.extend(self._closure_audit.check_no_orphan_specs())
        issues.extend(self._memory.check_memory_atomicity())
        # 9: covered inside check_active_md (release id ↔ dir)
        # checks 10 and 11 (HTML image-links / mermaid-script) retired with HTML atoms
        # SPEC-DOC-012/022/023 RETIRED (v0.12.0 T-120-08, ADR D10) — the candidates.md
        # bullet-schema validator retired with candidates.md itself, archived by the
        # same cutover; see doctor_governance.py's module docstring.
        issues.extend(self._release.check_release_semver_naming())
        # TREE invariants (spec-context-tree-v2)
        issues.extend(self._structural.check_tree1_foundation())
        issues.extend(self._structural.check_repo_dadaia1())
        issues.extend(self._structural.check_tree2_root_spec_md())
        issues.extend(self._structural.check_tree3_memory_md())
        issues.extend(self._structural.check_tree4_required_dirs())
        issues.extend(self._structural.check_tree5_agents_md())
        issues.extend(self._structural.check_memory_agents_md())
        issues.extend(self._structural.check_tree6_release_artifacts())
        issues.extend(self._structural.check_tree7_bug_session_id())
        # CAT-1 (memory-context-enforcement-v1) — now based on .md files
        issues.extend(self._memory.check_cat1_catalog_sync())
        # LINT-1 (memory-markdown-source-v1) — invoke lint-memory-atoms.py
        issues.extend(self._memory.check_lint1_memory_atoms())
        # SPECS-VERSION (specs-evolution / FR-S05) — pattern-version staleness
        issues.extend(self._coherence.check_specs_pattern_version())
        # v0.1.10 / T-010-14 (R6b) — ledger invariants + identity-coherence backstop
        issues.extend(self._release.check_phase_markers_coherence())  # SPEC-DOC-024
        issues.extend(self._release.check_unique_release_ids())  # SPEC-DOC-026
        issues.extend(self._release.check_release_naming_canon())  # SPEC-DOC-027
        issues.extend(self._coherence.check_constitution_file_refs())  # SPEC-DOC-028
        # SPEC-DOC-029 RETIRED (v0.1.76 T-4, FR7, NO-LOCKS DOCTRINE) — see doctor_coherence.py.
        issues.extend(self._closure_audit.check_audits_naming_canon())  # SPEC-DOC-030
        # v0.1.11 / T-011-10 (bug B1) — closure-disposition canon
        issues.extend(self._governance.check_consumed_backlog_disposition())  # SPEC-DOC-031
        issues.extend(self._governance.check_bug_status_canon())  # SPEC-DOC-032
        # v0.1.46 / T-46-04 (AC-1) — event-sourced JSONL bug-telemetry invariant
        issues.extend(self._governance.check_bugs_jsonl_invariant())  # SPEC-DOC-033
        # v0.1.46 / T-46-13 (AC-4) — taxonomy + disposition invariants
        issues.extend(self._closure_audit.check_archive_dirs_exist())  # SPEC-DOC-034
        issues.extend(self._governance.check_unarchived_terminal_backlog())  # SPEC-DOC-035
        issues.extend(self._closure_audit.check_audit_disposition())  # SPEC-DOC-036
        # v0.1.47 / W1-9 — recurrence guards (constitution runtime enum + loose audits)
        issues.extend(self._coherence.check_constitution_no_runtime_enum())  # SPEC-DOC-037
        issues.extend(self._closure_audit.check_loose_undisposed_audits())  # SPEC-DOC-038
        # v0.1.81 / FR2 (audit G-23) — partial (artifact-empty) archived release dirs
        issues.extend(self._release.check_partial_archived_release_dirs())  # SPEC-DOC-039
        return issues

    def fix(self, issues: list[SpecsDoctorIssue] | None = None) -> list[SpecsDoctorIssue]:
        """Apply auto-fixes for all fixable issues.

        Resolves TREE-4 (structural) and SPEC-DOC-034 (closure_audit) only — the coordinator
        dispatches by issue code to the owning validator's public fix method; warn-only and
        no-fix invariants are never touched.

        Args:
            issues: Pre-computed issue list (avoids a second ``check()`` call).
                    If None, ``check()`` is called internally.

        Returns:
            List of issues that were fixed (i.e. ``fixable=True`` issues that
            were acted upon).  Issues that could not be fixed due to missing
            templates are omitted and left as residual issues on the next
            ``check()`` call.
        """
        if issues is None:
            issues = self.check()
        fixed: list[SpecsDoctorIssue] = []
        for issue in issues:
            if not issue.fixable:
                continue
            try:
                if issue.code == "TREE-4":
                    self._structural.fix_tree4(issue)
                    fixed.append(issue)
                elif issue.code == "TREE-5":
                    self._structural.fix_tree5(issue)
                    fixed.append(issue)
                elif issue.code == "REPO-DADAIA-1":
                    self._structural.fix_repo_dadaia1(issue)
                    fixed.append(issue)
                elif issue.code == "SPEC-DOC-034":
                    self._closure_audit.fix_archive_dir(issue)
                    fixed.append(issue)
                elif issue.code == "MEM-PLACEHOLDER-1":
                    self._memory.fix_placeholder_atom(issue)
                    fixed.append(issue)
            except Exception:
                # Leave as residual — will re-appear on next check()
                pass
        return fixed
