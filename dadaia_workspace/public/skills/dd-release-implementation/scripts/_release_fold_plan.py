#!/usr/bin/env python3
"""What `fold` refuses and what it computes before a single path moves — the pure half.

Split from `_release_fold` so the transaction there reads as exactly three steps: move,
write, remove. Everything that can say no, and everything that decides what the merged
published state will look like, is decided here first.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _release_phase import note  # noqa: E402
from _release_schema import SEMVER_RE, SHA_RE, STATE, semver_key, utc_now  # noqa: E402
from _release_store import Refusal, State, live_ids, read_state  # noqa: E402

SCRIPT = Path(__file__).parent / "release.py"


def refuse_bad_ids(specs: Path, folded_id: str, into: str) -> Path:
    """Both ids are path segments under `_archive/`: only a bare SemVer name may ever be
    joined, moved or removed — anything else is refused before a path is built (CWE-22)."""
    for value, what in ((folded_id, "the archived release id"), (into, "--into")):
        if not SEMVER_RE.match(value):
            raise Refusal(
                f"{what} {value!r} is not bare SemVer M.m.p",
                f"ls {specs / 'releases' / '_archive'}",
            )
    if folded_id == into:
        raise Refusal(
            f"{folded_id} cannot be folded into itself",
            f"{SCRIPT} fold {folded_id} --into <the version that published it>",
        )
    above = [live for live in live_ids(specs) if semver_key(into) >= semver_key(live)]
    if above:
        raise Refusal(
            f"--into {into} is not below the live release {above[0]} — the archive holds "
            "published versions only",
            f"{SCRIPT} fold {folded_id} --into <last published M.m.p>",
        )
    folded_dir = specs / "releases" / "_archive" / folded_id
    if not (folded_dir / STATE).is_file():
        raise Refusal(
            f"_archive/{folded_id}/ is not an archived release (no directory or no state document)",
            f"ls {specs / 'releases' / '_archive'}",
        )
    return folded_dir


def target_state(specs: Path, into: str, sha: str | None, pr: int | None, ts: str | None) -> State:
    """The published version's state: read when `_archive/<into>/` already exists, born
    from its publication when it does not (both values then required)."""
    target = specs / "releases" / "_archive" / into / STATE
    if target.is_file():
        state = read_state(target)
        shipped = state.get("shipped")
        if state.get("phase") != "ARCHIVED" or not (
            isinstance(shipped, dict) and shipped.get("sha") and shipped.get("pr")
        ):
            raise Refusal(
                f"_archive/{into}/ is not a published, ARCHIVED release",
                f"{SCRIPT} check --specs {specs}",
            )
        return state
    if not sha or not pr or not SHA_RE.match(sha) or pr <= 0:
        raise Refusal(
            f"_archive/{into}/ carries no state document yet — its publication must be named",
            f"{SCRIPT} fold <id> --into {into} --shipped <develop->main sha> --pr <ship PR>",
        )
    return {
        "schema": "release-state-v1", "release": into, "phase": "ARCHIVED", "rc": None,
        "defined": None, "implemented": None,
        "shipped": {"sha": sha, "pr": pr, "ts": ts or utc_now()}, "log": [],
    }  # fmt: skip


def merged_state(
    target: State, folded: State, rc: int | None, placement: str, folded_id: str
) -> State:
    """The two logs in `ts` order plus one note; `rc` becomes the highest `rc-N` present;
    `defined` keeps the earliest milestone and `implemented` the folded one when the
    target has none."""
    merged = dict(target)
    merged["log"] = sorted(
        [*target.get("log", []), *folded.get("log", [])], key=lambda e: str(e.get("ts", ""))
    )
    note(
        merged,
        utc_now(),
        f"Folded former archived release {folded_id} into {merged['release']}/{placement}: "
        "the archive holds published versions only (operator ruling 2026-09-14, ADR 0014).",
    )
    merged["rc"] = rc or None
    defined = [d for d in (target.get("defined"), folded.get("defined")) if isinstance(d, dict)]
    merged["defined"] = min(defined, key=lambda d: str(d.get("ts", ""))) if defined else None
    if merged.get("implemented") is None:
        merged["implemented"] = folded.get("implemented")
    return merged
