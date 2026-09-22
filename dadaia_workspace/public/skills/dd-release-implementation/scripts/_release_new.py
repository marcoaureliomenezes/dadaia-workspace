#!/usr/bin/env python3
"""`release.py new <id>` — the ONE act that opens a candidate, birth or stacked.

SPEC.md and `_RELEASE.json` are written in ONE transaction; a failure anywhere removes the
whole directory. `--origin bugs:<ids>` seeds one scope clause per bug from the ledger."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _release_schema import ARTIFACTS, SEMVER_RE, STATE, TRIO, utc_now  # noqa: E402
from _release_store import Refusal, State, live_ids, read_state, replace, validated  # noqa: E402

SCRIPT = Path(__file__).parent / "release.py"
SPEC_STUB = """\
# SPEC — Release: {release_id}

**Status:** Draft
**Release ID:** {release_id}
**Owner:** dd-product-engineer
**Opened:** {today}
**Origin:** {origin}

---

## 1. Problem and context

(Describe the problem this release solves.)

---

## 2. Objective

(State the release objective in one sentence.)

---

## 3. Scope

{scope}

---

## 4. Out of scope

(Explicitly list what this release does NOT cover.)

---

## 5. Dependencies and risks

(Upstream blockers, sequencing constraints, risk table.)
"""


def seeded_scope(specs: Path, origin: str) -> str:
    """One scope clause per bug named by a `bugs:` origin, else the placeholder."""
    if not origin.startswith("bugs:"):
        return "(List the scope clusters / acceptance criteria.)"
    ledger = specs / "bugs" / "BUGS.jsonl"
    lines = ledger.read_text(encoding="utf-8").splitlines() if ledger.is_file() else []
    known = {str(r.get("id")): r for r in (json.loads(x) for x in lines if x.strip())}
    bugs = [b.strip() for b in origin[5:].split(",") if b.strip()]
    return "\n".join(
        f"### FR{n} — {known.get(bug, {}).get('title', bug)}\n\n- Bug `{bug}`.\n"
        f"- Repro: {known.get(bug, {}).get('repro', '(unrecorded)')}\n"
        for n, bug in enumerate(bugs, start=1)
    )


def candidate_state(release_id: str, prior: State | None) -> State:
    """The state a candidate opens on: a birth document, or the live release's own closed
    state reopened — the stacked candidate keeps every milestone standing."""
    state: State = prior or {
        "schema": "release-state-v1", "release": release_id, "phase": "DEFINITION",
        "defined": None, "implemented": None, "shipped": None, "log": [],
    }  # fmt: skip
    closed = ((prior or {}).get("implemented") or {}).get("sha")
    stacked = f"Candidate born on {release_id} (prior candidate closed at {closed})"
    note = stacked if prior else f"Release {release_id} born"
    state["phase"] = "DEFINITION"
    state["log"].append({"ts": utc_now(), "agent": "release.py new", "kind": "note", "text": note})
    return state


def refuse_unfree(specs: Path, release_id: str) -> State | None:
    """`new`'s two legal states: no live release (birth — returns ``None``), and the live
    release IS *release_id* in phase CLOSURE, the stacked candidate the law requires
    (returns the closed state to reopen). Anything else, or a symlink, refuses (CWE-59)."""
    if not SEMVER_RE.match(release_id):
        raise Refusal(
            f"{release_id!r} is not a bare SemVer release id (M.m.p)",
            f"{SCRIPT} new 0.1.23 --specs {specs}",
        )
    releases, live = specs / "releases", live_ids(specs)
    release_dir = releases / release_id
    for path in (releases, release_dir, *(release_dir / name for name in ARTIFACTS)):
        if path.is_symlink():
            raise Refusal(
                f"{path.name} resolves through a symlink — refusing to mint through one",
                f"ls -l {releases}",
            )
    others = [other for other in live if other != release_id]
    if others:
        raise Refusal(
            f"a live release already exists ({', '.join(others)}) — exactly one is allowed: "
            f"stack the next candidate on it, or ship {others[0]} first",
            f"{SCRIPT} check --specs {specs}",
        )
    if release_id not in live:
        return None
    prior = read_state(release_dir / STATE)
    if prior.get("phase") != "CLOSURE":
        raise Refusal(
            f"release {release_id} is live in phase {prior.get('phase')!r} — the next "
            "candidate is stacked only on a closed one",
            f"{SCRIPT} phase CLOSURE --sha $(git rev-parse --short HEAD) --specs {specs}",
        )
    return prior


def new_release(specs: Path, release_id: str, today: str, origin: str) -> Path:
    """Open ``releases/<id>/`` on a fresh SPEC stub and state document, all or nothing. A
    stacked candidate's closed PLAN/TASKS die: a stale Approved pair would let `phase
    IMPLEMENTATION` pass on the prior candidate's documents."""
    prior = refuse_unfree(specs, release_id)
    release_dir = specs / "releases" / release_id
    text = validated(candidate_state(release_id, prior), f"releases/{release_id}/{STATE}")
    stub = SPEC_STUB.format(
        release_id=release_id, today=today, origin=origin, scope=seeded_scope(specs, origin)
    )
    created = not release_dir.exists()
    try:
        release_dir.mkdir(parents=True, exist_ok=True)
        (release_dir / "SPEC.md").write_text(stub, encoding="utf-8")
        replace(release_dir / STATE, text)
        for name in TRIO[1:]:
            (release_dir / name).unlink(missing_ok=True)
    except BaseException:
        if created:
            shutil.rmtree(release_dir, ignore_errors=True)
        raise
    return release_dir
