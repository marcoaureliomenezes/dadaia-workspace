#!/usr/bin/env python3
"""`release.py rc-archive` — the "continue" answer of the promote-or-continue gate.

The completed candidate trio moves into the next `rc-N/` (ADR 0008), the counter bumps
and the phase resets to DEFINITION so the next candidate's trio can be born at root. The
version never increments here — only an operator-approved deploy does that.

The trio moves BEFORE the state is written and is moved back if that write refuses: the
state document is the thing every reader resolves the live candidate by, so it is the
last thing to change and never names an `rc-N/` that is not on disk.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _release_phase import SCRIPT, note, refuse_unfinished  # noqa: E402
from _release_schema import STATE, TRIO, rc_numbers, utc_now  # noqa: E402
from _release_store import Refusal, State, commit, live_release  # noqa: E402


def rc_archive(specs: Path) -> tuple[str, int, Path]:
    """Archive the live release's completed candidate trio into the next ``rc-N/``."""
    live = live_release(specs)
    missing = [name for name in TRIO if not (live.release_dir / name).is_file()]
    if missing:
        raise Refusal(
            f"release {live.release_id} has no complete trio at root: {', '.join(missing)}",
            f"{SCRIPT} check --specs {specs}",
        )
    refuse_unfinished(
        live,
        "a candidate archives only fully implemented ([x])",
        f"sed -i 's/^- \\[-\\]/- [x]/' specs/releases/{live.release_id}/TASKS.md",
    )
    if live.state.get("phase") != "CLOSURE":
        raise Refusal(
            f"release {live.release_id} is in phase {live.state.get('phase')!r} — a "
            "candidate archives only from CLOSURE",
            f"{SCRIPT} phase CLOSURE --sha $(git rev-parse --short HEAD)",
        )
    rc = max(rc_numbers(live.release_dir), default=0) + 1
    ts = utc_now()
    rc_dir = live.release_dir / f"rc-{rc}"
    rc_dir.mkdir()
    moved: list[str] = []
    try:
        for name in TRIO:
            (live.release_dir / name).rename(rc_dir / name)
            moved.append(name)
        commit(live.release_dir / STATE, f"releases/{live.release_id}/{STATE}",
               lambda state: _archived_state(state, rc, ts))  # fmt: skip
    except BaseException:
        for name in moved:
            (rc_dir / name).rename(live.release_dir / name)
        rc_dir.rmdir()
        raise
    return live.release_id, rc, rc_dir


def _archived_state(state: State, rc: int, ts: str) -> State:
    state["rc"], state["phase"] = rc, "DEFINITION"
    note(
        state,
        ts,
        f"Candidate {rc} archived to rc-{rc}/ (operator ruled continue at the "
        "promote-or-continue gate); root is ready for the next candidate's trio.",
    )
    return state
