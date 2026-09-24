#!/usr/bin/env python3
"""The closure worklist: which atoms the window's code changes touched, and which code no
atom describes at all.

A pure function of the catalog's `sources`, `git diff --name-only <since>..HEAD` and `git
ls-files`; `release.py memory` imports :func:`report`, so no caller hands it a worklist.

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

from _memory_schema import CATALOG

CODE = frozenset(
    {".py", ".js", ".mjs", ".ts", ".tsx", ".jsx", ".go", ".rs", ".java", ".kt", ".rb", ".gd"}
)
NOT_CODE = frozenset({"specs", "tests", "test", "docs"})


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


def report(specs: Path, since: str, until: str = "HEAD") -> dict[str, Any]:
    """The worklist for the window *since*..*until* — the ONE decider every verb calls."""
    repo = specs.parent
    catalog = json.loads((specs / CATALOG).read_text(encoding="utf-8"))
    changed = git(repo, "diff", "--name-only", f"{since}..{until}")
    return {"since": since, **worklist(catalog, changed, git(repo, "ls-files"))}


def _units(tracked: list[str]) -> dict[str, list[str]]:
    """Every directory directly holding a tracked code file, mapped to every file beneath it.

    Derived from the audited repo alone: `specs/`, `tests/`, `docs/`, dot-dirs and root
    files hold no unit, so a parent directory is covered as soon as any child is.
    """
    dirs = {
        path.rsplit("/", 1)[0]
        for path in tracked
        if "/" in path
        and Path(path).suffix in CODE
        and not (top := path.split("/", 1)[0]).startswith(".")
        and top not in NOT_CODE
    }
    return {d: [p for p in tracked if p.startswith(f"{d}/")] for d in dirs}


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
