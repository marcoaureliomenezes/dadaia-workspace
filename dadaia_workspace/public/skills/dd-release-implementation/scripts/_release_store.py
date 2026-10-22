#!/usr/bin/env python3
"""The ONE write path onto the release files: read -> apply -> validate -> replace.

Every write goes through :func:`commit`, which binds the document to the kernel's one write
loop (`_commit`): the candidate bytes pass the SAME `check` they are validated by, then replace
atomically, and a concurrent write is re-applied once.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import _commit
from _bugs_check import OPEN
from _grammar import STATE
from _ledger import records, replace
from _refusal import Refusal
from _release_check import state_findings
from _release_schema import SCRIPT, State, UnreadableRelease, current_candidate, live_id, read_state


@dataclass(frozen=True)
class Live:
    """The one live release, already proven readable, and its live candidate folder."""

    release_id: str
    release_dir: Path
    state: State
    candidate: Path | None


def live_release(specs: Path) -> Live:
    """Resolve the ONE live release and read its state, or refuse naming the reason."""
    try:
        live = live_id(specs)
    except UnreadableRelease as exc:
        vars(refusal := Refusal(*exc.args)).update(vars(exc))  # the act's choice, if any
        raise refusal from None
    release_dir = specs / "releases" / live
    state = read_state(release_dir / STATE)
    if found := state_findings(json.dumps(state), f"releases/{live}/{STATE}", specs.resolve()):
        raise Refusal(found[0]["message"], found[0]["fix"])  # readers never see a refused shape
    return Live(live, release_dir, state, current_candidate(release_dir, state))


def window_start(state: State) -> list[str]:
    """The memory window's start candidates, newest first: each memory entry's `until`,
    newest entry first, then `defined.sha`."""
    bounds = [str(e["until"]) for e in reversed(state.get("log") or [])
              if e.get("kind") == "memory" and e.get("until")]  # fmt: skip
    return bounds + [str(d) for d in [(state.get("defined") or {}).get("sha")] if d]


def open_bug_ids(specs: Path) -> list[str]:
    """Every persisted open bug id, sorted for deterministic refusals."""
    return sorted(
        str(record["id"])
        for record in records(specs / "bugs" / "BUGS.jsonl")
        if record.get("status") == OPEN and record.get("id")
    )


def validated(state: State, rel: str) -> str:
    text = json.dumps(state, indent=2, ensure_ascii=False) + "\n"  # the canonical bytes
    return _commit.validated(text, rel, lambda t: state_findings(t, rel), SCRIPT("check"))


def commit(path: Path, rel: str, apply: Callable[[State], State]) -> State:
    """Apply *apply* to *path*'s state and replace the document atomically; a refused write
    leaves the file byte-identical (the document is the loop's one record)."""
    written = _commit.commit(
        path,
        lambda p: [read_state(p)],
        lambda states: [apply(states[0])],
        lambda written, *_: validated(written[0], rel),
        replace,
    )
    return written[0]
