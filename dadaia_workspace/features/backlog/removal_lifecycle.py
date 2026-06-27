"""Removal-on-release lifecycle wiring (SPEC §3.6) — the two halves that close BL-STALE.

R1 shipped the ``consumed_backlog`` ledger *reader* + the BL-STALE doctor check, but left
both ends of the loop unwired: nothing wrote the ledger and nothing removed a consumed item
at closure. This module is the thin orchestration that ties R2's pure ``features/backlog/``
ops onto the lifecycle surface:

* :func:`consume_at_release_definition` — at release-definition time, compute the **verified
  shipped subject-anchor set** for each consumed slug (by binding the live item's intents
  through the R1 registry) and write the ``consumed_backlog.json`` ledger via the R1-shaped
  :func:`write_consumed`.
* :func:`remove_at_closure` — at closure, read the ledger back, union its shipped anchors,
  and apply the residual-aware :func:`apply_removal` hook (rewrite-down-to-residual by
  default; full removal — archive-copy-before-unlink — only at zero residual).

Both functions are pure over **injected** roots (backlog dir, archive root) — never cwd
(SPEC §3.8). Together with R1's BL-STALE check they close the staleness loop: after the
writer + removal run, ``backlog doctor`` reports zero BL-STALE; a consumed slug left behind
in ``specs/backlog/`` is flagged BL-STALE.
"""

from __future__ import annotations

from collections.abc import Set as AbstractSet
from dataclasses import dataclass
from pathlib import Path

from dadaia_workspace.features.backlog.ledger import read_consumed
from dadaia_workspace.features.backlog.ledger_writer import ConsumedEntry, write_consumed
from dadaia_workspace.features.backlog.preview import bound_anchor_changes, load_backlog_items
from dadaia_workspace.features.backlog.removal import RemovalResult, apply_removal
from dadaia_workspace.features.backlog.subject_registry import Registry

__all__ = [
    "BacklogRemovalLifecycle",
    "consume_at_release_definition",
    "remove_at_closure",
]


def consume_at_release_definition(
    *,
    backlog_dir: Path,
    archive_root: Path,
    release_id: str,
    shipped_anchors: AbstractSet[str],
    registry: Registry,
) -> Path:
    """Write the ``consumed_backlog`` ledger for the items this release FULLY consumed.

    ``shipped_anchors`` is the **verified set of canonical anchor ids the release shipped**.
    A live backlog item is recorded as *consumed* (a removable slug, the basis for BL-STALE)
    **only when every one of its bound intents' anchors is in the shipped set** — i.e. it has
    zero residual. A partially-shipped item is NOT recorded: it survives (rewritten to its
    residual at closure), so listing it would (correctly, per R1) be flagged BL-STALE. The
    entry's ``shipped_anchors`` are the item's own bound anchors (always ⊆ the shipped set).

    The ledger is emitted in the exact R1 reader shape via :func:`write_consumed`, in
    sorted-slug order for deterministic output. All roots are injected; nothing reads cwd.
    """
    entries: list[ConsumedEntry] = []
    for item in sorted(load_backlog_items(backlog_dir), key=lambda it: it.slug):
        anchor_changes, _unresolved = bound_anchor_changes(item, registry)
        item_anchors = frozenset(anchor_changes.keys())
        # Fully consumed ⇔ the item has bound anchors and every one of them shipped.
        if item_anchors and item_anchors <= set(shipped_anchors):
            entries.append(ConsumedEntry(slug=item.slug, shipped_anchors=item_anchors))
    return write_consumed(archive_root=archive_root, release_id=release_id, consumed=entries)


def remove_at_closure(
    *,
    backlog_dir: Path,
    archive_root: Path,
    release_id: str,
    registry: Registry,
) -> RemovalResult:
    """Apply residual-aware removal for the items recorded in the consumed ledger.

    Reads every archived release's ``consumed_backlog.json`` (R1 :func:`read_consumed`),
    unions the shipped anchor sets, and runs the residual-aware :func:`apply_removal` hook
    over the live backlog. An item whose intents are all shipped is archived-then-removed
    (copy precedes unlink, ADR-C); a partially-shipped item is rewritten to its residual and
    kept. All roots are injected.
    """
    consumed = read_consumed(archive_root)
    shipped_anchors: set[str] = set()
    for anchors in consumed.values():
        shipped_anchors |= anchors
    return apply_removal(
        backlog_dir=backlog_dir,
        archive_root=archive_root,
        release_id=release_id,
        shipped_anchors=shipped_anchors,
        registry=registry,
    )


@dataclass(frozen=True)
class BacklogRemovalLifecycle:
    """Container-composed facade binding the injected roots + registry for §3.6.

    Wraps the two pure module functions so a caller (the release-definition / closure
    lifecycle surface, or the CLI) writes the ledger and applies removal without
    re-resolving roots. Composed by ``container.build_backlog_removal_lifecycle``.
    """

    backlog_dir: Path
    archive_root: Path
    registry: Registry

    def consume(self, *, release_id: str, shipped_anchors: AbstractSet[str]) -> Path:
        """Write the consumed ledger for fully-shipped items (release-definition time)."""
        return consume_at_release_definition(
            backlog_dir=self.backlog_dir,
            archive_root=self.archive_root,
            release_id=release_id,
            shipped_anchors=shipped_anchors,
            registry=self.registry,
        )

    def remove(self, *, release_id: str) -> RemovalResult:
        """Apply residual-aware removal over the ledgered shipped anchors (closure time)."""
        return remove_at_closure(
            backlog_dir=self.backlog_dir,
            archive_root=self.archive_root,
            release_id=release_id,
            registry=self.registry,
        )
