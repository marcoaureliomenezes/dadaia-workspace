"""SpecsDoctor — thin coordinator for SDD release-lifecycle structural validation.

v0.1.55 FR1 decomposed the former 2,830-line god module into a thin ``SpecsDoctor``
coordinator (this file) that **owns check()/fix() ORDER** and delegates all LOGIC to six
single-responsibility validator siblings plus two shared leaf modules:

  * ``doctor_types``     — ``Severity`` / ``SpecsDoctorIssue`` / ``_MemoryMdSummary``
  * ``doctor_common``    — cross-validator pure helpers (``resolve_live_release_id`` + release-dir discovery)
  * ``doctor_structural``   — TREE-1..8 + TREE-5M spec-tree invariants; ``fix_tree4``,
                              ``fix_tree8``
  * ``doctor_memory``       — memory files/atomicity, CAT-1, LINT-1
  * ``doctor_release``      — active release (RELEASE.json state document), release artifacts, SemVer + ledger invariants
  * ``doctor_closure_audit``— orphan specs, audit disposition; ``fix_archive_dir``
  * ``doctor_governance``   — single-source backlog invariants, bug status/JSONL
  * ``doctor_coherence``    — constitution and pattern-version coherence

The coordinator owns ORDER: ``check()`` invokes the validators' public methods in the exact
original interleaved sequence (families interleave — coherence→memory→release→…→governance→
closure→coherence), and ``fix()`` dispatches by issue code. It imports NO ``spec_context``
(R-1 cap invariant): v0.1.76 T-4 retired the former ``pid_probe``/``workspace_state_dir`` seam
along with SPEC-DOC-029 (see ``doctor_coherence.py``), so the coordinator holds no
``spec_context`` cross-feature edge at all — not even via a typed leaf seam. Behavior is
byte-identical to the pre-split module (golden lock
``tests/unit/features/specs/test_doctor_golden.py``).

Pure module — no I/O outside the supplied specs_dir / public_dir. No external dependencies.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from dadaia_workspace.core.models.bugs import BugRecord
from dadaia_workspace.core.models.findings import FindingRecord
from dadaia_workspace.features.specs.doctor_closure_audit import ClosureAuditValidator
from dadaia_workspace.features.specs.doctor_coherence import CoherenceValidator
from dadaia_workspace.features.specs.doctor_governance import GovernanceValidator
from dadaia_workspace.features.specs.doctor_memory import MemoryValidator
from dadaia_workspace.features.specs.doctor_release import ReleaseValidator
from dadaia_workspace.features.specs.doctor_structural import StructuralValidator
from dadaia_workspace.features.specs.doctor_types import SpecsDoctorIssue
from dadaia_workspace.features.specs.rules import FIX_BY_CODE, RULES
from dadaia_workspace.features.specs.specs_tree import SpecsTree
from dadaia_workspace.infrastructure.jsonl_record_store import JsonlRecordStore


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
        findings_store_factory: Optional DI seam for SPEC-DOC-036/038's
            ``FINDINGS.jsonl`` fold (v0.5.0 T-050-25A, A13.4) — no composition root
            wires this today (release 0.5.1 K9 deleted the never-called
            ``container.build_findings_store`` seam as dead code); ``None`` keeps
            ``ClosureAuditValidator``'s zero-dependency fallback reader (same model).
        bug_store_factory: Optional DI seam for SPEC-DOC-033/041's ``BUGS.jsonl``
            read (v0.5.1 K5 deepening, same ``strict``/malformed-line shape as
            ``findings_store_factory`` — but takes ``specs_dir``, not a file path:
            a bug ledger is ONE-per-``specs_dir``, unlike the unbounded per-audit-dir
            ``FINDINGS.jsonl`` set) — a composition root wires
            ``container.build_bug_record_store`` (the SAME factory ``cli.commands
            .bugs`` already calls); ``None`` keeps ``GovernanceValidator``'s
            zero-dependency fallback reader (same model).
        head_sha: Optional branch HEAD sha, resolved ONCE by the CLI composition
            root (through the ``GitObjectReader`` port) and passed in as plain data
            (v0.5.0 specs-canon closure) — feeds SPEC-DOC-044 (stale verdicts).
            ``None`` (default) keeps that check a silent no-op; this coordinator
            never resolves git state itself.
        parent_sha: Optional first-parent sha of *head_sha*, resolved the same way.
    """

    def __init__(
        self,
        specs_dir: Path,
        public_dir: Path | None = None,
        templates_dir: Path | None = None,
        repo_root: Path | None = None,
        findings_store_factory: Callable[[Path], JsonlRecordStore[FindingRecord]] | None = None,
        bug_store_factory: Callable[[Path], JsonlRecordStore[BugRecord]] | None = None,
        head_sha: str | None = None,
        parent_sha: str | None = None,
    ) -> None:
        self.specs_dir = Path(specs_dir)
        self.public_dir: Path | None = Path(public_dir) if public_dir is not None else None
        # repo_root: when supplied, the constitution file-ref invariant (SPEC-DOC-028)
        # resolves path-like references against it, and the pyproject-version-vs-
        # release-id invariant (SPEC-DOC-045) reads pyproject.toml from it. None ->
        # both checks are a no-op.
        self.repo_root: Path | None = Path(repo_root) if repo_root is not None else None
        # head_sha/parent_sha (v0.5.0 specs-canon closure): SPEC-DOC-044's plain-data
        # inputs, resolved once by the CLI. None -> that check is a no-op.
        self.head_sha: str | None = head_sha
        self.parent_sha: str | None = parent_sha
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

        # Build the six validators (each independently testable). The coordinator owns the
        # config resolution; validators own their family LOGIC and family-local helpers.
        self._structural: StructuralValidator = StructuralValidator(
            self.specs_dir, self._scaffold_dir, self._templates_dir
        )
        self._memory: MemoryValidator = MemoryValidator(self.specs_dir)
        self._release: ReleaseValidator = ReleaseValidator(self.specs_dir)
        self._closure_audit: ClosureAuditValidator = ClosureAuditValidator(
            self.specs_dir, findings_store_factory
        )
        self._governance: GovernanceValidator = GovernanceValidator(
            self.specs_dir,
            self.public_dir,
            bug_store_factory,
        )
        self._coherence: CoherenceValidator = CoherenceValidator(
            self.specs_dir,
            self.public_dir,
            self.repo_root,
        )

    def check(self) -> list[SpecsDoctorIssue]:
        """Run every rule in the ONE ordered registry (F012) over a FRESH SpecsTree
        snapshot (F010) — shared facts are parsed once per run, the registry owns
        order, and the golden lock pins the rendered output byte-identically."""
        tree = SpecsTree(self.specs_dir)
        self._release.tree = tree
        issues: list[SpecsDoctorIssue] = []
        for rule in RULES:
            issues.extend(rule.run(self, tree))
        return issues

    def fix(self, issues: list[SpecsDoctorIssue] | None = None) -> list[SpecsDoctorIssue]:
        """Apply auto-fixes for all fixable issues.

        Dispatch derives from the registry (:data:`~dadaia_workspace.features.specs
        .rules.FIX_BY_CODE`) — never a hand-kept branch list. Warn-only invariants are
        never touched; a failed fix is left as a residual issue for the next check().
        """
        if issues is None:
            issues = self.check()
        fixed: list[SpecsDoctorIssue] = []
        for issue in issues:
            if not issue.fixable:
                continue
            rule = FIX_BY_CODE.get(issue.code)
            if rule is None or rule.fix is None:
                continue
            try:
                rule.fix(self, issue)
            except Exception:  # noqa: BLE001 — leave as residual for the next check()
                continue
            fixed.append(issue)
        return fixed
