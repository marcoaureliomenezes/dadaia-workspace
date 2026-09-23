"""The single definition of the SDD artifact status vocabulary and its on-disk token.

Before this module the vocabulary lived in four places that each re-implemented the same
rule: ``doctor_release`` parsed the ``**Status:**`` line with its own regex, ``certification``
and ``release_definition`` each asked ``"**Status:** <token>" in text`` (a substring test —
it accepts ``**Status:** Approved (pending)`` and rejects a double-space variant the doctor
accepts), ``release_definition`` rebuilt the token alternation to strip worker-authored
lines, and ``capabilities`` published a hardcoded list to consumer-side validators.

That shape is the second-largest bug class in the ledger: a rule with more than one
implementation drifts, and the gate oscillates between too-strict and too-permissive as
fixes land at one site and not the others (``doctor-root-whitelist-contradicts-root-law``,
``root-whitelist-message-drifts-from-policy``, ``backlog-doctor-yaml-parse-misdiagnosis``).

Everything here is pure text (``core/`` may not touch the filesystem — see the
``test_core_file_io_purity`` ratchet); the path-shaped helpers stay in ``features``.

The vocabulary is English. The retired Portuguese tokens are NOT a second
accepted spelling: a tree still carrying them is migrated once by ``dadaia specs upgrade``
(``features/migrate/upgrade.py``), so this module keeps exactly one token per status and
the doctor keeps exactly one rule.
"""

from __future__ import annotations

import re

#: The approved token. The only status that unlocks IMPLEMENTATION/CLOSURE.
APPROVED = "Approved"
#: The authored-but-unreviewed token (scaffold default).
DRAFT = "Draft"
#: The under-review token.
IN_REVIEW = "In review"

#: The complete canonical vocabulary. A status outside this set is a doctor ERROR.
CANONICAL_STATUS = {DRAFT, IN_REVIEW, APPROVED}

#: The spellings recognized when stripping worker-written status lines. Exactly the
#: canonical vocabulary — one spelling per token, so "recognized" and "canonical" can
#: never drift apart (``extract_status`` returns the token verbatim regardless).
_TOKEN_SPELLINGS = (DRAFT, IN_REVIEW, APPROVED)

#: Matches the canonical ``**Status:** <token>`` line as the doctor reads it.
STATUS_LINE = re.compile(r"\*\*Status:\*\*\s*(.+?)\s*$")

#: Matches ANY worker-authored status line — blockquoted or not, bullet-prefixed, colon
#: inside or outside the bold markers, any case — for single-writer normalization.
ANY_STATUS_LINE = re.compile(
    r"(?mi)^\s*(?:[-*]\s*)?(?:>\s*)?(?:\*\*Status:?\*\*:?|Status:)\s*"
    r"(?:" + "|".join(_TOKEN_SPELLINGS) + r")\s*$"
)

#: The canonical line Python writes. Single-writer law: workers never author this.
APPROVED_LINE = f"> **Status:** {APPROVED}"

#: How far into a document a status line is looked for.
_HEAD_LINES = 30


def extract_status(text: str) -> str | None:
    """Return the declared status token, or ``None`` when the document declares none.

    The token is returned verbatim so callers can tell "not canonical" (an ERROR the
    doctor reports) apart from "absent".
    """
    for line in text.splitlines()[:_HEAD_LINES]:
        match = STATUS_LINE.search(line)
        if match:
            return match.group(1).strip()
    return None


def is_approved(text: str) -> bool:
    """Whether the document carries a canonical ``**Status:** Approved``.

    This is a full-token comparison on the parsed line, not a substring test: an artifact
    whose status reads ``Approved (pending)`` is NOT approved, and one written with extra
    whitespace IS — matching, in both directions, what the doctor enforces.
    """
    return extract_status(text) == APPROVED
