"""CLI command group: ``dadaia migrate [subcommand]``.

Bare ``dadaia migrate`` performs the state-file migration (spec_contexts.json v1 → v2).
``dadaia migrate tree-v2`` migrates the specs/ directory tree layout (from R1).
``dadaia migrate memory-yaml`` converts existing HTML memory atoms → YAML source files.
All subcommands are preserved; the bare form does NOT break the others.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import typer

from dadaia_workspace.features.migrate.memory_yaml import migrate_html_atom_to_yaml
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


@app.command("memory-yaml")
def memory_yaml(
    atom_path: str = typer.Argument(
        None,
        help=(
            "Path to a single HTML memory atom to migrate (e.g. specs/memory/architecture.html). "
            "Mutually exclusive with --all."
        ),
    ),
    all_atoms: bool = typer.Option(
        False,
        "--all",
        help="Batch-migrate every HTML atom found under specs/memory/ in the resolved specs_dir.",
    ),
    specs_dir: str | None = typer.Option(
        None,
        "--specs-dir",
        help="Path to specs/ directory. Default: resolve from primary_context.json.",
    ),
) -> None:
    """Migrate existing HTML memory atoms to schema-validated YAML source files.

    This command is the inverse of the renderer: it parses the known HTML structure of each
    memory atom type and produces a best-effort schema-valid YAML file adjacent to the HTML.

    \b
    Modes:
      Single atom:  dadaia migrate memory-yaml specs/memory/architecture.html
      Batch:        dadaia migrate memory-yaml --all [--specs-dir PATH]

    \b
    Idempotent guard:
      If the target .yaml file already exists, the command prints a WARN and skips it.
      Running the command a second time is always a no-op.

    \b
    On extraction:
      Fields are extracted from known section IDs, table rows and <li> lists.
      If a required field cannot be confidently extracted, a clearly-marked placeholder
      ("TODO: migrate from HTML") is used so the YAML still passes schema validation.
    """
    if atom_path is None and not all_atoms:
        typer.echo(
            "[error] Provide a path to an HTML atom OR use --all to batch-migrate all atoms.",
            err=True,
        )
        sys.exit(1)

    if atom_path is not None and all_atoms:
        typer.echo(
            "[error] --all and a positional atom path are mutually exclusive.",
            err=True,
        )
        sys.exit(1)

    if atom_path is not None:
        # ---- Single-atom mode ----------------------------------------
        html_file = Path(atom_path).resolve()
        if not html_file.exists():
            typer.echo(f"[error] File not found: {html_file}", err=True)
            sys.exit(1)
        _migrate_one(html_file)
        return

    # ---- Batch mode (--all) ------------------------------------------
    resolved_specs = _resolve_specs_dir(specs_dir)
    if not resolved_specs.is_dir():
        typer.echo(f"[error] specs_dir not found: {resolved_specs}", err=True)
        sys.exit(1)

    memory_dir = resolved_specs / "memory"
    if not memory_dir.is_dir():
        typer.echo(f"[error] memory/ directory not found under: {resolved_specs}", err=True)
        sys.exit(1)

    candidates: list[Path] = []
    # Structural atoms at memory root
    for name in ("architecture.html", "tech-stack.html"):
        p = memory_dir / name
        if p.exists():
            candidates.append(p)
    # Product index
    product_dir = memory_dir / "product"
    if product_dir.is_dir():
        index_html = product_dir / "index.html"
        if index_html.exists():
            candidates.append(index_html)
        # Feature atoms — all HTML except index.html
        for p in sorted(product_dir.glob("*.html")):
            if p.name != "index.html":
                candidates.append(p)

    if not candidates:
        typer.echo("[warn] No HTML atoms found under memory/.", err=True)
        return

    migrated = 0
    skipped = 0
    errored = 0
    for html_file in candidates:
        result = _migrate_one(html_file)
        if result == "migrated":
            migrated += 1
        elif result == "skipped":
            skipped += 1
        else:
            errored += 1

    typer.echo(
        f"[ok] Batch migration complete: "
        f"{migrated} migrated, {skipped} skipped (already exist), {errored} error(s)."
    )
    if errored > 0:
        sys.exit(1)


def _migrate_one(html_file: Path) -> str:
    """Migrate a single HTML atom to YAML.

    Returns 'migrated', 'skipped', or 'error'.
    """
    yaml_file = html_file.with_suffix(".yaml")

    # AC-C7-4: idempotent guard — do not overwrite existing .yaml
    if yaml_file.exists():
        typer.echo(
            f"[warn] YAML already exists, skipping: {yaml_file} "
            "(run is idempotent — delete the file manually to re-migrate)"
        )
        return "skipped"

    try:
        data, atom_type, warnings = migrate_html_atom_to_yaml(html_file)
    except Exception as exc:  # noqa: BLE001
        typer.echo(f"[error] Failed to parse {html_file}: {exc}", err=True)
        return "error"

    for w in warnings:
        typer.echo(f"[warn] {html_file.name}: {w}")

    # Validate before writing.
    try:
        from dadaia_workspace.features.specs.renderer import validate_atom

        validate_atom(data, atom_type)
    except Exception as exc:  # noqa: BLE001
        typer.echo(
            f"[error] Schema validation failed for {html_file.name} ({atom_type}): {exc}",
            err=True,
        )
        return "error"

    import yaml  # local import; PyYAML is a runtime dep

    yaml_text = yaml.safe_dump(data, allow_unicode=True, sort_keys=False, default_flow_style=False)
    yaml_file.write_text(yaml_text, encoding="utf-8")
    typer.echo(f"[ok] Migrated: {html_file.name} → {yaml_file.name} ({atom_type})")
    return "migrated"
