"""Bug ``backlog-doctor-rejects-deferred-status-documented-by-skill`` (T-044-34).

Intent: CONTRACT — pins the single-owner resolution of the contradiction: the six
canonical terminal LEDGER disposition tokens (``core.models.backlog.
TERMINAL_DISPOSITION_TOKENS``, which includes ``DEFERRED``) are the ONE canonical
vocabulary for "this item left ACTIVE"; a status an ACTIVE item may still legitimately
carry is a disjoint set. ``dd-backlog-definition`` SKILL.md's own §2 "Terminal
disposition tokens" table already lists ``DEFERRED`` as terminal (LEDGER-only) — its
ACTIVE ``- **Status:**`` enumeration line must never re-list a terminal token as if it
were a live status the doctor accepts, or the skill contradicts itself and the doctor's
BL-STALE check (``dadaia_workspace/features/backlog/doctor.py::_check_stale``) in the
same document. Size: SMALL (one real file read against the real shipped skill and the
real canonical token tuple; no subprocess, no fixture, no network).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

import dadaia_workspace
from dadaia_workspace.core.models.backlog import TERMINAL_DISPOSITION_TOKENS

pytestmark = pytest.mark.contract

_SKILL_MD = (
    Path(dadaia_workspace.__file__).resolve().parent
    / "public"
    / "skills"
    / "dd-backlog-definition"
    / "SKILL.md"
)

#: The ACTIVE-subsection ``- **Status:** a | b | c`` enumeration line (SKILL.md §2).
_ACTIVE_STATUS_LINE_RE = re.compile(r"^-\s+\*\*Status:\*\*\s+(?P<values>.+)$", re.MULTILINE)


def test_skill_active_status_enumeration_excludes_terminal_disposition_tokens() -> None:
    text = _SKILL_MD.read_text(encoding="utf-8")
    match = _ACTIVE_STATUS_LINE_RE.search(text)
    assert match is not None, (
        "dd-backlog-definition SKILL.md must document an ACTIVE '- **Status:**' "
        "enumeration line in §2"
    )
    documented = {value.strip().upper() for value in match.group("values").split("|")}
    terminal = frozenset(TERMINAL_DISPOSITION_TOKENS)
    overlap = documented & terminal
    assert not overlap, (
        "dd-backlog-definition SKILL.md's ACTIVE '- **Status:**' enumeration lists a "
        f"terminal LEDGER disposition token as a live ACTIVE status: {sorted(overlap)!r} "
        "— a terminal token (core.models.backlog.TERMINAL_DISPOSITION_TOKENS) belongs "
        "only in a '## LEDGER' line (the skill's own Terminal disposition tokens table), "
        "never as a status an ACTIVE item may carry; the doctor's BL-STALE check "
        "correctly refuses it "
        "(bug backlog-doctor-rejects-deferred-status-documented-by-skill)."
    )
