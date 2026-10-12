"""Shared fixture-side ``RELEASE.json`` phase-state writer.

The live release's phase is read directly off ``specs/releases/<release_id>/RELEASE.json``
(``core.release_state.parse_release_state``). A fixture that puts a context into a known
phase seeds one ``RELEASE.json`` document via this helper, so every fixture shares ONE
writer instead of drifting into independent copies.
"""

from __future__ import annotations

import json
from pathlib import Path

#: A PLAN `release.py` admits: a `## DAG` table and a `### Hot files` list.
PLAN = (
    "## 1. As-is review\n\n## DAG\n\n| job | waits on | why |\n|---|---|---|\n"
    "| Job 1 | — | x |\n\n### Hot files\n\n- none.\n"
)


def write_release_phase(specs_dir: Path, release_id: str, phase: str) -> None:
    """Write (overwrite) ``<specs_dir>/releases/<release_id>/RELEASE.json`` with a
    minimal ``release-state-v1`` document carrying exactly *phase*.

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
        "defined": None,
        "implemented": None,
        "shipped": None,
        "log": [],
    }
    (rdir / "_RELEASE.json").write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
