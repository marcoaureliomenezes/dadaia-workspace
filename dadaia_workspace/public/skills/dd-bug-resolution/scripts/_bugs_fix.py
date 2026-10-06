#!/usr/bin/env python3
"""The ONE fix reader: which commits fixed each bug, what they wrote, what reworked it.

Derived from git on every call, never stored, in two steps.

- Link: oldest first, a `Revert "<subject>"` (git's default, or a short form quoting a
  word-prefix of it; a pairing on the subject survives a rebase, the body's sha does not)
  undoes the earlier live commit it names in most words (a tie: the shorter subject, then
  the nearest), and undoing a revert flips the whole chain beneath it. A live shape-3, shape-4 or REBUILD subject then links its ids — a class
  commit the ids on its body lines — to itself or to the task commits it names.
- Diff: every linked sha's numstat; its production paths are its fix surface. A later
  live REBUILD (planned) or `fix(bugs)` of another bug (overfitting) writing a surface
  path is its rework.
"""

from __future__ import annotations

import re
import subprocess
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import NamedTuple

from _bugs_store import Refusal

#: Shapes 3, 4 and a REBUILD share one id list; shape 4 names its task commit(s) as `(<sha>[, <sha>])`.
_LINK = re.compile(r"(fix\(bugs\): |chore\(bugs\): resolve |refactor\(bugs\): )(.+?) — (.*)$")
_TASK_SHAS = re.compile(r"\((\w+(?:, \w+)*)\)$")
_REBUILD = re.compile(r"(fix|refactor)\([^)]+\): .*\bREBUILD\b")
_BODY_ID = re.compile(r"[a-z0-9][a-z0-9.-]*")
_GREP = (
    r"--grep=^(fix|chore|refactor)\(bugs\): ",
    r"--grep=^refactor\(.*REBUILD",
    '--grep=^Revert "',
)
_FORMAT = "--format=%x01%H %ct %s%x02%b%x02"
#: Never a fix's own lines: tests (metric 6) and specs; `own` adds the generated files.
NOT_PRODUCTION = ("tests/", "specs/")


class Fix(NamedTuple):
    commits: dict[str, list[list[str]]]  # full sha -> numstat rows, newest link first
    surface: set[str]  # the production paths those commits wrote
    rework: Counter[str]  # later commits on the surface: "planned", "overfitting"
    last: int  # unix time of the surface's last touch, fix or rework


@dataclass
class _Commit:
    sha: str
    time: int
    subject: str
    body: str
    rows: list[list[str]]
    live: bool = True
    undid: _Commit | None = field(default=None, repr=False)


def git(cwd: Path | str, *argv: str, stdin: str | None = None) -> str:
    return subprocess.run(["git", "-c", "core.quotePath=false", "-C", str(cwd), *argv], input=stdin, capture_output=True, encoding="utf-8",
                          errors="replace", check=True).stdout  # fmt: skip


def own(specs: Path, paths: set[str], skip: tuple[str, ...] = NOT_PRODUCTION) -> set[str]:
    """The paths a fix writes: not under *skip* (the direction: tests, metric 6, and specs;
    the blame: specs only), not a file `.gitattributes` marks `dadaia-generated`."""
    top = git(specs, "rev-parse", "--show-toplevel").strip()
    # -z: NUL never meets Windows' text-mode \n -> \r\n stdin translation, nor path quoting
    out = git(top, "check-attr", "-z", "--stdin", "dadaia-generated", stdin="\0".join(paths)).split("\0")  # fmt: skip
    generated = {p for p, v in zip(out[0::3], out[2::3], strict=False) if v in ("set", "true")}  # fmt: skip
    return {p for p in paths if not p.startswith(skip)} - generated


def _parse(out: str) -> list[_Commit]:
    commits = []
    for chunk in out.split("\x01")[1:]:
        head, body, stat = chunk.split("\x02")
        sha, time, subject = (head.split(" ", 2) + [""])[:3]
        rows = [line.split("\t") for line in stat.splitlines() if line]
        commits.append(_Commit(sha, int(time), subject, body, rows))
    return commits


def _undoes(revert: str, subject: str) -> int:
    """How many of *subject*'s words the revert's quote starts with; 0 = it undoes nothing."""
    quoted, words = revert.removeprefix('Revert "'), subject.split(" ")
    if quoted == revert:
        return 0
    return max((n for n in range(1, len(words) + 1) if quoted.startswith(" ".join(words[:n]) + '"')), default=0)  # fmt: skip


def _kind(commit: _Commit) -> str | None:
    if _REBUILD.match(commit.subject):
        return "planned"
    return "overfitting" if commit.subject.startswith("fix(bugs): ") else None


def fixes(specs: Path) -> dict[str, Fix]:
    """Bug id -> its :class:`Fix`, for every bug a live commit links."""
    head = subprocess.run(["git", "-C", str(specs), "rev-parse", "-q", "--verify", "HEAD"], capture_output=True, check=False)  # fmt: skip
    if head.returncode == 1:  # a repo with no commit yet links nothing
        return {}
    try:
        order = git(specs, "rev-list", "--reverse", "HEAD").split()
    except subprocess.CalledProcessError:
        raise Refusal("cannot read the repo's history", "Operator action: point --specs at a specs tree inside a git repo") from None  # fmt: skip
    pos = {sha: i for i, sha in enumerate(order)}
    log = _parse(git(specs, "log", "--reverse", "-E", *_GREP, "--numstat", _FORMAT))
    for i, commit in enumerate(log):  # link step 1: the reverts
        if not commit.subject.startswith('Revert "'):
            continue
        # the live commit whose subject the quote matches in most words, a tie to the shorter subject, then the nearest
        fits = [(n, -len(e.subject.split(" ")), j) for j, e in enumerate(log[:i]) if e.live and (n := _undoes(commit.subject, e.subject))]  # fmt: skip
        target = log[max(fits)[2]] if fits else None
        commit.undid = target
        while target:  # undoing a revert reinstates its own, and so on down the chain
            target.live, target = not target.live, target.undid
    named: dict[str, list[str]] = {}
    for commit in reversed([c for c in log if c.live]):  # link step 2, newest first
        link = _LINK.match(commit.subject)
        task = _TASK_SHAS.search(link[3]) if link and link[1].startswith("chore") else None
        if link is None or (task is None and link[1].startswith("chore")):
            continue
        ids = [ln.strip() for ln in commit.body.splitlines() if _BODY_ID.fullmatch(ln.strip())] if link[2].startswith("class ") else link[2].split(", ")  # fmt: skip
        for bug in ids:
            named.setdefault(bug, []).extend(task[1].split(", ") if task else [commit.sha])
    full = {s: next((f for f in order if f.startswith(s)), None) for s in {s for v in named.values() for s in v}}  # fmt: skip
    by_sha = {c.sha: c for c in log}
    shown = sorted({f for f in full.values() if f and f not in by_sha})
    by_sha |= {c.sha: c for c in _parse(git(specs, "show", "--numstat", _FORMAT, *shown))} if shown else {}  # fmt: skip
    links = {bug: list(dict.fromkeys(f for s in shas if (f := full[s]))) for bug, shas in named.items()}  # fmt: skip
    prod = own(specs, {r[2] for shas in links.values() for s in shas for r in by_sha[s].rows})
    reworkers = [c for c in log if c.live and _kind(c)]
    found: dict[str, Fix] = {}
    for bug, shas in links.items():
        if not shas:
            continue
        surfaces = {s: {r[2] for r in by_sha[s].rows} & prod for s in shas}
        rework = [r for r in reworkers if r.sha not in surfaces and any(pos[r.sha] > pos[s] and surfaces[s] & {x[2] for x in r.rows} for s in shas)]  # fmt: skip
        # ponytail: a surface is the files a fix wrote, not its lines; blame per line if file-level overcounts
        found[bug] = Fix(
            {s: by_sha[s].rows for s in shas},
            set().union(*surfaces.values()),
            Counter(str(_kind(r)) for r in rework),
            max(by_sha[s].time for s in [*shas, *(r.sha for r in rework)]),
        )
    return found


def direction(fix: Fix) -> str:
    net = sum(int(a) - int(d) for rows in fix.commits.values() for a, d, path in rows if a != "-" and path in fix.surface)  # fmt: skip
    return "net-negative" if net < 0 else "net-positive" if net > 0 else "net-neutral"
