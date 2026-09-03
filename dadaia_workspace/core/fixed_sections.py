"""Fixed law sections: the marker grammar and the two pure text operations over it.

A fixed section is one library fragment rendered between ``<!-- dadaia:fixed <id> -->``
and ``<!-- /dadaia:fixed <id> -->`` lines; the body between them is the fragment, byte
for byte. Stdlib only: hooks import this leaf on the prompt path.
"""

from __future__ import annotations

import re

#: ``specs/``-relative file -> fragment id (``public/data/fixed/<id>.md``).
FIXED_SECTIONS: tuple[tuple[str, str], ...] = (
    ("constitution.md", "slop-law"),
    ("memory/ARCHITECTURE.md", "slop-code"),
    ("memory/QUALITY.md", "slop-tests"),
)


def _markers(section_id: str) -> tuple[str, str]:
    return f"<!-- dadaia:fixed {section_id} -->", f"<!-- /dadaia:fixed {section_id} -->"


def _body_span(text: str, section_id: str) -> tuple[int, int] | None:
    """``(start, end)`` of the body between the two marker lines, or ``None``."""
    opening, closing = _markers(section_id)
    pattern = re.compile(
        rf"^{re.escape(opening)}\n(.*?)^{re.escape(closing)}$", re.MULTILINE | re.DOTALL
    )
    match = pattern.search(text)
    return (match.start(1), match.end(1)) if match else None


def extract_fixed_section(text: str, section_id: str) -> str | None:
    """The body between the markers of *section_id*, or ``None`` when the pair is absent."""
    span = _body_span(text, section_id)
    return text[span[0] : span[1]] if span else None


def render_fixed_section(text: str, section_id: str, fragment: str) -> str:
    """*text* with *fragment* as the body of *section_id*: appended when absent, replaced when present."""
    span = _body_span(text, section_id)
    if span:
        return text[: span[0]] + fragment + text[span[1] :]
    opening, closing = _markers(section_id)
    head = text.rstrip("\n")
    prefix = f"{head}\n\n" if head else ""
    return f"{prefix}{opening}\n{fragment}{closing}\n"
