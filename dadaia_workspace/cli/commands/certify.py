"""CLI adapter for the disposable full-capability certification journey."""

from __future__ import annotations

import json

import typer

from dadaia_workspace import container
from dadaia_workspace.core.workspace_resolver import resolve_workspace_root


def certify(
    json_output: bool = typer.Option(False, "--json", help="Emit stable result JSON."),
    keep: bool = typer.Option(False, "--keep", help="Keep the disposable workspace."),
) -> None:
    """Certify assembled public features in a disposable local workspace."""
    result = container.run_certification(resolve_workspace_root(), keep=keep)
    payload = result.to_dict()
    if json_output:
        typer.echo(json.dumps(payload, sort_keys=True))
    else:
        for item in result.checks:
            typer.echo(f"[{item.status}] {item.name}: {item.detail}")
        typer.echo("CERTIFIED" if result.ok else "CERTIFICATION FAILED")
    if not result.ok:
        raise typer.Exit(1)
