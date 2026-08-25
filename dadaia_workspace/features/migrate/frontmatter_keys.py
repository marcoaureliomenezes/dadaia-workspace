"""Shared frontmatter key-stripping primitive for the memory-atom migration steps.

Extracted from ``agent_tier_frontmatter`` (v0.1.72 FR1) when a second schema-drop needed
the same mechanics (bug ``specs-upgrade-emits-atoms-violating-frontmatter-schema``): one
scanner, two callers, no duplicated fence parsing.

Mechanics: operate on the LEADING frontmatter block only, remove whole key lines the
caller's predicate selects (plus any indented continuation lines belonging to them), and
preserve everything else — no YAML round-trip, which would reorder and reformat unrelated
keys. Prose mentions in the body are never touched.

Newline contract — LF-canonical, not byte-preserving of line endings (bug
``migration-normalises-crlf-atoms-to-lf-contradicting-its-byte-preserve-wording``,
T-044-37, DECIDED): ``strip_frontmatter_keys`` and ``core.atomic_write.atomic_write`` are
themselves line-ending AGNOSTIC — fed CRLF directly, ``strip_frontmatter_keys`` reproduces
CRLF on every surviving line, and the primitive's ``newline=""`` writes back exactly the
bytes it is handed. The migration as every registered step actually runs it (real
``Path.read_text()`` -> ``strip_frontmatter_keys`` -> ``atomic_write(..., preserve_mode=True)``)
is LF-canonical end to end, because ``Path.read_text()``'s universal-newline translation
already collapses CRLF/CR to LF before this module ever sees the text — a CRLF atom
therefore leaves with LF on every line, not only the ones the key removal touched. This
matches the platform-wide LF-canonical write contract for managed files (the primitive's
own ``newline=""`` default; the same guarantee ``infrastructure/public_assets_common``
relied on for projected assets, FR-RC2-2) rather than reproducing whatever line endings
the atom arrived with. "Preserve everything else" above is a claim about CONTENT —
unrelated key lines, key order, the body — never about line-ending bytes.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

__all__ = ["load_frontmatter_schema", "strip_frontmatter_keys"]

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


# --- packaged data -----------------------------------------------------------------
# The atomic write of the stripped text back to disk is the caller's job (T-045-14):
# every migration step here calls core.atomic_write.atomic_write(..., preserve_mode=True)
# directly — ruled the shared home for this idiom on the core/specs_repair precedent
# (AR-1, T-045-11): a pure core leaf, stdlib-only, legally importable from every layer
# including features.

_PACKAGE_ROOT = Path(__file__).resolve().parents[2]  # dadaia_workspace/
_SCHEMA_REL = Path("public") / "schemas" / "memory" / "memory-frontmatter-v1.schema.json"


def load_frontmatter_schema() -> dict[str, Any]:
    """Load the packaged memory-atom frontmatter schema (``public/`` ships as package data)."""
    schema_path = _PACKAGE_ROOT / _SCHEMA_REL
    if not schema_path.exists():
        raise FileNotFoundError(
            f"memory-frontmatter-v1.schema.json not found at {schema_path} "
            "— the installed dadaia-workspace package is incomplete."
        )
    return cast(dict[str, Any], json.loads(schema_path.read_text(encoding="utf-8")))
