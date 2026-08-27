"""Closure/audit validator (v0.1.55 FR1): archive closures, orphan specs, audit disposition.

Single-responsibility sibling of the SpecsDoctor coordinator. Owns archive-CLOSURE completeness
(SPEC-DOC-006), orphan-spec detection (SPEC-DOC-007), audit naming canon (SPEC-DOC-030), the
per-artifact ``_archive`` landing zones (SPEC-DOC-034 + ``fix_archive_dir``), archived-audit
disposition (SPEC-DOC-036), and archive-due detection (SPEC-DOC-038). Leaf-only: imports the
shared leaves, never a sibling validator.

v0.5.0 FR15 (T-050-25, ``audit-canon-v1`` D5/D7): SPEC-DOC-036/038 no longer regex audit
prose — the disposition-marker pattern the former ``check_audit_disposition`` matched
against ``**Disposition:** vX.Y.Z`` lines is deleted outright (A15.1). Both checks fold
``specs/audits/<slug>/FINDINGS.jsonl`` instead, through the ``_iter_findings`` seam below.
``check_archive_closures`` (SPEC-DOC-006, CLOSURE.md) is untouched here — its retirement
is T-050-25A's, once FR4/T-050-21A deletes ``CLOSURE.md`` outright.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterator
from pathlib import Path

from dadaia_workspace.features.specs.doctor_common import (
    is_legacy_nested_release,
    iter_archive_release_dirs,
)
from dadaia_workspace.features.specs.doctor_types import Severity, SpecsDoctorIssue

# SPEC-DOC-030 (constitution §8 collision-safe naming): every new specs/audits/ directory
# must be named ``<YYYYMMDDTHHMMSSZ>-<session_id_8chars>`` so two concurrent additive
# sessions never collide. Compact timestamp (no colons/dashes inside it) + an 8-char
# session discriminator.
AUDIT_DIR_NAME_RE = re.compile(r"^\d{8}T\d{6}Z-[A-Za-z0-9]{8}$")

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

# SPEC-DOC-034 (v0.1.46 AC-4): the three per-artifact ``_archive`` dirs that must exist
# (the FROZEN landing zone for disposed bugs/backlog/audits). Absent → WARN + auto-fix.
_ARCHIVE_PARENT_DIRS: tuple[str, ...] = ("backlog", "audits", "bugs")

# FR13 (D5): a finding's mutable governance triple. A record is done once its
# ``disposition`` lands here AND names a disposing ``release`` — the only two facts
# SPEC-DOC-036/038 need out of the finding-record shape.
_TERMINAL_DISPOSITIONS: frozenset[str] = frozenset({"fixed", "superseded", "deferred", "rejected"})

# Names never treated as a per-audit entry when walking ``audits/`` or ``audits/_archive/``.
_AUDIT_DIR_SKIP_NAMES: frozenset[str] = frozenset({".gitkeep", "README.md"})


def _iter_findings(findings_path: Path) -> Iterator[dict[str, object]]:
    """Yield one dict per JSON line of a ``FINDINGS.jsonl`` file.

    Deliberate seam (T-050-25 note, D15/A14.5 — no CLI verb writes this file; it is
    read here with plain file tools + ``json.loads``, never a typed model). The
    finding-record model/store lands in ``core/models/findings.py`` + the
    ``JsonlRecordStore`` seam under T-050-23, authored concurrently with this task;
    this function is the one place T-050-25A swaps for that model/store once it
    exists. Nothing downstream of this function assumes more than the plain FR13
    field names: ``id, pillar, severity, refs, claim, evidence, disposition,
    release, reason``. Missing file or a malformed line yields nothing for that
    line — this validator never raises on a corrupt/absent findings file.
    """
    if not findings_path.is_file():
        return
    with findings_path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(record, dict):
                yield record


class ClosureAuditValidator:
    """Archive-closure completeness, orphan specs, and audit-disposition invariants."""

    def __init__(self, specs_dir: Path) -> None:
        self.specs_dir = specs_dir

    def check_archive_closures(self) -> list[SpecsDoctorIssue]:
        """SPEC-DOC-006: every archived release dir must have a complete CLOSURE.md.

        v0.1.10 (T-010-14): recurse into nested archive layouts so legacy milestone
        dirs (e.g. ``_archive/releases/v0.2.0/v0.1.9``) that carry SDD release
        artifacts (SPEC/PLAN/TASKS) but no CLOSURE.md are also caught — the original
        check only inspected the top level of ``_archive/releases/``.
        """
        issues: list[SpecsDoctorIssue] = []
        arch = self.specs_dir / "_archive" / "releases"
        if not arch.exists():
            return issues
        for release_dir in iter_archive_release_dirs(arch):
            # Documented-legacy nested milestone dirs (e.g. v0.2.0/v0.1.9) are slated
            # for rename + retro-CLOSURE in T-010-15. Until then they are surfaced at
            # WARNING — not ERROR — so doctor stays exit-0 on the un-repaired tree
            # (matching the SPEC-DOC-026 legacy carve-out). Top-level archive dirs keep
            # the original ERROR contract.
            is_legacy_nested = is_legacy_nested_release(release_dir, arch)
            closure = release_dir / "CLOSURE.md"
            if not closure.exists():
                issues.append(
                    SpecsDoctorIssue(
                        code="SPEC-DOC-006",
                        severity=(Severity.WARNING if is_legacy_nested else Severity.ERROR),
                        description=(
                            "Archived release "
                            f"{release_dir.relative_to(self.specs_dir).as_posix()} "
                            "has no CLOSURE.md"
                            + (
                                " (documented-legacy nested dir — slated for "
                                "rename + retro-CLOSURE in T-010-15)"
                                if is_legacy_nested
                                else ""
                            )
                        ),
                        path=str(closure),
                    )
                )
                continue
            text = closure.read_text(encoding="utf-8")
            required = ["## Summary", "## Validations", "## Drifts", "## Memory updates"]
            missing = [s for s in required if s not in text]
            if missing:
                issues.append(
                    SpecsDoctorIssue(
                        code="SPEC-DOC-006",
                        severity=Severity.ERROR,
                        description=(f"CLOSURE.md missing required sections: {missing}"),
                        path=str(closure),
                    )
                )
            # >=1 evidence triple inside Validations
            val_match = re.search(
                r"## Validations\s*(.*?)(?=^## |\Z)",
                text,
                re.MULTILINE | re.DOTALL,
            )
            if val_match:
                body = val_match.group(1)
                row_count = sum(
                    1
                    for ln in body.splitlines()
                    if re.match(r"^\s*\|[^|]+\|[^|]+\|[^|]+\|", ln)
                    and "---" not in ln
                    and "Description" not in ln
                )
                if row_count < 1:
                    issues.append(
                        SpecsDoctorIssue(
                            code="SPEC-DOC-006",
                            severity=Severity.ERROR,
                            description="CLOSURE.md has no validation triple in ## Validations",
                            path=str(closure),
                        )
                    )
        return issues

    def check_no_orphan_specs(self) -> list[SpecsDoctorIssue]:
        issues: list[SpecsDoctorIssue] = []
        for name in ("SPEC.md", "PLAN.md", "TASKS.md"):
            for p in self.specs_dir.rglob(name):
                rel = p.relative_to(self.specs_dir).as_posix()
                if rel.startswith(("releases/", "_archive/")):
                    continue
                # Top-level SPEC.md/PLAN.md/TASKS.md are legacy roots
                # features/<x>/SPEC.md is legacy too
                issues.append(
                    SpecsDoctorIssue(
                        code="SPEC-DOC-007",
                        severity=Severity.WARNING,
                        description=(
                            f"Legacy {name} outside releases/ or _archive/releases/: {rel}. "
                            "Migrate to a release or archive as a legacy-feature."
                        ),
                        path=str(p),
                    )
                )
        return issues

    def check_audits_naming_canon(self) -> list[SpecsDoctorIssue]:
        """SPEC-DOC-030 (constitution §8): WARN on any non-conforming ``specs/audits/`` dir.

        Forward enforcement of the collision-safe naming law: every audit directory must
        be named ``<YYYYMMDDTHHMMSSZ>-<session_id_8chars>`` (:data:`AUDIT_DIR_NAME_RE`) so
        two concurrent additive sessions never collide on a path. WARN-only (legacy names
        are preserved, never auto-renamed), mirroring the SPEC-DOC-027 legacy policy.

        Exempt: the four grandfathered dirs from the §8 amendment
        (:data:`_AUDIT_DIR_GRANDFATHER`) and ``specs/audits/_archive/``. Silent when the
        ``audits/`` dir is absent.
        """
        audits_dir = self.specs_dir / "audits"
        if not audits_dir.is_dir():
            return []
        issues: list[SpecsDoctorIssue] = []
        for child in sorted(audits_dir.iterdir()):
            if not child.is_dir():
                continue
            name = child.name
            if name == "_archive" or name in _AUDIT_DIR_GRANDFATHER:
                continue
            if AUDIT_DIR_NAME_RE.match(name):
                continue
            issues.append(
                SpecsDoctorIssue(
                    code="SPEC-DOC-030",
                    severity=Severity.WARNING,
                    description=(
                        f"Audit dir 'audits/{name}' does not follow the collision-safe "
                        "naming law <YYYYMMDDTHHMMSSZ>-<session_id_8chars> (constitution §8) "
                        "— rename it (SPEC-DOC-030, WARNING)."
                    ),
                    path=str(child),
                )
            )
        return issues

    def check_archive_dirs_exist(self) -> list[SpecsDoctorIssue]:
        """SPEC-DOC-034 (v0.1.46 AC-4): the three per-artifact ``_archive`` dirs must exist.

        ``specs/{backlog,audits,bugs}/_archive/`` are the FROZEN landing zones for disposed
        artifacts. A missing dir is a WARNING with an auto-fix (``doctor --fix`` mkdirs it
        with a ``.gitkeep``). A parent dir that does not itself exist is skipped — its
        absence is a separate TREE-4 concern, not this taxonomy invariant.
        """
        issues: list[SpecsDoctorIssue] = []
        for parent in _ARCHIVE_PARENT_DIRS:
            parent_dir = self.specs_dir / parent
            if not parent_dir.is_dir():
                continue
            archive_dir = parent_dir / "_archive"
            if archive_dir.is_dir():
                continue
            issues.append(
                SpecsDoctorIssue(
                    code="SPEC-DOC-034",
                    severity=Severity.WARNING,
                    description=(
                        f"specs/{parent}/_archive/ is missing — the FROZEN landing zone for "
                        "disposed artifacts (SPEC-DOC-034, WARNING). Auto-fix available "
                        "(run doctor --fix)."
                    ),
                    path=str(archive_dir),
                    fixable=True,
                )
            )
        return issues

    def fix_archive_dir(self, issue: SpecsDoctorIssue) -> None:
        """Create a missing ``_archive`` dir with a ``.gitkeep`` (SPEC-DOC-034 auto-fix)."""
        assert issue.code == "SPEC-DOC-034"
        target = Path(issue.path)  # type: ignore[arg-type]
        target.mkdir(parents=True, exist_ok=True)
        gitkeep = target / ".gitkeep"
        if not gitkeep.exists():
            gitkeep.write_text("", encoding="utf-8")

    def check_audit_disposition(self) -> list[SpecsDoctorIssue]:
        """SPEC-DOC-036 (v0.5.0 FR15, A15.1/A15.2): fold ``FINDINGS.jsonl``, never prose.

        Every immediate child of ``specs/audits/_archive/`` that carries a
        ``FINDINGS.jsonl`` is folded (:func:`_iter_findings`): any record whose
        ``disposition`` is still ``"open"`` is an ERROR — an audit archives only once
        every finding is terminal (D5/D7). A child with no ``FINDINGS.jsonl`` predates
        the ``audit-canon-v1`` schema (Markdown-only, pre-canon) and is never itself
        inspected for a disposition marker — that regex is deleted (A15.1). It is
        instead counted into a single aggregate WARNING so the legacy population stays
        visible without turning into N false positives per legacy audit. Absent
        ``audits/_archive/`` dir → no-op.
        """
        archive_dir = self.specs_dir / "audits" / "_archive"
        if not archive_dir.is_dir():
            return []
        issues: list[SpecsDoctorIssue] = []
        legacy_names: list[str] = []
        for child in sorted(archive_dir.iterdir()):
            if child.name in _AUDIT_DIR_SKIP_NAMES:
                continue
            findings_path = child / "FINDINGS.jsonl" if child.is_dir() else None
            if findings_path is None or not findings_path.is_file():
                legacy_names.append(child.name)
                continue
            for record in _iter_findings(findings_path):
                if record.get("disposition") != "open":
                    continue
                issues.append(
                    SpecsDoctorIssue(
                        code="SPEC-DOC-036",
                        severity=Severity.ERROR,
                        description=(
                            f"audits/_archive/{child.name}: finding "
                            f"{record.get('id', '?')} is still 'open' inside an archived "
                            "audit — an audit archives only once every finding is terminal "
                            "(SPEC-DOC-036, ERROR)."
                        ),
                        path=str(findings_path),
                    )
                )
        if legacy_names:
            issues.append(
                SpecsDoctorIssue(
                    code="SPEC-DOC-036",
                    severity=Severity.WARNING,
                    description=(
                        f"{len(legacy_names)} archived audit(s) under audits/_archive/ "
                        "predate the FINDINGS.jsonl canon (audit-canon-v1, D5) and carry no "
                        "FINDINGS.jsonl — skipped by the fold, never an error: "
                        + ", ".join(legacy_names)
                    ),
                    path=str(archive_dir),
                )
            )
        return issues

    def check_loose_undisposed_audits(self) -> list[SpecsDoctorIssue]:
        """SPEC-DOC-038 (v0.5.0 FR15, A15.1/A15.2): fold ``FINDINGS.jsonl`` archive-due WARN.

        A live (non-archived) audit directory directly under ``specs/audits/`` whose
        ``FINDINGS.jsonl`` records are ALL terminal (:data:`_TERMINAL_DISPOSITIONS`) and
        each names a disposing ``release`` is due for archiving — one WARN
        (:func:`_iter_findings`). A live audit still carrying an open record, or one
        with no ``FINDINGS.jsonl`` at all (still in flight, or pre-canon), is silent —
        it is not the doctor's concern until it is fully dispositioned. Silent when
        ``audits/`` is absent or holds only ``_archive/``.
        """
        audits_dir = self.specs_dir / "audits"
        if not audits_dir.is_dir():
            return []
        issues: list[SpecsDoctorIssue] = []
        for child in sorted(audits_dir.iterdir()):
            if not child.is_dir() or child.name == "_archive":
                continue
            records = list(_iter_findings(child / "FINDINGS.jsonl"))
            if not records:
                continue
            if all(
                record.get("disposition") in _TERMINAL_DISPOSITIONS and record.get("release")
                for record in records
            ):
                issues.append(
                    SpecsDoctorIssue(
                        code="SPEC-DOC-038",
                        severity=Severity.WARNING,
                        description=(
                            f"audits/{child.name} is fully dispositioned (every finding "
                            "terminal, each naming a release) — archive due (SPEC-DOC-038, "
                            "WARNING)."
                        ),
                        path=str(child),
                    )
                )
        return issues
