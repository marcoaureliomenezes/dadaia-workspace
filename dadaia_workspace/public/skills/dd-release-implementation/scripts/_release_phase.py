#!/usr/bin/env python3
"""`release.py phase` — the two in-candidate transitions a release walks.

`phase` is the ONE writer of `phase`, `defined` and `implemented` (0.4.7 FR5): the phase
and its milestone move in one act, so they cannot disagree.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _release_plan import PLAN_FIX, plan_errors  # noqa: E402
from _release_schema import (  # noqa: E402
    APPROVED,
    SHA_RE,
    STATE,
    TRIO,
    extract_status,
    unfinished_tasks,
    utc_now,
)
from _release_store import SCRIPT, Live, Refusal, State, commit, live_release  # noqa: E402

#: DEFINITION is `new`'s; each later phase has one predecessor (out-of-order = re-run).
PREDECESSOR = {"IMPLEMENTATION": "DEFINITION", "CLOSURE": "IMPLEMENTATION"}


def note(state: State, ts: str, text: str) -> None:
    state.setdefault("log", []).append(
        {"ts": ts, "agent": "release.py", "kind": "note", "text": text}
    )


def _refuse_unapproved_trio(live: Live) -> Path:
    """A candidate enters IMPLEMENTATION only with all three documents `Approved`; returns
    the candidate folder that holds them (no folder yet: `rc-1/` is where they belong)."""
    candidate = live.candidate or live.release_dir / "rc-1"
    for name in TRIO:
        document = candidate / name
        if not document.is_file():
            raise Refusal(
                f"release {live.release_id} has no {document.relative_to(live.release_dir)}",
                f"write {document.resolve()} carrying '**Status:** {APPROVED}'",
            )
        status = extract_status(document.read_text(encoding="utf-8"))
        if status != APPROVED:
            raise Refusal(
                f"{document.relative_to(live.release_dir)} of release {live.release_id} "
                f"carries status {status!r} — SPEC, PLAN "
                f"and TASKS must all be '**Status:** {APPROVED}' to enter IMPLEMENTATION",
                f"set '**Status:** {APPROVED}' in {document.resolve()}",
            )
    return candidate


def _refuse_open_worktrees(specs: Path) -> None:
    """ADR 0128 (4): a candidate closes with every `wt/*` of its repo merged or cleaned — read
    from the owner's rows (imported, ADR 0135), sparing the tree closure runs from."""
    marker = Path(".dadaia", "states", "spec_contexts.json")
    root = next((d for d in (specs, *specs.parents) if (d / marker).is_file()), None)
    if root is None:  # no workspace holds this tree: there is no worktree to wait for
        return
    sys.path.append(str(Path(__file__).resolve().parents[2] / "dd-gitflow-default" / "scripts"))
    import _worktree_git as worktree_git  # the worktrees' owner, read-only (ADR 0135)
    from _worktree_kinds import Refusal as WorktreeRefusal

    top = worktree_git.git(specs, "rev-parse", "--path-format=absolute", "--show-toplevel",
                           "--git-common-dir", check=False).split() or ["", ""]  # fmt: skip
    try:
        found = worktree_git.rows(root)
    except WorktreeRefusal as error:
        raise Refusal(f"worktree rows unreadable: {error}", error.fix) from error
    repo = Path(top[1]).parent.name
    held = [r for r in found if r["repo"] == repo and r["exit"]
            and Path(str(r["path"])).resolve() != Path(top[0]).resolve()]  # fmt: skip
    if held:
        raise Refusal(f"repos/{repo} still holds {len(held)} open wt/* worktree(s) — a "
                      "candidate closes with every one merged", str(held[0]["exit"]))  # fmt: skip


#: The one verb that moves each phase forward — every refusal's fix names it, so a fix
#: never names a verb that refuses in the same state.
NEXT = {"DEFINITION": "phase IMPLEMENTATION", "IMPLEMENTATION": "phase CLOSURE",
        "CLOSURE": "ship --pr <n>"}  # fmt: skip


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
        raise Refusal(
            f"release {live.release_id} is in phase {current!r} — `phase` writes "
            "IMPLEMENTATION after DEFINITION and CLOSURE after IMPLEMENTATION, once each",
            f"{SCRIPT} {NEXT.get(current, 'check')} --sha {sha}",
        )
    ts = utc_now()
    if phase == "IMPLEMENTATION":
        candidate = _refuse_unapproved_trio(live)
        plan = (candidate / "PLAN.md").read_text(encoding="utf-8")
        if errors := plan_errors(plan, unfinished_tasks(candidate)):
            raise Refusal(errors[0], PLAN_FIX)
    elif live.candidate and (unfinished := unfinished_tasks(live.candidate)):
        raise Refusal(
            f"TASKS.md still carries {len(unfinished)} open '[ ]'/reserved '[-]' marker(s) "
            f"— a candidate closes fully implemented: {unfinished[0]}",
            f"finish and mark every task '[x]' in {(live.candidate / 'TASKS.md').resolve()}",
        )
    else:
        _refuse_open_worktrees(specs.resolve())

    def apply(state: State) -> State:
        if phase == "IMPLEMENTATION":
            state["defined"] = {"sha": sha, "ts": ts}
            note(state, ts, f"Candidate defined at {sha}; phase IMPLEMENTATION.")
        else:
            state["implemented"] = {"sha": sha, "ts": ts}
            note(state, ts, f"Candidate implemented at {sha}; phase CLOSURE.")
        state["phase"] = phase
        return state

    commit(live.release_dir / STATE, f"releases/{live.release_id}/{STATE}", apply)
    return live.release_id, ts
