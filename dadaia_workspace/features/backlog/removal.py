"""Residual-aware closure removal hook — take a consumed item out of the SET (SPEC §3.6).

When a release ships an item's content, the item leaves the **live working SET** of
``specs/backlog/``. The hook is residual-aware (ADR-C):

* **Rewrite-down-to-residual is the DEFAULT.** For an item whose intents are only *partly*
  shipped, the shipped intents are stripped and the item is rewritten to its residual and
  **kept** — never deleted whole (the 2026-06-26 hand pattern, mechanised).
* **Full removal only at zero residual.** When every intent's anchor is in the shipped set,
  the file is **copied** to ``specs/_archive/<release-id>/consumed-backlog/<slug>.md`` and
  only **then** unlinked. The copy precedes the unlink unconditionally — ``specs/backlog/``
  is gitignored, so the archive copy is the only surviving copy of a CRITICAL safety record.

Pure module: all roots are **injected** (SPEC §3.8), no cwd lookups, no I/O outside the
supplied paths. ``residual`` is computed by binding each intent's subject through the
injected R1 registry and testing anchor membership in the shipped set.
"""

from __future__ import annotations

import re
from collections.abc import Set as AbstractSet
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

import yaml

from dadaia_workspace.core.models.backlog import Intent, serialize_intents
from dadaia_workspace.features.backlog.preview import BacklogItem, load_backlog_items
from dadaia_workspace.features.backlog.subject_registry import BindStatus, Registry

__all__ = ["RemovalAction", "RemovalResult", "ItemAction", "apply_removal"]

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


class RemovalAction(StrEnum):
    """What the hook did to one consumed item."""

    UNCHANGED = "unchanged"
    REWRITTEN = "rewritten"
    ARCHIVED_AND_REMOVED = "archived_and_removed"


@dataclass(frozen=True)
class ItemAction:
    """The action taken for one backlog item."""

    slug: str
    action: RemovalAction


@dataclass(frozen=True)
class RemovalResult:
    """The aggregate outcome of a closure-removal pass."""

    actions: tuple[ItemAction, ...] = field(default_factory=tuple)


def _residual_intents(
    item: BacklogItem, registry: Registry, shipped_anchors: AbstractSet[str]
) -> tuple[list[Intent], bool]:
    """Return ``(residual_intents, any_shipped)``.

    An intent is *shipped* when its subject binds to an anchor present in ``shipped_anchors``.
    Residual intents are the ones NOT shipped. ``any_shipped`` is True iff at least one intent
    was shipped — when False the item is untouched. An intent whose subject does not resolve
    is conservatively kept as residual (never silently dropped).
    """
    residual: list[Intent] = []
    any_shipped = False
    for intent in item.intents:
        bind = registry.bind(intent.subject.ref, intent.subject.kind)
        if (
            bind.status is BindStatus.RESOLVED
            and bind.anchor is not None
            and bind.anchor.id in shipped_anchors
        ):
            any_shipped = True
            continue
        residual.append(intent)
    return residual, any_shipped


def _rewrite_to_residual(path: Path, residual: tuple[Intent, ...]) -> None:
    """Rewrite ``path``'s frontmatter ``intents:`` to ``residual``, preserving everything else."""
    text = path.read_text(encoding="utf-8")
    match = _FRONTMATTER_RE.match(text)
    if match is None:  # no frontmatter to rewrite — leave untouched.
        return
    meta = yaml.safe_load(match.group(1)) or {}
    if not isinstance(meta, dict):
        return
    meta["intents"] = serialize_intents(residual)
    body = text[match.end() :]
    new_front = yaml.safe_dump(meta, sort_keys=False, allow_unicode=True).rstrip("\n")
    path.write_text(f"---\n{new_front}\n---\n{body}", encoding="utf-8")


def apply_removal(
    *,
    backlog_dir: Path,
    archive_root: Path,
    release_id: str,
    shipped_anchors: AbstractSet[str],
    registry: Registry,
) -> RemovalResult:
    """Apply residual-aware removal to every backlog item the release consumed.

    For each item under ``backlog_dir``: compute the residual against ``shipped_anchors``
    (bound via ``registry``). No intent shipped → UNCHANGED. Some but not all shipped →
    rewrite to residual and KEEP (REWRITTEN). All shipped (zero residual) → copy to
    ``archive_root/<release_id>/consumed-backlog/<slug>.md`` THEN unlink
    (ARCHIVED_AND_REMOVED). All paths are injected; the archive copy always precedes the
    unlink (ADR-C safety).
    """
    actions: list[ItemAction] = []
    consumed_dir = archive_root / release_id / "consumed-backlog"
    for item in load_backlog_items(backlog_dir):
        residual, any_shipped = _residual_intents(item, registry, shipped_anchors)
        if not any_shipped:
            actions.append(ItemAction(slug=item.slug, action=RemovalAction.UNCHANGED))
            continue
        if residual:
            _rewrite_to_residual(item.path, tuple(residual))
            actions.append(ItemAction(slug=item.slug, action=RemovalAction.REWRITTEN))
            continue
        # Zero residual → copy-before-remove (ADR-C). The copy must land before the unlink.
        consumed_dir.mkdir(parents=True, exist_ok=True)
        archive_copy = consumed_dir / item.path.name
        archive_copy.write_text(item.path.read_text(encoding="utf-8"), encoding="utf-8")
        item.path.unlink()
        actions.append(ItemAction(slug=item.slug, action=RemovalAction.ARCHIVED_AND_REMOVED))
    return RemovalResult(actions=tuple(actions))
