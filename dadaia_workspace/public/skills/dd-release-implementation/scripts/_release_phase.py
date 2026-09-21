#!/usr/bin/env python3
"""`release.py phase` and `release.py rc-archive` — the two in-candidate transitions.

`phase` is the ONE writer of `phase`, `defined` and `implemented` (0.4.7 FR5). Those
three fields were Read-then-Edit, which is how `archive` came to refuse on a hand-set
`implemented` it validated itself: the phase and its milestone now move in one act, so
they cannot disagree.

`rc-archive`'s sibling half lives in `_release_rc`; both share this module's note and
task-marker refusals, so the two phase writers cannot disagree about either.
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
#: The one ordered lane a candidate walks. DEFINITION is written by `new`/`rc-archive`
#: and ARCHIVED by `archive` — this verb owns the two transitions in between, each from
#: exactly one predecessor, so an out-of-order move and a re-run are the same check.
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


def set_phase(specs: Path, phase: str, sha: str) -> tuple[str, str]:
    """Move the live release to *phase* and stamp the milestone that phase records."""
    if not SHA_RE.match(sha):
        raise Refusal(
            f"--sha {sha!r} is not a 7-40 character lowercase hex commit sha",
            f"{SCRIPT} phase {phase} --sha $(git rev-parse --short HEAD)",
        )
    if phase not in PREDECESSOR:
        raise Refusal(
            f"{phase!r} is not a phase this verb writes: DEFINITION belongs to "
            "`new`/`rc-archive` and ARCHIVED to `archive`",
            f"{SCRIPT} phase IMPLEMENTATION --sha {sha}",
        )
    live = live_release(specs)
    current, expected = live.state.get("phase"), PREDECESSOR[phase]
    if current != expected:
        raise Refusal(
            f"release {live.release_id} is in phase {current!r} — {phase} follows "
            f"{expected} exactly once",
            f"{SCRIPT} phase {expected} --sha {sha}"
            if current != phase
            else f"{SCRIPT} rc-archive --specs {specs}",
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
            rc = int(state.get("rc") or 0) + 1
            state["implemented"] = {"sha": sha, "rc": rc, "ts": ts}
            note(state, ts, f"Candidate {rc} implemented at {sha}; phase CLOSURE.")
        state["phase"] = phase
        return state

    commit(live.release_dir / STATE, f"releases/{live.release_id}/{STATE}", apply)
    return live.release_id, ts
