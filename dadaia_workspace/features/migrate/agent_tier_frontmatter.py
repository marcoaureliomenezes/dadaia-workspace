"""``agent-tier-frontmatter`` migration — v0.1.72 FR1 (bug
``memory-agent-tier-migration-deadlock``, CRITICAL).

``agent_tier`` was deprecated in v0.1.53 and schema-dropped in v0.1.61
(``memory-frontmatter-v1`` has ``additionalProperties: false``), but no migration ever
shipped: consumer workspaces scaffolded before the drop still carry memory atoms with
``agent_tier:`` in frontmatter. ``specs doctor`` correctly rejects them, memory writes
are phase-locked outside DEFINITION/CLOSURE, and ``doctor --fix`` never strips unknown
frontmatter keys — so a release in IMPLEMENTATION was **deadlocked**: the gate demanded a
repair the rules forbade. A schema-drop MUST ship its migration; this is that step.

Mechanics: for every ``specs/memory/**/*.md`` whose LEADING frontmatter block carries a
top-level ``agent_tier`` key, remove exactly that key's line (and any indented
continuation lines), byte-preserving everything else — no YAML round-trip (a re-dump
would reorder/reformat unrelated keys). Prose mentions of ``agent_tier`` in the body are
never touched. Idempotent (second run finds nothing) and dry-run-capable (plans, writes
nothing). ``MigrateResult.moved`` records ``(path, path)`` per migrated atom.
"""

from __future__ import annotations

import re
from pathlib import Path

from dadaia_workspace.features.migrate.tree_v2 import MigrateResult

__all__ = ["migrate_agent_tier_frontmatter"]

#: Opening/closing frontmatter fence line (whole line, optional trailing whitespace).
_FENCE_RE = re.compile(r"^---\s*$")

#: A top-level (non-indented) ``agent_tier:`` key line inside the frontmatter body.
_AGENT_TIER_LINE_RE = re.compile(r"^agent_tier\s*:")

#: A continuation line belonging to the removed key (indented deeper than top level).
_CONTINUATION_RE = re.compile(r"^\s+\S")


def migrate_agent_tier_frontmatter(specs_dir: Path, *, dry_run: bool = False) -> MigrateResult:
    """Strip the schema-dropped ``agent_tier`` key from memory-atom frontmatter.

    Args:
        specs_dir: Absolute path to the ``specs/`` directory being migrated.
        dry_run:   When *True*, plan only (paths recorded in ``moved``), write nothing.

    Returns:
        :class:`MigrateResult` — ``moved`` holds one ``(path, path)`` pair per atom whose
        frontmatter was (or would be) rewritten; ``skipped`` carries informational notes.
    """
    result = MigrateResult(dry_run=dry_run)
    memory_dir = specs_dir / "memory"
    if not memory_dir.is_dir():
        result.skipped.append("memory/ not found — nothing to migrate.")
        return result

    for md_path in sorted(memory_dir.rglob("*.md")):
        original = md_path.read_text(encoding="utf-8")
        rewritten = _strip_agent_tier(original)
        if rewritten is None:
            continue
        if not dry_run:
            md_path.write_text(rewritten, encoding="utf-8")
        result.moved.append((md_path, md_path))

    if not result.moved:
        result.skipped.append("no memory atom carries agent_tier — nothing to migrate.")
    return result


def _strip_agent_tier(text: str) -> str | None:
    """Return *text* with the frontmatter ``agent_tier`` key removed, or ``None`` if the
    file has no leading frontmatter block or no ``agent_tier`` key in it.

    v0.1.73 FR4 (bug ``migrate-agent-tier-frontmatter-redos-on-unterminated-block``):
    LINEAR splitlines scan — the previous DOTALL ``.*?`` regex backtracked
    super-linearly (~34s at 50k newlines) on a malformed atom with an opening fence and
    no closing fence. Line-by-line fence detection is O(n) on every input.
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
        if _AGENT_TIER_LINE_RE.match(bare):
            removed = True
            skipping_continuation = True
            continue
        if skipping_continuation and _CONTINUATION_RE.match(bare):
            # An indented continuation of the removed key (block list/scalar) — drop it.
            continue
        skipping_continuation = False
        kept.append(line)

    if not removed:
        return None

    return lines[0] + "".join(kept) + "".join(lines[close_idx:])
