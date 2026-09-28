"""The SDD artifact status vocabulary and the one ``**Status:**`` line rule.

The stdlib ``_release_schema.py`` cannot import this module; it copies ``STATUS_LINE``
literally and ``tests/unit/core/test_spec_status.py`` holds both to parity.
"""

from __future__ import annotations

import re

APPROVED = "Approved"
DRAFT = "Draft"
IN_REVIEW = "In review"
CANONICAL_STATUS = {DRAFT, IN_REVIEW, APPROVED}
#: Line-anchored, first match anywhere: a bullet, blockquote or quoted mid-line never counts.
STATUS_LINE = re.compile(r"^\*\*Status:\*\*\s*(.+?)\s*$", re.MULTILINE)


def extract_status(text: str) -> str | None:
    """The declared token verbatim (so 'not canonical' differs from absent), or ``None``."""
    match = STATUS_LINE.search(text)
    return match.group(1) if match else None
