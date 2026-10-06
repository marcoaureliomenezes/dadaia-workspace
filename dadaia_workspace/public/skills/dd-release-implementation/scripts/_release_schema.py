#!/usr/bin/env python3
"""The release ledger's vocabulary; schema reading and validation are `_ledger`'s."""

from __future__ import annotations

import datetime as _dt
import functools
import json
import re
import subprocess
from collections.abc import Iterable
from pathlib import Path

CODE = "LEDGER-RELEASE-SCHEMA"
STATE = "_RELEASE.json"
HISTO = "releases/_archive/releases_histo.jsonl"
#: One candidate's documents, born in its own `rc-<N>/` and never rewritten after closure; its
#: tasks live in one job file per job, `rc-<N>/tasks/<job>.md` (a closed rc keeps `TASKS.md`).
CANDIDATE_DOCS = ("SPEC.md", "PLAN.md")
#: A candidate folder; the live one is the highest N — `core.release_state.CANDIDATE_RE`.
CANDIDATE_RE = re.compile(r"^rc-([1-9][0-9]*)$")
#: The three lifecycle phases — pinned equal to the schema's enum; a shipped release
#: moves whole to `_archive/<v>/` (ADR 0152 (1)).
PHASES = ("DEFINITION", "IMPLEMENTATION", "CLOSURE")
#: The phases in which the live candidate's trio is REQUIRED; DEFINITION is authoring it.
TRIO_PHASES = frozenset({"IMPLEMENTATION", "CLOSURE"})
#: A release ships `delivered` — the one histo disposition this ledger writes.
DELIVERED = "delivered"
APPROVED = "Approved"
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")
#: A shipped commit sha as a human pastes it from a merge: short (7) to full (40).
SHA_RE = re.compile(r"^[0-9a-f]{7,40}$")
#: The task markers in order — open < reserved < done (ADR 0111); the ONE task-line grammar.
MARKS = (" ", "-", "x")
#: A task line: indent and any Markdown bullet (``-``, ``*``, ``+``) or none, the marker, the rest.
MARK_RE = re.compile(r"^([ \t]*(?:[-*+][ \t]*)?\[)([ x-])(\].*)$", re.MULTILINE)
_STATUS_RE = re.compile(r"^\*\*Status:\*\*\s*(.+?)\s*$", re.MULTILINE)
#: The Origin clause kinds, each at most once on the line (ADR 0161).
ORIGIN_KINDS = ("backlog", "bugs", "findings")
_ORIGIN_RE = re.compile(r"^\*\*Origin:\*\*[ \t]*(.*?)[ \t]*$", re.MULTILINE)
_ORIGIN_GRAMMAR = "operator-demand | backlog:<ids>; bugs:<ids>; findings:<ids>, each kind once"


def utc_now() -> str:
    return _dt.datetime.now(_dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def extract_status(text: str) -> str | None:
    """The ``**Status:**`` token a trio document carries, or ``None``."""
    match = _STATUS_RE.search(text)
    return match.group(1) if match else None


class ShallowClone(ValueError):
    """*specs* sits in a shallow clone: no instant can be placed in its cut history."""


class Unreadable(ValueError):
    """A release state or the history `candidate_at` reads is unreadable; ``args[1]`` is the act."""


def live_ids(specs: Path) -> list[str]:
    """Every SemVer-named release directory directly under ``releases/`` carrying a state
    document — `_archive` is not live."""
    releases = specs / "releases"
    if not releases.is_dir():
        return []
    return sorted(
        d.name
        for d in releases.iterdir()
        if d.is_dir() and SEMVER_RE.match(d.name) and (d / STATE).is_file()
    )


def live_id(specs: Path) -> str:
    """The ONE live release id; :class:`Unreadable` names why not and its act."""
    from _specs import choice, script  # on every caller's sys.path; a runpy load never acts

    ids, release = live_ids(specs), script(Path(__file__).resolve().parent / "release.py")
    if not ids:
        raise choice(Unreadable("no live release under specs/releases/ — nothing to operate on",
                                f"{release} new"), "with the release version you choose")  # fmt: skip
    if len(ids) > 1:
        raise Unreadable(f"multiple live release directories carry {STATE}: {', '.join(ids)} — "
                         "the release-candidates model allows exactly one", f"{release} check")  # fmt: skip
    return ids[0]


def _utc(ts: str) -> _dt.datetime:
    return _dt.datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(_dt.UTC)


@functools.cache
def releases(specs: Path) -> dict[str, tuple[_dt.datetime, _dt.datetime | None]]:
    """Each release id, live or archived -> its span: first `log` ts, `shipped.ts` or None."""
    spans: dict[str, tuple[_dt.datetime, _dt.datetime | None]] = {}
    for path in [*(specs / "releases").glob(f"*/{STATE}"), *(specs / "releases/_archive").glob(f"*/{STATE}")]:  # fmt: skip
        try:
            state = json.loads(path.read_text(encoding="utf-8"))
            shipped = (state.get("shipped") or {}).get("ts")
            spans[path.parent.name] = (
                _utc(state["log"][0]["ts"]),
                _utc(shipped) if shipped else None,
            )
        except (OSError, ValueError, LookupError, TypeError, AttributeError) as exc:
            raise Unreadable(f"{path} has no readable first log ts and shipped ts ({exc})",
                             f"Operator action: repair {path} until `release.py check` passes") from None  # fmt: skip
    return spans


@functools.cache
def candidate_adds(specs: Path) -> list[tuple[_dt.datetime, str, str]]:
    """Each candidate's birth as (instant, release, rc): a commit adding exactly one
    rc-<N>/SPEC.md whose status reads non-Approved; a shallow history is refused."""
    git = ["git", "-C", str(specs)]
    shallow = subprocess.run([*git, "rev-parse", "--is-shallow-repository"], capture_output=True, text=True, check=False)  # fmt: skip
    if shallow.stdout.strip() == "true":
        raise ShallowClone(f"{specs} is in a shallow clone: a release candidate read from a cut history "
                           "would be stamped wrong for good (ADR 0187)")  # fmt: skip
    head = subprocess.run([*git, "rev-parse", "-q", "--verify", "HEAD"], capture_output=True, check=False)  # fmt: skip
    log = subprocess.run([*git, "log", "--diff-filter=A", "--name-only", "--format=%x00%H %cI", "--",
                          ":(glob)releases/**/rc-*/SPEC.md"], capture_output=True, text=True, check=False)  # fmt: skip
    if head.returncode == 0 and log.returncode:  # a repo with no commit yet holds no birth
        from _specs import git_line  # on every caller's sys.path; a runpy load never acts

        raise Unreadable(f"cannot read the history of {specs}: {log.stderr.strip()}",
                         git_line(specs, "fsck"))  # fmt: skip
    adds = []
    for commit in log.stdout.split("\0")[1:] if head.returncode == 0 else []:
        sha, *paths = commit.split()
        if len(paths) != 2:  # the instant, then exactly one added SPEC.md
            continue
        show = subprocess.run([*git, "show", f"{sha}:{paths[1]}"], capture_output=True, text=True, check=False)  # fmt: skip
        if extract_status(show.stdout) != APPROVED:
            parts = paths[1].split("/")
            adds.append((_utc(paths[0]), parts[-3], parts[-2]))
    return adds


def candidate_at(specs: Path, instant: str) -> dict[str, str]:
    """The ONE answer to "which candidate held *instant*": the release whose half-open span
    holds it, the rc born last before it in that release, else ``unknown``; raises
    :class:`ShallowClone`, :class:`Unreadable`, or ``ValueError`` for a bad *instant*."""
    when = _utc(instant)
    adds = candidate_adds(specs)
    held = (r for r, (start, end) in releases(specs).items() if start <= when and (end is None or when < end))  # fmt: skip
    release = next(held, "unknown")
    born = [(t, rc) for t, r, rc in adds if r == release and t <= when]
    return {"release": release, "rc": max(born)[1] if born else "unknown"}


def origin(text: str) -> dict[str, list[str]]:
    """The ids the first ``**Origin:**`` line carries, by kind; ``{}`` for operator-demand.
    The ONE Origin parser (ADR 0161): raises ``ValueError`` saying what is wrong."""
    match = _ORIGIN_RE.search(text)
    if match is None:
        raise ValueError(f"has no `**Origin:**` line ({_ORIGIN_GRAMMAR})")
    carried: dict[str, list[str]] = {}
    for clause in [] if match.group(1) == "operator-demand" else match.group(1).split(";"):
        kind, _, ids = clause.strip().partition(":")
        cited = [i.strip() for i in ids.split(",") if i.strip()]
        if kind not in ORIGIN_KINDS or kind in carried or not cited:
            raise ValueError(f"Origin {match.group(1)!r} is not canonical: {_ORIGIN_GRAMMAR}")
        carried[kind] = cited
    return carried


def origin_line(text: str) -> int:
    """The 1-based line :func:`origin` reads, 1 when there is none."""
    match = _ORIGIN_RE.search(text)
    return text.count("\n", 0, match.start()) + 1 if match else 1


def candidate_number(names: Iterable[str]) -> int:
    """The highest ``rc-<N>`` among *names*, 0 when none — the live candidate's number."""
    return max((int(m.group(1)) for n in names if (m := CANDIDATE_RE.match(n))), default=0)


def candidate_dir(release_dir: Path) -> Path | None:
    """The highest-numbered ``rc-<N>/`` under *release_dir* (ADR 0150) —
    `core.gitflow.candidate_dir`'s twin; ``None`` when there is none."""
    n = candidate_number(d.name for d in release_dir.iterdir() if d.is_dir())
    return release_dir / f"rc-{n}" if n else None


def next_candidate(release_dir: Path) -> Path:
    """The ``rc-<N+1>/`` a new candidate is born in — past every ``rc-<N>`` entry, a stray
    file included, so the birth never lands on an existing path."""
    names = [p.name for p in release_dir.iterdir()] if release_dir.is_dir() else []
    return release_dir / f"rc-{candidate_number(names) + 1}"


def writes(line: str) -> list[str]:
    """The backticked paths a task line's `W:` writes, up to the first ``·``; a path in a
    parenthesized span (nesting counted) is named, not written."""
    field, depth, kept = line.partition("`W:`")[2].split("·")[0], 0, ""
    for char in field:
        depth = max(0, depth + (char == "(") - (char == ")"))
        kept += char if depth == 0 and char != ")" else ""
    return re.findall(r"`([^`]+)`", kept)


def stage_writes(body: str) -> list[list[str]]:
    """Each task line's `W:` paths in one stage *body*: a bullet's `W:` field, or a table
    row's cell under its header's `W:` column."""
    tasks, column = [], None
    for line in body.splitlines():
        cells = [c.strip() for c in line.split("|")] if line.lstrip().startswith("|") else []
        if "`W:`" in cells:
            column = cells.index("`W:`")
            continue
        column = column if cells else None
        if paths := writes("`W:` " + cells[column] if column and column < len(cells) else line):
            tasks.append(paths)
    return tasks


def job_errors(text: str, rel: str) -> list[str]:
    """Why job file *text* at *rel* is malformed: no `## Stage` heading, a stage with no
    `- Contract:` line, two tasks of one stage writing one path, or a first stage whose
    tasks write anything but tests."""
    stages = re.split(r"^## Stage ", text, flags=re.MULTILINE)[1:]
    if not stages:
        return [f"{rel} has no '## Stage <id>' heading"]
    errors: list[str] = []
    for index, body in enumerate(stages):
        stage, tasks = body.split(maxsplit=1)[0], stage_writes(body)
        if not re.search(r"^- Contract:", body, re.MULTILINE):
            errors.append(f"{rel} stage {stage} has no '- Contract:' line")
        flat = [path for paths in tasks for path in set(paths)]
        errors += [f"{rel} stage {stage}: two tasks write {path} — `W:` sets overlap"
                   for path in sorted({p for p in flat if flat.count(p) > 1})]  # fmt: skip
        errors += [
            f"{rel} stage {stage} writes {path} — stage 1 writes tests only"
            for path in (flat if index == 0 else [])
            if not (path.startswith("tests/") or Path(path).name.startswith("test_"))
        ]
    return errors
