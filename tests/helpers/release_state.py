"""Shared fixture-side ``RELEASE.json`` phase-state writer (v0.5.x, successor to
``release_jsonl.py`` — RELEASE.jsonl -> RELEASE.json, operator ruling: the release
record is a mutable state document, never an append-only event stream).

``ACTIVE.md`` is retired -- the live release's phase is read directly off
``specs/releases/<release_id>/RELEASE.json`` (``core.release_state.parse_release_state``).
Any fixture that used to seed a synthetic ``ACTIVE.md``, or a one-line
``RELEASE.jsonl`` ``phase`` record, to put a context into a known phase now seeds one
``RELEASE.json`` document via this helper instead.

Extracted (S2 QA-close, T-050-22 item 3; renamed at the RELEASE.json migration) so every
fixture that needs this shares ONE writer instead of drifting into independent copies.
"""

from __future__ import annotations

import json
from pathlib import Path


def write_release_phase(
    specs_dir: Path, release_id: str, phase: str, *, segment: str | None = None
) -> None:
    """Write (overwrite) ``<specs_dir>/releases/<release_id>/RELEASE.json`` with a
    minimal ``release-state-v1`` document carrying exactly *phase* (and, when given,
    *segment*).

    A single document is sufficient: the reader takes the document's own ``phase``
    field, so one write fully represents "current state" for a test. Pass
    ``phase=None`` at the call site (i.e. never call this helper for that fixture) to
    simulate "no active release" -- the resolver requires a ``RELEASE.json`` file to
    exist at all.
    """
    rdir = specs_dir / "releases" / release_id
    rdir.mkdir(parents=True, exist_ok=True)
    state: dict[str, object] = {
        "schema": "release-state-v1",
        "release": release_id,
        "phase": phase,
        "rc": None,
        "defined": None,
        "implemented": None,
        "shipped": None,
        "audited": None,
        "notes": [],
    }
    if segment:
        state["segment"] = segment
    (rdir / "RELEASE.json").write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
