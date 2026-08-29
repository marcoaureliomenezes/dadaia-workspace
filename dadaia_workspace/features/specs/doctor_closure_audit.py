"""Closure/audit validator (v0.1.55 FR1): orphan specs, audit disposition.

Single-responsibility sibling of the SpecsDoctor coordinator. Owns orphan-spec detection
(SPEC-DOC-007), audit naming canon (SPEC-DOC-030), the per-artifact ``_archive`` landing
zones (SPEC-DOC-034 + ``fix_archive_dir``), archived-audit disposition (SPEC-DOC-036), and
archive-due detection (SPEC-DOC-038). Leaf-only: imports the shared leaves, never a sibling
validator.

v0.5.0 FR15 (T-050-25, ``audit-canon-v1`` D5/D7): SPEC-DOC-036/038 no longer regex audit
prose — the disposition-marker pattern the former ``check_audit_disposition`` matched
against ``**Disposition:** vX.Y.Z`` lines is deleted outright (A15.1). Both checks fold
``specs/audits/<slug>/FINDINGS.jsonl`` instead, through the ``_iter_findings`` seam below.

v0.5.0 FR15 extended scope (T-050-25A, A4.4): ``check_archive_closures`` (SPEC-DOC-006,
CLOSURE.md-completeness) is DELETED here, not adapted — FR4/T-050-21A retired
``CLOSURE.md`` outright, and a checker that parses a file which no longer exists is dead
code behind a dead artifact, the exact shape this release exists to stop. The same task
also swaps ``_iter_findings`` from a plain dict yield onto
:class:`~dadaia_workspace.core.models.findings.FindingRecord`, the typed model T-050-23
landed — through an optional ``findings_store_factory`` seam (mirrors
``features.agents.reader``'s ``store_factory`` DI) so this leaf-only module never gains a
``features -> infrastructure`` edge: the production default is a zero-dependency parse
over the SAME model; the generic
:class:`~dadaia_workspace.infrastructure.jsonl_record_store.JsonlRecordStore`, registered
at :func:`~dadaia_workspace.container.build_findings_store`, is the SAME read shape the
moment a caller injects it.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Iterator
from pathlib import Path

from dadaia_workspace.core.models.findings import FindingRecord
from dadaia_workspace.core.protocols.record_store import RecordStore
from dadaia_workspace.core.workspace_layout import AUDIT_DIR_NAME_RE
from dadaia_workspace.features.specs.canon import REQUIRED_ROOT_DIRS
from dadaia_workspace.features.specs.doctor_types import Severity, SpecsDoctorIssue

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
# (the FROZEN landing zone for disposed artifacts). Anchored to the canon table's
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

# FR13 (D5): a finding's mutable governance triple. A record is done once its
# ``disposition`` lands here AND names a disposing ``release`` — the only two facts
# SPEC-DOC-036/038 need out of the finding-record shape.
_TERMINAL_DISPOSITIONS: frozenset[str] = frozenset({"fixed", "superseded", "deferred", "rejected"})

# Names never treated as a per-audit entry when walking ``audits/`` or ``audits/_archive/``.
_AUDIT_DIR_SKIP_NAMES: frozenset[str] = frozenset({"README.md"})


def _default_iter_findings(findings_path: Path) -> Iterator[FindingRecord]:
    """Zero-dependency fallback reader — one :class:`FindingRecord` per well-formed
    JSONL line of *findings_path*.

    Used whenever no ``findings_store_factory`` is injected (the production default
    until a caller wires :func:`~dadaia_workspace.container.build_findings_store` in) —
    plain file I/O + ``json.loads`` + ``FindingRecord.from_dict``, never a hand-kept
    field mirror (T-050-25's original ``_iter_findings`` note, now satisfied by the
    typed model instead of a bare dict). Missing file or a malformed line/record yields
    nothing for that line — this validator never raises on a corrupt/absent findings
    file.
    """
    if not findings_path.is_file():
        return
    with findings_path.open(encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            try:
                raw = json.loads(stripped)
            except json.JSONDecodeError:
                continue
            if not isinstance(raw, dict):
                continue
            try:
                yield FindingRecord.from_dict(raw)
            except (ValueError, TypeError):
                continue


class ClosureAuditValidator:
    """Orphan specs and audit-disposition invariants."""

    def __init__(
        self,
        specs_dir: Path,
        findings_store_factory: Callable[[Path], RecordStore[FindingRecord]] | None = None,
    ) -> None:
        self.specs_dir = specs_dir
        # DI seam (A13.4): injected by a composition root that wires
        # container.build_findings_store; None keeps the zero-dependency default reader
        # (_default_iter_findings) so this leaf module never imports infrastructure.
        self._findings_store_factory = findings_store_factory

    def _iter_findings(self, findings_path: Path) -> Iterator[FindingRecord]:
        if self._findings_store_factory is not None:
            yield from self._findings_store_factory(findings_path).iter_records()
            return
        yield from _default_iter_findings(findings_path)

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
        be named ``<YYYYMMDDTHHMMSSZ>-<session_id_8chars>`` (:data:`AUDIT_DIR_NAME_RE`,
        the single home in ``core.workspace_layout``) so two concurrent additive sessions
        never collide on a path. WARN-only (legacy names are preserved, never
        auto-renamed), mirroring the SPEC-DOC-027 legacy policy.

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
        artifacts. A missing dir is a WARNING with an auto-fix (``doctor --fix`` mkdirs
        it — a directory is kept by its own future content, no ``.gitkeep``
        placeholder). A parent dir that does not itself exist is skipped — its
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
        """Create a missing ``_archive`` dir (SPEC-DOC-034 auto-fix). A directory is
        kept by its own future content — no ``.gitkeep`` placeholder is written."""
        assert issue.code == "SPEC-DOC-034"
        target = Path(issue.path)  # type: ignore[arg-type]
        target.mkdir(parents=True, exist_ok=True)

    def check_audit_disposition(self) -> list[SpecsDoctorIssue]:
        """SPEC-DOC-036 (v0.5.0 FR15, A15.1/A15.2): fold ``FINDINGS.jsonl``, never prose.

        Every immediate child of ``specs/audits/_archive/`` that carries a
        ``FINDINGS.jsonl`` is folded (:meth:`_iter_findings`): any record whose
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
            if child.name.endswith("_histo.jsonl"):
                continue  # the area history file is not an archived audit
            if child.name in _AUDIT_DIR_SKIP_NAMES:
                continue
            findings_path = child / "FINDINGS.jsonl" if child.is_dir() else None
            if findings_path is None or not findings_path.is_file():
                legacy_names.append(child.name)
                continue
            for record in self._iter_findings(findings_path):
                if record.disposition != "open":
                    continue
                issues.append(
                    SpecsDoctorIssue(
                        code="SPEC-DOC-036",
                        severity=Severity.ERROR,
                        description=(
                            f"audits/_archive/{child.name}: finding "
                            f"{record.id} is still 'open' inside an archived "
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
        (:meth:`_iter_findings`). A live audit still carrying an open record, or one
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
            records = list(self._iter_findings(child / "FINDINGS.jsonl"))
            if not records:
                continue
            if all(
                record.disposition in _TERMINAL_DISPOSITIONS and record.release
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
