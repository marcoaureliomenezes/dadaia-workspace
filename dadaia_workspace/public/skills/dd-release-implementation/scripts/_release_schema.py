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
#: One candidate's trio, born in its own `rc-<N>/` and never rewritten after closure (ADR 0150).
TRIO = ("SPEC.md", "PLAN.md", "TASKS.md")
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


def _utc(ts: str) -> _dt.datetime:
    return _dt.datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(_dt.UTC)


def releases(specs: Path) -> dict[str, tuple[_dt.datetime, _dt.datetime | None]]:
    """Each release id, live or archived -> its span: first `log` ts, `shipped.ts` or None."""
    spans: dict[str, tuple[_dt.datetime, _dt.datetime | None]] = {}
    for path in [
        *(specs / "releases").glob(f"*/{STATE}"),
        *(specs / "releases/_archive").glob(f"*/{STATE}"),
    ]:
        state = json.loads(path.read_text(encoding="utf-8"))
        shipped = (state.get("shipped") or {}).get("ts")
        spans[path.parent.name] = (_utc(state["log"][0]["ts"]), _utc(shipped) if shipped else None)
    return spans


@functools.cache
def _candidate_adds(specs: Path) -> list[tuple[_dt.datetime, str, str]]:
    """Each candidate's birth as (instant, release, rc): a commit adding exactly one
    rc-<N>/SPEC.md whose status reads non-Approved; a shallow history is refused."""
    git = ["git", "-C", str(specs)]
    shallow = subprocess.run([*git, "rev-parse", "--is-shallow-repository"], capture_output=True, text=True, check=False)  # fmt: skip
    if shallow.stdout.strip() == "true":
        raise ValueError(f"{specs} is in a shallow clone: a release candidate read from a cut history "
                         "would be stamped wrong for good (ADR 0187)")  # fmt: skip
    log = subprocess.run([*git, "log", "--diff-filter=A", "--name-only", "--format=%x00%H %cI", "--",
                          ":(glob)releases/**/rc-*/SPEC.md"], capture_output=True, text=True, check=False)  # fmt: skip
    adds = []
    for commit in log.stdout.split("\0")[1:] if log.returncode == 0 else []:
        head, *paths = commit.split()
        if len(paths) != 2:  # the instant, then exactly one added SPEC.md
            continue
        show = subprocess.run([*git, "show", f"{head}:{paths[1]}"], capture_output=True, text=True, check=False)  # fmt: skip
        if extract_status(show.stdout) != APPROVED:
            parts = paths[1].split("/")
            adds.append((_utc(paths[0]), parts[-3], parts[-2]))
    return adds


def candidate_at(specs: Path, instant: str) -> dict[str, str]:
    """The ONE answer to "which candidate held *instant*": the release whose span
    holds it, the rc born last before it in that release, else ``unknown``; raises
    ``ValueError`` in a shallow clone."""
    adds, when = _candidate_adds(specs), _utc(instant)
    held = (
        r
        for r, (start, end) in releases(specs).items()
        if start <= when and (end is None or when < end)
    )
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


def unfinished_tasks(candidate: Path) -> list[str]:
    """The ``[ ]``/``[-]`` lines TASKS.md still carries — the LINES, so a refusal names
    the task that blocks it. A missing TASKS.md carries none: its absence is the trio
    rule's business, not this one's."""
    tasks = candidate / "TASKS.md"
    if not tasks.is_file():
        return []
    text = tasks.read_text(encoding="utf-8")
    return [m.group(0).strip() for m in MARK_RE.finditer(text) if m[2] != MARKS[-1]]


def writes(line: str) -> list[str]:
    """The backticked paths a task line's `W:` writes, up to the first ``·``; a path in a
    parenthesized span (nesting counted) is named, not written."""
    field, depth, kept = line.partition("`W:`")[2].split("·")[0], 0, ""
    for char in field:
        depth = max(0, depth + (char == "(") - (char == ")"))
        kept += char if depth == 0 and char != ")" else ""
    return re.findall(r"`([^`]+)`", kept)
