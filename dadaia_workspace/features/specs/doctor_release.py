"""Release validator: the active release, its artifacts, SemVer + ledger invariants.

Single-responsibility sibling of the SpecsDoctor coordinator. Owns the active-release
lifecycle checks (SPEC-DOC-003/004/005/009), the release ledger invariants (phase<->markers
SPEC-DOC-024, unique ids SPEC-DOC-026, naming canon SPEC-DOC-027) and the partial-archive
residue invariant (SPEC-DOC-039), plus the family-local status/created-date extractors.
Leaf-only: imports the shared leaves + core, never a sibling validator.

The active release and its phase are read directly off ``RELEASE.json``
(:func:`resolve_active_release`) — no fallback branch: a workspace with zero live release
directories resolves cleanly to "no active release".
"""

from __future__ import annotations

import json
import re
import tomllib
from collections.abc import Callable, Collection
from datetime import date
from pathlib import Path

from dadaia_workspace.core.release_state import (
    LEGACY_RELEASE_STATE_FILENAME,
    RELEASE_STATE_FILENAME,
)
from dadaia_workspace.core.release_state import PHASES as _PHASES
from dadaia_workspace.core.spec_status import APPROVED, extract_status
from dadaia_workspace.core.spec_status import CANONICAL_STATUS as _CANONICAL_STATUS
from dadaia_workspace.core.specs_version import RELEASE_SEMVER_RE
from dadaia_workspace.features.specs.doctor_common import (
    RELEASE_ARTIFACTS,
    _read_and_parse_release_json,
    iter_all_release_dirs,
    resolve_live_release_id,
)
from dadaia_workspace.features.specs.doctor_types import Severity, SpecsDoctorIssue
from dadaia_workspace.features.specs.specs_tree import SpecsTree

# Vocabulary + parser live in core.spec_status (single definition); re-exported here
# because doctor_release has been the documented import site for both.
CANONICAL_STATUS = _CANONICAL_STATUS
CANONICAL_PHASES = _PHASES
PLAN_MAX_LINES = 300

# Release-id canon cutoff: a live release whose SPEC.md Created: is on/after this date
# must carry a canon-conformant directory name (SPEC-DOC-027). Vintage releases are
# excluded — this grandfathers the frozen pre-cutoff _archive sub-patch releases.
RELEASE_SEMVER_CUTOFF = date(2026, 6, 1)  # WARNING starts here

# SPEC-DOC-027: permanent allowlist of legacy ``_archive`` release-dir names that
# predate the SemVer naming canon. FROZEN HISTORY — renaming an archived dir breaks
# historical pointers. Silent only inside _archive/releases/; any name NOT here WARNs.
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
# SPEC-DOC-047: a task block runs from its marker line to the next marker line; a
# ``Write set:`` naming ``specs/memory`` inside it schedules memory as implementation work.
_TASK_BLOCK_RE = re.compile(
    r"^\s*[-*]?\s*\[[ \-xX]\][^\n]*(?:\n(?![-*]?\s*\[[ \-xX]\])[^\n]*)*", re.MULTILINE
)
_MEMORY_WRITE_SET_RE = re.compile(r"Write set:[^\n]*specs/memory")


def read_release_phase(specs_dir: Path, release_id: str) -> str | None:
    """The narrow ``RELEASE.json`` phase reader, given an ALREADY-KNOWN ``release_id``
    — a thin wrapper over :func:`doctor_common._read_and_parse_release_json`, the ONE
    tri-state disk read; it does not re-implement it. The hook reads directly through
    ``core.release_state`` instead, so a one-shot process never pays for importing the
    whole ``SpecsDoctor`` decomposition.

    ``str`` when the document's ``phase`` field is readable (possibly ``""`` when it
    carries an empty phase value), ``""`` when
    ``specs_dir/releases/<release_id>/RELEASE.json`` does not exist, ``None`` when it
    exists but could not be read or parsed (genuine I/O failure or a malformed
    document) — callers must treat ``None`` as UNKNOWN, never as "no phase".
    """
    state, exists = _read_and_parse_release_json(specs_dir, release_id)
    if not exists:
        return ""
    if state is None:
        return None
    return state.phase


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

    def check_active_md(self) -> list[SpecsDoctorIssue]:
        """SPEC-DOC-003/009 (v0.5.x, successor to the RELEASE.jsonl fold; v0.5.0
        FR4/T-050-21A): the active release, resolved by reading ``RELEASE.json``
        directly (:func:`resolve_active_release`) — ``ACTIVE.md`` is
        retired, no file stands in its place. SPEC-DOC-009 (a resolved release_id
        naming a directory that does not exist) is now unreachable in practice:
        :func:`resolve_live_release_id` only ever returns a release_id it found BY
        locating that exact directory — kept as a defensive assertion, never dead
        code behind a docstring, in case a future resolver relaxes that guarantee.
        """
        issues: list[SpecsDoctorIssue] = []
        path = self.specs_dir / "releases"
        active = self.tree.active_release
        release, phase, err = (active.release, active.phase, active.error)
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
        if release is None:
            # No live release: there is no phase to judge. The retired "none" phase
            # sentinel used to make this case indistinguishable from a real phase.
            return issues
        if phase not in CANONICAL_PHASES:
            issues.append(
                SpecsDoctorIssue(
                    code="SPEC-DOC-003",
                    severity=Severity.ERROR,
                    description=(
                        f"Active release phase '{phase}' is not canonical. "
                        f"Valid: {sorted(CANONICAL_PHASES)}"
                    ),
                    path=str(path),
                )
            )
        if release:
            release_dir = self.specs_dir / "releases" / release
            if not release_dir.exists():
                issues.append(
                    SpecsDoctorIssue(
                        code="SPEC-DOC-009",
                        severity=Severity.ERROR,
                        description=(
                            f"Active release='{release}' but no directory at {release_dir}"
                        ),
                        path=str(release_dir),
                    )
                )
        return issues

    def check_spec_origin(
        self, open_bug_ids: Callable[[], Collection[str]]
    ) -> list[SpecsDoctorIssue]:
        """SPEC-DOC-048: the live SPEC and every candidate SPEC archived under it name
        where the work came from — the header is the flow's only machine-read input.
        Releases under ``_archive/`` are frozen history and out of scope.

        ``open_bug_ids`` is read lazily: a tree citing no bug never touches the bug
        ledger, so this rule borrows the governance family's ONE bug reader without
        forcing its store on every construction site.
        """
        release = self.tree.active_release.release
        if not release:
            return []
        rdir = self.specs_dir / "releases" / release
        issues: list[SpecsDoctorIssue] = []
        for path in (rdir / "SPEC.md", *sorted(rdir.glob("rc-*/SPEC.md"))):
            if not path.exists():
                continue
            problem = self._origin_problem(path, open_bug_ids)
            if problem:
                issues.append(
                    SpecsDoctorIssue(
                        code="SPEC-DOC-048",
                        severity=Severity.ERROR,
                        description=f"{path.relative_to(self.specs_dir)} {problem}",
                        path=str(path),
                    )
                )
        return issues

    def _origin_problem(self, path: Path, open_bug_ids: Callable[[], Collection[str]]) -> str:
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
            live = set(open_bug_ids())
            closed = [i for i in cited if i not in live]
            return (
                f"Origin cites bugs {', '.join(closed)} — a bug origin names an OPEN "
                "bugs/BUGS.jsonl record"
                if closed
                else ""
            )
        return f"Origin {value!r} is not canonical. Valid: {_ORIGIN_VOCABULARY}"

    def check_active_release_artifacts(self) -> list[SpecsDoctorIssue]:
        issues: list[SpecsDoctorIssue] = []
        active = self.tree.active_release
        release, phase, err = (active.release, active.phase, active.error)
        if err or not release:
            return issues
        # Segment routing retired (release 0.4.6, ADR 0006): the live candidate trio
        # always sits flat at the release root; rc-N/ subfolders are archives owned by
        # `release rc-archive`, never routed to.
        rdir = self.specs_dir / "releases" / release
        for fname in ("SPEC.md", "PLAN.md", "TASKS.md"):
            fpath = rdir / fname
            if not fpath.exists():
                # Presence is RELEASE-TREE-TRIO's rule, in ONE home
                # (features/specs/release_tree.py). This rule judges the `**Status:**`
                # line of the trio documents that exist — a second "missing" finding
                # here was the same fact reported twice, and it was what forced the
                # deleted between-candidates DISCOVERY carve-out.
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
            elif status != APPROVED and phase in ("IMPLEMENTATION", "CLOSURE"):
                # Bug fresh-release-scaffold-emits-spec-doctor-warnings-042: Draft/In
                # review IS the legitimate state of a DEFINITION-phase release — the
                # scaffolder emits exactly that. Only implementation-bound phases
                # expect approved artifacts.
                issues.append(
                    SpecsDoctorIssue(
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

    def check_plan_line_limit(self) -> list[SpecsDoctorIssue]:
        issues: list[SpecsDoctorIssue] = []
        for plan in self.specs_dir.glob("releases/*/PLAN.md"):
            n_lines = sum(1 for _ in plan.read_text(encoding="utf-8").splitlines())
            if n_lines <= PLAN_MAX_LINES:
                continue
            issues.append(
                SpecsDoctorIssue(
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

    def _active_tasks_markers(self, release: str) -> list[str] | None:
        """Return the list of task marker chars (' ', '-', 'x') for the active release's
        TASKS.md, or None when TASKS.md is absent/unreadable."""
        tasks = self.specs_dir / "releases" / release / "TASKS.md"
        if not tasks.exists():
            return None
        text = tasks.read_text(encoding="utf-8")
        return [m.group(1).lower() for m in _TASK_MARKER_RE.finditer(text)]

    def check_no_memory_task(self) -> list[SpecsDoctorIssue]:
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
        if active.error or not active.release:
            return []
        tasks = self.specs_dir / "releases" / active.release / "TASKS.md"
        if not tasks.exists():
            return []
        text = tasks.read_text(encoding="utf-8")
        issues: list[SpecsDoctorIssue] = []
        for block in _TASK_BLOCK_RE.finditer(text):
            if _MEMORY_WRITE_SET_RE.search(block.group(0)) is None:
                continue
            task_line = block.group(0).splitlines()[0].strip()
            issues.append(
                SpecsDoctorIssue(
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

    def check_phase_markers_coherence(self) -> list[SpecsDoctorIssue]:
        """SPEC-DOC-024 (v0.5.x, successor to the RELEASE.jsonl fold; v0.5.0
        FR4/T-050-21A): the active release's ``RELEASE.json`` phase must be coherent
        with its TASKS.md markers (constitution §7 lifecycle).

        Mechanical rules (minimal):
        - phase ∈ {SPEC, DEFINITION}: the active TASKS must NOT already be an
          ``[x]``-majority (work claimed complete before implementation began —
          the live audit incident where phase=SPEC but 19/19 tasks were ``[x]``).
        - phase == IMPLEMENTATION: TASKS.md must exist and carry ``**Status:** Approved``.
        - phase == CLOSURE: every non-CLOSURE task must be ``[x]`` (no ``[ ]``/``[-]``).
        Other phases are not constrained here.
        """
        issues: list[SpecsDoctorIssue] = []
        active_path = self.specs_dir / "releases"
        active = self.tree.active_release
        release, phase, err = (active.release, active.phase, active.error)
        if err or not release or phase is None:
            return issues
        rdir = self.specs_dir / "releases" / release
        if not rdir.exists():
            return issues  # release dir issues already reported by SPEC-DOC-009/004

        markers = self._active_tasks_markers(release)

        if phase in ("SPEC", "DEFINITION"):
            if markers:
                done = sum(1 for m in markers if m == "x")
                if done * 2 > len(markers):  # strict [x]-majority
                    issues.append(
                        SpecsDoctorIssue(
                            code="SPEC-DOC-024",
                            severity=Severity.ERROR,
                            description=(
                                f"Active release phase='{phase}' but the active "
                                f"release '{release}' has an [x]-majority TASKS.md "
                                f"({done}/{len(markers)} done). The phase was never "
                                "advanced through IMPLEMENTATION — update `phase` in "
                                "RELEASE.json or correct the markers "
                                "(constitution §7)."
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
                            f"Active release phase='IMPLEMENTATION' but release "
                            f"'{release}' has no TASKS.md."
                        ),
                        path=str(tasks),
                    )
                )
            elif _extract_status(tasks) != APPROVED:
                issues.append(
                    SpecsDoctorIssue(
                        code="SPEC-DOC-024",
                        severity=Severity.ERROR,
                        description=(
                            f"Active release phase='IMPLEMENTATION' but TASKS.md of "
                            f"release '{release}' is not '**Status:** {APPROVED}' "
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
                            f"Active release phase='CLOSURE' but release '{release}' "
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
        """SPEC-DOC-027: release dir names should match the release-id canon
        (``RELEASE_SEMVER_RE``; mintable ids are bare ``MAJOR.MINOR.PATCH``).

        The ONE naming rule (F005, 20260830 audit — SPEC-DOC-016 retired as a second
        implementation of this same rule; no ``date.today()`` gating survives):
        - A non-conforming dir in the live ``releases/`` tree whose SPEC.md
          ``Created:`` date is on/after the canon cutoff (``RELEASE_SEMVER_CUTOFF``)
          is an ERROR — a release born after the canon must be SemVer-clean.
        - Every other non-conforming dir (archive, pre-cutoff ``Created:``, or an
          undeterminable date) is a WARNING — legacy names predate the canon and are
          preserved until renamed.

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

    def check_partial_archived_release_dirs(self) -> list[SpecsDoctorIssue]:
        """SPEC-DOC-039 (v0.1.81 FR2): WARN on a ``specs/_archive/releases/<id>/`` dir
        that carries NONE of :data:`~dadaia_workspace.features.specs.doctor_common.
        RELEASE_ARTIFACTS` (SPEC.md/PLAN.md/TASKS.md — ``CLOSURE.md`` dropped at v0.5.0
        T-050-25A, A4.4: it retired as a going-forward artifact, so its bare presence is
        no longer release-dir evidence) — directly, or nested under any of its
        subdirectories (a segmented layout, e.g. ``<id>/alpha-1/``, ``<id>/rc-1/``, is a
        legitimate archived-release shape whose artifacts live one level down).

        Such a dir is residue masquerading as an archived release — the v0.1.41
        precedent held only ``GRILL.md`` + ``OQ-DECISIONS.md`` and sat undetected until
        the 2026-07-06 audit (audit G-23). The check honors the SPEC-DOC-027 permanent
        legacy-name allowlist (ADR-9: frozen history, never flagged by name alone) and
        only inspects ``_archive/releases/`` — the live ``releases/`` tree is untouched
        (an active release under construction legitimately lacks a real artifact yet,
        and SPEC-DOC-004/009 already cover it). WARNING severity only: historical trees
        must never hard-fail doctor over this.
        """
        issues: list[SpecsDoctorIssue] = []
        arch_root = self.specs_dir / "_archive" / "releases"
        if not arch_root.is_dir():
            return issues
        for entry in sorted(p for p in arch_root.iterdir() if p.is_dir()):
            if entry.name in RELEASE_NAMING_LEGACY_ALLOWLIST:
                continue
            if any((entry / artifact).exists() for artifact in RELEASE_ARTIFACTS):
                continue
            # Tolerate segmented layouts: any artifact anywhere under the dir (e.g. a
            # nested alpha-N/rc-N segment subdir) counts as "this archived release has
            # its artifacts" even though the parent dir carries none directly.
            if any(next(entry.rglob(artifact), None) is not None for artifact in RELEASE_ARTIFACTS):
                continue
            issues.append(
                SpecsDoctorIssue(
                    code="SPEC-DOC-039",
                    severity=Severity.WARNING,
                    description=(
                        f"_archive/releases/{entry.name} carries none of "
                        "SPEC.md/PLAN.md/TASKS.md (directly or in any segment "
                        "subdir) — residue masquerading as an archived release "
                        "(the v0.1.41 precedent). Relocate it to "
                        f"specs/_archive/wip-abandoned/{entry.name}/ with a README "
                        "breadcrumb explaining why it was abandoned. SPEC-DOC-039, "
                        "WARNING."
                    ),
                    path=str(entry),
                )
            )
        return issues

    def check_release_state_filename(self) -> list[SpecsDoctorIssue]:
        """SPEC-DOC-046 (release 0.4.6 FR3, ADR 0007): the live release's state
        document carries the legacy ``RELEASE.json`` name — WARNING with a doctor
        ``--fix`` rename to the canonical ``_RELEASE.json``. Read-side both names
        already work (``core.release_state.release_state_file``); this rule is the
        migration lane that retires the legacy name from a consumer instance."""
        release_id, err = resolve_live_release_id(self.specs_dir)
        if err or release_id is None:
            return []
        release_dir = self.specs_dir / "releases" / release_id
        legacy = release_dir / LEGACY_RELEASE_STATE_FILENAME
        if not legacy.is_file() or (release_dir / RELEASE_STATE_FILENAME).is_file():
            return []
        return [
            SpecsDoctorIssue(
                code="SPEC-DOC-046",
                severity=Severity.WARNING,
                description=(
                    f"releases/{release_id}/{LEGACY_RELEASE_STATE_FILENAME} carries the "
                    f"legacy state-file name — canonical is {RELEASE_STATE_FILENAME} "
                    "(release-candidates model, ADR 0007). Auto-fix available (run "
                    "doctor --fix) to rename it."
                ),
                path=str(legacy),
                fixable=True,
            )
        ]

    def fix_release_state_filename(self, issue: SpecsDoctorIssue) -> None:
        """Rename the legacy state file to the canonical name (SPEC-DOC-046 auto-fix)."""
        assert issue.code == "SPEC-DOC-046"
        legacy = Path(issue.path)  # type: ignore[arg-type]
        if legacy.is_file():
            legacy.rename(legacy.with_name(RELEASE_STATE_FILENAME))

    def check_pyproject_version_matches_release(
        self, repo_root: Path | None
    ) -> list[SpecsDoctorIssue]:
        """SPEC-DOC-045 (bug release-shipped-without-a-pyproject-version-bump):
        pyproject.toml's [tool.poetry].version must equal the release id once the
        active release reaches CLOSURE/ARCHIVED — read directly off disk, never
        installed-package metadata. Silent absent repo_root/pyproject.toml/release.
        """
        if repo_root is None or not (pyproject_path := repo_root / "pyproject.toml").is_file():
            return []
        active = self.tree.active_release
        release, phase, err = active.release, active.phase, active.error
        if err or not release or phase not in {"CLOSURE", "ARCHIVED"}:
            return []
        try:
            data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
        except (tomllib.TOMLDecodeError, OSError):
            return []
        version = data.get("tool", {}).get("poetry", {}).get("version", "")
        if not version or version == release:
            return []
        description = (
            f"Active release '{release}' is phase '{phase}' but pyproject.toml mints "
            f"'{version}' — bump [tool.poetry].version to the release id (SPEC-DOC-045)."
        )
        issue = SpecsDoctorIssue("SPEC-DOC-045", Severity.ERROR, description, str(pyproject_path))
        return [issue]
