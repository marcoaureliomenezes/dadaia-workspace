"""What the package reads of a release state: the file's name and the id grammars.

`release.py` (dd-release-implementation) is the ONE writer and validator of
``specs/releases/<M.m.p>/_RELEASE.json``; the grammars are `_grammar`'s, re-exported.
"""

from __future__ import annotations

import re

from dadaia_workspace.core.skill_owner import load_owner

__all__ = [
    "CANDIDATE_RE",
    "LEGACY_RELEASE_STATE_FILENAME",
    "RELEASE_ID_RE",
    "RELEASE_STATE_FILENAME",
]

#: The one release-state filename (ADR 0007): the legacy name is never read as live —
#: the doctor renames it (SPEC-DOC-046).
RELEASE_STATE_FILENAME = "_RELEASE.json"
LEGACY_RELEASE_STATE_FILENAME = "RELEASE.json"

_grammar = load_owner("dd-bug-resolution", "_grammar")
RELEASE_ID_RE: re.Pattern[str] = _grammar.SEMVER_RE
CANDIDATE_RE: re.Pattern[str] = _grammar.CANDIDATE_RE
