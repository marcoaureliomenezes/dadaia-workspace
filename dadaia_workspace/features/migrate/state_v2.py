"""State-file migration: spec_contexts.json v1 → v2.

This module implements the v1-to-v2 context-record migration.
It is called by ``dadaia migrate [--dry-run] [--yes]``.

Migration is idempotent on v2 workspaces (no-op).
On unknown schema versions it raises ValueError.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class MigrationPlan:
    """Describes what the migration will do — produced in dry-run mode."""

    schema_version_before: str
    contexts_to_migrate: list[dict]  # type: ignore[type-arg]
    primary_context_exists: bool
    dirs_to_create: list[str] = field(default_factory=list)
    already_v2: bool = False


def _detect_schema_version(data: dict) -> str:  # type: ignore[type-arg]
    """Return the schema version string from the data dict.

    Returns "1", "2", or raises ValueError on unknown versions.
    """
    # Support both "schema_version" (v2 key) and "version" (v1 key)
    ver = data.get("schema_version") or data.get("version")
    if ver is None:
        # Infer from context state values
        for ctx in data.get("contexts", []):
            if ctx.get("state") in ("ativo", "inativo"):
                return "1"
        # No recognisable markers — treat as v2
        return "2"
    return str(ver)


def plan_migration(states_dir: Path) -> MigrationPlan:
    """Read spec_contexts.json and compute the migration plan without writing."""
    ctx_file = states_dir / "spec_contexts.json"
    primary_file = states_dir / "primary_context.json"

    if not ctx_file.exists():
        # Nothing to migrate
        return MigrationPlan(
            schema_version_before="2",
            contexts_to_migrate=[],
            primary_context_exists=primary_file.exists(),
            already_v2=True,
        )

    raw = json.loads(ctx_file.read_text(encoding="utf-8"))
    schema_ver = _detect_schema_version(raw)

    if schema_ver == "2":
        return MigrationPlan(
            schema_version_before="2",
            contexts_to_migrate=[],
            primary_context_exists=primary_file.exists(),
            already_v2=True,
        )

    if schema_ver != "1":
        raise ValueError(
            f"Unknown schema_version '{schema_ver}' in spec_contexts.json. "
            "Manual intervention required."
        )

    # Build list of context changes
    contexts_to_migrate = []
    for ctx in raw.get("contexts", []):
        old_state = ctx.get("state", "")
        new_state = "alive" if old_state == "ativo" else "dead"
        entry = {
            "name": ctx.get("name"),
            "old_state": old_state,
            "new_state": new_state,
            "had_is_primary": "is_primary" in ctx,
            "had_activated_at": "activated_at" in ctx,
        }
        contexts_to_migrate.append(entry)

    dirs_to_create = []
    for rel in (".dadaia/sessions",):
        dirs_to_create.append(rel)

    return MigrationPlan(
        schema_version_before="1",
        contexts_to_migrate=contexts_to_migrate,
        primary_context_exists=primary_file.exists(),
        dirs_to_create=dirs_to_create,
        already_v2=False,
    )


def execute_migration(states_dir: Path, workspace_root: Path) -> None:
    """Execute the migration atomically.

    Actions (in spec order):
    1.  Detect schema_version.
    2a. Map states: ativo→alive, inativo→dead.
    2b. Rename activated_at → alive_since.
    2c. Remove is_primary.
    2d. Add dead_since: null.
    2e. Set schema_version = "2".
    2f. Write atomically (tmp → os.replace()).
    2g. Delete primary_context.json if exists.
    2h. Create .dadaia/sessions/ directory.
    """
    ctx_file = states_dir / "spec_contexts.json"
    primary_file = states_dir / "primary_context.json"

    if not ctx_file.exists():
        _create_dirs(workspace_root)
        return

    raw = json.loads(ctx_file.read_text(encoding="utf-8"))
    schema_ver = _detect_schema_version(raw)

    if schema_ver == "2":
        # Idempotent: nothing to do for the JSON file, but ensure dirs exist
        _create_dirs(workspace_root)
        return

    if schema_ver != "1":
        raise ValueError(
            f"Unknown schema_version '{schema_ver}' in spec_contexts.json. "
            "Manual intervention required."
        )

    # Transform context rows
    new_contexts = []
    for ctx in raw.get("contexts", []):
        old_state = ctx.get("state", "")
        new_state = "alive" if old_state == "ativo" else "dead"

        # alive_since: use activated_at value if present, else None
        alive_since = ctx.get("activated_at")

        new_ctx: dict[str, object] = {
            "name": ctx["name"],
            "state": new_state,
            "repo_slug": ctx.get("repo_slug", ""),
            "repo_url": ctx.get("repo_url", ""),
            "created_at": ctx.get("created_at", ""),
            "alive_since": alive_since,
            "dead_since": None,
            "current_branch": ctx.get("current_branch"),
        }
        new_contexts.append(new_ctx)

    migrated: dict[str, object] = {
        "schema_version": "2",
        "contexts": new_contexts,
    }

    # Write atomically
    tmp = ctx_file.with_suffix(".tmp")
    tmp.write_text(json.dumps(migrated, indent=2), encoding="utf-8")
    os.replace(tmp, ctx_file)

    # Delete primary_context.json
    if primary_file.exists():
        primary_file.unlink()

    # Create required directories
    _create_dirs(workspace_root)


def _create_dirs(workspace_root: Path) -> None:
    """Create the new directories required by v2."""
    for rel in (".dadaia/sessions",):
        (workspace_root / rel).mkdir(parents=True, exist_ok=True)
