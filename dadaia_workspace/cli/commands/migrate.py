"""CLI command group: ``dadaia migrate [subcommand]``.

Bare ``dadaia migrate`` performs the state-file migration (spec_contexts.json v1 → v2).

Note: ``dadaia migrate memory-yaml`` was removed in memory-markdown-source-v1.
      HTML → YAML migration is no longer needed (.md is the canonical source).
Note: ``dadaia migrate tree-v2`` (specs/ directory tree layout, from R1) is RETIRED
      (v0.5.1 T-051-16, K10) — it was the v0 -> v1 leg of the migration chain
      ``features/migrate/registry.py`` deleted (see that module's docstring for why).
      A tree still below canonical uses dadaia-workspace 0.4.x's ``migrate tree-v2``.
"""

from __future__ import annotations

import sys
from pathlib import Path

import typer

from dadaia_workspace.cli._specs_resolution import resolve_specs_dir_for_cli
from dadaia_workspace.features.migrate.state_v2 import (
    MigrationPlan,
    execute_migration,
    plan_migration,
)

app = typer.Typer(
    help="Migration helpers for dadaia workspace and spec trees.",
    invoke_without_command=True,
)


def _resolve_workspace_root() -> Path:
    """The workspace root above cwd (core's one sentinel walk); cwd when uninitialized."""
    from dadaia_workspace.core.exceptions import WorkspaceNotInitializedError
    from dadaia_workspace.core.workspace_resolver import resolve_workspace_root

    try:
        return resolve_workspace_root(Path.cwd())
    except WorkspaceNotInitializedError:
        return Path.cwd()


def _resolve_specs_dir(specs_dir: str | None) -> Path:
    """Resolve the target specs/ directory.

    Priority:
    1. Explicit ``--specs-dir`` argument.
    2. Bound context session (``DADAIA_CONTEXT`` or ``DADAIA_SESSION_ID``).
    3. ``<cwd>/specs`` fallback.
    """
    return resolve_specs_dir_for_cli(specs_dir)


def _print_plan(plan: MigrationPlan) -> None:
    """Print a human-readable diff-like summary of what the migration will do."""
    if plan.already_v2:
        typer.echo("[ok] spec_contexts.json is already at schema_version 2 — nothing to do.")
        return

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

    workspace_root = _resolve_workspace_root()
    states_dir = workspace_root / ".dadaia" / "states"

    # Compute plan
    try:
        plan = plan_migration(states_dir)
    except ValueError as exc:
        typer.echo(f"[error] {exc}", err=True)
        sys.exit(1)

    if plan.already_v2:
        typer.echo("[ok] spec_contexts.json is already at schema_version 2 — nothing to do.")
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
    try:
        execute_migration(states_dir, workspace_root)
    except ValueError as exc:
        typer.echo(f"[error] {exc}", err=True)
        sys.exit(1)

    typer.echo("[ok] Migration complete. spec_contexts.json is now at schema_version 2.")
