"""What the package reads of a release state: the file's name, the id grammar, its phase.

`release.py` (dd-release-implementation) is the ONE writer and validator of
``specs/releases/<M.m.p>/_RELEASE.json`` and owns the one-live-release rule; the doctor
consults it (``LEDGER-RELEASE-SCHEMA``) and reads a phase here. Pure: no file I/O.
"""

from __future__ import annotations

import json
import re

__all__ = [
    "CANDIDATE_RE",
    "LEGACY_RELEASE_STATE_FILENAME",
    "RELEASE_ID_RE",
    "RELEASE_STATE_FILENAME",
    "read_phase",
]

#: The one release-state filename (ADR 0007): the legacy name is never read as live —
#: the doctor renames it (SPEC-DOC-046).
RELEASE_STATE_FILENAME = "_RELEASE.json"
LEGACY_RELEASE_STATE_FILENAME = "RELEASE.json"

#: The ONE release-id grammar: bare ``M.m.p`` — `_release_schema.SEMVER_RE`'s pattern,
#: pinned equal by ``tests/public/skills/dd_release_implementation/scripts/test__release_schema.py``. No ``v``, no suffix;
#: an archived directory is exempt by its location (``_archive/``), never by its name.
RELEASE_ID_RE = re.compile(r"^\d+\.\d+\.\d+$")

#: The ONE candidate-folder grammar (ADR 0150): ``rc-<N>``, N from 1, no leading zero —
#: `_release_schema.CANDIDATE_RE`'s pattern, pinned equal by tests/public/skills/dd_release_implementation/scripts/test_release__release_script.py.
CANDIDATE_RE = re.compile(r"^rc-([1-9][0-9]*)$")


def read_phase(text: str) -> str | None:
    """The ``phase`` a state document's *text* carries, or ``None`` when it names none;
    whether the document is valid is `release.py check`'s question, never this one."""
    try:
        document = json.loads(text)
    except json.JSONDecodeError:
        return None
    phase = document.get("phase") if isinstance(document, dict) else None
    return phase if isinstance(phase, str) and phase else None
