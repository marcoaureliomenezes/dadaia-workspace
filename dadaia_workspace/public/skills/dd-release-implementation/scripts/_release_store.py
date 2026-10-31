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
from _grammar import STATE
from _ledger import replace
from _memory_drift import by_subject
from _refusal import Refusal
from _release_check import state_findings
from _release_schema import SCRIPT, State, UnreadableRelease, current_candidate, live_id, read_state

PASS = "memory pass recorded"
IMPLEMENTATION = "(?:phase|enters) IMPLEMENTATION"


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


def window_start(repo: Path, live: Live) -> list[str]:
    """The memory window's start candidates, newest first: the newest memory pass of any
    candidate in any release except the live candidate's own passes in the live release
    (product memory is one per repo; sync rebases what landed after an own pass under it),
    then the live candidate's IMPLEMENTATION commit."""
    if not live.candidate:
        return []
    name, own = live.candidate.name, by_subject(repo, live.release_id, live.candidate.name, PASS)
    other = [sha for sha in by_subject(repo, "", r"rc-\d+", PASS) if sha not in own]
    return [*other[:1], *by_subject(repo, live.release_id, name, IMPLEMENTATION)[:1]]


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
