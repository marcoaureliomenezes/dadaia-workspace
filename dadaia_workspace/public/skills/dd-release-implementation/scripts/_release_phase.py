#!/usr/bin/env python3
"""`release.py phase` — the two in-candidate transitions a release walks.

`phase` is the ONE writer of `phase`, `defined` and `implemented` (0.4.7 FR5): the phase
and its milestone move in one act, so they cannot disagree.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import _clock
import _git
from _grammar import SHA_RE, STATE
from _refusal import Refusal
from _release_check import candidate_errors
from _release_schema import (
    APPROVED,
    CANDIDATE_DOCS,
    CLOSURE,
    DEFINITION,
    IMPLEMENTATION,
    PHASES,
    extract_status,
    next_candidate,
)
from _release_store import SCRIPT, Live, State, commit, live_release
from _specs import choice

#: DEFINITION is `new`'s; each later phase has one predecessor (out-of-order = re-run).
PREDECESSOR = dict(zip(PHASES[1:], PHASES, strict=False))


def _refuse_unapproved_docs(live: Live) -> Path:
    """A candidate enters IMPLEMENTATION only with SPEC and PLAN `Approved`; returns the
    candidate folder that holds them (no folder yet: `rc-1/` is where they belong)."""
    candidate = live.candidate or live.release_dir / "rc-1"
    for name in CANDIDATE_DOCS:
        document = candidate / name
        if not document.is_file():
            raise Refusal(
                f"release {live.release_id} has no {document.relative_to(live.release_dir).as_posix()}",
                f"Operator action: write {document.resolve()} carrying '**Status:** {APPROVED}'",
            )
        status = extract_status(document.read_text(encoding="utf-8"))
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
    done = subprocess.run([sys.executable, str(owner), "list", "--json"], cwd=root, env=_git.scrubbed_env(),
                          capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)  # fmt: skip
    if done.returncode:
        lines = done.stderr.splitlines()
        fix = next(
            (ln[5:] for ln in lines if ln.startswith("fix: ")), f"{sys.executable} {owner} list"
        )
        raise Refusal(f"worktree rows unreadable: {lines[0] if lines else done.returncode}", fix)
    rows: list[dict[str, Any]] = json.loads(done.stdout)
    return rows


def _refuse_open_worktrees(specs: Path) -> None:
    """Closure waits for every open `wt/*` of the repo except its own tree and the next
    candidate's define tree — read from the worktree owner's rows."""
    from _ledger import workspace_of

    root = workspace_of(specs)
    if root is None:  # no workspace holds this tree: there is no worktree to wait for
        return
    top = _git.git(specs, "rev-parse", "--path-format=absolute", "--show-toplevel",
                   "--git-common-dir", check=False).split() or ["", ""]  # fmt: skip
    repo = Path(top[1]).parent.name
    live = live_release(specs)
    nxt = f"{live.release_id}-{next_candidate(live.release_dir, live.state).name.replace('-', '')}"
    held = [r for r in _worktree_rows(root) if r["repo"] == repo and r["exit"]
            and r.get("name") != f"{nxt}/define"
            and Path(str(r["path"])).resolve() != Path(top[0]).resolve()]  # fmt: skip
    if held:
        raise Refusal(f"repos/{repo} still holds {len(held)} open wt/* worktree(s) — a "
                      "candidate closes with every one merged", str(held[0]["exit"]))  # fmt: skip


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
            f"{SCRIPT} phase {phase} --sha $(git rev-parse --short HEAD)",
        )
    live = live_release(specs)
    current = str(live.state.get("phase"))
    if PREDECESSOR.get(phase) != current:
        refusal = Refusal(
            f"release {live.release_id} is in phase {current!r} — `phase` writes "
            f"{IMPLEMENTATION} after {DEFINITION} and {CLOSURE} after {IMPLEMENTATION}, once each",
            f"{SCRIPT} {NEXT.get(current, 'check')} --sha {sha}",
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
