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

import os
from pathlib import Path

from dadaia_workspace.features.migrate.frontmatter_keys import (
    strip_frontmatter_keys,
    write_text_atomic,
)
from dadaia_workspace.features.migrate.tree_v2 import MigrateResult

__all__ = ["migrate_agent_tier_frontmatter"]


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

    if memory_dir.is_symlink():
        # The walk ROOT itself may be a link out of the tree: the per-file guard cannot see
        # it (the atoms inside are regular files) and rglob happily walks its target
        # (CWE-59). Same doctrine the tests/AGENTS.md symlink bug established.
        result.skipped.append(
            "memory/ is a symlink — left untouched (never migrate through a link)."
        )
        return result

    for md_path in sorted(memory_dir.rglob("*.md")):
        if md_path.is_symlink():
            result.skipped.append(
                f"{md_path.name}: symlink — left untouched (never write through a link)."
            )
            continue
        try:
            original = md_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            result.skipped.append(f"{md_path.name}: unreadable ({type(exc).__name__}) — skipped.")
            continue
        rewritten = _strip_agent_tier(original)
        if rewritten is None:
            continue
        if not os.access(md_path, os.W_OK):
            # Checked AFTER the no-change determination above (bug
            # read-only-atom-honouring-is-advisory-and-root-bypasses-it, LOW): a clean
            # read-only atom now stays silent instead of emitting a note it never earned.
            # Best-effort by construction, not a hard boundary — os.access lets root
            # through and os.replace only needs directory permission — but it still
            # honours the flag for the common case where a real change was refused.
            result.skipped.append(f"{md_path.name}: read-only — skipped.")
            continue
        if not dry_run:
            try:
                write_text_atomic(md_path, rewritten)
            except OSError as exc:
                result.skipped.append(
                    f"{md_path.name}: unwritable ({type(exc).__name__}) — skipped."
                )
                continue
        result.moved.append((md_path, md_path))

    if not result.moved:
        result.skipped.append("no memory atom carries agent_tier — nothing to migrate.")
    return result


def _strip_agent_tier(text: str) -> str | None:
    """Return *text* with the frontmatter ``agent_tier`` key removed, or ``None`` if the
    file has no leading frontmatter block or no ``agent_tier`` key in it.

    Delegates to :func:`strip_frontmatter_keys`, the shared linear scanner (extracted for
    bug ``specs-upgrade-emits-atoms-violating-frontmatter-schema``, which needed the same
    mechanics for the whole retired-key class).
    """
    return strip_frontmatter_keys(text, drop=lambda key: key == "agent_tier")
