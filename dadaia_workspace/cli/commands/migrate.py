"""CLI command group: ``dadaia migrate [subcommand]``.

Bare ``dadaia migrate`` performs the state-file migration (spec_contexts.json v1 → v2).
``dadaia migrate tree-v2`` migrates the specs/ directory tree layout (from R1).

Note: ``dadaia migrate memory-yaml`` was removed in memory-markdown-source-v1.
      HTML → YAML migration is no longer needed (.md is the canonical source).
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
from dadaia_workspace.features.migrate.tree_v2 import migrate_tree_v2

app = typer.Typer(
    help="Migration helpers for dadaia workspace and spec trees.",
    invoke_without_command=True,
)


def _resolve_workspace_root() -> Path:
    """Resolve the workspace root from cwd walking upwards."""
    cwd = Path.cwd()
    for parent in [cwd, *cwd.parents]:
        if (parent / ".dadaia" / "states").exists():
            return parent
    return cwd


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
    typer.echo("  APPEND .dadaia/logs/lock-events.jsonl  (migration event)")


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
    Run ``dadaia migrate tree-v2`` to migrate the specs/ directory tree layout.
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


@app.command("tree-v2")
def tree_v2(
    specs_dir: str | None = typer.Option(
        None,
        "--specs-dir",
        help="Path to specs/ directory. Default: resolve from bound context session.",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Print what would be done without writing any files.",
    ),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Skip interactive confirmation prompt before any destructive operation.",
    ),
) -> None:
    """Migrate a consumer specs/ tree from the old layout to v2.

    Actions performed:

    \b
    1. If specs/foundation/ exists: move its contents to
       specs/releases/legacy/foundation/ and remove the empty foundation/ dir.
    2. If specs/SPEC.md exists at the tree root: move to
       specs/releases/legacy/SPEC.md (timestamp suffix added if the destination
       already exists to avoid clobbering).

    Both operations are idempotent — running the command twice is safe.
    """
    target = _resolve_specs_dir(specs_dir)

    if not target.is_dir():
        typer.echo(f"[error] specs_dir not found: {target}", err=True)
        sys.exit(1)

    # ---------------------------------------------------------------- dry-run
    if dry_run:
        preview = migrate_tree_v2(target, dry_run=True)
        typer.echo(f"[dry-run] specs_dir = {target}")
        for src, dst in preview.moved:
            typer.echo(f"  MOVE  {src}  →  {dst}")
        for msg in preview.skipped:
            typer.echo(f"  SKIP  {msg}")
        if not preview.moved:
            typer.echo("  (nothing to migrate)")
        sys.exit(0)

    # -------------------------------- determine if anything needs to happen
    preview = migrate_tree_v2(target, dry_run=True)
    if not preview.moved:
        typer.echo("[ok] Nothing to migrate — specs/ tree is already at v2 layout.")
        sys.exit(0)

    # ---------------------------------------------------------------- confirm
    if not yes:
        typer.echo(f"[migrate tree-v2] specs_dir = {target}")
        typer.echo("The following changes will be made:")
        for src, dst in preview.moved:
            typer.echo(f"  MOVE  {src}  →  {dst}")
        confirmed = typer.confirm("Proceed?", default=False)
        if not confirmed:
            typer.echo("[aborted] No changes made.")
            sys.exit(0)

    # ----------------------------------------------------------------- execute
    result = migrate_tree_v2(target, dry_run=False)

    for src, dst in result.moved:
        typer.echo(f"[moved]  {src}  →  {dst}")
    for msg in result.skipped:
        typer.echo(f"[skip]   {msg}")

    typer.echo(
        f"[ok] Migration complete. {len(result.moved)} move(s), {len(result.skipped)} skip(s)."
    )
