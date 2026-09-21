#!/usr/bin/env python3
"""`release.py phase` — the two in-candidate transitions a release walks.

`phase` is the ONE writer of `phase`, `defined` and `implemented` (0.4.7 FR5). Those
three fields were Read-then-Edit, which is how `archive` came to refuse on a hand-set
`implemented` it validated itself: the phase and its milestone now move in one act, so
they cannot disagree.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _release_schema import (  # noqa: E402
    APPROVED,
    SHA_RE,
    STATE,
    TRIO,
    extract_status,
    unfinished_tasks,
    utc_now,
)
from _release_store import Live, Refusal, State, commit, live_release  # noqa: E402

SCRIPT = Path(__file__).parent / "release.py"
#: The one ordered lane a candidate walks. DEFINITION is written by `new` — this verb
#: owns the two transitions after it, each from exactly one predecessor, so an
#: out-of-order move and a re-run are the same check.
PREDECESSOR = {"IMPLEMENTATION": "DEFINITION", "CLOSURE": "IMPLEMENTATION"}


def note(state: State, ts: str, text: str) -> None:
    state.setdefault("log", []).append(
        {"ts": ts, "agent": "release.py", "kind": "note", "text": text}
    )


def _refuse_unapproved_trio(live: Live) -> None:
    """A candidate enters IMPLEMENTATION only with all three documents `Approved`."""
    for name in TRIO:
        document = live.release_dir / name
        if not document.is_file():
            raise Refusal(
                f"release {live.release_id} has no {name} at root",
                f"{SCRIPT} new {live.release_id} --specs <specs>",
            )
        status = extract_status(document.read_text(encoding="utf-8"))
        if status != APPROVED:
            raise Refusal(
                f"releases/{live.release_id}/{name} carries status {status!r} — a candidate "
                f"enters IMPLEMENTATION only once SPEC, PLAN and TASKS are all "
                f"'**Status:** {APPROVED}'",
                f"sed -i 's/^\\*\\*Status:\\*\\* .*/**Status:** {APPROVED}/' "
                f"specs/releases/{live.release_id}/{name}",
            )


def refuse_unfinished(live: Live, what: str, fix: str) -> None:
    unfinished = unfinished_tasks(live.release_dir)
    if unfinished:
        raise Refusal(
            f"TASKS.md still carries {len(unfinished)} open '[ ]'/reserved '[-]' marker(s) "
            f"— {what}: {unfinished[0]}",
            fix,
        )


def set_phase(specs: Path, phase: str, sha: str, pr: int | None = None) -> tuple[str, str]:
    """Move the live release to *phase* and stamp the milestone that phase records.

    *pr* is the merged release PR number, recorded in the CLOSURE note: promoting a
    release leaves a number in the log, not a moved directory.
    """
    if not SHA_RE.match(sha):
        raise Refusal(
            f"--sha {sha!r} is not a 7-40 character lowercase hex commit sha",
            f"{SCRIPT} phase {phase} --sha $(git rev-parse --short HEAD)",
        )
    if pr is not None and phase != "CLOSURE":
        raise Refusal(
            f"--pr names the merged release PR and belongs to CLOSURE, not {phase}",
            f"{SCRIPT} phase {phase} --sha {sha}",
        )
    if phase not in PREDECESSOR:
        raise Refusal(
            f"{phase!r} is not a phase this verb writes: DEFINITION belongs to `new` "
            "and ARCHIVED is never written by a verb",
            f"{SCRIPT} phase IMPLEMENTATION --sha {sha}",
        )
    live = live_release(specs)
    current, expected = live.state.get("phase"), PREDECESSOR[phase]
    if current != expected:
        raise Refusal(
            f"release {live.release_id} is in phase {current!r} — {phase} follows "
            f"{expected} exactly once",
            f"{SCRIPT} phase {expected} --sha {sha}",
        )
    ts = utc_now()
    if phase == "IMPLEMENTATION":
        _refuse_unapproved_trio(live)
    else:
        refuse_unfinished(
            live,
            "a candidate closes fully implemented",
            f"sed -i 's/^- \\[-\\]/- [x]/' specs/releases/{live.release_id}/TASKS.md",
        )

    def apply(state: State) -> State:
        if phase == "IMPLEMENTATION":
            state["defined"] = {"sha": sha, "ts": ts}
            note(state, ts, f"Candidate defined at {sha}; phase IMPLEMENTATION.")
        else:
            state["implemented"] = {"sha": sha, "ts": ts}
            promoted = f" Release PR #{pr} merged." if pr is not None else ""
            note(state, ts, f"Candidate implemented at {sha}; phase CLOSURE.{promoted}")
        state["phase"] = phase
        return state

    commit(live.release_dir / STATE, f"releases/{live.release_id}/{STATE}", apply)
    return live.release_id, ts
