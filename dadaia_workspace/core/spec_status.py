"""The SDD artifact status vocabulary and the one ``**Status:**`` line rule.

``STATUS_LINE`` is the kernel's ``_grammar.STATUS_RE``, the one definition the skill scripts read too.
"""

from __future__ import annotations

import re

from dadaia_workspace.core.skill_owner import load_owner

APPROVED = "Approved"
DRAFT = "Draft"
IN_REVIEW = "In review"
CANONICAL_STATUS = {DRAFT, IN_REVIEW, APPROVED}
#: Line-anchored, first match anywhere: a bullet, blockquote or quoted mid-line never counts.
STATUS_LINE: re.Pattern[str] = load_owner("dd-bug-resolution", "_grammar").STATUS_RE


def extract_status(text: str) -> str | None:
    """The declared token verbatim (so 'not canonical' differs from absent), or ``None``."""
    match = STATUS_LINE.search(text)
    return match.group(1) if match else None
