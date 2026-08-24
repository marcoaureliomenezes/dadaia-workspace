"""``retired-frontmatter-keys`` migration — bug
``specs-upgrade-emits-atoms-violating-frontmatter-schema`` (HIGH).

``memory-frontmatter-v1`` is a CLOSED schema (``additionalProperties: false``), so every
key dropped from it turns existing consumer atoms into doctor errors. v0.1.72 FR1 shipped
that migration for ``agent_tier`` — as a hard-coded, single-key step. When
``token_estimate`` was dropped later, no migration followed: ``dadaia specs upgrade``
rewrote atoms, then failed its own post-upgrade doctor with LINT-1 ``Additional properties
are not allowed ('token_estimate' was unexpected)`` and pointed the operator at a backup,
leaving the tree stuck at its old pattern version.

This step closes the CLASS instead of the instance: the retired set is derived from the
shipped schema at run time — any top-level frontmatter key absent from the schema's
``properties`` is retired and gets stripped. A future schema-drop is therefore migrated by
construction, with no new step to write.

It is registered AFTER the historical ``agent-tier-frontmatter`` step so that trees which
already reached that version are repaired too; both are byte-preserving, idempotent and
dry-run-capable.
"""

from __future__ import annotations

import os
from pathlib import Path

from dadaia_workspace.features.migrate.frontmatter_keys import (
    load_frontmatter_schema,
    strip_frontmatter_keys,
    write_text_atomic,
)
from dadaia_workspace.features.migrate.tree_v2 import MigrateResult

__all__ = ["migrate_retired_frontmatter_keys"]


def migrate_retired_frontmatter_keys(specs_dir: Path, *, dry_run: bool = False) -> MigrateResult:
    """Strip every frontmatter key the shipped memory schema no longer accepts.

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

    schema = load_frontmatter_schema()
    allowed = set(schema.get("properties", {}))
    if not allowed:
        # A schema with no declared properties would make every key look retired; refuse
        # to strip anything rather than empty the frontmatter of every atom.
        result.skipped.append("frontmatter schema declares no properties — nothing to migrate.")
        return result

    for md_path in sorted(memory_dir.rglob("*.md")):
        # Never write through a link: the target may live outside the tree being migrated
        # (CWE-59). The repo already paid for this once — the tests/AGENTS.md dangling
        # symlink bug — so both migration write sites refuse links outright.
        if md_path.is_symlink():
            result.skipped.append(
                f"{md_path.name}: symlink — left untouched (never write through a link)."
            )
            continue
        try:
            original = md_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            # One unreadable atom must not abort the chain and strand the tree half
            # migrated (CWE-703); record it and keep going.
            result.skipped.append(f"{md_path.name}: unreadable ({type(exc).__name__}) — skipped.")
            continue
        rewritten = strip_frontmatter_keys(original, drop=lambda key: key not in allowed)
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
        result.skipped.append("no memory atom carries a retired frontmatter key — nothing to do.")
    return result
