#!/usr/bin/env python3
"""The release TREE walk `release.py check` runs: every state document under
``releases/`` plus the ship ledger, validated through `_release_check`'s findings.

Split from `_release_check` because the two answer different questions: that module
judges DOCUMENT bytes (and is therefore what every write validates itself against),
this one judges a tree on disk.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _release_check import finding, histo_findings, state_findings  # noqa: E402
from _release_schema import HISTO, SEMVER_RE, STATE, TRIO, TRIO_PHASES, semver_key  # noqa: E402


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
    return findings
