#!/usr/bin/env python3
"""The release TREE walk `release.py check` runs: every state document under
``releases/``, the ship ledger, and the live CLOSURE's memory entry re-judged over git.

Split from `_release_check`, which judges DOCUMENT bytes every write validates against;
this one judges a tree on disk and the history beside it.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
# The worklist has ONE decider, the spec navigator's drift function, projected beside
# this skill: importing a pure function is not a script calling a script (SPEC D6).
sys.path.insert(1, str(Path(__file__).resolve().parents[2] / "dd-spec-navigator" / "scripts"))

import _memory_drift as drift  # noqa: E402
from _release_check import finding, histo_findings, state_findings  # noqa: E402
from _release_schema import HISTO, SEMVER_RE, STATE, TRIO, TRIO_PHASES, semver_key  # noqa: E402
from _release_store import Refusal, live_release  # noqa: E402

__all__ = ["check", "drift", "memory_errors"]


def _release_dirs(releases: Path) -> list[tuple[Path, bool]]:
    """Every release directory as ``(dir, archived)``: the SemVer-named directories
    directly under ``releases/``, then every directory under ``releases/_archive/``."""
    if not releases.is_dir():
        return []
    dirs: list[tuple[Path, bool]] = [
        (d, False) for d in sorted(releases.iterdir()) if d.is_dir() and SEMVER_RE.match(d.name)
    ]
    archive = releases / "_archive"
    if archive.is_dir():
        dirs += [(d, True) for d in sorted(archive.iterdir()) if d.is_dir()]
    return dirs


def _directory_findings(
    release_dir: Path, specs: Path, live_ids: list[str], *, archived: bool
) -> list[dict[str, Any]]:
    dir_rel = release_dir.relative_to(specs).as_posix()
    state_path = release_dir / STATE
    if not state_path.is_file():
        return [finding(dir_rel, 1, f"release directory carries no {STATE}")]
    rel = state_path.relative_to(specs).as_posix()
    findings = state_findings(state_path.read_text(encoding="utf-8"), rel, archived=archived)
    if findings:
        return findings
    document = json.loads(state_path.read_text(encoding="utf-8"))
    if not archived and document["phase"] in TRIO_PHASES:
        missing = [name for name in TRIO if not (release_dir / name).is_file()]
        if missing:
            findings.append(
                finding(dir_rel, 1, f"phase {document['phase']} is missing {', '.join(missing)}")
            )
    if archived and SEMVER_RE.match(release_dir.name):
        above = [i for i in live_ids if semver_key(release_dir.name) >= semver_key(i)]
        if above:
            findings.append(
                finding(
                    dir_rel,
                    1,
                    f"archived id {release_dir.name} is not below the live release "
                    f"{above[0]} — the archive holds published versions only",
                )
            )
    return findings


def memory_errors(specs: Path, phase: str, entry: dict[str, Any]) -> list[str]:
    """Why *entry* reconciles nothing over its own [since, until]: the ONE judgement the
    `memory` verb refuses on and `check` re-applies to the entry the log records."""
    since, until = str(entry.get("since")), str(entry.get("until"))
    worklist = drift.report(specs, since, until)
    lists = [[str(s) for s in entry.get(name) or []] for name in ("reviewed", "changed")]
    paths = {str(atom["slug"]): str(atom["path"]) for atom in worklist["atoms"]}
    # git decides "moved": it normalises line endings a byte compare would not.
    unmoved = [f"--changed names {slug!r}, whose atom did not move since {since}"
               for slug in lists[1] if slug in paths and not drift.git(
                   specs.parent, "diff", "--name-only", since, until, "--", paths[slug])]  # fmt: skip
    if phase != "CLOSURE":
        return [f"release is in phase {phase!r} — the memory reconciliation is CLOSURE work"]
    listed = [str(atom["slug"]) for atom in worklist["atoms"]] + worklist["uncovered"]
    named = set(lists[0]) | set(lists[1])
    errors = [f"worklist entry {e!r} is in neither --reviewed nor --changed"
              for e in listed if e not in named]  # fmt: skip
    errors += [f"{e!r} is not in the window's worklist" for e in sorted(named - set(listed))]
    return errors or unmoved


def _window_findings(specs: Path) -> list[dict[str, Any]]:
    """CLOSURE: the latest memory entry re-judged over its [since, until], and no atom's
    sources moved over [until, HEAD] — code after the entry is unreconciled."""
    try:
        live = live_release(specs)
    except Refusal:
        return []  # the tree walk reports a missing or doubled live release
    entries = [e for e in live.state.get("log") or [] if e.get("kind") == "memory"]
    if live.state.get("phase") != "CLOSURE" or not entries:
        return []  # the doctor's RELEASE-TREE-MEMORY owns a closure with no entry
    until, rel = str(entries[-1].get("until")), f"releases/{live.release_id}/{STATE}"
    try:
        errors = memory_errors(specs, "CLOSURE", entries[-1])
        errors += [f"atom {a['slug']!r} moved after the memory entry's until {until[:12]}: "
                   f"{', '.join(a['matched'])}" for a in drift.report(specs, until)["atoms"]]  # fmt: skip
    except (drift.Refusal, OSError) as refusal:
        errors = [str(refusal)]
    return [finding(rel, 1, message) for message in errors]


def check(specs: Path) -> list[dict[str, Any]]:
    """Validate every release state document under ``releases/`` and the ship ledger."""
    releases = specs / "releases"
    dirs = _release_dirs(releases)
    live_ids = [d.name for d, archived in dirs if not archived]
    findings: list[dict[str, Any]] = []
    for release_dir, archived in dirs:
        findings += _directory_findings(release_dir, specs, live_ids, archived=archived)
    histo = specs / HISTO
    if histo.is_file():
        findings += histo_findings(histo.read_text(encoding="utf-8"))
    return findings + _window_findings(specs)
