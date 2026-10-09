#!/usr/bin/env python3
"""`release.py new <id>` — the ONE act that opens a candidate, birth or stacked: its
`rc-<N+1>/SPEC.md` and `_RELEASE.json` in ONE transaction (a failure removes what it made);
`--origin bugs:<ids>` seeds one scope clause per bug from the ledger."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.append(str(Path(__file__).resolve().parents[2] / "dd-bug-resolution" / "scripts"))

from _ledger import records, replace  # noqa: E402
from _release_schema import SEMVER_RE, STATE, next_candidate, utc_now  # noqa: E402
from _release_store import SCRIPT, Refusal, State, live_ids, read_state, validated  # noqa: E402
from _release_tree import BUG_WINDOW, tree_findings  # noqa: E402

SPEC_STUB = """\
# SPEC — Release: {release_id}

**Status:** Draft
**Release ID:** {release_id}
**Owner:** dd-product-engineer
**Opened:** {today}
**Origin:** {origin}

---

{bug_window}

(Read the prior candidate's `## Bug window review`, then inspect each resolved record's
persisted `fix_sha` with `git show` as `dd-bug-resolution/LINEAGE.md` defines.)

## 1. Problem

(Describe the problem this release solves.)

## 2. Measurable Goals

(List observable outcomes.)

## 3. Non-goals

(Explicitly list what this release does NOT cover.)

## 4. Requirements

{scope}

## 5. Constraints and risks

(Upstream blockers, sequencing constraints, risk table.)

## 6. Open questions

(Questions the operator must decide before approval, or `none`.)
"""


def seeded_scope(specs: Path, origin: str) -> str:
    """One scope clause per bug named by a `bugs:` origin, else the placeholder."""
    if not origin.startswith("bugs:"):
        return "(List the scope clusters / acceptance criteria.)"
    known = {str(r.get("id")): r for r in records(specs / "bugs" / "BUGS.jsonl")}
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
    (returns the closed state to reopen), once the tree's global open-bug readiness permits it.
    Anything else, a red tree, or a symlink, refuses."""
    if not SEMVER_RE.match(release_id):
        raise Refusal(
            f"{release_id!r} is not a bare SemVer release id (M.m.p)",
            f"{SCRIPT} new 0.1.23",
        )
    releases, live = specs / "releases", live_ids(specs)
    release_dir = releases / release_id
    for path in (releases, release_dir, release_dir / STATE):
        if path.is_symlink():
            raise Refusal(
                f"{path.name} resolves through a symlink — refusing to mint through one",
                f"ls -l {releases}",
            )
    if findings := tree_findings(specs):
        first = f"{findings[0]['path']} {findings[0]['message']}"
        raise Refusal(f"a release opens only on a clean tree: {first}", f"{SCRIPT} check")
    others = [other for other in live if other != release_id]
    if others:
        raise Refusal(
            f"a live release already exists ({', '.join(others)}) — exactly one is allowed: "
            f"stack the next candidate on it, or ship {others[0]} first",
            f"{SCRIPT} check",
        )
    if release_id not in live:
        return None
    prior = read_state(release_dir / STATE)
    if prior.get("phase") != "CLOSURE":
        raise Refusal(
            f"release {release_id} is live in phase {prior.get('phase')!r} — the next "
            "candidate is stacked only on a closed one",
            f"{SCRIPT} phase CLOSURE --sha $(git rev-parse --short HEAD)",
        )
    return prior


def new_release(specs: Path, release_id: str, today: str, origin: str) -> Path:
    """Open ``releases/<id>/rc-<N+1>/`` on a fresh SPEC stub and reopen the state document,
    all or nothing (ADR 0150): a closed ``rc-<N>/`` is never touched. Returns the candidate."""
    prior = refuse_unfree(specs, release_id)
    release_dir = specs / "releases" / release_id
    text = validated(candidate_state(release_id, prior), f"releases/{release_id}/{STATE}")
    stub = SPEC_STUB.format(
        release_id=release_id,
        today=today,
        origin=origin,
        scope=seeded_scope(specs, origin),
        bug_window=BUG_WINDOW,
    )
    candidate = next_candidate(release_dir)
    made = candidate if release_dir.exists() else release_dir
    candidate.mkdir(parents=True)
    try:
        (candidate / "SPEC.md").write_text(stub, encoding="utf-8")
        replace(release_dir / STATE, text)
    except BaseException:
        shutil.rmtree(made, ignore_errors=True)
        raise
    return candidate
