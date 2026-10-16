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
from _grammar import SHA_RE, STATE
from _platform import command, read_text, run
from _refusal import Refusal, fix_of
from _release_check import candidate_errors
from _release_schema import (
    APPROVED,
    CANDIDATE_DOCS,
    CLOSURE,
    DEFINITION,
    IMPLEMENTATION,
    PHASES,
    extract_status,
)
from _release_store import SCRIPT, Live, State, at_head, commit, live_release
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
                f"Operator action: write {document.resolve()} carrying '**Status:** {APPROVED}'",
            )
        status = extract_status(read_text(document))
        if status != APPROVED:
            raise Refusal(
                f"{document.relative_to(live.release_dir).as_posix()} of release {live.release_id} "
                f"carries status {status!r} — SPEC and PLAN "
                f"must both be '**Status:** {APPROVED}' to enter {IMPLEMENTATION}",
                f"Operator action: set '**Status:** {APPROVED}' in {document.resolve()}",
            )
    return candidate


def _worktree_rows(root: Path) -> list[dict[str, Any]]:
    """The rows of `worktree.py list --json`, the worktrees' one owner, run as its own script."""
    owner = Path(__file__).resolve().parents[2] / "dd-gitflow-default" / "scripts" / "worktree.py"
    done = run([sys.executable, str(owner), "list", "--json"], cwd=root, env=_git.scrubbed_env())
    if done.returncode:
        lines = done.stderr.splitlines()
        fix = fix_of(done.stderr, command(sys.executable, str(owner), "list"))
        raise Refusal(f"worktree rows unreadable: {lines[0] if lines else done.returncode}", fix)
    rows: list[dict[str, Any]] = json.loads(done.stdout)
    return rows


def _refuse_open_worktrees(specs: Path) -> None:
    """Closure waits for every worktree row of the repo, bar its own tree: a candidate's `wt-rc`
    tree holds no work and never blocks it. Read from the worktree owner's rows."""
    from _ledger import workspace_of

    root = workspace_of(specs)
    if root is None:  # no workspace holds this tree: there is no worktree to wait for
        return
    top = _git.git(specs, "rev-parse", "--path-format=absolute", "--show-toplevel",
                   "--git-common-dir", check=False).split() or ["", ""]  # fmt: skip
    repo = Path(top[1]).parent.name
    held = [r for r in _worktree_rows(root) if r["repo"] == repo
            and Path(str(r["path"])).name != "wt-rc"
            and Path(str(r["path"])).resolve() != Path(top[0]).resolve()]  # fmt: skip
    if held:
        fix = held[0]["exit"] or f"Agent action: land or remove the wt/* work at {held[0]['path']}, then close again"  # fmt: skip
        raise Refusal(f"repos/{repo} still holds {len(held)} open wt/* worktree(s) — a "
                      "candidate closes with every one merged", str(fix))  # fmt: skip


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


def set_phase(specs: Path, phase: str, sha: str) -> tuple[str, str]:
    """Move the live release to *phase* and stamp its milestone."""
    if not SHA_RE.match(sha):
        raise Refusal(
            f"--sha {sha!r} is not a 7-40 character lowercase hex commit sha",
            at_head(specs, "phase", phase),
        )
    live = live_release(specs)
    current = str(live.state.get("phase"))
    if PREDECESSOR.get(phase) != current:
        refusal = Refusal(
            f"release {live.release_id} is in phase {current!r} — `phase` writes "
            f"{IMPLEMENTATION} after {DEFINITION} and {CLOSURE} after {IMPLEMENTATION}, once each",
            SCRIPT(*NEXT.get(current, "check").split(), "--sha", sha),
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
        state[milestone] = {"sha": sha, "ts": ts}
        state.setdefault("log", []).append({
            "ts": ts, "agent": "release.py", "kind": "milestone", **rc,
            "milestone": milestone, "sha": sha,
            "text": f"Candidate {milestone} at {sha}; phase {phase}."})  # fmt: skip
        state["phase"] = phase
        return state

    commit(live.release_dir / STATE, f"releases/{live.release_id}/{STATE}", apply)
    return live.release_id, ts
