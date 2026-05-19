"""dadaia reports subcommands — inspect and validate agent handoff reports."""

from __future__ import annotations

import json as _json
from pathlib import Path

import typer
from rich.console import Console

from dadaia_workspace import container
from dadaia_workspace.core.exceptions import HandoffSchemaError, WorkspaceNotInitializedError
from dadaia_workspace.core.workspace_resolver import resolve_workspace_root
from dadaia_workspace.features.reports_validation.service import ValidationResult

app = typer.Typer(help="Inspect and validate agent handoff reports.")
console = Console()
err_console = Console(stderr=True)


# ---------------------------------------------------------------------------
# validate subcommand
# ---------------------------------------------------------------------------


@app.command(name="validate")
def validate(
    paths: list[Path] | None = typer.Argument(
        default=None, help="Paths to .handoff.json files to validate."
    ),
    all_: bool = typer.Option(
        False, "--all", help="Validate all *.handoff.json files under the workspace reports root."
    ),
    release: str | None = typer.Option(
        None,
        "--release",
        help="Filter to a specific release ID (matches against handoff release_id field).",
    ),
    strict: bool = typer.Option(
        False,
        "--strict/--no-strict",
        help="Exit 1 on any validation violation. Default: non-strict (warnings only).",
    ),
    json_output: bool = typer.Option(
        False, "--json", help="Emit machine-readable JSON output instead of human-readable text."
    ),
) -> None:
    """Validate one or more agent handoff JSON files.

    \b
    Exit codes:
      0  All files valid (or violations found in non-strict mode)
      1  One or more violations in strict mode
      2  One or more file paths not found
      3  Bad invocation (no paths and not --all) or workspace not initialized

    \b
    Examples:
      dadaia reports validate path/to/report.handoff.json
      dadaia reports validate --all
      dadaia reports validate --all --strict
      dadaia reports validate --all --json
    """
    # Invocation guard: must have paths or --all
    if not paths and not all_:
        err_console.print("[red]Error:[/red] provide one or more PATHS or use [bold]--all[/bold].")
        raise typer.Exit(3)

    workspace_root = resolve_workspace_root()

    # Build service — schema must be staged
    try:
        service = container.build_reports_validation_service(workspace_root)
    except HandoffSchemaError as exc:
        err_console.print(
            f"[red]Error:[/red] Could not load handoff schema: {exc}\n"
            "Run [bold]dadaia public stage && dadaia public install --target all[/bold] first."
        )
        raise typer.Exit(3) from None
    except WorkspaceNotInitializedError:
        err_console.print(
            "[red]Error:[/red] Workspace not initialized. Run [bold]dadaia init[/bold] first."
        )
        raise typer.Exit(3) from None

    # Collect results
    results: list[ValidationResult] = []

    if all_:
        results.extend(service.validate_all())
    elif paths:
        # Check for missing files first
        missing = [p for p in paths if not p.exists()]
        if missing:
            for m in missing:
                err_console.print(f"[red]Error:[/red] File not found: {m}")
            raise typer.Exit(2)
        for p in paths:
            results.append(service.validate_file(p))

    # Apply release filter if requested
    if release:
        filtered: list[ValidationResult] = []
        for r in results:
            if r.valid:
                # Re-read to inspect release_id
                try:
                    doc = _json.loads(r.path.read_text(encoding="utf-8"))
                    if doc.get("release_id") == release:
                        filtered.append(r)
                except Exception:  # noqa: BLE001
                    filtered.append(r)
            else:
                filtered.append(r)
        results = filtered

    # Output
    n_valid = sum(1 for r in results if r.valid)
    n_invalid = len(results) - n_valid

    if json_output:
        payload = [
            {
                "path": str(r.path),
                "valid": r.valid,
                "errors": [{"field_path": e.field_path, "message": e.message} for e in r.errors],
                "hash_status": r.hash_status,
            }
            for r in results
        ]
        console.print_json(data=payload)
    else:
        for r in results:
            if r.valid:
                console.print(f"[green]VALID[/green]   {r.path}")
            else:
                console.print(f"[red]INVALID[/red] {r.path}")
                for err in r.errors:
                    console.print(f"         [yellow]{err.field_path}[/yellow]: {err.message}")
        console.print(
            f"\nSummary: [green]{n_valid} valid[/green], [red]{n_invalid} invalid[/red] "
            f"(of {len(results)} files)"
        )

    # Exit code logic
    if strict and n_invalid > 0:
        raise typer.Exit(1)
