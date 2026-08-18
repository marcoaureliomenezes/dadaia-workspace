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

from pathlib import Path

from dadaia_workspace.features.migrate.frontmatter_keys import strip_frontmatter_keys
from dadaia_workspace.features.migrate.tree_v2 import MigrateResult
from dadaia_workspace.features.specs.memory_lint import load_frontmatter_schema

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

    schema = load_frontmatter_schema()
    allowed = set(schema.get("properties", {}))
    if not allowed:
        # A schema with no declared properties would make every key look retired; refuse
        # to strip anything rather than empty the frontmatter of every atom.
        result.skipped.append("frontmatter schema declares no properties — nothing to migrate.")
        return result

    for md_path in sorted(memory_dir.rglob("*.md")):
        original = md_path.read_text(encoding="utf-8")
        rewritten = strip_frontmatter_keys(original, drop=lambda key: key not in allowed)
        if rewritten is None:
            continue
        if not dry_run:
            md_path.write_text(rewritten, encoding="utf-8")
        result.moved.append((md_path, md_path))

    if not result.moved:
        result.skipped.append("no memory atom carries a retired frontmatter key — nothing to do.")
    return result
