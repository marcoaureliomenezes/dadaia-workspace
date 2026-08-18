"""Shared frontmatter key-stripping primitive for the memory-atom migration steps.

Extracted from ``agent_tier_frontmatter`` (v0.1.72 FR1) when a second schema-drop needed
the same mechanics (bug ``specs-upgrade-emits-atoms-violating-frontmatter-schema``): one
scanner, two callers, no duplicated fence parsing.

Mechanics: operate on the LEADING frontmatter block only, remove whole key lines the
caller's predicate selects (plus any indented continuation lines belonging to them), and
byte-preserve everything else — no YAML round-trip, which would reorder and reformat
unrelated keys. Prose mentions in the body are never touched.
"""

from __future__ import annotations

import re
from collections.abc import Callable

__all__ = ["strip_frontmatter_keys"]

#: Opening/closing frontmatter fence line (whole line, optional trailing whitespace).
_FENCE_RE = re.compile(r"^---\s*$")

#: A top-level (non-indented) ``key:`` line inside the frontmatter body.
_KEY_LINE_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_.\-]*)\s*:")

#: A continuation line belonging to a removed key (indented deeper than top level).
_CONTINUATION_RE = re.compile(r"^\s+\S")


def strip_frontmatter_keys(text: str, *, drop: Callable[[str], bool]) -> str | None:
    """Return *text* with every frontmatter key selected by *drop* removed.

    Args:
        text: Full file contents.
        drop: Predicate over a top-level frontmatter key name; ``True`` removes the key.

    Returns:
        The rewritten text, or ``None`` when the file has no leading frontmatter block
        (or an unterminated one) or when *drop* selected nothing — signalling "no change",
        which keeps every caller idempotent.

    The scan is LINEAR over lines (v0.1.73 FR4, bug
    ``migrate-agent-tier-frontmatter-redos-on-unterminated-block``): a DOTALL ``.*?``
    frontmatter regex backtracked super-linearly (~34s at 50k newlines) on a malformed
    atom with an opening fence and no closing fence.
    """
    lines = text.splitlines(keepends=True)
    if not lines or not _FENCE_RE.match(lines[0].rstrip("\n")):
        return None
    close_idx: int | None = None
    for idx in range(1, len(lines)):
        if _FENCE_RE.match(lines[idx].rstrip("\n")):
            close_idx = idx
            break
    if close_idx is None:
        return None  # unterminated fence — not a frontmatter block; leave untouched

    kept: list[str] = []
    removed = False
    skipping_continuation = False
    for line in lines[1:close_idx]:
        bare = line.rstrip("\n")
        match = _KEY_LINE_RE.match(bare)
        if match is not None and drop(match.group(1)):
            removed = True
            skipping_continuation = True
            continue
        if skipping_continuation and match is None and _CONTINUATION_RE.match(bare):
            # An indented continuation of the removed key (block list/scalar) — drop it.
            continue
        skipping_continuation = False
        kept.append(line)

    if not removed:
        return None

    return lines[0] + "".join(kept) + "".join(lines[close_idx:])
