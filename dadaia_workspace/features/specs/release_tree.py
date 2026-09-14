"""The one release-tree validator (release 0.4.7 FR1, T-047-01).

Before this module the ``release-state-v1`` schema was exercised only against
synthetic fixtures (``tests/contract/test_release_state_schema.py``) and the only
disk reader of a release state was ``doctor_common._read_and_parse_release_json``,
which reads the LIVE release alone and swallows every parse failure into a tri-state
flag. Nothing ever read ``specs/releases/_archive/<id>/_RELEASE.json``, so an
archived document could fail its own schema and raise in the parser while every
doctor printed zero errors (bug
``archived-release-state-invalid-and-unparseable-doctor-silent``).

:func:`validate_release_tree` is that missing reader: ONE walk over every release
directory, ONE list of issues, no I/O beyond reading each state document. Its callers
are the doctor's release rule (T-047-02), ``rc-archive``/``release archive``
(T-047-09) and the contract test over this repo's own tree —
``doctor_common.iter_all_release_dirs`` is not one of them: it enumerates the
pre-0.5.0 ``specs/_archive/releases/`` layout and classifies a directory by the
presence of a SPEC/PLAN/TASKS artifact, while this validator must walk the current
``releases/_archive/<id>/`` layout and treat a release directory with NO state
document as an issue rather than as "not a release".
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from dadaia_workspace.core.models.telemetry import GovernanceBaseline
from dadaia_workspace.core.release_state import PHASES, parse_release_state, release_state_file
from dadaia_workspace.features.specs.doctor_common import RELEASE_ARTIFACTS
from dadaia_workspace.features.specs.doctor_types import Severity, SpecsDoctorIssue
from dadaia_workspace.features.specs.schemas import validator_for

__all__ = [
    "GOVERNED_STATE_FIELDS",
    "RELEASE_TREE_PHASES",
    "ReleaseTreeIssue",
    "governed_state",
    "release_tree_issues",
    "validate_release_tree",
]

#: The lifecycle phases a committed release state may carry — ONE home
#: (``core.release_state.PHASES``), re-exported here under this module's own name for
#: the readers that speak of the release TREE. Aliased, never re-listed: T-047-07
#: shrank the canonical vocabulary to exactly these four, so a second literal tuple
#: here would be a copy that can drift.
RELEASE_TREE_PHASES: tuple[str, ...] = PHASES

#: The ``_RELEASE.json`` fields a verb OWNS, and therefore the exact shape the
#: ``releases`` governance event hashes (0.4.7 FR6 / SPEC Q3). Everything else in the
#: document is hand-written by design — the `log` narrative above all — so hashing the
#: whole state would read every closure paragraph as a hand edit. Stated here, beside
#: the rule that recomputes it, and imported by the verb that writes it
#: (``cli/commands/newartifacts.py::_record_release_event``): ONE shape, one home.
GOVERNED_STATE_FIELDS: tuple[str, ...] = ("phase", "defined", "implemented")

_SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")
_SCHEMA_NAME = "releases/release-state-v1"


@dataclass(frozen=True)
class ReleaseTreeIssue:
    """One conformance failure. ``path`` is POSIX and relative to ``specs_dir`` — an
    issue is rendered by a doctor and pasted into a report, so it never carries a
    local absolute path (and neither does ``message``: jsonschema error text names
    the instance property, never the file)."""

    path: str
    code: str
    message: str


def _release_dirs(releases_root: Path) -> list[tuple[Path, bool]]:
    """Every release directory as ``(dir, archived)``: the SemVer-named directories
    directly under ``releases/`` (``_ideas``, ``_archive``, ``AGENTS.md`` and the
    candidate ``rc-N/`` archives excluded by the name rule) and every directory under
    ``releases/_archive/`` (the histo file is not a directory)."""
    out: list[tuple[Path, bool]] = []
    if not releases_root.is_dir():
        return out
    out.extend(
        (d, False)
        for d in sorted(releases_root.iterdir())
        if d.is_dir() and _SEMVER_RE.match(d.name)
    )
    archive_root = releases_root / "_archive"
    if archive_root.is_dir():
        out.extend((d, True) for d in sorted(archive_root.iterdir()) if d.is_dir())
    return out


def _document_issues(
    doc: Any, text: str, rel: str, *, archived: bool, validator: Draft202012Validator
) -> list[ReleaseTreeIssue]:
    issues = [
        ReleaseTreeIssue(rel, "RELEASE-TREE-SCHEMA", err.message)
        for err in sorted(validator.iter_errors(doc), key=str)
    ]
    try:
        state = parse_release_state(text)
    except ValueError as exc:
        issues.append(ReleaseTreeIssue(rel, "RELEASE-TREE-PARSE", str(exc)))
        return issues

    timestamps = [entry.get("ts") for entry in state.log]
    for i, (earlier, later) in enumerate(zip(timestamps, timestamps[1:], strict=False)):
        if isinstance(earlier, str) and isinstance(later, str) and later < earlier:
            issues.append(
                ReleaseTreeIssue(
                    rel,
                    "RELEASE-TREE-TS-ORDER",
                    f"log[{i + 1}].ts {later!r} precedes log[{i}].ts {earlier!r}",
                )
            )
    if state.phase not in RELEASE_TREE_PHASES:
        issues.append(
            ReleaseTreeIssue(
                rel,
                "RELEASE-TREE-PHASE",
                f"phase {state.phase!r} is not one of {', '.join(RELEASE_TREE_PHASES)}",
            )
        )
    elif archived != (state.phase == "ARCHIVED"):
        expected = "ARCHIVED" if archived else "a live phase"
        where = "under _archive/" if archived else "a live release directory"
        issues.append(
            ReleaseTreeIssue(
                rel,
                "RELEASE-TREE-ARCHIVED",
                f"{where} carries phase {state.phase!r}, expected {expected}",
            )
        )
    return issues


#: The phases in which the candidate trio is REQUIRED at the release root. A release in
#: DEFINITION is between candidates: ``release new`` leaves SPEC.md alone and
#: ``rc-archive`` leaves the root with no trio at all, both by design — the next
#: candidate's PLAN/TASKS are authored during DEFINITION. Scoping the rule by phase in
#: its ONE home is the whole fix: the alternative (each verb teaching the validator an
#: exemption) is the shape that produced bug
#: ``rc-archive-discovery-state-rejected-by-doctor``, where a verb's own legitimate
#: output was refused by the checker it shares.
_TRIO_REQUIRED_PHASES: frozenset[str] = frozenset({"IMPLEMENTATION", "CLOSURE"})


def _trio_issues(
    release_dir: Path, dir_rel: str, doc: Any, *, archived: bool
) -> list[ReleaseTreeIssue]:
    """The RELEASE-TREE-TRIO rule, phase-scoped. An archived release keeps its final
    trio at root (ADR 0009) but is never re-checked here: it is history, not a live
    candidate."""
    phase = doc.get("phase") if isinstance(doc, dict) else None
    if archived or phase not in _TRIO_REQUIRED_PHASES:
        return []
    missing = [a for a in RELEASE_ARTIFACTS if not (release_dir / a).is_file()]
    if not missing:
        return []
    return [
        ReleaseTreeIssue(
            dir_rel,
            "RELEASE-TREE-TRIO",
            f"release in phase {phase} is missing {', '.join(missing)}",
        )
    ]


def governed_state(document: Mapping[str, Any]) -> dict[str, Any]:
    """The verb-owned slice of a release state — the record a ``releases`` governance
    event hashes. Absent keys are absent, never defaulted: a document missing `phase`
    fails its schema, and inventing a value here would hash a record nobody wrote."""
    return {key: document[key] for key in GOVERNED_STATE_FIELDS if key in document}


def _hand_edit_issue(
    doc: Any, rel: str, release_id: str, governance: GovernanceBaseline | None
) -> list[ReleaseTreeIssue]:
    """RELEASE-TREE-HANDEDIT (0.4.7 FR6): the live phase/milestones differ from what the
    last `release` verb wrote.

    ``record_ts=None`` by construction: a state document carries no timestamp of its
    own, so the "no event at all" shape cannot be dated and stays silent — a release
    that predates the verbs is history, not drift.
    """
    if governance is None or not isinstance(doc, dict):
        return []
    message = governance.hand_edit(
        ledger="releases", record_id=release_id, record=governed_state(doc)
    )
    return [] if message is None else [ReleaseTreeIssue(rel, "RELEASE-TREE-HANDEDIT", message)]


def validate_release_tree(
    specs_dir: Path, *, governance: GovernanceBaseline | None = None
) -> list[ReleaseTreeIssue]:
    """Validate every release directory under ``specs_dir/releases/``.

    One issue per failure, in walk order: live releases first (SemVer-sorted by
    directory name), then the archive. Rules, per release directory: a state document
    exists; it validates ``release-state-v1``; it parses with
    :func:`~dadaia_workspace.core.release_state.parse_release_state`; its ``log[].ts``
    values are non-decreasing; its ``phase`` is one of :data:`RELEASE_TREE_PHASES`;
    ``ARCHIVED`` iff the directory sits under ``_archive/``; a live release in
    IMPLEMENTATION or CLOSURE carries its SPEC/PLAN/TASKS trio
    (:data:`_TRIO_REQUIRED_PHASES`).
    """
    issues: list[ReleaseTreeIssue] = []
    validator = validator_for(_SCHEMA_NAME)
    dirs = _release_dirs(specs_dir / "releases")
    live_ids = [d.name for d, archived in dirs if not archived]
    for release_dir, archived in dirs:
        dir_rel = release_dir.relative_to(specs_dir).as_posix()
        state_path = release_state_file(release_dir)
        if state_path is None:
            issues.append(
                ReleaseTreeIssue(dir_rel, "RELEASE-TREE-STATE-MISSING", "no _RELEASE.json")
            )
            continue
        rel = state_path.relative_to(specs_dir).as_posix()
        text = state_path.read_text(encoding="utf-8")
        try:
            doc = json.loads(text)
        except json.JSONDecodeError as exc:
            issues.append(ReleaseTreeIssue(rel, "RELEASE-TREE-PARSE", f"not valid JSON: {exc}"))
            continue
        issues.extend(_trio_issues(release_dir, dir_rel, doc, archived=archived))
        issues.extend(_hand_edit_issue(doc, rel, release_dir.name, governance))
        issues.extend(_document_issues(doc, text, rel, archived=archived, validator=validator))
        if archived:
            issues.extend(_archive_issues(doc, rel, release_dir.name, live_ids))
    return issues


def _semver_key(release_id: str) -> tuple[int, ...]:
    return tuple(int(part) for part in release_id.split("."))


def _archive_issues(
    doc: Any, rel: str, release_id: str, live_ids: list[str]
) -> list[ReleaseTreeIssue]:
    """The archive holds PUBLISHED versions only (operator ruling 2026-09-14, ADR 0014):
    every candidate closed between two publications is an ``rc-N/`` of the version that
    published it, never its own archived release. Two shapes violate that and both are
    errors: an archived id at or above the live release (a version that was never
    minted at deploy — the live release IS last-published + 1 patch, so nothing above it
    can have shipped), and an archived release whose ``shipped`` carries no sha/pr (it
    never went through the ship lane). Both repair through ONE governed verb,
    ``dadaia release fold``, never a hand move."""
    if (
        not isinstance(doc, Mapping)
        or doc.get("phase") != "ARCHIVED"
        or not _SEMVER_RE.match(release_id)
    ):
        return []  # a non-ARCHIVED document under the archive is RELEASE-TREE-ARCHIVED's
    issues: list[ReleaseTreeIssue] = []
    fix = f"dadaia release fold {release_id} --into <published-id> --shipped <sha> --pr <n>"
    above = [live for live in live_ids if _semver_key(release_id) >= _semver_key(live)]
    if above:
        issues.append(
            ReleaseTreeIssue(
                rel,
                "RELEASE-TREE-ARCHIVE-ID",
                f"archived release {release_id} is not below the live release "
                f"{above[0]} — the archive holds published versions only; a candidate "
                f"closed before a publication is rc-N of the version that published it. "
                f"fix: {fix}",
            )
        )
    shipped = doc.get("shipped")
    if not (isinstance(shipped, Mapping) and shipped.get("sha") and shipped.get("pr")):
        issues.append(
            ReleaseTreeIssue(
                rel,
                "RELEASE-TREE-ARCHIVE-UNSHIPPED",
                f"archived release {release_id} carries no shipped sha/pr — it never went "
                f"through the ship lane and is a candidate of the version that published "
                f"it. fix: {fix}",
            )
        )
    return issues


#: The one code this validator emits that is not a conformance failure: the document
#: is valid and merely unexplained (0.4.7 FR6). Judgment, so WARNING and no `fix:`.
_HAND_EDIT_CODE = "RELEASE-TREE-HANDEDIT"


def release_tree_issues(
    specs_dir: Path, *, governance: GovernanceBaseline | None = None
) -> list[SpecsDoctorIssue]:
    """The validator rendered as doctor issues — the `specs` section's RELEASE-TREE rule.

    Every conformance failure is an ERROR: a committed governance record is either valid
    or it is not. The one exception is :data:`_HAND_EDIT_CODE`, which reports PROVENANCE
    over a valid document. Lives here, next to the validator it renders, so the rule
    registry stays a table of one-line rows and no validator module grows for it.
    """
    return [
        SpecsDoctorIssue(
            issue.code,
            Severity.WARNING if issue.code == _HAND_EDIT_CODE else Severity.ERROR,
            issue.message,
            issue.path,
        )
        for issue in validate_release_tree(specs_dir, governance=governance)
    ]
