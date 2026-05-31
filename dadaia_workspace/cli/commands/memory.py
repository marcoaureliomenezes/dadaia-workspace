"""CLI command group: ``dadaia memory <subcommand>``."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import typer
from jsonschema import ValidationError

from dadaia_workspace.features.spec_artifacts.memory import memory_product_add
from dadaia_workspace.features.specs.catalog import generate_catalog, write_catalog
from dadaia_workspace.features.specs.renderer import render_atom

app = typer.Typer(help="Memory catalog management commands.")
product_app = typer.Typer(help="Product memory catalog commands.")
app.add_typer(product_app, name="product")

catalog_app = typer.Typer(help="Catalog JSON generation commands.")
app.add_typer(catalog_app, name="catalog")


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


@app.command("render")
def memory_render(
    yaml_path: str = typer.Argument(
        ...,
        help="Path to the YAML memory atom to render (e.g. specs/memory/architecture.yaml).",
    ),
    atom_type: str | None = typer.Option(
        None,
        "--atom-type",
        help=(
            "Explicit atom type identifier. One of: memory-architecture-v1, "
            "memory-tech-stack-v1, memory-product-index-v1, memory-product-feature-v1. "
            "If omitted, the type is inferred from the file path."
        ),
    ),
    project_name: str = typer.Option(
        "Projeto",
        "--project-name",
        help="Project name injected as context_name / project_name template variable.",
    ),
) -> None:
    """Validate and render a YAML memory atom to adjacent HTML.

    \b
    1. Parses <yaml_path> with yaml.safe_load.
    2. Validates against the matching JSON Schema (schema violations exit non-zero).
    3. Renders to HTML using the canonical Jinja2 template.
    4. Writes the output as <yaml_path_stem>.html in the same directory.

    Exit 0 on success. Exit 1 on schema validation error or any other failure.
    """
    src = Path(yaml_path).resolve()
    if not src.exists():
        typer.echo(f"[error] YAML file not found: {src}", err=True)
        sys.exit(1)
    if src.suffix.lower() not in (".yaml", ".yml"):
        typer.echo(f"[error] Expected a .yaml or .yml file, got: {src.suffix}", err=True)
        sys.exit(1)

    extra_context: dict[str, str] = {
        "project_name": project_name,
        "context_name": project_name,
    }

    try:
        html = render_atom(
            src,
            atom_type=atom_type if atom_type else None,
            extra_context=extra_context,
        )
    except ValidationError as exc:
        typer.echo(f"[error] Schema validation failed: {exc.message}", err=True)
        sys.exit(1)
    except ValueError as exc:
        typer.echo(f"[error] {exc}", err=True)
        sys.exit(1)
    except Exception as exc:  # noqa: BLE001
        typer.echo(f"[error] Render failed: {exc}", err=True)
        sys.exit(1)

    out_path = src.parent / (src.stem + ".html")
    try:
        out_path.write_text(html, encoding="utf-8")
    except OSError as exc:
        typer.echo(f"[error] Failed to write {out_path}: {exc}", err=True)
        sys.exit(1)

    typer.echo(f"[ok] rendered: {out_path}")


@catalog_app.command("generate")
def catalog_generate(
    specs_dir: str | None = typer.Option(
        None,
        "--specs-dir",
        help="Path to specs/ directory. Default: resolve from primary_context.json.",
    ),
) -> None:
    """Generate (or regenerate) specs/memory/product/catalog.json from index.html.

    Reads the ``<ol class="catalog">`` entries in ``index.html`` and writes
    a machine-readable ``catalog.json`` to the same directory.  Running the
    command a second time is idempotent — it overwrites the previous file.
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
    except FileNotFoundError as exc:
        typer.echo(f"[error] {exc}", err=True)
        sys.exit(1)

    out_path = write_catalog(target, catalog)
    n = len(catalog.get("features", []))
    typer.echo(f"[ok] catalog.json written ({n} feature{'s' if n != 1 else ''}): {out_path}")
