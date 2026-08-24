"""Shipped-version history for projected template assets — bug
``upgrade-never-refreshes-uncustomised-scoped-law-projection`` (MEDIUM).

A projected law file (``specs/AGENTS.md``) is installed once and then never refreshed:
overwriting it could destroy operator customisation, so ``specs doctor`` reports drift
(TREE-5) and declines to repair. Without a way to recognise our own earlier output, a file
nobody ever edited is protected exactly like a hand-written one — and every instance kept
scoped law citing a command the CLI had already removed.

This module supplies the missing evidence: the set of sha256 digests of every version of a
template this project has published. On-disk bytes found in that set were written by us
and never touched, so refreshing them is lossless; anything else is operator content and
stays untouched.

The history ships beside the templates as ``shipped-hashes.json`` (``{asset: [sha256,
…]}``) and is part of ``public/``, so it projects into every instance with the templates
it describes. It is append-only by contract: editing a template without appending the new
digest makes the next stale projection unrecognisable, which
``test_shipped_history_records_the_current_canonical_template`` refuses to allow.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

__all__ = ["SHIPPED_HASHES_FILENAME", "load_shipped_hashes", "was_shipped"]

#: Name of the history file, resolved inside the templates directory.
SHIPPED_HASHES_FILENAME = "shipped-hashes.json"


def load_shipped_hashes(templates_dir: Path) -> dict[str, set[str]]:
    """Return ``{asset_name: {sha256, …}}`` for every recorded template version.

    A missing, unreadable or malformed history yields an empty mapping: callers then see
    "nothing is provably ours" and keep their conservative behaviour, which is the safe
    direction for a file that may hold operator content.
    """
    history_path = templates_dir / SHIPPED_HASHES_FILENAME
    try:
        raw = json.loads(history_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, RecursionError):
        # RecursionError: a deeply nested document blows the JSON parser's stack; a corrupt
        # history must degrade to "nothing is provably ours", never take the doctor down.
        return {}
    if not isinstance(raw, dict):
        return {}
    out: dict[str, set[str]] = {}
    for asset, digests in raw.items():
        if isinstance(asset, str) and isinstance(digests, list):
            out[asset] = {d for d in digests if isinstance(d, str)}
    return out


def was_shipped(text: str, asset_name: str, templates_dir: Path) -> bool:
    """True when *text* is byte-identical to some published version of *asset_name*."""
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return digest in load_shipped_hashes(templates_dir).get(asset_name, set())
