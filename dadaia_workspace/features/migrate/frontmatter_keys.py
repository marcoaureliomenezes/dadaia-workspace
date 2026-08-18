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

import contextlib
import json
import os
import re
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

__all__ = ["load_frontmatter_schema", "strip_frontmatter_keys", "write_text_atomic"]

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


# --- packaged data + safe writing -------------------------------------------------
# Both live here rather than in a shared layer: features are mutually independent by
# contract (setup.cfg, features-no-cross-feature), features may not import infrastructure,
# and core/ file I/O is a closed ratchet (architect A9). The repo already resolves this the
# same way — hooks/_common.py and infrastructure/public_assets_common.py each keep their
# own atomic writer.

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


def write_text_atomic(path: Path, text: str) -> None:
    """Write *text* to *path* by atomic replacement, never THROUGH the existing file.

    Refusing symlinks closes CWE-59 for the obvious case, but a hard link is not a symlink
    and a path checked then opened is a TOCTOU window (CWE-367) — both let a write land
    outside the tree being migrated. Rendering to a temp file in the same directory and
    ``os.replace``-ing it rebinds the name instead of writing through whatever it points
    at, and the swap is atomic, so no reader sees a half-written atom.
    """
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
        os.replace(tmp_name, path)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(tmp_name)
        raise
