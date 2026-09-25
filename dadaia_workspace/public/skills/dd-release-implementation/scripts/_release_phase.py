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
#: PLAN §1 — structure only (ADR 0041): any level-2 heading naming the As-is review.
AS_IS = re.compile(r"^##[ \t].*\bas[- ]is review", re.IGNORECASE | re.MULTILINE)
SKILL = Path(__file__).resolve().parents[2] / "dd-release-definition" / "SKILL.md"
AS_IS_FIX = f"copy the PLAN §1 skeleton under the As-is review section of {SKILL} into PLAN.md"
COLUMNS = ["unit", "today", "bugs", "verdict", "why"]


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
                f"releases/{live.release_id}/{name} carries status {status!r} — SPEC, PLAN "
                f"and TASKS must all be '**Status:** {APPROVED}' to enter IMPLEMENTATION",
                f"set '**Status:** {APPROVED}' in {document.resolve()}",
            )


def _refuse_missing_as_is_table(plan: str) -> None:
    heading = AS_IS.search(plan)
    if heading is None:
        raise Refusal("PLAN.md has no '## … As-is review' heading", AS_IS_FIX)
    rows: list[list[str]] = []  # the first table under the heading, split on unescaped pipes
    for line in plan[heading.end() :].split("\n## ")[0].splitlines()[1:]:
        if "|" not in line and rows:
            break
        if "|" in line:
            cells = re.split(r"(?<!\\)\|", line.strip().strip("|"))
            rows.append([cell.strip(" \t`*") for cell in cells])
    if len(rows) < 3 or [c.lower() for c in rows[0]] != COLUMNS:
        raise Refusal("PLAN.md's As-is review heading is not followed by a table with header "
                      "'unit | today | bugs | verdict | why' and >= 1 row", AS_IS_FIX)  # fmt: skip
    for row in (r + [""] * 4 for r in rows[2:]):
        if row[3].upper() not in {"DELETE", "REBUILD", "UPDATE", "KEEP", "ADD"}:
            raise Refusal(f"PLAN.md As-is review row {row[0]!r} carries verdict {row[3]!r} "
                          "— one of DELETE REBUILD UPDATE KEEP ADD", AS_IS_FIX)  # fmt: skip


def set_phase(specs: Path, phase: str, sha: str, pr: int | None = None) -> tuple[str, str]:
    """Move the live release to *phase*, stamp its milestone; *pr* (CLOSURE) enters the note."""
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
            f"finish and mark every task '[x]' in {(live.release_dir / 'TASKS.md').resolve()}",
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
