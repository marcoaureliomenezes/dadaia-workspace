"""Closure/audit validator: audit naming, archives, disposition.

Owns the audit naming canon, the per-artifact ``_archive`` landing zones and their
auto-fix. Imports the shared leaves only, never a sibling validator.

Archived-audit disposition belongs to `audit.py close`, which refuses to archive an
audit whose FINDINGS.jsonl fails `check`.
"""

from __future__ import annotations

from pathlib import Path

from dadaia_workspace.core.doctor_rules import SectionFinding
from dadaia_workspace.core.workspace_layout import AUDIT_DIR_NAME_RE
from dadaia_workspace.features.specs.canon import REQUIRED_ROOT_DIRS
from dadaia_workspace.features.specs.doctor_types import Severity, finding_path, specs_finding

# Legacy audit dirs exempt from the naming law: their session ids are unrecoverable, and
# immutable ledger reports cite their timestamps.
_AUDIT_DIR_GRANDFATHER: frozenset[str] = frozenset(
    {
        "2026-06-09T075056Z",
        "2026-06-10T010550Z",
        "2026-06-10T052944Z",
        "2026-06-10T140553Z",
    }
)

# The per-artifact ``_archive`` dirs that must exist: the histo landing zones of backlog
# and bugs, a subset of REQUIRED_ROOT_DIRS. Releases and audits archive rarely, so a
# missing ``_archive`` there is not drift and is not checked.
_ARCHIVE_PARENT_DIRS: tuple[str, ...] = tuple(
    d for d in REQUIRED_ROOT_DIRS if d in ("backlog", "bugs")
)


class ClosureAuditValidator:
    """Orphan specs and audit-disposition invariants."""

    def __init__(self, specs_dir: Path) -> None:
        self.specs_dir = specs_dir

    def check_audits_naming_canon(self) -> list[SectionFinding]:
        """WARN on each ``specs/audits/`` dir not named ``<YYYYMMDD>-<slug>``.

        The shape is :data:`AUDIT_DIR_NAME_RE` from ``core.workspace_layout``, the one
        home of that pattern. WARN-only: legacy names are never renamed.

        Exempt: the dirs in :data:`_AUDIT_DIR_GRANDFATHER` and ``specs/audits/_archive/``.
        Silent when the ``audits/`` dir is absent.
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
        """WARN on each missing ``specs/{backlog,bugs}/_archive/`` dir, auto-fixable.

        Those are the additive histo landing zones for disposed artifacts. A parent dir
        that does not exist is skipped: its absence is a tree finding, not this one.
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
        """Create the missing ``_archive`` dir named by *issue*. Writes no ``.gitkeep``."""
        assert issue.code == "SPEC-DOC-034"
        target = Path(str(finding_path(issue)))
        target.mkdir(parents=True, exist_ok=True)
