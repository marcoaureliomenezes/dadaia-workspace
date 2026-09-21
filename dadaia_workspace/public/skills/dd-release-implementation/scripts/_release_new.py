#!/usr/bin/env python3
"""`release.py new <id>` — the ONE birth act of a release.

SPEC.md and `_RELEASE.json` are written in ONE transaction; a failure anywhere removes
the whole directory. `--origin bugs:<ids>` seeds one scope clause per bug from the ledger."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _release_schema import ARTIFACTS, SEMVER_RE, STATE, utc_now  # noqa: E402
from _release_store import Refusal, State, live_ids, replace, validated  # noqa: E402

SCRIPT = Path(__file__).parent / "release.py"
SPEC_STUB = """\
# SPEC — Release: {release_id}

**Status:** Draft
**Release ID:** {release_id}
**Owner:** product-engineer
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


def birth_state(release_id: str) -> State:
    """The birth document: DEFINITION, no candidate yet, every milestone unreached."""
    return {
        "schema": "release-state-v1",
        "release": release_id,
        "phase": "DEFINITION",
        "rc": None,
        "defined": None,
        "implemented": None,
        "shipped": None,
        "log": [
            {
                "ts": utc_now(),
                "agent": "release.py new",
                "kind": "note",
                "text": f"Release {release_id} born",
            }
        ],
    }


def refuse_unfree(specs: Path, release_id: str) -> Path:
    """No-clobber: the single-live-release slot, the directory, every artifact inside
    it; a symlinked releases/ or release dir is refused outright (CWE-59)."""
    if not SEMVER_RE.match(release_id):
        raise Refusal(
            f"{release_id!r} is not a bare SemVer release id (M.m.p)",
            f"{SCRIPT} new 0.1.23 --specs {specs}",
        )
    others = [other for other in live_ids(specs) if other != release_id]
    if others:
        raise Refusal(
            f"a live release already exists ({', '.join(others)}) — exactly one is "
            f"allowed: stack the work as a candidate, or ship {others[0]} first",
            f"{SCRIPT} rc-archive --specs {specs}",
        )
    releases = specs / "releases"
    release_dir = releases / release_id
    if releases.is_symlink() or release_dir.is_symlink():
        raise Refusal(
            f"releases/{release_id} resolves through a symlink — refusing to mint through one",
            f"ls -l {releases}",
        )
    for name in ARTIFACTS:
        if (release_dir / name).exists() or (release_dir / name).is_symlink():
            raise Refusal(
                f"releases/{release_id}/{name} already exists — refusing to overwrite",
                f"{SCRIPT} check --specs {specs}",
            )
    return release_dir


def new_release(specs: Path, release_id: str, today: str, origin: str) -> Path:
    """Mint ``releases/<id>/`` with its SPEC stub and state document, all or nothing."""
    release_dir = refuse_unfree(specs, release_id)
    rel = f"releases/{release_id}/{STATE}"
    text = validated(birth_state(release_id), rel)
    created = not release_dir.exists()
    try:
        release_dir.mkdir(parents=True, exist_ok=True)
        (release_dir / "SPEC.md").write_text(
            SPEC_STUB.format(
                release_id=release_id,
                today=today,
                origin=origin,
                scope=seeded_scope(specs, origin),
            ),
            encoding="utf-8",
        )
        replace(release_dir / STATE, text)
    except BaseException:
        if created:
            shutil.rmtree(release_dir, ignore_errors=True)
        raise
    return release_dir
