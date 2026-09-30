"""Closure/audit validator (v0.1.55 FR1): audit naming, archives, disposition.

Single-responsibility sibling of the SpecsDoctor coordinator. Owns audit naming canon
(SPEC-DOC-030), the per-artifact ``_archive`` landing zones (SPEC-DOC-034 +
``fix_archive_dir``), Leaf-only: imports the shared leaves, never a sibling
validator.

Archived-audit disposition belongs to `audit.py close`, which refuses to archive an
audit whose FINDINGS.jsonl fails `check` (sa-audit-close-archives-without-validating).
"""

from __future__ import annotations

from pathlib import Path

from dadaia_workspace.core.doctor_rules import SectionFinding
from dadaia_workspace.core.workspace_layout import AUDIT_DIR_NAME_RE
from dadaia_workspace.features.specs.canon import REQUIRED_ROOT_DIRS
from dadaia_workspace.features.specs.doctor_types import Severity, finding_path, specs_finding

# Four audit dirs from the v0.1.9/v0.1.10 audit cycles predate the doctor WARN and are
# grandfathered in place by the constitution §8 amendment (2026-06-10) — their session ids
# are unrecoverable and their timestamps are cross-referenced in immutable ledger reports.
_AUDIT_DIR_GRANDFATHER: frozenset[str] = frozenset(
    {
        "2026-06-09T075056Z",
        "2026-06-10T010550Z",
        "2026-06-10T052944Z",
        "2026-06-10T140553Z",
    }
)

# SPEC-DOC-034 (v0.1.46 AC-4): the per-artifact ``_archive`` dirs that must PRE-EXIST
# (the histo landing zone for disposed artifacts, ADDITIVE). Anchored to the canon table's
# REQUIRED_ROOT_DIRS (v0.5.1 K4) rather than an independent hand-kept tuple, then
# narrowed to the two areas that dispose routinely — backlog/bugs' histo ledgers grow
# constantly, so a missing `_archive/` there is meaningful drift worth a standing
# WARNING; releases/audits archive far less often (an audit's `_archive/` landing zone
# is legitimately empty for most of a project's life) and stay outside this narrower
# check. The narrowing is a deliberate, documented business decision — not a second
# independent member list, since it can only ever be a SUBSET of REQUIRED_ROOT_DIRS.
_ARCHIVE_PARENT_DIRS: tuple[str, ...] = tuple(
    d for d in REQUIRED_ROOT_DIRS if d in ("backlog", "bugs")
)


class ClosureAuditValidator:
    """Orphan specs and audit-disposition invariants."""

    def __init__(self, specs_dir: Path) -> None:
        self.specs_dir = specs_dir

    def check_audits_naming_canon(self) -> list[SectionFinding]:
        """SPEC-DOC-030 (specs/audits/AGENTS.md, v6 canon): WARN on any non-conforming
        ``specs/audits/`` dir.

        Forward enforcement of the naming law: every audit directory must be named
        ``<YYYYMMDD>-<slug>`` (:data:`AUDIT_DIR_NAME_RE`, the single home in
        ``core.workspace_layout`` — the SAME shape ``features.specs.canon``'s own
        audits ``CanonEntry`` pattern uses, never a second, independently hand-kept
        regex; bug spec-doc-030-audit-dir-rule-contradicts-dadaia-6-8-canon fixed a
        stale ``<YYYYMMDDTHHMMSSZ>-<session_id_8chars>`` shape that predated the v6
        canon). WARN-only (legacy names are preserved, never auto-renamed).

        Exempt: the four grandfathered dirs from the old pre-canon amendment
        (:data:`_AUDIT_DIR_GRANDFATHER`) and ``specs/audits/_archive/``. Silent when the
        ``audits/`` dir is absent.
        """
        audits_dir = self.specs_dir / "audits"
        if not audits_dir.is_dir():
            return []
        issues: list[SectionFinding] = []
        for child in sorted(audits_dir.iterdir()):
            if not child.is_dir():
                continue
            name = child.name
            if name == "_archive" or name in _AUDIT_DIR_GRANDFATHER:
                continue
            if AUDIT_DIR_NAME_RE.match(name):
                continue
            issues.append(
                specs_finding(
                    code="SPEC-DOC-030",
                    severity=Severity.WARNING,
                    description=(
                        f"Audit dir 'audits/{name}' does not follow the naming law "
                        "<YYYYMMDD>-<slug> (specs/audits/AGENTS.md) — rename it (SPEC-DOC-030, "
                        "WARNING)."
                    ),
                    path=str(child),
                )
            )
        return issues

    def check_archive_dirs_exist(self) -> list[SectionFinding]:
        """SPEC-DOC-034 (v0.1.46 AC-4): the three per-artifact ``_archive`` dirs must exist.

        ``specs/{backlog,audits,bugs}/_archive/`` are the ADDITIVE histo landing zones for disposed
        artifacts. A missing dir is a WARNING with an auto-fix (``doctor --fix`` mkdirs
        it — a directory is kept by its own future content, no ``.gitkeep``
        placeholder). A parent dir that does not itself exist is skipped — its
        absence is a separate TREE-4 concern, not this taxonomy invariant.
        """
        issues: list[SectionFinding] = []
        for parent in _ARCHIVE_PARENT_DIRS:
            parent_dir = self.specs_dir / parent
            if not parent_dir.is_dir():
                continue
            archive_dir = parent_dir / "_archive"
            if archive_dir.is_dir():
                continue
            issues.append(
                specs_finding(
                    code="SPEC-DOC-034",
                    severity=Severity.WARNING,
                    description=(
                        f"specs/{parent}/_archive/ is missing — the histo landing zone for "
                        "disposed artifacts (SPEC-DOC-034, WARNING). Auto-fix available "
                        "(run doctor --fix)."
                    ),
                    path=str(archive_dir),
                    fixable=True,
                )
            )
        return issues

    def fix_archive_dir(self, issue: SectionFinding) -> None:
        """Create a missing ``_archive`` dir (SPEC-DOC-034 auto-fix). A directory is
        kept by its own future content — no ``.gitkeep`` placeholder is written."""
        assert issue.code == "SPEC-DOC-034"
        target = Path(str(finding_path(issue)))
        target.mkdir(parents=True, exist_ok=True)
