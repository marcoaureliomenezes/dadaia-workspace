"""Release validator: the active release, its artifacts, SemVer + ledger invariants.

Single-responsibility sibling of the SpecsDoctor coordinator. Owns the active-release
lifecycle check (SPEC-DOC-004), the release ledger invariant (unique ids SPEC-DOC-026), plus the family-local status extractor.
A release dir's name and placement are TREE-8's alone.
Leaf-only: imports the shared leaves + core, never a sibling validator.

The active release and its phase are read by :func:`resolve_active_release`; whether the
state document is valid is `release.py check`'s answer (LEDGER-RELEASE-SCHEMA).
"""

from __future__ import annotations

from pathlib import Path

from dadaia_workspace.core.doctor_rules import SectionFinding
from dadaia_workspace.core.release_state import (
    LEGACY_RELEASE_STATE_FILENAME,
    RELEASE_ID_RE,
    RELEASE_STATE_FILENAME,
)
from dadaia_workspace.core.spec_status import APPROVED, extract_status
from dadaia_workspace.core.spec_status import CANONICAL_STATUS as _CANONICAL_STATUS
from dadaia_workspace.features.specs.doctor_common import iter_all_release_dirs
from dadaia_workspace.features.specs.doctor_types import Severity, finding_path, specs_finding
from dadaia_workspace.features.specs.specs_tree import SpecsTree

# Vocabulary + parser live in core.spec_status (single definition); re-exported here
# because doctor_release has been the documented import site for both.
CANONICAL_STATUS = _CANONICAL_STATUS


def _extract_status(md_path: Path) -> str | None:
    """Read a release artifact's declared status. Parsing itself is core.spec_status."""
    if not md_path.exists():
        return None
    return extract_status(md_path.read_text(encoding="utf-8"))


class ReleaseValidator:
    """Active-release lifecycle and release-ledger invariants."""

    def __init__(self, specs_dir: Path) -> None:
        self.specs_dir = specs_dir
        #: Fresh per check() run (assigned by the coordinator, F010) — the parsed
        #: snapshot every active-release read goes through; never survives a fix pass.
        self.tree: SpecsTree = SpecsTree(specs_dir)

    def check_active_release_artifacts(self) -> list[SectionFinding]:
        issues: list[SectionFinding] = []
        active = self.tree.active_release
        if not active.candidate:
            return issues
        for fname in ("SPEC.md", "PLAN.md"):
            fpath = active.candidate / fname
            if not fpath.exists():
                # Presence is `release.py check`'s rule, in ONE home. This rule judges the `**Status:**`
                # line of the trio documents that exist — a second "missing" finding
                # here was the same fact reported twice, and it was what forced the
                # deleted between-candidates DISCOVERY carve-out.
                continue
            status = _extract_status(fpath)
            if status is None:
                issues.append(
                    specs_finding(
                        code="SPEC-DOC-004",
                        severity=Severity.ERROR,
                        description=f"{fname} has no `**Status:**` line",
                        path=str(fpath),
                        fix=f"Operator action: add the `**Status:**` line to {fpath}",
                    )
                )
            elif status not in CANONICAL_STATUS:
                issues.append(
                    specs_finding(
                        code="SPEC-DOC-004",
                        severity=Severity.ERROR,
                        description=(
                            f"{fname} Status='{status}' is not canonical. "
                            f"Valid: {sorted(CANONICAL_STATUS)}"
                        ),
                        path=str(fpath),
                        fix=f"Operator action: set a canonical `**Status:**` in {fpath}",
                    )
                )
            elif status != APPROVED and active.phase in ("IMPLEMENTATION", "CLOSURE"):
                # Bug fresh-release-scaffold-emits-spec-doctor-warnings-042: Draft/In
                # review IS the legitimate state of a DEFINITION-phase release — the
                # scaffolder emits exactly that. Only implementation-bound phases
                # expect approved artifacts.
                issues.append(
                    specs_finding(
                        code="SPEC-DOC-004",
                        severity=Severity.WARNING,
                        description=(
                            f"{fname} is '{status}' but the active release phase is "
                            f"'{active.phase}'; expected '{APPROVED}' for implementation-bound "
                            "phases"
                        ),
                        path=str(fpath),
                    )
                )
        return issues

    def check_unique_release_ids(self) -> list[SectionFinding]:
        """SPEC-DOC-026: release ids (dir basenames) must be unique across
        ``releases/`` ∪ ``releases/_archive/`` (recursive). A collision is an ERROR.
        """
        issues: list[SectionFinding] = []
        by_name: dict[str, list[Path]] = {}
        for d, _root in iter_all_release_dirs(self.specs_dir):
            by_name.setdefault(d.name, []).append(d)

        for name, entries in sorted(by_name.items()):
            if len(entries) < 2:
                continue
            paths = ", ".join(d.relative_to(self.specs_dir).as_posix() for d in sorted(entries))
            issues.append(
                specs_finding(
                    code="SPEC-DOC-026",
                    severity=Severity.ERROR,
                    description=(
                        f"Release id '{name}' is not unique across releases/ + "
                        f"releases/_archive/: {paths}."
                    ),
                    path=str(self.specs_dir / "releases"),
                )
            )
        return issues

    def check_release_state_filename(self) -> list[SectionFinding]:
        """SPEC-DOC-046 (ADR 0007, restored by ADR 0152 (4)): a release directory holds
        the legacy ``RELEASE.json`` and no ``_RELEASE.json`` — `doctor --fix` renames it."""
        return [
            specs_finding(
                "SPEC-DOC-046",
                Severity.WARNING,
                f"{legacy.relative_to(self.specs_dir).as_posix()} carries the legacy state-file name — "
                f"canonical is {RELEASE_STATE_FILENAME} (ADR 0007)",
                str(legacy),
                fixable=True,
            )
            for legacy in sorted(self.specs_dir.glob(f"releases/*/{LEGACY_RELEASE_STATE_FILENAME}"))
            if RELEASE_ID_RE.match(legacy.parent.name)
            and not legacy.with_name(RELEASE_STATE_FILENAME).exists()
        ]

    def fix_release_state_filename(self, issue: SectionFinding) -> None:
        """Rename the legacy state file (SPEC-DOC-046) — re-verified before the rename."""
        if (named := finding_path(issue)) and Path(named).name == LEGACY_RELEASE_STATE_FILENAME:
            legacy = Path(named)
            if legacy.is_file() and not legacy.with_name(RELEASE_STATE_FILENAME).exists():
                legacy.rename(legacy.with_name(RELEASE_STATE_FILENAME))
