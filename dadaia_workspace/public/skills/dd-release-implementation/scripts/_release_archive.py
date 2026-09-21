#!/usr/bin/env python3
"""`release.py archive <id> --shipped --pr --next` — the promote lane as ONE act.

Refuses — writing NOTHING — unless *id* IS the one live release, its TASKS carry no
`[ ]`/`[-]` marker, its phase is CLOSURE, `_archive/<id>/` is free and the three
operator-supplied values are well-formed. Every refusal names an executable `fix:`.

On success, in this order: the state document takes `shipped`/ARCHIVED, the whole
directory moves under `_archive/`, the next release is born, and the ONE histo record is
appended LAST. Last on purpose — it is the only step with an append-only ledger behind
it, so the record exists if and only if every filesystem step already succeeded.
Everything before it rolls back here, so a failure anywhere leaves the tree
byte-identical and the operator re-runs one verb. This verb runs no git: it PRINTS the
commands the operator runs next.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _release_histo import append_histo, summary  # noqa: E402
from _release_new import new_release  # noqa: E402
from _release_phase import note  # noqa: E402
from _release_schema import (  # noqa: E402
    DELIVERED,
    HISTO,
    SEMVER_RE,
    SHA_RE,
    STATE,
    unfinished_tasks,
    utc_now,
)
from _release_store import Refusal, State, live_release, replace, validated  # noqa: E402

SCRIPT = Path(__file__).parent / "release.py"


def _refuse_bad_arguments(sha: str, pr: int, next_release: str) -> None:
    """The three operator-supplied values, checked before anything is read from disk."""
    if not SHA_RE.match(sha):
        raise Refusal(
            f"--shipped {sha!r} is not a commit sha (7-40 lowercase hex); it takes the "
            "sha of the develop -> main merge commit",
            "git rev-parse origin/main",
        )
    if pr <= 0:
        raise Refusal(
            f"--pr {pr} is not a pull-request number; it takes the ship PR's number",
            "gh pr list --state merged --base main --limit 1",
        )
    if not SEMVER_RE.match(next_release):
        raise Refusal(
            f"--next {next_release!r} is not bare SemVer M.m.p",
            f"{SCRIPT} archive <id> --next 1.2.4",
        )


def archive_release(specs: Path, release_id: str, sha: str, pr: int, next_release: str) -> Path:
    """Ship the live release; returns the archived directory."""
    _refuse_bad_arguments(sha, pr, next_release)
    live = live_release(specs)
    if live.release_id != release_id:
        raise Refusal(
            f"{release_id} is not the live release ({live.release_id} is)",
            f"{SCRIPT} archive {live.release_id} --shipped {sha} --pr {pr} --next {next_release}",
        )
    unfinished = unfinished_tasks(live.release_dir)
    if unfinished:
        raise Refusal(
            f"TASKS.md still carries {len(unfinished)} open '[ ]'/reserved '[-]' marker(s) "
            f"— a release ships only fully implemented work: {unfinished[0]}",
            f"sed -i 's/^- \\[-\\]/- [x]/' specs/releases/{release_id}/TASKS.md",
        )
    if live.state.get("phase") != "CLOSURE":
        # ONE check, not two (0.4.7 FR5): `phase` and `implemented` are written by the
        # same act, so a release in CLOSURE always carries the milestone.
        raise Refusal(
            f"release {release_id} is in phase {live.state.get('phase')!r} — a release "
            "archives only from CLOSURE",
            f"{SCRIPT} phase CLOSURE --sha <implementation-tip-sha>",
        )
    archive_root = specs / "releases" / "_archive"
    destination = archive_root / release_id
    if destination.exists():
        raise Refusal(
            f"releases/_archive/{release_id} already exists — this release is archived",
            f"{SCRIPT} check --specs {specs}",
        )
    if (specs / "releases" / next_release).exists() or (archive_root / next_release).exists():
        raise Refusal(
            f"release {next_release} already exists — --next must name an unused version",
            f"{SCRIPT} archive {release_id} --next <unused M.m.p>",
        )
    return _ship(specs, live.release_dir, live.state, (release_id, sha, pr, next_release))


def _ship(specs: Path, release_dir: Path, state: State, args: tuple[str, str, int, str]) -> Path:
    release_id, sha, pr, next_release = args
    ts = utc_now()
    shipped = dict(state)
    shipped["shipped"] = {"sha": sha, "pr": pr, "ts": ts}
    shipped["phase"] = "ARCHIVED"
    shipped["log"] = list(state.get("log", []))
    note(
        shipped,
        ts,
        f"Shipped {sha} (PR #{pr}); release archived to _archive/{release_id}/ and "
        f"{next_release} born.",
    )
    rel = f"releases/_archive/{release_id}/{STATE}"
    text = validated(shipped, rel, archived=True)
    destination = specs / "releases" / "_archive" / release_id
    original = (release_dir / STATE).read_bytes()
    moved, born = False, None
    try:
        replace(release_dir / STATE, text)
        destination.parent.mkdir(parents=True, exist_ok=True)
        release_dir.rename(destination)
        moved = True
        born = new_release(specs, next_release, ts[:10], "operator-demand")
        append_histo(
            specs / HISTO,
            {
                "id": release_id,
                "ts": ts,
                "disposition": DELIVERED,
                "release": release_id,
                "reason": None,
                "summary": summary(release_id, sha, pr, state),
                "entry": None,
            },
        )
    except BaseException:
        if born is not None:
            shutil.rmtree(born, ignore_errors=True)
        if moved:
            destination.rename(release_dir)
        (release_dir / STATE).write_bytes(original)
        raise
    return destination
