#!/usr/bin/env python3
"""The closure worklist: which atoms the window's code changes touched, and which code no
atom describes at all.

A pure function of three inputs — the catalog's per-feature `sources`, `git diff
--name-only <since>..HEAD` and `git ls-files` — so the answer is reproducible from a
commit window and nothing else. It creates no state and no file format; the worklist
travels to `release.py memory` as JSON on the operator's command line.

`sources` globs are matched with `fnmatch` over repo-relative POSIX paths, where `*` and
`**` both cross `/`: a prefix glob (`dadaia_workspace/features/specs/**`) is the shape the
lint requires, and a wider match here can only ADD an atom to the worklist, never hide one.
"""

from __future__ import annotations

import fnmatch
import json
import subprocess
from pathlib import Path
from typing import Any

FEATURES = "dadaia_workspace/features"
HOOKS = "dadaia_workspace/hooks"


class Refusal(Exception):
    """A refusal carrying the one `fix:` line that unblocks it."""

    def __init__(self, message: str, fix: str = "") -> None:
        super().__init__(message)
        self.fix = fix


def git(repo: Path, *argv: str) -> list[str]:
    """`git *argv` from *repo*, as non-empty lines; a git that refuses is a Refusal."""
    done = subprocess.run(["git", *argv], cwd=repo, capture_output=True, text=True, check=False)
    if done.returncode != 0:
        raise Refusal(
            f"git {' '.join(argv)} failed in {repo}: {done.stderr.strip()}",
            "run this verb from a checkout whose history holds --since",
        )
    return [line for line in done.stdout.splitlines() if line]


def since_default(specs: Path) -> str:
    """The live release's `implemented.sha`, else its `defined.sha`."""
    for state in sorted((specs / "releases").glob("*/_RELEASE.json")):
        document = json.loads(state.read_text(encoding="utf-8"))
        for milestone in ("implemented", "defined"):
            sha = (document.get(milestone) or {}).get("sha")
            if sha:
                return str(sha)
    raise Refusal(
        "no live release milestone to date the window from",
        "python3 memory.py drift --since <sha>",
    )


def _units(tracked: list[str]) -> dict[str, list[str]]:
    """Every tracked feature package and hook module, mapped to the files inside it."""
    units: dict[str, list[str]] = {}
    for path in tracked:
        parts = path.split("/")
        if path.startswith(f"{FEATURES}/") and len(parts) > 3:
            units.setdefault("/".join(parts[:3]), []).append(path)
        elif path.startswith(f"{HOOKS}/") and len(parts) == 3 and path.endswith(".py"):
            units.setdefault(path, []).append(path)
    return units


def _matches(sources: list[str], paths: list[str]) -> list[str]:
    return sorted({p for p in paths for glob in sources if fnmatch.fnmatch(p, glob)})


def worklist(catalog: dict[str, Any], changed: list[str], tracked: list[str]) -> dict[str, Any]:
    """The two lists: atoms whose sources matched a changed path, and uncovered units.

    An atom with no `sources` covers nothing — it matches no change and leaves every unit
    it might have described in the uncovered list, which is exactly the drift to report.
    """
    features = catalog.get("features", [])
    atoms = [
        {"slug": str(f["slug"]), "path": str(f["path"]), "matched": matched}
        for f in features
        if (matched := _matches([str(s) for s in f.get("sources") or []], changed))
    ]
    covered = {
        unit
        for unit, inside in _units(tracked).items()
        for f in features
        if _matches([str(s) for s in f.get("sources") or []], inside)
    }
    uncovered = sorted(set(_units(tracked)) - covered)
    return {"atoms": atoms, "uncovered": uncovered}


def render(report: dict[str, Any]) -> str:
    """The human rendering — one line per atom to reconcile, one per uncovered unit."""
    lines = [f"[drift] since {report['since']}"]
    lines += [f"  atom {a['slug']} <- {', '.join(a['matched'])}" for a in report["atoms"]]
    lines += [f"  uncovered {unit}" for unit in report["uncovered"]]
    if len(lines) == 1:
        lines.append("  nothing drifted: every atom is current and every unit is covered")
    return "\n".join(lines)
