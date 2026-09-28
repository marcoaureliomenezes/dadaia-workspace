"""Release validator: the active release, its artifacts, SemVer + ledger invariants.

Single-responsibility sibling of the SpecsDoctor coordinator. Owns the active-release
lifecycle checks (SPEC-DOC-004/005), the release ledger invariants (phase<->markers
SPEC-DOC-024, unique ids SPEC-DOC-026, naming canon SPEC-DOC-027), plus the family-local
status/created-date extractors.
Leaf-only: imports the shared leaves + core, never a sibling validator.

The active release and its phase are read by :func:`resolve_active_release`; whether the
state document is valid is `release.py check`'s answer (LEDGER-RELEASE-SCHEMA).
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Collection
from datetime import date
from pathlib import Path

from dadaia_workspace.core.doctor_rules import SectionFinding
from dadaia_workspace.core.release_state import RELEASE_ID_RE
from dadaia_workspace.core.spec_status import APPROVED, extract_status
from dadaia_workspace.core.spec_status import CANONICAL_STATUS as _CANONICAL_STATUS
from dadaia_workspace.features.specs.doctor_common import RELEASE_ARTIFACTS, iter_all_release_dirs
from dadaia_workspace.features.specs.doctor_types import Severity, specs_finding
from dadaia_workspace.features.specs.specs_tree import SpecsTree

# Vocabulary + parser live in core.spec_status (single definition); re-exported here
# because doctor_release has been the documented import site for both.
CANONICAL_STATUS = _CANONICAL_STATUS
PLAN_MAX_LINES = 300

# Release-id canon cutoff: a live release whose SPEC.md Created: is on/after this date
# must carry a canon-conformant directory name (SPEC-DOC-027). Vintage releases are
# excluded — this grandfathers the frozen pre-cutoff archived releases.
RELEASE_SEMVER_CUTOFF = date(2026, 6, 1)  # WARNING starts here

# SPEC-DOC-047: a task block runs from its marker line to the next marker line; a
# ``Write set:`` naming the ``specs/memory`` tree inside it schedules memory as
# implementation work. Both patterns are anchored: the block indent is HORIZONTAL space
# only (``\s`` spans newlines, so a block matched from the blank line above it reported
# an empty task id), and the path ends on a word boundary, so the source file
# ``features/specs/memory_lint.py`` is not the memory tree.
_TASK_BLOCK_RE = re.compile(
    r"^[ \t]*[-*]?[ \t]*\[[ \-xX]\][^\n]*(?:\n(?![ \t]*[-*]?[ \t]*\[[ \-xX]\])[^\n]*)*",
    re.MULTILINE,
)
_MEMORY_WRITE_SET_RE = re.compile(r"Write set:[^\n]*\bspecs/memory\b")


def _extract_status(md_path: Path) -> str | None:
    """Read a release artifact's declared status. Parsing itself is core.spec_status."""
    if not md_path.exists():
        return None
    return extract_status(md_path.read_text(encoding="utf-8"))


_ORIGIN_RE = re.compile(r"^\*\*Origin:\*\*\s*(.+?)\s*$", re.MULTILINE)
_OPERATOR_DEMAND = "operator-demand"
_ORIGIN_VOCABULARY = f"{_OPERATOR_DEMAND} | backlog:<id>[,..] | bugs:<id>[,..]"


def _json_records(path: Path) -> list[dict[str, object]]:
    """Every JSON object in *path*, read as a document or as one object per line."""
    if not path.is_file():
        return []
    text = path.read_text(encoding="utf-8")
    lines = [text] if path.suffix == ".json" else text.splitlines()
    records: list[dict[str, object]] = []
    for line in lines:
        if not line.strip():
            continue
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            records.append(parsed)
    return records


def _known_backlog_ids(specs_dir: Path) -> frozenset[str]:
    """Every backlog id a SPEC may cite: the live entries plus the archived histo."""
    backlog = specs_dir / "backlog"
    document = _json_records(backlog / "BACKLOG.json")
    active = document[0].get("active", []) if document else []
    entries: list[object] = list(active) if isinstance(active, list) else []
    entries += _json_records(backlog / "_archive" / "backlog_histo.jsonl")
    return frozenset(
        str(e["id"]) for e in entries if isinstance(e, dict) and e.get("id") is not None
    )


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
        #: Fresh per check() run (assigned by the coordinator, F010) — the parsed
        #: snapshot every active-release read goes through; never survives a fix pass.
        self.tree: SpecsTree = SpecsTree(specs_dir)

    def check_spec_origin(
        self, known_bug_ids: Callable[[], Collection[str]]
    ) -> list[SectionFinding]:
        """SPEC-DOC-048: the live SPEC names where the work came from — the header is the
        flow's only machine-read input. A closed candidate is history in git, never ranked.

        ``known_bug_ids`` is read lazily: a tree citing no bug never touches the bug
        ledger, so this rule borrows the governance family's ONE bug reader without
        forcing its store on every construction site.
        """
        release = self.tree.active_release.release
        if not release:
            return []
        path = self.specs_dir / "releases" / release / "SPEC.md"
        if not path.exists() or not (problem := self._origin_problem(path, known_bug_ids)):
            return []
        fix = f"Operator action: name the work's origin under **Opened:** in {path}"
        description = f"{path.relative_to(self.specs_dir)} {problem}"
        return [specs_finding("SPEC-DOC-048", Severity.ERROR, description, str(path), fix=fix)]

    def _origin_problem(self, path: Path, known_bug_ids: Callable[[], Collection[str]]) -> str:
        """One SPEC header judged — presence, vocabulary, then the cited ids; "" is clean."""
        match = _ORIGIN_RE.search(path.read_text(encoding="utf-8"))
        if match is None:
            return f"has no `**Origin:**` line — every live and candidate SPEC declares its origin ({_ORIGIN_VOCABULARY})"
        value = match.group(1)
        if value == _OPERATOR_DEMAND:
            return ""
        kind, _, rest = value.partition(":")
        cited = [i.strip() for i in rest.split(",") if i.strip()]
        if kind == "backlog" and cited:
            unknown = [i for i in cited if i not in _known_backlog_ids(self.specs_dir)]
            return (
                f"Origin cites backlog {', '.join(unknown)} — no such entry in "
                "backlog/BACKLOG.json or backlog/_archive/backlog_histo.jsonl"
                if unknown
                else ""
            )
        if kind == "bugs" and cited:
            known = set(known_bug_ids())
            unknown = [i for i in cited if i not in known]
            return (
                f"Origin cites bugs {', '.join(unknown)} — no such record in bugs/BUGS.jsonl"
                if unknown
                else ""
            )
        return f"Origin {value!r} is not canonical. Valid: {_ORIGIN_VOCABULARY}"

    def check_active_release_artifacts(self) -> list[SectionFinding]:
        issues: list[SectionFinding] = []
        active = self.tree.active_release
        release, phase = active.release, active.phase
        if not release:
            return issues
        rdir = self.specs_dir / "releases" / release
        for fname in RELEASE_ARTIFACTS:
            fpath = rdir / fname
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
            elif status != APPROVED and phase in ("IMPLEMENTATION", "CLOSURE"):
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
                            f"'{phase}'; expected '{APPROVED}' for implementation-bound "
                            "phases"
                        ),
                        path=str(fpath),
                    )
                )
        return issues

    def check_plan_line_limit(self) -> list[SectionFinding]:
        issues: list[SectionFinding] = []
        for plan in self.specs_dir.glob("releases/*/PLAN.md"):
            n_lines = sum(1 for _ in plan.read_text(encoding="utf-8").splitlines())
            if n_lines <= PLAN_MAX_LINES:
                continue
            issues.append(
                specs_finding(
                    code="SPEC-DOC-005",
                    # WARNING, always: the remedy is splitting the PLAN — judgment, with
                    # no command to hand back. An exit-1 whose only runnable "fix" was
                    # `sed -i '<limit>,$d'` deleted the plan's tail (0.4.7 c2 review).
                    severity=Severity.WARNING,
                    description=f"PLAN.md has {n_lines} lines > {PLAN_MAX_LINES}",
                    path=str(plan),
                )
            )
        return issues

    def check_no_memory_task(self) -> list[SectionFinding]:
        """SPEC-DOC-047: memory is closure procedure, never a task. ``specs/memory/AGENTS.md`` lets
        ``specs/memory/**`` be written only in DEFINITION/CLOSURE (the gate's RULE A
        reads no SDD artifact), and §6.7 orders memory update -> closure narrative ->
        gate AFTER the last task; SPEC-DOC-024 refuses CLOSURE with an open task. A
        TASKS.md task whose ``Write set:`` names ``specs/memory`` therefore cannot be
        executed in any phase without toggling the phase twice (bug
        memory-gate-requires-closure-phase-that-spec-doc-024-forbids-before-last-task):
        the contradiction is refused at definition, where it is born.
        """
        active = self.tree.active_release
        if not active.release:
            return []
        tasks = self.specs_dir / "releases" / active.release / "TASKS.md"
        if not tasks.exists():
            return []
        text = tasks.read_text(encoding="utf-8")
        issues: list[SectionFinding] = []
        for block in _TASK_BLOCK_RE.finditer(text):
            if _MEMORY_WRITE_SET_RE.search(block.group(0)) is None:
                continue
            task_line = block.group(0).splitlines()[0].strip()
            issues.append(
                specs_finding(
                    code="SPEC-DOC-047",
                    severity=Severity.ERROR,
                    description=(
                        f"TASKS.md of release '{active.release}' schedules memory as a "
                        f"task ({task_line[:80]}): its write set names specs/memory. "
                        "Memory update is closure procedure (RC-FLOW step 5, "
                        "§6.7) run in CLOSURE after the last task — drop the task and "
                        "keep the memory work in the closure steps."
                    ),
                    path=str(tasks),
                )
            )
        return issues

    def check_phase_markers_coherence(self) -> list[SectionFinding]:
        """SPEC-DOC-024: a live release in IMPLEMENTATION carries an approved TASKS.md.
        Whether a task is still open is `release.py phase CLOSURE`'s one refusal
        (`_release_schema.UNFINISHED_RE`) — the doctor keeps no task-marker regex."""
        release, phase = self.tree.active_release.release, self.tree.active_release.phase
        if not release or phase != "IMPLEMENTATION":
            return []
        tasks = self.specs_dir / "releases" / release / "TASKS.md"
        status = _extract_status(tasks) if tasks.exists() else None
        if status == APPROVED:
            return []
        description = (
            f"Active release phase='IMPLEMENTATION' but TASKS.md of release '{release}' is "
            f"not '**Status:** {APPROVED}' (found {status!r})."
        )
        return [specs_finding("SPEC-DOC-024", Severity.ERROR, description, str(tasks))]

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

    def check_release_naming_canon(self) -> list[SectionFinding]:
        """SPEC-DOC-027: release dir names should match the release-id canon
        (``RELEASE_ID_RE``; mintable ids are bare ``MAJOR.MINOR.PATCH``).

        The ONE naming rule (F005, 20260830 audit — SPEC-DOC-016 retired as a second
        implementation of this same rule; no ``date.today()`` gating survives):
        - A non-conforming dir in the live ``releases/`` tree whose SPEC.md
          ``Created:`` date is on/after the canon cutoff (``RELEASE_SEMVER_CUTOFF``)
          is an ERROR — a release born after the canon must be SemVer-clean.
        - A non-conforming LIVE dir with a pre-cutoff or undeterminable ``Created:``
          date is a WARNING — a legacy name predates the canon and is preserved until
          renamed.

        The archive is not this rule's unit (0.4.7 c8 review MEDIUM-2). ADR-9's
        rationale is that frozen history is never renamed — renaming an archived dir
        breaks every historical pointer into it — so an archived name is scored once, by
        the canon (TREE-8), and a second opinion here only multiplied one fact into
        several findings (ledger precedent
        ``doctor-016-errors-archived-legacy-release-027-tolerates``).
        """
        issues: list[SectionFinding] = []
        live_root = self.specs_dir / "releases"
        for d, root in iter_all_release_dirs(self.specs_dir):
            if root != live_root or RELEASE_ID_RE.match(d.name):
                continue
            spec_path = d / "SPEC.md"
            created = _extract_created_date(spec_path) if spec_path.exists() else None
            born_after_canon = created is not None and created >= RELEASE_SEMVER_CUTOFF
            severity = Severity.ERROR if born_after_canon else Severity.WARNING
            issues.append(
                specs_finding(
                    code="SPEC-DOC-027",
                    severity=severity,
                    description=(
                        f"Release dir '{d.relative_to(self.specs_dir).as_posix()}' does "
                        "not follow the release-id canon (bare <MAJOR>.<MINOR>.<PATCH>) "
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
