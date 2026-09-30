#!/usr/bin/env python3
"""`release.py phase` — the two in-candidate transitions a release walks.

`phase` is the ONE writer of `phase`, `defined` and `implemented` (0.4.7 FR5): the phase
and its milestone move in one act, so they cannot disagree.
"""

from __future__ import annotations

import re
import subprocess
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
from _release_store import SCRIPT, Live, Refusal, State, commit, live_release  # noqa: E402

#: DEFINITION is `new`'s; each later phase has one predecessor (out-of-order = re-run).
PREDECESSOR = {"IMPLEMENTATION": "DEFINITION", "CLOSURE": "IMPLEMENTATION"}
#: PLAN §1 — structure only (ADR 0041): any level-2 heading naming the As-is review.
AS_IS = re.compile(r"^##[ \t].*\bas[- ]is review", re.IGNORECASE | re.MULTILINE)
SKILL = Path(__file__).resolve().parents[2] / "dd-release-definition" / "SKILL.md"
WORKTREE = Path(__file__).resolve().parents[2] / "dd-gitflow-default" / "scripts" / "worktree.py"
AS_IS_FIX = f"copy the PLAN §1 skeleton under the As-is review section of {SKILL} into PLAN.md"
COLUMNS = ["unit", "today", "bugs", "verdict", "why"]
AUTH_COLUMNS = ["question", "authority", "consults", "deleted"]
AUTHORITIES = re.compile(r"^###[ \t].*\bAuthorities\b", re.IGNORECASE | re.MULTILINE)


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
                f"{SCRIPT} new {live.release_id}",
            )
        status = extract_status(document.read_text(encoding="utf-8"))
        if status != APPROVED:
            raise Refusal(
                f"releases/{live.release_id}/{name} carries status {status!r} — SPEC, PLAN "
                f"and TASKS must all be '**Status:** {APPROVED}' to enter IMPLEMENTATION",
                f"set '**Status:** {APPROVED}' in {document.resolve()}",
            )


def _refuse_open_worktrees(repo: Path) -> None:
    """ADR 0128 (4): a candidate closes with no `wt/*` branch left in its repo, read from git."""
    refs = subprocess.run(["git", "-C", str(repo), "for-each-ref", "--format=%(refname:short) %(worktreepath)",
                           "refs/heads/wt/"], capture_output=True, text=True, check=False).stdout  # fmt: skip
    if refs.strip():
        branch, _, path = refs.splitlines()[0].partition(" ")
        raise Refusal(f"{repo} still holds branch {branch} — a candidate closes with every wt/* "
                      "worktree merged", f"python3 {WORKTREE} merge {path}" if path
                      else f"git -C {repo} branch -d {branch}")  # fmt: skip


def _table(text: str, columns: list[str]) -> list[list[str]]:
    rows: list[list[str]] = []
    for line in text.splitlines():
        cells = [c.strip(" \t`*") for c in re.split(r"(?<!\\)\|", line.strip().strip("|"))]
        if rows and "|" not in line:
            break
        if rows or [c.lower() for c in cells] == columns:
            rows.append(cells + [""] * len(columns))
    return rows[2:] if len(rows) >= 3 else []


def _refuse_missing_as_is_table(plan: str) -> None:
    heading = AS_IS.search(plan)
    if heading is None:
        raise Refusal("PLAN.md has no '## … As-is review' heading", AS_IS_FIX)
    rows = _table(section := plan[heading.end() :].split("\n## ")[0], COLUMNS)
    if not rows:
        raise Refusal("PLAN.md's As-is review heading is not followed by a table with header "
                      "'unit | today | bugs | verdict | why' and >= 1 row", AS_IS_FIX)  # fmt: skip
    for row in rows:
        if row[3].upper() not in {"DELETE", "REBUILD", "UPDATE", "KEEP", "ADD"}:
            raise Refusal(f"PLAN.md As-is review row {row[0]!r} carries verdict {row[3]!r} "
                          "— one of DELETE REBUILD UPDATE KEEP ADD", AS_IS_FIX)  # fmt: skip
    rows = _table(section[m.end() :], AUTH_COLUMNS) if (m := AUTHORITIES.search(section)) else []
    if not rows:
        raise Refusal("PLAN.md §1 has no '### … Authorities' table with header "
                      "'question | authority | consults | deleted' and >= 1 row", AS_IS_FIX)  # fmt: skip
    seen: dict[str, str] = {}
    for question, authority, *_ in rows:
        if not authority:
            raise Refusal(f"PLAN.md Authorities row {question!r} has an empty authority", AS_IS_FIX)
        if (first := seen.setdefault(question.lower(), authority)) != authority:
            raise Refusal(f"PLAN.md Authorities question {question.lower()!r} names two "
                          f"authorities: `{first}` and `{authority}` — keep one", AS_IS_FIX)  # fmt: skip


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
        _refuse_unapproved_trio(live)
        _refuse_missing_as_is_table((live.release_dir / "PLAN.md").read_text(encoding="utf-8"))
    elif unfinished := unfinished_tasks(live.release_dir):
        raise Refusal(
            f"TASKS.md still carries {len(unfinished)} open '[ ]'/reserved '[-]' marker(s) "
            f"— a candidate closes fully implemented: {unfinished[0]}",
            f"finish and mark every task '[x]' in {(live.release_dir / 'TASKS.md').resolve()}",
        )
    else:
        _refuse_open_worktrees(specs.resolve().parent)

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
