"""CLI command group: ``dadaia memory <subcommand>``."""

from __future__ import annotations

import sys
from pathlib import Path

import typer

from dadaia_workspace.features.spec_artifacts.memory import memory_product_add
from dadaia_workspace.features.specs.catalog import generate_catalog, write_catalog
from dadaia_workspace.core.specs_resolver import resolve_specs_dir as _shared_resolve_specs_dir

app = typer.Typer(help="Memory catalog management commands.")
product_app = typer.Typer(help="Product memory catalog commands.")
app.add_typer(product_app, name="product")

catalog_app = typer.Typer(help="Catalog JSON generation commands.")
app.add_typer(catalog_app, name="catalog")


def _resolve_specs_dir(specs_dir: str | None) -> Path:
    """Resolve the target specs/ directory.

    Priority:
    1. Explicit ``--specs-dir`` argument.
    2. Bound context session (``DADAIA_CONTEXT`` or ``DADAIA_SESSION_ID``).
    3. ``<cwd>/specs`` fallback.
    """
    return _shared_resolve_specs_dir(specs_dir)


@product_app.command("add")
def product_add(
    slug: str = typer.Argument(
        ..., help="Feature slug (e.g. payments). Must match ^[a-z][a-z0-9-]+$."
    ),
    specs_dir: str | None = typer.Option(
        None,
        "--specs-dir",
        help="Path to specs/ directory. Default: resolve from bound context session.",
    ),
    project_name: str = typer.Option(
        "Projeto",
        "--project-name",
        help="Project name used in rendered HTML.",
    ),
) -> None:
    """Create a product feature Markdown atom.

    \b
    1. Creates specs/memory/product/<slug>.md from the born-markdown scaffold template
       (skipped if the file already exists).
    2. To regenerate the product catalog JSON, run: dadaia memory catalog generate
    """
    target = _resolve_specs_dir(specs_dir)

    if not target.is_dir():
        typer.echo(f"[error] specs_dir not found: {target}", err=True)
        sys.exit(1)

    try:
        result = memory_product_add(
            target,
            slug,
            project_name=project_name,
        )
    except ValueError as exc:
        typer.echo(f"[error] {exc}", err=True)
        sys.exit(1)

    action = "created" if result.created_feature else "already exists"
    typer.echo(f"[ok] feature atom ({action}): {result.feature_html}")
    typer.echo(
        f"     catalog entries ({len(result.slug_entries)}): {', '.join(result.slug_entries)}"
    )


@catalog_app.command("generate")
def catalog_generate(
    specs_dir: str | None = typer.Option(
        None,
        "--specs-dir",
        help="Path to specs/ directory. Default: resolve from bound context session.",
    ),
) -> None:
    """Generate (or regenerate) specs/memory/product/catalog.json from .md frontmatter.

    Reads YAML frontmatter from all ``*.md`` feature atom files in
    ``specs/memory/product/`` and writes a machine-readable ``catalog.json``
    to the same directory.  Running the command a second time is idempotent.
    """
    try:
        target = _resolve_specs_dir(specs_dir)
    except typer.BadParameter as exc:
        typer.echo(f"[error] {exc}", err=True)
        sys.exit(1)

    if not target.is_dir():
        typer.echo(f"[error] specs_dir not found: {target}", err=True)
        sys.exit(1)

    try:
        catalog = generate_catalog(target)
    except (FileNotFoundError, ValueError) as exc:
        typer.echo(f"[error] {exc}", err=True)
        sys.exit(1)

    out_path = write_catalog(target, catalog)
    n = len(catalog.get("features", []))
    typer.echo(f"[ok] catalog.json written ({n} feature{'s' if n != 1 else ''}): {out_path}")
