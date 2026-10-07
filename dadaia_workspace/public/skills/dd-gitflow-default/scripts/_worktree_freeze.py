#!/usr/bin/env python3
"""The test freeze (ADR 0209): a task or job merge refuses any diff that modifies or deletes a
test line from the RED anchor on. Test paths are the globs of the `tests:` line the work
branch's `AGENTS.md` declares — no tree picks its own judge. Everything is read from
`git log` over `<merge-base>..HEAD`, each commit diffed against its first parent, so it holds
for any language.

A range whose subject ids (`J<n>.S<m>.T<k>`) name stages but not stage 1 — the RED stage —
refuses. The anchor is the parent of the first commit not in it, else the range base. Past it a commit may only delete lines
matching the repo's `tests-red:` pattern (the RED marker), and may only add test lines in a
stage group that touches test paths alone (a new RED stage); a commit with no stage id is
its own group. A pure rename has no hunks and lands."""

from __future__ import annotations

import re
from pathlib import Path
from typing import NamedTuple

from _worktree_git import git
from _worktree_names import Refusal

_ID = re.compile(r"\b(?P<stage>J\d+\.S(?P<n>\d+))\.T\d+\b")
_HUNK = re.compile(r"^@@ -\d+(?:,(?P<old>\d+))? \+\d+(?:,(?P<new>\d+))? @@")
_BINARY = re.compile(r"^Binary files (?P<a>.+) and (?P<b>.+) differ$")
#: What a binary test file's change counts as: one removed line no `tests-red:` pattern matches.
_BINARY_LINE = "\0binary"
Edit = tuple[str, tuple[str, ...], int]  # (test path, removed lines, added line count)


class Commit(NamedTuple):
    sha: str
    subject: str
    paths: frozenset[str]  # every path the commit touches
    tests: frozenset[str]  # those matching the `tests:` globs
    edits: tuple[Edit, ...]  # the test paths' line changes


def _edits(patch: str) -> tuple[Edit, ...]:
    """The (path, removed lines, added count) of each hunk of a `-U0 -M` patch; a hunk's line
    counts say how many body lines it owns, so a body line is never read as a header."""
    lines, edits, path, old_path, i = patch.split("\n"), [], "", "", 0
    while i < len(lines):
        line, i = lines[i], i + 1
        if hunk := _HUNK.match(line):
            old, new = (1 if hunk[g] is None else int(hunk[g]) for g in ("old", "new"))
            body: list[str] = []
            while len(body) < old + new and i < len(lines):
                body += [] if lines[i].startswith("\\") else [lines[i]]
                i += 1
            edits.append((path, tuple(x[1:] for x in body[:old]), new))
        elif line.startswith("--- "):
            old_path = line[6:]
        elif line.startswith("+++ "):
            path = old_path if line.endswith("/dev/null") else line[6:]
        elif binary := _BINARY.match(line):
            gone = binary["a"] != "/dev/null"
            name = binary["a" if gone else "b"][2:]
            edits.append((name, (_BINARY_LINE,) * gone, int(not gone)))
    return tuple(edits)


def _blocks(tree: Path, rng: str, specs: list[str], *flags: str) -> list[tuple[str, str, str]]:
    """(sha, subject, rest of the entry) per commit of *rng*, oldest first, over *specs*."""
    out = git(
        tree,
        "log",
        "--reverse",
        "--no-color",
        "--no-ext-diff",
        "--no-show-signature",
        "--diff-merges=first-parent",
        "--format=%x00%H %s",
        *flags,
        rng,
        "--",
        *specs,
    )
    rows = []
    for entry in out.split("\0")[1:]:
        head, _, rest = entry.partition("\n")
        sha, _, subject = head.partition(" ")
        rows.append((sha, subject, rest))
    return rows


def _rows(tree: Path, rng: str, globs: list[str]) -> list[Commit]:
    """The one git read: each commit of *rng* with its paths, its test paths and its test edits."""
    specs = [f":(glob){g}" for g in globs]
    tests = {sha: rest.split() for sha, _, rest in _blocks(tree, rng, specs, "--name-only")}
    patches = {sha: rest for sha, _, rest in _blocks(tree, rng, specs, "-p", "-U0", "-M")}
    return [
        Commit(
            sha,
            subject,
            frozenset(rest.split()),
            frozenset(tests.get(sha, ())),
            _edits(patches.get(sha, "")),
        )
        for sha, subject, rest in _blocks(tree, rng, [], "--name-only")
    ]


def _group(row: Commit) -> str:
    return found["stage"] if (found := _ID.search(row.subject)) else row.sha


def judge(rows: list[Commit], base: str, red: re.Pattern[str] | None) -> tuple[str, str] | None:
    """(path, anchor) of the first test edit the freeze refuses in *rows* (oldest first, cut
    from *base*), else `None`."""
    cut = next((i for i, r in enumerate(rows) if not _red_stage(r)), 0)
    anchor, past = (rows[cut - 1].sha if cut else base), rows[cut:]
    dirty = {_group(r) for r in past if r.paths - r.tests}  # stage groups holding non-test paths
    for row in past:
        for path, removed, added in row.edits:
            kept = all(red and red.search(x) for x in removed)
            if not kept or (added and _group(row) in dirty):
                return path, anchor
    return None


def _red_stage(row: Commit) -> bool:
    found = _ID.search(row.subject)
    return found is not None and found["n"] == "1"


def check(tree: Path, work: str, tests: str, red: str) -> None:
    """Refuse when the merge of *tree* onto *work* breaks the freeze. *tests* and *red* are the
    values of *work*'s `tests:` and `tests-red:` lines, `""` when absent."""
    if not tests.split():
        raise Refusal(
            "this repo declares no tests: line",
            f"Operator action: commit the tests: line on {work}'s AGENTS.md",
        )
    try:
        pattern = re.compile(red) if red else None
    except re.error as error:
        raise Refusal(
            f"tests-red: {red!r} is not a regular expression: {error}",
            f"Operator action: fix the tests-red: line on {work}'s AGENTS.md and commit it",
        ) from error
    try:
        base = git(tree, "merge-base", work, "HEAD").strip()
        rows = _rows(tree, f"{base}..HEAD", tests.split())
    except RuntimeError as error:  # fail closed: no anchor, no merge
        raise Refusal(
            f"the RED anchor cannot be derived: {error}",
            f"Operator action: stop and report — the RED anchor since {work} cannot be derived (ADR 0209)",
        ) from error
    if (stages := {f["n"] for r in rows if (f := _ID.search(r.subject))}) and "1" not in stages:
        raise Refusal(
            f"no commit since {work} names its RED stage",
            f"Operator action: stop and report — no commit since {work} names its RED stage, so the RED anchor cannot be derived (ADR 0209)",
        )
    if hit := judge(rows, base, pattern):
        raise Refusal(
            "a test is frozen past the RED anchor",
            f"Operator action: stop and report — {hit[0]} is frozen past the RED anchor {hit[1]} (ADR 0209)",
        )
