"""Bug ``backlog-doctor-rejects-deferred-status-documented-by-skill`` (T-044-34).

Intent: CONTRACT — pins the single-owner resolution of the contradiction: the five
canonical terminal dispositions (``core.models.histo.
TERMINAL_DISPOSITIONS``, which includes ``deferred``) are the ONE canonical
vocabulary for "this item left ACTIVE"; a status an ACTIVE item may still legitimately
carry is a disjoint set. ``scaffold/backlog/AGENTS.md`` — the one home of the document
contract — states both in the same file: its §3 lists the terminal dispositions and its
§2 enumerates the live ``status`` tokens. The live enumeration must never re-list a
terminal token as if it were a status the doctor accepts, or the scoped rule contradicts
itself and the doctor's BL-STALE check
(``dadaia_workspace/features/backlog/doctor.py::_check_stale``) in the same document.
Size: SMALL (one real file read against the real shipped asset and the real canonical
token tuple; no subprocess, no fixture, no network).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

import dadaia_workspace
from dadaia_workspace.core.models.histo import TERMINAL_DISPOSITIONS

pytestmark = pytest.mark.contract

_SCOPED_RULE = (
    Path(dadaia_workspace.__file__).resolve().parent
    / "public"
    / "scaffold"
    / "backlog"
    / "AGENTS.md"
)

#: The live-status enumeration line (``- `status` is `a`, `b`, ...``) of §2.
_ACTIVE_STATUS_LINE_RE = re.compile(r"^-\s+`status` is (?P<values>.+)$", re.MULTILINE)
_BACKTICKED_RE = re.compile(r"`([a-z-]+)`")


def test_skill_active_status_enumeration_excludes_terminal_disposition_tokens() -> None:
    text = _SCOPED_RULE.read_text(encoding="utf-8")
    match = _ACTIVE_STATUS_LINE_RE.search(text)
    assert match is not None, (
        "scaffold/backlog/AGENTS.md must document the live `status` enumeration in §2"
    )
    documented = {value.upper() for value in _BACKTICKED_RE.findall(match.group("values"))}
    terminal = frozenset(word.upper() for word in TERMINAL_DISPOSITIONS)
    overlap = documented & terminal
    assert not overlap, (
        "scaffold/backlog/AGENTS.md's live `status` enumeration lists a "
        f"terminal disposition token as a live ACTIVE status: {sorted(overlap)!r} "
        "— a terminal token (core.models.histo.TERMINAL_DISPOSITIONS) belongs "
        "only in §3's Terminal disposition tokens list, "
        "never as a status an ACTIVE item may carry; the doctor's BL-STALE check "
        "correctly refuses it "
        "(bug backlog-doctor-rejects-deferred-status-documented-by-skill)."
    )
