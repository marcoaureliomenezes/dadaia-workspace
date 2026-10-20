"""State-file migration: spec_contexts.json v1 rows to the current schema."""

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
    if (version := parse_schema_version(raw, states_dir / "spec_contexts.json")) >= 2:
        return MigrationPlan(
            schema_version_before=str(version),
            contexts_to_migrate=[],
            primary_context_exists=primary_file.exists(),
            already_v2=True,
        )

    contexts_to_migrate = [
        {
            "name": ctx.get("name"),
            "old_state": state,
            "new_state": "alive" if state == "ativo" else "dead",
            "had_is_primary": "is_primary" in ctx,
            "had_activated_at": "activated_at" in ctx,
        }
        for ctx in raw.get("contexts", [])
        if (state := ctx.get("state", "")) in LEGACY_STATES
    ]

    return MigrationPlan(
        schema_version_before=str(version),
        contexts_to_migrate=contexts_to_migrate,
        primary_context_exists=primary_file.exists(),
        dirs_to_create=[".dadaia/sessions"],
        already_v2=False,
    )


def execute_migration(store: JsonContextStore, workspace_root: Path) -> None:
    """Migrate the registry and its retired primary marker to the current schema."""
    states_dir = store.states_dir
    primary_file = states_dir / "primary_context.json"
    raw = store.read_raw() if store.exists() else None
    if raw is not None and parse_schema_version(raw, states_dir / "spec_contexts.json") < 2:
        store.replace_raw(
            {
                "contexts": [
                    ctx
                    if ctx.get("state") not in LEGACY_STATES
                    else {
                        "name": ctx["name"],
                        "state": "alive" if ctx.get("state") == "ativo" else "dead",
                        "repo_slug": ctx.get("repo_slug", ""),
                        "repo_url": ctx.get("repo_url", ""),
                        "created_at": ctx.get("created_at", ""),
                        "alive_since": ctx.get("activated_at"),
                        "dead_since": None,
                    }
                    for ctx in raw.get("contexts", [])
                ],
            },
        )
        if primary_file.exists():
            primary_file.unlink()
    (workspace_root / ".dadaia/sessions").mkdir(parents=True, exist_ok=True)
