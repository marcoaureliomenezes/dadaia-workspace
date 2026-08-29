"""Specs-pattern upgrade policy (v0.5.1 T-051-16, K10): stamp v6 or refuse.

Retires the versioned migration-chain registry (``MigrationStep``/``plan``/
``run_chain``, six steps walking pattern version 0 -> 5 through ``tree_v2.py``,
``bugs_jsonl.py``, ``agent_tier_frontmatter.py``, ``bugs_single_file.py``,
``retired_frontmatter_keys.py``, plus the stamp-only 5 -> 6 hop) and the six
migration modules those steps applied. Two facts made the chain dead weight
rather than a live capability:

1. **Zero live callers of what it fed.** ``bugs_jsonl.py``'s step converted legacy
   Markdown bugs into the v5 ``{event, data}`` JSONL shape — a shape
   ``features/bugs/migrate_v5.py`` (also deleted, T-051-16) was the only reader of,
   and that module itself had zero production callers (``BugService`` reads
   records through the injected ``RecordStore`` directly, never the v5 fold). A
   full v0 -> v6 run in THIS release would have produced a bugs ledger nothing in
   the current codebase can read back — a latent data-corruption bug waiting to
   ship, not a feature.
2. **No bug touched steps 1-5 after 2026-07-09** (deepening audit, 2026-08-28):
   the chain's only real users are pre-0.4.x trees, which reach canonical the way
   every prior release told them to — through 0.4.x's own upgrade, which still
   carries this exact chain historically.

What survives: a tree already at :data:`~dadaia_workspace.core.specs_version.CANONICAL_SPECS_VERSION`
upgrades as a no-op; a tree below it refuses immediately, pointing at 0.4.x. No
filesystem write happens on either path — refusal never touches the tree, and a
canonical tree needs no re-stamp of its own version.
"""

from __future__ import annotations


class UpgradeRefused(Exception):
    """Raised by :func:`check_upgradable` when a specs/ tree's pattern version sits
    below this release's floor.

    This release deleted the migration chain that used to walk a tree up from an
    arbitrary pre-canon version — the operator's remaining path is dadaia-workspace
    0.4.x's own ``dadaia specs upgrade`` (the last release still carrying that
    chain), then upgrading again to reach this release's canonical version.
    """


def check_upgradable(current: int, goal: int) -> None:
    """Raise :class:`UpgradeRefused` when ``current < goal``; a no-op otherwise.

    ``current >= goal`` (already at, or somehow past, the floor) is deliberately
    NOT an error here — the caller (:mod:`features.migrate.upgrade`) treats it as
    "nothing to migrate."
    """
    if current < goal:
        raise UpgradeRefused(
            f"specs pattern version {current} is below {goal}, and this release no "
            "longer carries the migration chain that reaches it. Upgrade this specs/ "
            "tree with dadaia-workspace 0.4.x first (its `dadaia specs upgrade` still "
            "carries the retired chain), then upgrade again to this release."
        )
