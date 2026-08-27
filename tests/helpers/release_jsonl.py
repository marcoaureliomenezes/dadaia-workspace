"""Shared fixture-side ``RELEASE.jsonl`` phase-record writer (v0.5.0 FR4/T-050-21A).

``ACTIVE.md`` is retired -- the live release's phase is folded exclusively from
``specs/releases/<release_id>/RELEASE.jsonl`` (``core.release_events.fold_release_events``,
last ``phase`` record wins). Any fixture that used to seed a synthetic ``ACTIVE.md`` to
put a context into a known phase now seeds one ``phase`` record via this helper instead.

Extracted (S2 QA-close, T-050-22 item 3) so every fixture that needs this shares ONE
writer instead of drifting into independent copies -- mirroring the pattern
``tests/unit/features/specs/test_doctor.py`` and ``tests/unit/hooks/test_sdd_gate.py``
already established locally before this extraction.
"""

from __future__ import annotations

import json
from pathlib import Path


def write_release_phase(
    specs_dir: Path, release_id: str, phase: str, *, segment: str | None = None
) -> None:
    """Write (overwrite) ``<specs_dir>/releases/<release_id>/RELEASE.jsonl`` with
    exactly ONE ``phase`` record.

    A single record is sufficient: the fold takes the LAST ``phase`` record, so one
    line fully represents "current state" for a test. Pass ``phase=None`` at the call
    site (i.e. never call this helper for that fixture) to simulate "no active
    release" -- the resolver requires a ``RELEASE.jsonl`` file to exist at all.
    """
    rdir = specs_dir / "releases" / release_id
    rdir.mkdir(parents=True, exist_ok=True)
    data: dict[str, object] = {"phase": phase}
    if segment:
        data["segment"] = segment
    record = {
        "ts": "2026-06-01T00:00:00Z",
        "event": "phase",
        "agent": "test",
        "data": data,
    }
    (rdir / "RELEASE.jsonl").write_text(json.dumps(record) + "\n", encoding="utf-8")
