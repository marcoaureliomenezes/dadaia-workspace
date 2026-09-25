#!/usr/bin/env python3
"""`release.py phase` — the two in-candidate transitions a release walks.

`phase` is the ONE writer of `phase`, `defined` and `implemented` (0.4.7 FR5): the phase
and its milestone move in one act, so they cannot disagree.
"""

from __future__ import annotations

import re
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
#: DEFINITION is `new`'s; each later phase has one predecessor (out-of-order = re-run).
PREDECESSOR = {"IMPLEMENTATION": "DEFINITION", "CLOSURE": "IMPLEMENTATION"}
#: PLAN §1 — structure only (ADR 0041); the fix prints the skill section whose skeleton passes.
AS_IS = re.compile(r"^##\s+(?:\d+\.\s*)?as-is review[ \t]*$", re.IGNORECASE | re.MULTILINE)
AS_IS_FIX = "sed -n '/^## 2. As-is review/,/^## 3/p' .agents/skills/dd-release-definition/SKILL.md"


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


def _refuse_missing_as_is_table(plan: str) -> None:
    """PLAN.md opens with the As-is review table: the five columns, >= 1 row, known verdicts."""
    heading = AS_IS.search(plan)
    section = plan[heading.end() :].split("\n## ")[0] if heading else ""
    rows = [[c.strip(" `*") for c in line.strip().strip("|").split("|")]
            for line in section.splitlines() if line.strip().startswith("|")]  # fmt: skip
    if len(rows) < 3 or [c.lower() for c in rows[0]] != ["unit", "today", "bugs", "verdict", "why"]:
        raise Refusal("PLAN.md has no As-is review table ('## As-is review' + 'unit | today | "
                      "bugs | verdict | why' + >= 1 row)", AS_IS_FIX)  # fmt: skip
    for row in (r + [""] * 4 for r in rows[2:]):
        if row[3].upper() not in {"DELETE", "REBUILD", "UPDATE", "KEEP", "ADD"}:
            raise Refusal(f"PLAN.md As-is review row {row[0]!r} carries verdict {row[3]!r} "
                          "— one of DELETE REBUILD UPDATE KEEP ADD", AS_IS_FIX)  # fmt: skip


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
        _refuse_missing_as_is_table((live.release_dir / "PLAN.md").read_text(encoding="utf-8"))
    elif unfinished := unfinished_tasks(live.release_dir):
        raise Refusal(
            f"TASKS.md still carries {len(unfinished)} open '[ ]'/reserved '[-]' marker(s) "
            f"— a candidate closes fully implemented: {unfinished[0]}",
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
