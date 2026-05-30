"""CLI command group: ``dadaia migrate <subcommand>``."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import typer

from dadaia_workspace.features.migrate.tree_v2 import migrate_tree_v2

app = typer.Typer(help="Migration helpers for dadaia workspace and spec trees.")


def _resolve_specs_dir(specs_dir: str | None) -> Path:
    """Resolve the target specs/ directory.

    Priority:
    1. Explicit ``--specs-dir`` argument.
    2. ``primary_context.json`` in ``.dadaia/states/``.
    3. ``<cwd>/specs`` fallback.
    """
    if specs_dir:
        return Path(specs_dir).resolve()

    cwd = Path.cwd()
    for parent in [cwd, *cwd.parents]:
        primary = parent / ".dadaia" / "states" / "primary_context.json"
        if primary.exists():
            try:
                data = json.loads(primary.read_text(encoding="utf-8"))
                sd = data.get("specs_dir")
                if sd:
                    return Path(sd).resolve()
            except (OSError, ValueError):
                pass

    candidate = cwd / "specs"
    if candidate.exists():
        return candidate.resolve()

    raise typer.BadParameter(
        "Could not resolve specs_dir. Pass --specs-dir or activate a context "
        "with `dadaia context activate <name>`."
    )


@app.command("tree-v2")
def tree_v2(
    specs_dir: str | None = typer.Option(
        None,
        "--specs-dir",
        help="Path to specs/ directory. Default: resolve from primary_context.json.",
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
        f"[ok] Migration complete. "
        f"{len(result.moved)} move(s), {len(result.skipped)} skip(s)."
    )
