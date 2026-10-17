#!/usr/bin/env python3
"""The one skill-script walk to the workspace root."""

from __future__ import annotations

import os
from pathlib import Path

STATES = Path(".dadaia") / "states"


def fenced_roots() -> frozenset[Path]:
    """The roots `DADAIA_FENCED_ROOTS` names: never resolved to."""
    return frozenset(
        Path(p).resolve() for p in os.environ.get("DADAIA_FENCED_ROOTS", "").split(os.pathsep) if p
    )


def workspace_of(*starts: Path, fenced: frozenset[Path] | None = None) -> Path | None:
    """The first ancestor of any of *starts* holding `.dadaia/states/spec_contexts.json`,
    never a root in *fenced* (default: `fenced_roots()`)."""
    fenced = fenced_roots() if fenced is None else fenced
    return next((d for s in starts for d in (s.resolve(), *s.resolve().parents)
                 if d not in fenced and (d / STATES / "spec_contexts.json").is_file()), None)  # fmt: skip
