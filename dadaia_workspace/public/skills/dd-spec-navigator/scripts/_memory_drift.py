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
from _specs import git_line

NOT_CODE = frozenset({"specs", "tests", "test", "docs"})


class Refusal(Exception):
    """A refusal carrying the one `fix:` line that unblocks it."""

    def __init__(self, message: str, fix: str = "") -> None:
        super().__init__(message)
        self.fix = fix


def _cut(repo: Path, what: str) -> Refusal | None:
    """The one refusal naming a history cut: *repo* is a shallow clone, else None."""
    shallow = subprocess.run(["git", "rev-parse", "--is-shallow-repository"], cwd=repo, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)  # fmt: skip
    if shallow.stdout != "true\n":
        return None
    return Refusal(
        f"{what}: a shallow clone lacks the window's history",
        git_line(repo, "fetch", "--unshallow"),
    )


def git(repo: Path, *argv: str) -> list[str]:
    """`git *argv` from *repo*, as non-empty lines; a git that refuses is a Refusal."""
    done = subprocess.run(["git", *argv], cwd=repo, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)  # fmt: skip
    if done.returncode != 0:  # a bound-less caller's history precondition: a cut is named first
        what = f"git {' '.join(argv)} failed in {repo}"
        raise _cut(repo, what) or Refusal(f"{what}: {done.stderr.strip()}",
                                          "Operator action: run this verb from a checkout whose history holds the --since commit")  # fmt: skip
    return [line for line in done.stdout.split("\n") if line]


def report(specs: Path, since: str, until: str = "HEAD") -> dict[str, Any]:
    """The worklist for the window *since*..*until* — the ONE decider every verb calls."""
    repo = specs.parent
    for bound in (since, until):  # usable = an ancestor of HEAD; absent (128) is left to git()
        reach = subprocess.run(["git", "merge-base", "--is-ancestor", bound, "HEAD"], cwd=repo, capture_output=True, check=False).returncode  # fmt: skip
        if reach and (cut := _cut(repo, f"{bound} is out of reach")):  # a cut is checked first
            raise cut
        if reach == 1:  # present, reached by no path from HEAD
            raise Refusal(f"{bound} is not an ancestor of HEAD — a clone of this branch lacks it (a rebase rewrote it)",
                          f"Operator action: replace {bound[:12]} with the commit HEAD reaches in its place")  # fmt: skip
    catalog = json.loads((specs / CATALOG).read_text(encoding="utf-8"))
    changed = git(repo, "diff", "--name-only", f"{since}..{until}")
    return {"since": since, **worklist(catalog, changed, git(repo, "ls-files"))}


def _units(tracked: list[str]) -> dict[str, list[str]]:
    """Every directory directly holding a tracked file, any language, mapped to every file
    beneath it; a root-level file belongs to no unit.

    Derived from the audited repo alone: `specs/`, `tests/`, `docs/` and dot-dirs hold no
    unit, so a parent directory is covered as soon as any child is.
    """
    units = {
        path.rpartition("/")[0]
        for path in tracked
        if "/" in path
        and not (top := path.split("/", 1)[0]).startswith(".")
        and top not in NOT_CODE
    }
    return {u: [p for p in tracked if p == u or p.startswith(f"{u}/")] for u in units}


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
