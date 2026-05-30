"""CLI command group: ``dadaia memory <subcommand>``."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import typer

from dadaia_workspace.features.spec_artifacts.memory import memory_product_add

app = typer.Typer(help="Memory catalog management commands.")
product_app = typer.Typer(help="Product memory catalog commands.")
app.add_typer(product_app, name="product")


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


@product_app.command("add")
def product_add(
    slug: str = typer.Argument(..., help="Feature slug (e.g. payments). Must match ^[a-z][a-z0-9-]+$."),
    specs_dir: str | None = typer.Option(
        None,
        "--specs-dir",
        help="Path to specs/ directory. Default: resolve from primary_context.json.",
    ),
    project_name: str = typer.Option(
        "Projeto",
        "--project-name",
        help="Project name used in rendered HTML.",
    ),
) -> None:
    """Create a product feature HTML and regenerate the product catalog index.

    \b
    1. Creates specs/memory/product/<slug>.html from the canonical template
       (skipped if the file already exists).
    2. Regenerates specs/memory/product/index.html deterministically in
       lexicographic order over all feature slugs (idempotent).
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
    typer.echo(f"[ok] feature HTML ({action}): {result.feature_html}")
    typer.echo(f"[ok] index regenerated: {result.index_html}")
    typer.echo(f"     catalog entries ({len(result.slug_entries)}): {', '.join(result.slug_entries)}")
