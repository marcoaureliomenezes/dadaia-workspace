#!/usr/bin/env python3
"""`release.py fold <id> --into <published>` — the archive holds PUBLISHED versions only.

Operator ruling 2026-09-14, ADR 0014: a candidate closed between two publications is an
`rc-N/` of the version that published it, never its own archived release. This is the ONE
governed path for that repair — `RELEASE-TREE-ARCHIVE-ID`/`RELEASE-TREE-ARCHIVE-UNSHIPPED`
name it in their `fix:` line — so the move, the state merge and the histo rewrite happen
together or not at all; never a hand move.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _release_fold_plan import merged_state, refuse_bad_ids, target_state  # noqa: E402
from _release_histo import rewrite_histo  # noqa: E402
from _release_schema import STATE, TRIO, rc_numbers  # noqa: E402
from _release_store import Refusal, read_state, replace, validated  # noqa: E402

SCRIPT = Path(__file__).parent / "release.py"


def fold_release(
    specs: Path,
    folded_id: str,
    into: str,
    *,
    sha: str | None = None,
    pr: int | None = None,
    shipped_ts: str | None = None,
    final: bool = False,
) -> Path:
    """Fold `_archive/<folded_id>/` into `rc-N/` (or, with *final*, the root) of *into*."""
    folded_dir = refuse_bad_ids(specs, folded_id, into)
    folded_state = read_state(folded_dir / STATE)
    target = target_state(specs, into, sha, pr, shipped_ts)
    target_dir = specs / "releases" / "_archive" / into
    born = not (target_dir / STATE).is_file()
    target_dir.mkdir(parents=True, exist_ok=True)
    if final and any((target_dir / name).is_file() for name in TRIO):
        raise Refusal(
            f"_archive/{into}/ already carries a root trio — only one final candidate",
            f"{SCRIPT} fold {folded_id} --into {into}",
        )
    next_rc = max(rc_numbers(target_dir), default=0) + 1
    moves: list[tuple[Path, Path]] = []
    for k in rc_numbers(folded_dir):
        moves.append((folded_dir / f"rc-{k}", target_dir / f"rc-{next_rc}"))
        next_rc += 1
    root_trio = [name for name in TRIO if (folded_dir / name).is_file()]
    placed_at = target_dir if final else target_dir / f"rc-{next_rc}"
    moves += [(folded_dir / name, placed_at / name) for name in root_trio]
    rc_after = next_rc if (root_trio and not final) else next_rc - 1
    placement = "root (final candidate)" if final else placed_at.name
    merged = merged_state(target, folded_state, rc_after, placement, folded_id)
    text = validated(merged, f"releases/_archive/{into}/{STATE}", archived=True)
    _apply(target_dir, folded_dir, moves, text, born=born)
    rewrite_histo(specs, folded_id, into, placement)
    return placed_at


def _apply(
    target_dir: Path, folded_dir: Path, moves: list[tuple[Path, Path]], text: str, *, born: bool
) -> None:
    """Every move, then the state, then the folded directory's removal — rolled back in
    full when any step raises, so a refused fold leaves both trees byte-identical."""
    original = (target_dir / STATE).read_bytes() if not born else None
    done: list[tuple[Path, Path]] = []
    try:
        for src, dst in moves:
            dst.parent.mkdir(parents=True, exist_ok=True)
            src.rename(dst)
            done.append((src, dst))
        replace(target_dir / STATE, text)
        shutil.rmtree(folded_dir)
    except BaseException:
        for src, dst in reversed(done):
            dst.rename(src)
        if original is not None:
            (target_dir / STATE).write_bytes(original)
        elif born:
            shutil.rmtree(target_dir, ignore_errors=True)
        raise
