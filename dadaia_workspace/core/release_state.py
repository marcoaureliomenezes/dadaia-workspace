"""What the package reads of a release state: the file's name, the id grammar, its phase.

`release.py` (dd-release-implementation) is the ONE writer and validator of
``specs/releases/<M.m.p>/_RELEASE.json`` and owns the one-live-release rule; the doctor
consults it (``LEDGER-RELEASE-SCHEMA``) and reads a phase here. Pure: no file I/O.
"""

from __future__ import annotations

import json
import re

__all__ = ["RELEASE_ID_RE", "RELEASE_STATE_FILENAME", "read_phase"]

#: The one release-state filename (ADR 0090): no legacy name is read.
RELEASE_STATE_FILENAME = "_RELEASE.json"

#: A live release directory's name: bare ``M.m.p`` (`_release_schema.SEMVER_RE`).
RELEASE_ID_RE = re.compile(r"^\d+\.\d+\.\d+$")


def read_phase(text: str) -> str | None:
    """The ``phase`` a state document's *text* carries, or ``None`` when it names none;
    whether the document is valid is `release.py check`'s question, never this one."""
    try:
        document = json.loads(text)
    except json.JSONDecodeError:
        return None
    phase = document.get("phase") if isinstance(document, dict) else None
    return phase if isinstance(phase, str) and phase else None
