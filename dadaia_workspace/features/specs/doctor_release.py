"""Release validator (v0.1.55 FR1): ACTIVE.md, release artifacts, SemVer + ledger invariants.

Single-responsibility sibling of the SpecsDoctor coordinator. Owns the active-release lifecycle
checks (SPEC-DOC-003/004/005/009), SemVer naming (SPEC-DOC-016), and the release ledger
invariants (phase↔markers SPEC-DOC-024, unique ids SPEC-DOC-026, naming canon SPEC-DOC-027), plus
the family-local status/created-date extractors. Leaf-only: imports the shared leaves + core,
never a sibling validator.
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from dadaia_workspace.core.specs_version import RELEASE_SEMVER_RE
from dadaia_workspace.features.specs.doctor_common import iter_all_release_dirs, read_active_md
from dadaia_workspace.features.specs.doctor_types import Severity, SpecsDoctorIssue

CANONICAL_STATUS = {"Draft", "Em revisão", "Aprovado"}
CANONICAL_PHASES = {
    "DISCOVERY",
    "DEFINITION",  # v0.1.7: release-definition phase; product-engineer authors memory here
    "SPEC",
    "PLAN",
    "TASKS",
    "IMPLEMENTATION",
    "CLOSURE",
    "ARCHIVED",
    "none",  # scaffold default: no active release
}
HARD_LIMIT_PLAN_CUTOFF = date(2026, 5, 17)
PLAN_MAX_LINES = 300

# SPEC-DOC-016: SemVer folder naming for releases created on/after this date (D3).
# Vintage releases (Created: <= 2026-06-04) are excluded — this grandfathers the frozen
# pre-June-5 _archive sub-patch releases (v0.1.4.1..v0.1.4.6, ctx-inject-v2-drift-fix-v1)
# that predate the SemVer-folder mandate's rollout; the rule keeps hard-enforcing for
# every release created after the cutoff (v0.1.44 onward). See specs/bugs/
# specs-doctor-errors-on-frozen-nonsemver-archives.md (v0.1.45).
# RELEASE_SEMVER_RE is the shared canon (core.specs_version), imported above — v0.1.53 FR3
# centralised the pattern; the module-level name is preserved for the call sites below.
RELEASE_SEMVER_CUTOFF = date(2026, 6, 1)  # WARNING starts here
RELEASE_SEMVER_HARD = date(2026, 7, 1)  # ERROR starts here
RELEASE_VINTAGE_CUTOFF = date(2026, 6, 4)  # releases on/before this are excluded

# SPEC-DOC-027 (ADR-9, v0.1.11): permanent documented allowlist of legacy ``_archive``
# release-dir names that predate the SemVer naming canon. These are FROZEN HISTORY:
# renaming an archived dir would break historical pointers and is pure churn, so the
# honest permanent record is this enumerated allowlist (rationale: ADR-9). The doctor
# stays silent for exactly these names *only inside _archive/releases/* — they never
# silence a non-canon dir in the LIVE releases/ tree, and any name NOT in this set
# still WARNs, so forward enforcement for new/unrecognised legacy dirs is intact.
#   - ``ctx-inject-v2-drift-fix-v1`` / ``memory-markdown-source-v1``: pre-canon
#     descriptive-slug releases (the slug-naming era before SemVer dirs).
#   - ``v0.1.4.1``..``v0.1.4.6`` + ``v0.1.4.3-report-retention``: the v0.1.4.x hotfix
#     family, four-segment + suffixed names that predate the three-segment canon.
RELEASE_NAMING_LEGACY_ALLOWLIST: frozenset[str] = frozenset(
    {
        "ctx-inject-v2-drift-fix-v1",
        "memory-markdown-source-v1",
        "v0.1.4.1",
        "v0.1.4.2",
        "v0.1.4.3",
        "v0.1.4.3-report-retention",
        "v0.1.4.4",
        "v0.1.4.5",
        "v0.1.4.6",
    }
)

# SPEC-DOC-024: phase ↔ markers coherence.
_TASK_MARKER_RE = re.compile(r"^\s*[-*]?\s*\[([ \-xX])\]", re.MULTILINE)


def _extract_status(md_path: Path) -> str | None:
    if not md_path.exists():
        return None
    for line in md_path.read_text(encoding="utf-8").splitlines()[:30]:
        m = re.search(r"\*\*Status:\*\*\s*(.+?)\s*$", line)
        if m:
            return m.group(1).strip()
    return None


def _extract_created_date(md_path: Path) -> date | None:
    if not md_path.exists():
        return None
    for line in md_path.read_text(encoding="utf-8").splitlines()[:30]:
        m = re.search(r"\*\*Created:\*\*\s*(\d{4}-\d{2}-\d{2})", line)
        if m:
            try:
                y, mo, d = (int(x) for x in m.group(1).split("-"))
                return date(y, mo, d)
            except ValueError:
                return None
    return None


class ReleaseValidator:
    """Active-release lifecycle, SemVer naming, and release-ledger invariants."""

    def __init__(self, specs_dir: Path) -> None:
        self.specs_dir = specs_dir

    def check_active_md(self) -> list[SpecsDoctorIssue]:
        issues: list[SpecsDoctorIssue] = []
        path = self.specs_dir / "releases" / "ACTIVE.md"
        release, segment, phase, err = read_active_md(path)
        if err:
            issues.append(
                SpecsDoctorIssue(
                    code="SPEC-DOC-003",
                    severity=Severity.ERROR,
                    description=err,
                    path=str(path),
                )
            )
            return issues
        if phase not in CANONICAL_PHASES:
            issues.append(
                SpecsDoctorIssue(
                    code="SPEC-DOC-003",
                    severity=Severity.ERROR,
                    description=(
                        f"ACTIVE.md phase '{phase}' is not canonical. "
                        f"Valid: {sorted(CANONICAL_PHASES)}"
                    ),
                    path=str(path),
                )
            )
        if release and release != "none":
            release_dir = self.specs_dir / "releases" / release
            if not release_dir.exists():
                issues.append(
                    SpecsDoctorIssue(
                        code="SPEC-DOC-009",
                        severity=Severity.ERROR,
                        description=(
                            f"ACTIVE.md release='{release}' but no directory at {release_dir}"
                        ),
                        path=str(release_dir),
                    )
                )
        return issues

    def check_active_release_artifacts(self) -> list[SpecsDoctorIssue]:
        issues: list[SpecsDoctorIssue] = []
        path = self.specs_dir / "releases" / "ACTIVE.md"
        release, segment, phase, err = read_active_md(path)
        if err or not release or release == "none":
            return issues
        # Schema v2 (ADR-1/ADR-5): when ACTIVE.md carries a segment, the active
        # SPEC/PLAN/TASKS live in releases/<release>/<segment>/; else flat.
        rdir = self.specs_dir / "releases" / release
        if segment:
            rdir = rdir / segment
        if not rdir.exists():
            return issues  # already reported by check 9
        for fname in ("SPEC.md", "PLAN.md", "TASKS.md"):
            fpath = rdir / fname
            if not fpath.exists():
                issues.append(
                    SpecsDoctorIssue(
                        code="SPEC-DOC-004",
                        severity=Severity.ERROR,
                        description=f"Active release missing {fname}",
                        path=str(fpath),
                    )
                )
                continue
            status = _extract_status(fpath)
            if status is None:
                issues.append(
                    SpecsDoctorIssue(
                        code="SPEC-DOC-004",
                        severity=Severity.ERROR,
                        description=f"{fname} has no `**Status:**` line",
                        path=str(fpath),
                    )
                )
            elif status not in CANONICAL_STATUS:
                issues.append(
                    SpecsDoctorIssue(
                        code="SPEC-DOC-004",
                        severity=Severity.ERROR,
                        description=(
                            f"{fname} Status='{status}' is not canonical. "
                            f"Valid: {sorted(CANONICAL_STATUS)}"
                        ),
                        path=str(fpath),
                    )
                )
            elif status != "Aprovado" and phase != "ARCHIVED":
                issues.append(
                    SpecsDoctorIssue(
                        code="SPEC-DOC-004",
                        severity=Severity.WARNING,
                        description=(
                            f"{fname} is '{status}' but ACTIVE.md phase is '{phase}'; "
                            "expected 'Aprovado' for implementation-bound phases"
                        ),
                        path=str(fpath),
                    )
                )
        return issues

    def check_plan_line_limit(self) -> list[SpecsDoctorIssue]:
        issues: list[SpecsDoctorIssue] = []
        for plan in self.specs_dir.glob("releases/*/PLAN.md"):
            n_lines = sum(1 for _ in plan.read_text(encoding="utf-8").splitlines())
            if n_lines <= PLAN_MAX_LINES:
                continue
            spec = plan.with_name("SPEC.md")
            created = _extract_created_date(spec) if spec.exists() else None
            severity = (
                Severity.ERROR
                if (created is not None and created >= HARD_LIMIT_PLAN_CUTOFF)
                else Severity.WARNING
            )
            issues.append(
                SpecsDoctorIssue(
                    code="SPEC-DOC-005",
                    severity=severity,
                    description=(
                        f"PLAN.md has {n_lines} lines > {PLAN_MAX_LINES} "
                        f"(created={created or 'unknown'})"
                    ),
                    path=str(plan),
                )
            )
        return issues

    def check_release_semver_naming(self) -> list[SpecsDoctorIssue]:
        """SPEC-DOC-016: release folder names must follow SemVer (v<M>.<m>.<p>) for releases
        whose SPEC.md has Created: >= RELEASE_SEMVER_CUTOFF.

        Vintage releases (Created: <= RELEASE_VINTAGE_CUTOFF) are excluded.
        Severity: WARNING until RELEASE_SEMVER_HARD, ERROR on/after that date.

        Applies to both specs/releases/ and specs/_archive/releases/.
        """
        issues: list[SpecsDoctorIssue] = []
        today = date.today()

        # Only run this check if we are at or past the cutoff
        if today < RELEASE_SEMVER_CUTOFF:
            return issues

        severity = Severity.ERROR if today >= RELEASE_SEMVER_HARD else Severity.WARNING

        for releases_root in (
            self.specs_dir / "releases",
            self.specs_dir / "_archive" / "releases",
        ):
            if not releases_root.exists():
                continue
            for entry in releases_root.iterdir():
                if not entry.is_dir():
                    continue
                folder_name = entry.name
                # Resolve Created: date from SPEC.md
                spec_path = entry / "SPEC.md"
                created = _extract_created_date(spec_path) if spec_path.exists() else None

                # Skip vintage releases (Created: <= RELEASE_VINTAGE_CUTOFF)
                if created is not None and created <= RELEASE_VINTAGE_CUTOFF:
                    continue

                # Skip releases without a determinable Created: date
                # (they could be legacy — give benefit of the doubt)
                if created is None:
                    continue

                # Skip releases created before the cutoff
                if created < RELEASE_SEMVER_CUTOFF:
                    continue

                if not RELEASE_SEMVER_RE.match(folder_name):
                    issues.append(
                        SpecsDoctorIssue(
                            code="SPEC-DOC-016",
                            severity=severity,
                            description=(
                                f"Release folder '{folder_name}' does not follow SemVer "
                                f"naming (^v\\d+\\.\\d+\\.\\d+$). Created: {created}. "
                                "Rename to v<MAJOR>.<MINOR>.<PATCH> (D3, SPEC-DOC-016)."
                            ),
                            path=str(entry),
                        )
                    )
        return issues

    def _active_tasks_markers(self, release: str, segment: str | None) -> list[str] | None:
        """Return the list of task marker chars (' ', '-', 'x') for the active release's
        TASKS.md, or None when TASKS.md is absent/unreadable."""
        rdir = self.specs_dir / "releases" / release
        if segment:
            rdir = rdir / segment
        tasks = rdir / "TASKS.md"
        if not tasks.exists():
            return None
        text = tasks.read_text(encoding="utf-8")
        return [m.group(1).lower() for m in _TASK_MARKER_RE.finditer(text)]

    def check_phase_markers_coherence(self) -> list[SpecsDoctorIssue]:
        """SPEC-DOC-024: ACTIVE.md ``phase`` must be coherent with the active release's
        TASKS.md markers (constitution §7 lifecycle).

        Mechanical rules (minimal):
        - phase ∈ {SPEC, DEFINITION}: the active TASKS must NOT already be an
          ``[x]``-majority (work claimed complete before implementation began —
          the live audit incident where phase=SPEC but 19/19 tasks were ``[x]``).
        - phase == IMPLEMENTATION: TASKS.md must exist and carry ``**Status:** Aprovado``.
        - phase == CLOSURE: every non-CLOSURE task must be ``[x]`` (no ``[ ]``/``[-]``).
        Other phases are not constrained here.
        """
        issues: list[SpecsDoctorIssue] = []
        active_path = self.specs_dir / "releases" / "ACTIVE.md"
        release, segment, phase, err = read_active_md(active_path)
        if err or not release or release == "none" or phase is None:
            return issues
        rdir = self.specs_dir / "releases" / release
        if segment:
            rdir = rdir / segment
        if not rdir.exists():
            return issues  # release dir issues already reported by SPEC-DOC-009/004

        markers = self._active_tasks_markers(release, segment)

        if phase in ("SPEC", "DEFINITION"):
            if markers:
                done = sum(1 for m in markers if m == "x")
                if done * 2 > len(markers):  # strict [x]-majority
                    issues.append(
                        SpecsDoctorIssue(
                            code="SPEC-DOC-024",
                            severity=Severity.ERROR,
                            description=(
                                f"ACTIVE.md phase='{phase}' but the active release "
                                f"'{release}' has an [x]-majority TASKS.md "
                                f"({done}/{len(markers)} done). The phase field was "
                                "never advanced through IMPLEMENTATION — advance ACTIVE.md "
                                "or correct the markers (constitution §7)."
                            ),
                            path=str(active_path),
                        )
                    )
        elif phase == "IMPLEMENTATION":
            tasks = rdir / "TASKS.md"
            if not tasks.exists():
                issues.append(
                    SpecsDoctorIssue(
                        code="SPEC-DOC-024",
                        severity=Severity.ERROR,
                        description=(
                            f"ACTIVE.md phase='IMPLEMENTATION' but active release "
                            f"'{release}' has no TASKS.md."
                        ),
                        path=str(tasks),
                    )
                )
            elif _extract_status(tasks) != "Aprovado":
                issues.append(
                    SpecsDoctorIssue(
                        code="SPEC-DOC-024",
                        severity=Severity.ERROR,
                        description=(
                            f"ACTIVE.md phase='IMPLEMENTATION' but TASKS.md of release "
                            f"'{release}' is not '**Status:** Aprovado' "
                            f"(found '{_extract_status(tasks)}'). Implementation phase "
                            "requires an approved TASKS.md (constitution §7)."
                        ),
                        path=str(tasks),
                    )
                )
        elif phase == "CLOSURE" and markers is not None:
            unfinished = sum(1 for m in markers if m != "x")
            if unfinished:
                issues.append(
                    SpecsDoctorIssue(
                        code="SPEC-DOC-024",
                        severity=Severity.ERROR,
                        description=(
                            f"ACTIVE.md phase='CLOSURE' but active release '{release}' "
                            f"has {unfinished} unfinished task marker(s) "
                            "(expected every task '[x]' before closure; "
                            "constitution §7)."
                        ),
                        path=str(active_path),
                    )
                )
        return issues

    def check_unique_release_ids(self) -> list[SpecsDoctorIssue]:
        """SPEC-DOC-026: release ids (dir basenames) must be unique across
        ``releases/`` ∪ ``_archive/releases/`` (recursive).

        A collision among two real (non-legacy) dirs is an ERROR. A collision that
        involves a documented-legacy nested dir (``v0.2.0/v0.1.9`` milestone layout)
        is a WARNING — these are slated for rename in T-010-15 and must not break
        doctor exit-0 in the meantime.
        """
        issues: list[SpecsDoctorIssue] = []
        by_name: dict[str, list[tuple[Path, bool]]] = {}
        for d, _root, is_legacy in iter_all_release_dirs(self.specs_dir):
            by_name.setdefault(d.name, []).append((d, is_legacy))

        for name, entries in sorted(by_name.items()):
            if len(entries) < 2:
                continue
            any_legacy = any(is_legacy for _d, is_legacy in entries)
            severity = Severity.WARNING if any_legacy else Severity.ERROR
            paths = ", ".join(d.relative_to(self.specs_dir).as_posix() for d, _ in sorted(entries))
            note = (
                " (documented-legacy nested dir — slated for rename in T-010-15)"
                if any_legacy
                else ""
            )
            issues.append(
                SpecsDoctorIssue(
                    code="SPEC-DOC-026",
                    severity=severity,
                    description=(
                        f"Release id '{name}' is not unique across releases/ + "
                        f"_archive/releases/: {paths}{note}."
                    ),
                    path=str(self.specs_dir / "_archive" / "releases"),
                )
            )
        return issues

    def check_release_naming_canon(self) -> list[SpecsDoctorIssue]:
        """SPEC-DOC-027: release dir names should match ``^v\\d+\\.\\d+\\.\\d+$``.

        Severity follows the same legacy policy as SPEC-DOC-016 so the two checks
        never disagree:
        - A non-conforming dir in the live ``releases/`` tree whose SPEC.md
          ``Created:`` date is on/after the canon cutoff (``RELEASE_SEMVER_CUTOFF``)
          is an ERROR — a release born after the canon must be SemVer-clean.
        - Every other non-conforming dir (archive, vintage ``Created:`` ≤
          ``RELEASE_VINTAGE_CUTOFF``, pre-cutoff, or undeterminable date) is a
          WARNING — legacy names predate the canon and are preserved until renamed.

        ADR-9 (v0.1.11): archived dirs whose name is in the permanent documented
        ``RELEASE_NAMING_LEGACY_ALLOWLIST`` are silenced entirely — they are frozen
        history that is never renamed. The allowlist is name-exact and ``_archive``-only,
        so any unrecognised legacy dir still WARNs and forward enforcement holds.
        """
        issues: list[SpecsDoctorIssue] = []
        for d, root, _is_legacy in iter_all_release_dirs(self.specs_dir):
            if RELEASE_SEMVER_RE.match(d.name):
                continue
            is_live = root == self.specs_dir / "releases"
            # ADR-9: archived dirs on the permanent legacy allowlist are silent (frozen
            # history, never renamed). The allowlist applies ONLY to _archive/ — a
            # non-canon dir in the live releases/ tree is never silenced this way.
            if not is_live and d.name in RELEASE_NAMING_LEGACY_ALLOWLIST:
                continue
            spec_path = d / "SPEC.md"
            created = _extract_created_date(spec_path) if spec_path.exists() else None
            born_after_canon = created is not None and created >= RELEASE_SEMVER_CUTOFF
            severity = Severity.ERROR if (is_live and born_after_canon) else Severity.WARNING
            issues.append(
                SpecsDoctorIssue(
                    code="SPEC-DOC-027",
                    severity=severity,
                    description=(
                        f"Release dir '{d.relative_to(self.specs_dir).as_posix()}' does "
                        "not follow the naming canon ^v<MAJOR>.<MINOR>.<PATCH>$ "
                        + (
                            "— rename it (SPEC-DOC-027)."
                            if severity == Severity.ERROR
                            else "— legacy name (WARNING, preserved until renamed)."
                        )
                    ),
                    path=str(d),
                )
            )
        return issues
