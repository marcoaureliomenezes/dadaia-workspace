#!/usr/bin/env python3
"""The `QUALITY.md` side of the bug balance: read the ledgers and the releases' spans, hand
them to the pure `_bugs_balance`, and write the block back. `bugs.py balance` and
`release.py check` share it, so a block and its regeneration cannot disagree."""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.append(str(Path(__file__).resolve().parents[2] / "dd-release-implementation" / "scripts"))

import _bugs_balance as bal  # noqa: E402
import _bugs_fix as fx  # noqa: E402
from _bugs_check import HISTO, LEDGER  # noqa: E402
from _bugs_store import read_records  # noqa: E402
from _ledger import replace  # noqa: E402
from _release_schema import STATE, live_id, releases  # noqa: E402

_TREND = 4  # the releases the trend window opens over (the live one and 3 published)


def _day(instant: datetime) -> datetime:
    return instant.replace(hour=0, minute=0, second=0, microsecond=0)


def body(specs: Path) -> str:
    """The `## Bugs` block `QUALITY.md` must hold. The trend window opens on its oldest
    release's first day and ends on the live release's last log day; `release.py`'s
    `Unreadable` (a ValueError) names a tree it cannot read."""
    live, spans = live_id(specs), releases(specs)
    order = [*sorted((r for r in spans if r != live), key=lambda r: spans[r][0]), live]
    closed = json.loads((specs / "releases" / live / STATE).read_text(encoding="utf-8"))
    end = datetime.fromisoformat(closed["log"][-1]["ts"])
    ledger = read_records(specs / LEDGER)
    old = [r for r in read_records(specs / HISTO) if "id" in r]
    top = fx.git(specs, "rev-parse", "--show-toplevel").strip()
    surfaces = {str(r.get("surface") or bal.UNKNOWN) for r in [*ledger, *old]}
    dev = frozenset(fx.marked(top, "dadaia-dev-tooling", surfaces))
    window = bal.Window(order, _day(spans[order[-_TREND:][0]][0]), _day(end))
    return bal.render(ledger, old, window, dev)


def stale(specs: Path) -> bool:
    """True when `QUALITY.md` holds a `## Bugs` block that differs from :func:`body`;
    a document with no block is not judged."""
    quality = specs / "memory" / "QUALITY.md"
    held = bal.stored(quality.read_text(encoding="utf-8")) if quality.is_file() else None
    return held is not None and held != body(specs)


def write(specs: Path) -> Path:
    """Regenerate the block in `QUALITY.md`, appending its section when absent."""
    quality = specs / "memory" / "QUALITY.md"
    document = quality.read_text(encoding="utf-8") if quality.is_file() else ""
    replace(quality, bal.replaced(document, body(specs)))
    return quality
