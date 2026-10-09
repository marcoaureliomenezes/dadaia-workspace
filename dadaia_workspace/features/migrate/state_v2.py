"""State-file migration: spec_contexts.json v1 → v2."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from dadaia_workspace.core.workspace_resolver import not_initialized
from dadaia_workspace.infrastructure.json_context_store import (
    LEGACY_STATES,
    JsonContextStore,
    parse_schema_version,
)


@dataclass
class MigrationPlan:
    """Describes what the migration will do — produced in dry-run mode."""

    schema_version_before: str
    contexts_to_migrate: list[dict]  # type: ignore[type-arg]
    primary_context_exists: bool
    dirs_to_create: list[str] = field(default_factory=list)
    already_v2: bool = False


def plan_migration(store: JsonContextStore) -> MigrationPlan:
    """Read spec_contexts.json and compute the migration plan without writing."""
    states_dir = store.states_dir
    primary_file = states_dir / "primary_context.json"

    if not store.exists():
        raise ValueError(str(not_initialized(states_dir.parent.parent)))

    raw = store.read_raw()
    if parse_schema_version(raw, states_dir / "spec_contexts.json") >= 2:
        return MigrationPlan(
            schema_version_before="2",
            contexts_to_migrate=[],
            primary_context_exists=primary_file.exists(),
            already_v2=True,
        )

    contexts_to_migrate = []
    for ctx in raw.get("contexts", []):
        old_state = ctx.get("state", "")
        if old_state not in LEGACY_STATES:
            continue
        new_state = "alive" if old_state == "ativo" else "dead"
        entry = {
            "name": ctx.get("name"),
            "old_state": old_state,
            "new_state": new_state,
            "had_is_primary": "is_primary" in ctx,
            "had_activated_at": "activated_at" in ctx,
        }
        contexts_to_migrate.append(entry)

    return MigrationPlan(
        schema_version_before="1",
        contexts_to_migrate=contexts_to_migrate,
        primary_context_exists=primary_file.exists(),
        dirs_to_create=[".dadaia/sessions"],
        already_v2=False,
    )


def execute_migration(store: JsonContextStore, workspace_root: Path) -> None:
    """Migrate the registry and its retired primary marker to schema v2."""
    states_dir = store.states_dir
    primary_file = states_dir / "primary_context.json"

    if not store.exists():
        _create_dirs(workspace_root)
        return

    raw = store.read_raw()
    if parse_schema_version(raw, states_dir / "spec_contexts.json") >= 2:
        _create_dirs(workspace_root)
        return

    new_contexts = []
    for ctx in raw.get("contexts", []):
        if ctx.get("state") not in LEGACY_STATES:
            new_contexts.append(ctx)
            continue
        new_ctx: dict[str, object] = {
            "name": ctx["name"],
            "state": "alive" if ctx.get("state") == "ativo" else "dead",
            "repo_slug": ctx.get("repo_slug", ""),
            "repo_url": ctx.get("repo_url", ""),
            "created_at": ctx.get("created_at", ""),
            "alive_since": ctx.get("activated_at"),
            "dead_since": None,
            "current_branch": ctx.get("current_branch"),
        }
        new_contexts.append(new_ctx)

    migrated: dict[str, object] = {
        "schema_version": "2",
        "contexts": new_contexts,
    }

    store.replace_raw(migrated, newline=None)

    if primary_file.exists():
        primary_file.unlink()

    _create_dirs(workspace_root)


def _create_dirs(workspace_root: Path) -> None:
    """Create the new directories required by v2."""
    for rel in (".dadaia/sessions",):
        (workspace_root / rel).mkdir(parents=True, exist_ok=True)
