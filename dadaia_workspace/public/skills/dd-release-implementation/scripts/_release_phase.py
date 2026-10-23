#!/usr/bin/env python3
"""`release.py phase` — the two in-candidate transitions a release walks.

`phase` is the one writer of `phase`, `defined` and `implemented`: the phase
and its milestone move in one act, so they cannot disagree.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import _clock
import _git
from _grammar import APPROVED, STATE, extract_status
from _platform import act, command, read_text, run
from _refusal import Refusal, fix_of
from _release_check import candidate_errors
from _release_schema import (
    CANDIDATE_DOCS,
    CLOSURE,
    DEFINITION,
    IMPLEMENTATION,
    PHASES,
    SCRIPT,
    State,
)
from _release_store import Live, commit, live_release
from _specs import choice

#: DEFINITION is `new`'s; each later phase has one predecessor (out-of-order = re-run).
PREDECESSOR = dict(zip(PHASES[1:], PHASES, strict=False))


def _refuse_unapproved_docs(live: Live) -> Path:
    """A candidate enters IMPLEMENTATION only with SPEC and PLAN `Approved`; returns the
    candidate folder that holds them (no folder yet: the first candidate's folder is where they
    belong)."""
    candidate = live.candidate or live.release_dir / "rc-1"
    for name in CANDIDATE_DOCS:
        document = candidate / name
        if not document.is_file():
            raise Refusal(
                f"release {live.release_id} has no {document.relative_to(live.release_dir).as_posix()}",
                act(
                    "agent",
                    f"write {document.resolve()} (its writer per specs/AGENTS.md §4) and put it to the operator for approval",
                ),
            )
        status = extract_status(read_text(document))
        if status != APPROVED:
            raise Refusal(
                f"{document.relative_to(live.release_dir).as_posix()} of release {live.release_id} "
                f"carries status {status!r} — SPEC and PLAN "
                f"must both be '**Status:** {APPROVED}' to enter {IMPLEMENTATION}",
                act("operator", f"set '**Status:** {APPROVED}' in {document.resolve()}"),
            )
    return candidate


def _owner() -> Path:
    """The worktree owner script, run as its own process: the one reader of the worktree rows."""
    return Path(__file__).resolve().parents[2] / "dd-gitflow-default" / "scripts" / "worktree.py"


def _worktree_rows(root: Path) -> list[dict[str, Any]]:
    """The rows of `worktree.py list --json`, the worktrees' one owner, run as its own script."""
    fix = command(sys.executable, str(_owner()), "list")
    try:
        done = run(
            [sys.executable, str(_owner()), "list", "--json"], cwd=root, env=_git.scrubbed_env()
        )
    except OSError as exc:
        raise Refusal(f"worktree rows unreadable: {exc}", fix) from exc
    if done.returncode:
        lines = done.stderr.splitlines()
        raise Refusal(
            f"worktree rows unreadable: {lines[0] if lines else done.returncode}",
            fix_of(done.stderr, fix),
        )
    rows: list[dict[str, Any]] = json.loads(done.stdout)
    return rows


def _refuse_open_worktrees(specs: Path) -> None:
    """Closure waits for every worktree row of the repo bar a `wt-rc` tree (it holds no work) and
    the tree it runs from. Read from the worktree owner's rows."""
    from _ledger import workspace_of

    root = workspace_of(specs)
    if root is None:  # no workspace holds this tree: there is no worktree to wait for
        return
    try:
        main = _git.main_checkout(specs)
    except _git.GitError:
        raise Refusal(f"{specs} is in no git checkout", act("agent", "close from the specs of a repo's git checkout")) from None  # fmt: skip
    own = specs.parent.resolve()
    held = [
        r for r in _worktree_rows(root)
        if r["repo"] == main.name and r["kind"] != "rc" and Path(str(r["path"])).resolve() != own
    ]  # fmt: skip
    if held:
        raise Refusal(f"repos/{main.name} still holds {len(held)} open wt/* worktree(s) — a "
                      "candidate closes with every one merged", held[0]["exit"] or held[0]["fix"])  # fmt: skip


#: The one verb that moves each phase forward — every refusal's fix names it, so a fix
#: never names a verb that refuses in the same state.
NEXT = {
    **{now: f"phase {then}" for now, then in zip(PHASES, PHASES[1:], strict=False)},
    CLOSURE: "ship",
}
#: `ship`'s one optional value no code knows: the promote PR's number, when the host has one.
SHIP_PR = "with --pr set to the promote PR's number, when the host has one"
#: What the operator supplies to each NEXT verb that the code cannot fill.
SUPPLY = {CLOSURE: SHIP_PR}


def set_phase(specs: Path, phase: str) -> tuple[str, str]:
    """Move the live release to *phase* and stamp its milestone."""
    live = live_release(specs)
    current = str(live.state.get("phase"))
    if PREDECESSOR.get(phase) != current:
        refusal = Refusal(
            f"release {live.release_id} is in phase {current!r} — `phase` writes "
            f"{IMPLEMENTATION} after {DEFINITION} and {CLOSURE} after {IMPLEMENTATION}, once each",
            SCRIPT(*NEXT.get(current, "check").split()),
        )
        raise choice(refusal, SUPPLY.get(current, ""))
    ts, candidate = _clock.now_iso(), live.candidate
    if phase == IMPLEMENTATION:
        candidate = _refuse_unapproved_docs(live)
        if errors := candidate_errors(candidate):
            raise Refusal(errors[0][1], errors[0][2])
    else:
        _refuse_open_worktrees(specs.resolve())

    milestone = "defined" if phase == IMPLEMENTATION else "implemented"
    rc = {"candidate": candidate.name} if candidate else {}

    def apply(state: State) -> State:
        # The slot is the live candidate's stamp; the `milestone` entry is its history .
        state[milestone] = {"ts": ts}
        state.setdefault("log", []).append({
            "ts": ts, "agent": "release.py", "kind": "milestone", **rc,
            "milestone": milestone, "text": f"Candidate {milestone}; phase {phase}."})  # fmt: skip
        state["phase"] = phase
        return state

    commit(live.release_dir / STATE, f"releases/{live.release_id}/{STATE}", apply)
    return live.release_id, ts
