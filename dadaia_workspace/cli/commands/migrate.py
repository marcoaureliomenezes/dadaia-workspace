"""CLI command group: ``dadaia migrate [subcommand]``.

Bare ``dadaia migrate`` performs the state-file migration (spec_contexts.json v1 → v2).

Note: ``dadaia migrate memory-yaml`` was removed in memory-markdown-source-v1.
      HTML → YAML migration is no longer needed (.md is the canonical source).
Note: ``dadaia migrate tree-v2`` (specs/ directory tree layout, from R1) is RETIRED
      (v0.5.1 T-051-16, K10) — the v0 -> v1 leg of the deleted migration chain.
      A tree still below canonical uses dadaia-workspace 0.4.x's ``migrate tree-v2``.
"""

from __future__ import annotations

import sys

import typer

from dadaia_workspace.cli._fail import fail
from dadaia_workspace.core.exceptions import SchemaVersionError, WorkspaceNotInitializedError
from dadaia_workspace.core.workspace_resolver import resolve_workspace_root
from dadaia_workspace.features.migrate.state_v2 import (
    MigrationPlan,
    execute_migration,
    plan_migration,
)

app = typer.Typer(
    help="Migration helpers for dadaia workspace and spec trees.",
    invoke_without_command=True,
)


def _print_plan(plan: MigrationPlan) -> None:
    """Print a human-readable diff-like summary of what the migration will do."""
    typer.echo(f"[migrate] spec_contexts.json schema_version: {plan.schema_version_before!r} → '2'")
    typer.echo("")
    if plan.contexts_to_migrate:
        typer.echo("Context changes:")
        for c in plan.contexts_to_migrate:
            typer.echo(f"  {c['name']}: state {c['old_state']!r} → {c['new_state']!r}")
            if c["had_activated_at"]:
                typer.echo("    activated_at → alive_since")
            if c["had_is_primary"]:
                typer.echo("    is_primary   (removed)")
            typer.echo("    dead_since   null  (added)")
    else:
        typer.echo("  (no contexts to transform)")
    typer.echo("")
    if plan.primary_context_exists:
        typer.echo("  DELETE .dadaia/states/primary_context.json")
    for d in plan.dirs_to_create:
        typer.echo(f"  MKDIR  {d}")


@app.callback()
def migrate_state(
    ctx: typer.Context,
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show what would be done without writing anything.",
    ),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Skip interactive confirmation prompt.",
    ),
) -> None:
    """Migrate spec_contexts.json from schema v1 to v2.

    Without any subcommand, performs the state-file migration.
    """
    # If a subcommand was invoked, let it handle execution.
    if ctx.invoked_subcommand is not None:
        return

    try:
        workspace_root = resolve_workspace_root()
        states_dir = workspace_root / ".dadaia" / "states"
        plan = plan_migration(states_dir)
    except (ValueError, SchemaVersionError, WorkspaceNotInitializedError) as exc:
        fail(exc)

    if plan.already_v2:
        typer.echo("[ok] spec_contexts.json is current — nothing to do.")
        sys.exit(0)

    # --dry-run: show plan and exit
    if dry_run:
        _print_plan(plan)
        sys.exit(0)

    # Show plan + confirm (unless --yes)
    _print_plan(plan)
    typer.echo("")
    if not yes:
        confirmed = typer.confirm("Proceed with migration?", default=False)
        if not confirmed:
            typer.echo("[aborted] No changes made.")
            sys.exit(0)

    # Execute
    execute_migration(states_dir, workspace_root)

    typer.echo("[ok] Migration complete. spec_contexts.json is now at schema_version 2.")
