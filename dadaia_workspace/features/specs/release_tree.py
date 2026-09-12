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
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from dadaia_workspace.core.release_state import PHASES, parse_release_state, release_state_file
from dadaia_workspace.features.specs.doctor_common import RELEASE_ARTIFACTS
from dadaia_workspace.features.specs.doctor_types import Severity, SpecsDoctorIssue
from dadaia_workspace.features.specs.schemas import validator_for

__all__ = [
    "RELEASE_TREE_PHASES",
    "ReleaseTreeIssue",
    "release_tree_issues",
    "validate_release_tree",
]

#: The lifecycle phases a committed release state may carry — ONE home
#: (``core.release_state.PHASES``), re-exported here under this module's own name for
#: the readers that speak of the release TREE. Aliased, never re-listed: T-047-07
#: shrank the canonical vocabulary to exactly these four, so a second literal tuple
#: here would be a copy that can drift.
RELEASE_TREE_PHASES: tuple[str, ...] = PHASES

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


def validate_release_tree(specs_dir: Path) -> list[ReleaseTreeIssue]:
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
    for release_dir, archived in _release_dirs(specs_dir / "releases"):
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
        issues.extend(_document_issues(doc, text, rel, archived=archived, validator=validator))
    return issues


def release_tree_issues(specs_dir: Path) -> list[SpecsDoctorIssue]:
    """The validator rendered as doctor issues — the `specs` section's RELEASE-TREE rule.

    Every conformance failure is an ERROR: a committed governance record is either valid
    or it is not. Lives here, next to the validator it renders, so the rule registry
    stays a table of one-line rows and no validator module grows for it.
    """
    return [
        SpecsDoctorIssue(issue.code, Severity.ERROR, issue.message, issue.path)
        for issue in validate_release_tree(specs_dir)
    ]
