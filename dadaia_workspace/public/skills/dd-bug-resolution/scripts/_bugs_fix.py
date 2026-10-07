#!/usr/bin/env python3
"""The ONE fix reader: which commits fixed each bug, what they wrote, what reworked it.

Derived from git on every call, never stored, in two steps.

- Link: oldest first, a `Revert "<subject>"` (git's default, or a short form quoting a
  word-prefix of it; a pairing on the subject survives a rebase, the body's sha does not)
  undoes the earlier live commit it names with the fewest words beyond the quote (the
  exact subject; a tie: the nearest), and undoing a revert flips the whole chain beneath
  it. A live shape-3, shape-4 or REBUILD subject then links its ids — a class commit the
  ids on its body lines — to itself or, for shape 4's `by <task-id>`, to the commits whose
  subjects carry that task id (a rebase rewrites a sha, never the id).
- Diff: every linked sha's numstat; its production paths are its fix surface. A later
  live REBUILD (planned) or `fix(...)` commit, a bug's or a task's (overfitting), removing
  a line a fix wrote (`git blame` of its removed lines names the fix sha) is its rework.
"""

from __future__ import annotations

import functools
import re
import subprocess
import tempfile
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import NamedTuple

from _bugs_store import Refusal

#: Shapes 3, 4 and a REBUILD share one id list; shape 4 names its task as `by <task-id>` and may
#: cite its commits as `(<sha>[, <sha>])`.
_LINK = re.compile(r"(fix\(bugs\): |chore\(bugs\): resolve |refactor\(bugs\): )(.+?) — (.*)$")
_REF = re.compile(r"\bby ([\w.-]+)|\(([\w, ]+)\)$")
_TASK = re.compile(r"[a-z]+\((?P<task>[^)]+)\)")
_REBUILD = re.compile(r"(fix|refactor)\([^)]+\): .*\bREBUILD\b")
_BODY_ID = re.compile(r"[a-z0-9][a-z0-9.-]*")
_GREP = (
    r"--grep=^(fix|chore|refactor)\(bugs\): ",
    r"--grep=^fix\(",
    r"--grep=^refactor\(.*REBUILD",
    '--grep=^Revert "',
)
_FORMAT = "--format=%x01%H %ct %s%x02%b%x02"
#: Never a fix's own lines: tests (metric 6) and specs; `own` adds the generated files.
NOT_PRODUCTION = ("tests/", "specs/")


class Fix(NamedTuple):
    commits: dict[str, list[list[str]]]  # full sha -> numstat rows, newest link first
    surface: set[str]  # the production paths those commits wrote
    rework: Callable[
        [], tuple[Counter[str], int]
    ]  # rework by class, unix time of the last touch: blames, so read on demand


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


def marked(top: Path | str, attribute: str, paths: set[str]) -> set[str]:
    """The *paths* `.gitattributes` sets *attribute* on."""
    # -z: NUL never meets Windows' text-mode \n -> \r\n stdin translation, nor path quoting
    out = git(top, "check-attr", "-z", "--stdin", attribute, stdin="\0".join(paths)).split("\0")
    return {p for p, v in zip(out[0::3], out[2::3], strict=False) if v in ("set", "true")}


def own(specs: Path, paths: set[str], skip: tuple[str, ...] = NOT_PRODUCTION) -> set[str]:
    """The paths a fix writes: not under *skip* (the direction: tests, metric 6, and specs;
    the blame: specs only), not a file `.gitattributes` marks `dadaia-generated`."""
    top = git(specs, "rev-parse", "--show-toplevel").strip()
    return {p for p in paths if not p.startswith(skip)} - marked(top, "dadaia-generated", paths)


def subjects(top: Path) -> dict[str, str]:
    """Every commit of every ref, sha -> subject; `--all`, not HEAD: a repo with no commit yet lists none."""
    return {h: s for h, _, s in (ln.partition(" ") for ln in git(top, "log", "--all", "--format=%H %s").splitlines())}  # fmt: skip


def removed(
    top: Path,
    diff: tuple[str, ...],
    rev: str,
    named: dict[str, str],
    skip: tuple[str, ...],
    only: tuple[str, ...] = (),
) -> set[str]:
    """The shas that wrote the lines the `git diff *diff` removes: `git blame` at *rev*, past the
    `(#n)`-subject squashes of *named*; paths under *skip* and generated files never count, a
    rename is blamed at its old path; *only* limits the diff to those paths. The ONE blame authority:
    resolve's candidates and rework."""
    changed = {f[1]: f[1:] for f in (ln.split("\t") for ln in git(top, "diff", "--name-status", "--diff-filter=MDR", *diff, "--", *only).splitlines())}  # fmt: skip
    blamed = set[str]()
    with tempfile.TemporaryDirectory() as tmp:
        (revs := Path(tmp) / "revs").write_text("\n".join(h for h, s in named.items() if re.search(r"\(#\d+\)$", s)), encoding="utf-8")  # fmt: skip
        for path in own(top, set(changed), skip=skip):
            hunks = [ln.split()[1][1:].partition(",") for ln in git(top, "diff", "-U0", *diff, "--", *changed[path]).splitlines() if ln.startswith("@@ ")]  # fmt: skip
            ranges = [arg for start, _, n in hunks if n != "0" for arg in ("-L", f"{start},+{n or 1}")]  # fmt: skip
            blame = git(top, "blame", "--porcelain", "--ignore-revs-file", str(revs), *ranges, rev, "--", path) if ranges else ""  # fmt: skip
            blamed |= {ln[:40] for ln in blame.splitlines()}
    return blamed


def _parse(out: str) -> list[_Commit]:
    commits = []
    for chunk in out.split("\x01")[1:]:
        head, body, stat = chunk.split("\x02")
        sha, time, subject = (head.split(" ", 2) + [""])[:3]
        rows = [line.split("\t") for line in stat.splitlines() if line]
        commits.append(_Commit(sha, int(time), subject, body, rows))
    return commits


def _undoes(revert: str, subject: str) -> bool:
    quoted, words = revert.removeprefix('Revert "'), subject.split(" ")
    return quoted != revert and any(quoted.startswith(" ".join(words[:n]) + '"') for n in range(1, len(words) + 1))  # fmt: skip


def _kind(commit: _Commit) -> str | None:
    if _REBUILD.match(commit.subject):
        return "planned"
    return "overfitting" if commit.subject.startswith("fix(") else None


def _history(specs: Path) -> list[tuple[str, str]]:
    """Every commit on HEAD, oldest first, as ``(sha, subject)``; none in a repo with no commit."""
    head = subprocess.run(["git", "-C", str(specs), "rev-parse", "-q", "--verify", "HEAD"], capture_output=True, check=False)  # fmt: skip
    if head.returncode == 1:
        return []
    try:
        out = git(specs, "log", "--reverse", "--format=%H %s", "HEAD")
    except subprocess.CalledProcessError:
        raise Refusal("cannot read the repo's history", "Operator action: point --specs at a specs tree inside a git repo") from None  # fmt: skip
    return [(sha, subject) for sha, _, subject in (line.partition(" ") for line in out.splitlines())]  # fmt: skip


def _tasks(history: list[tuple[str, str]]) -> dict[str, list[str]]:
    found: dict[str, list[str]] = {}
    for sha, subject in history:
        if task := _TASK.match(subject):
            found.setdefault(task["task"], []).append(sha)
    return found


def tasked(specs: Path) -> dict[str, list[str]]:
    """Task id -> the shas of its `<type>(<task-id>)` commits on HEAD, oldest first: the ONE reader
    of a task's commits, by the id their subjects carry, which a rebase keeps and a sha does not."""
    return _tasks(_history(specs))


def _revert(log: list[_Commit]) -> None:
    """Link step 1: a `Revert "..."` kills the live commit it quotes; reverting a revert revives."""
    for i, commit in enumerate(log):
        if not commit.subject.startswith('Revert "'):
            continue
        # the live commit the quote names with the fewest words beyond it, then the nearest
        fits = [
            (-len(e.subject.split(" ")), j)
            for j, e in enumerate(log[:i])
            if e.live and _undoes(commit.subject, e.subject)
        ]
        target = log[max(fits)[1]] if fits else None
        commit.undid = target
        while target:  # undoing a revert reinstates its own, and so on down the chain
            target.live, target = not target.live, target.undid


def _named(log: list[_Commit], tasks: dict[str, list[str]], order: list[str]) -> dict[str, list[str]]:  # fmt: skip
    """Link step 2, newest first: bug id -> the shas its live subject names. A shape-4 resolve
    names refs, its `by <task-id>` first, then the shas it cites; the first ref that names commits
    wins (a task id a rebase keeps, a sha it drops)."""
    named: dict[str, list[str]] = {}
    for commit in reversed([c for c in log if c.live]):
        link = _LINK.match(commit.subject)
        if link is None:
            continue
        refs = (tasks.get(m[1]) or [] if m[1] else [f for r in m[2].split(", ") for f in _full(r, order)] for m in _REF.finditer(link[3]))  # fmt: skip
        shas = next(filter(None, refs), []) if link[1].startswith("chore") else [commit.sha]
        ids = [ln.strip() for ln in commit.body.splitlines() if _BODY_ID.fullmatch(ln.strip())] if link[2].startswith("class ") else link[2].split(", ")  # fmt: skip
        for bug in ids:
            named.setdefault(bug, []).extend(shas)
    return named


def _full(short: str, order: list[str]) -> list[str]:
    """The oldest sha of *order* that *short* starts; none when it is no sha or a rebase dropped it."""
    return [sha for sha in order if sha.startswith(short)][:1]


def _shown(specs: Path, log: list[_Commit], shas: set[str]) -> dict[str, _Commit]:
    """The log's commits (their paths) with the numstat of *shas*, which `git show` reads."""
    shown = _parse(git(specs, "show", "--numstat", _FORMAT, *sorted(shas))) if shas else []
    return {c.sha: c for c in log} | {c.sha: c for c in shown}


def fixes(specs: Path) -> dict[str, Fix]:
    """Bug id -> its :class:`Fix`, for every bug a live commit links."""
    history = _history(specs)
    if not history:
        return {}
    log = _parse(git(specs, "log", "--reverse", "-E", *_GREP, "--name-only", _FORMAT))
    _revert(log)
    order = [sha for sha, _ in history]
    named = _named(log, _tasks(history), order)
    by_sha = _shown(specs, log, {s for shas in named.values() for s in shas})
    links = {bug: list(dict.fromkeys(shas)) for bug, shas in named.items() if shas}
    prod = own(specs, {r[-1] for shas in links.values() for s in shas for r in by_sha[s].rows})
    top = Path(git(specs, "rev-parse", "--show-toplevel").strip())
    squashes = functools.cache(lambda: subjects(top))

    @functools.cache
    def wrote(sha: str) -> set[str]:
        # the shas whose lines this commit removed, on paths some fix wrote
        hot = tuple(sorted({x[-1] for x in by_sha[sha].rows} & prod))
        return removed(top, (f"{sha}^", sha), f"{sha}^", squashes(), NOT_PRODUCTION, hot) if hot else set()  # fmt: skip

    reworkers = [c for c in log if c.live and _kind(c)]
    pos = {sha: i for i, sha in enumerate(order)}
    return {bug: _fix(shas, by_sha, prod, reworkers, pos, wrote) for bug, shas in links.items()}


def _fix(
    shas: list[str],
    by_sha: dict[str, _Commit],
    prod: set[str],
    reworkers: list[_Commit],
    pos: dict[str, int],
    wrote: Callable[[str], set[str]],
) -> Fix:
    """One bug's :class:`Fix`; its rework blames, so only the verb that prints it pays."""
    surfaces = {s: {r[-1] for r in by_sha[s].rows} & prod for s in shas}

    def read() -> tuple[Counter[str], int]:
        rework = [
            r
            for r in reworkers
            if r.sha not in surfaces
            and any(
                pos[r.sha] > pos[s] and surfaces[s] & {x[-1] for x in r.rows} and s in wrote(r.sha)
                for s in shas
            )
        ]
        return Counter(str(_kind(r)) for r in rework), max(
            by_sha[s].time for s in [*shas, *(r.sha for r in rework)]
        )

    return Fix({s: by_sha[s].rows for s in shas}, set().union(*surfaces.values()), read)


def direction(fix: Fix) -> str:
    net = sum(int(a) - int(d) for rows in fix.commits.values() for a, d, path in rows if a != "-" and path in fix.surface)  # fmt: skip
    return "net-negative" if net < 0 else "net-positive" if net > 0 else "net-neutral"
