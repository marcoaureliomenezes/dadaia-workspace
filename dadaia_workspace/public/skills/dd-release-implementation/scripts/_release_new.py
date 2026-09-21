#!/usr/bin/env python3
"""`release.py new <id>` — the ONE birth act of a release (0.4.7 FR2).

SPEC.md and `_RELEASE.json` are written in ONE transaction: the gate's MEMORY class,
`dadaia context show`, `dd-spec-navigator` and `rc-archive` all resolve the live release
by the state document's presence, so a SPEC minted without it exists for nobody (bug
`release-new-writes-spec-only-never-creates-release-state`). Nothing touches disk until
the state bytes have passed `check`, and a failure anywhere removes the whole directory.
"""

from __future__ import annotations

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

---

## 1. Problem and context

(Describe the problem this release solves.)

---

## 2. Objective

(State the release objective in one sentence.)

---

## 3. Scope

(List the scope clusters / acceptance criteria.)

---

## 4. Out of scope

(Explicitly list what this release does NOT cover.)

---

## 5. Dependencies and risks

(Upstream blockers, sequencing constraints, risk table.)
"""


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
    """No-clobber, three layers deep: the single-live-release slot (ADR 0005), the
    directory as one unit, and every canonical artifact inside it. A symlinked
    ``releases/`` or release directory is refused outright (CWE-59) — minting through
    one could write the stub outside *specs*."""
    if not SEMVER_RE.match(release_id):
        raise Refusal(
            f"{release_id!r} is not a bare SemVer release id (M.m.p; a 'v' prefix is the "
            "retired archive axis and is refused at minting)",
            f"{SCRIPT} new 0.1.23 --specs {specs}",
        )
    others = [other for other in live_ids(specs) if other != release_id]
    if others:
        raise Refusal(
            f"a live release already exists ({', '.join(others)}) — the release-candidates "
            f"model allows exactly one (ADR 0005): stack the work as a candidate, or ship "
            f"{others[0]} first",
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
                f"releases/{release_id}/{name} already exists — refusing to overwrite a "
                "minted release artifact",
                f"{SCRIPT} check --specs {specs}",
            )
    return release_dir


def new_release(specs: Path, release_id: str, today: str) -> Path:
    """Mint ``releases/<id>/`` with its SPEC stub and state document, all or nothing."""
    release_dir = refuse_unfree(specs, release_id)
    rel = f"releases/{release_id}/{STATE}"
    text = validated(birth_state(release_id), rel)
    created = not release_dir.exists()
    try:
        release_dir.mkdir(parents=True, exist_ok=True)
        (release_dir / "SPEC.md").write_text(
            SPEC_STUB.format(release_id=release_id, today=today), encoding="utf-8"
        )
        replace(release_dir / STATE, text)
    except BaseException:
        if created:
            shutil.rmtree(release_dir, ignore_errors=True)
        raise
    return release_dir
