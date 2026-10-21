"""CLI adapter for exact-version post-install workspace reconciliation."""

from __future__ import annotations

import json

import typer

from dadaia_workspace import container
from dadaia_workspace.cli._fail import fail
from dadaia_workspace.core.workspace_resolver import resolve_workspace_root


def reconcile(
    expect_version: str = typer.Option(
        ..., "--expect-version", help="Exact installed dadaia-workspace version to certify."
    ),
    json_output: bool = typer.Option(False, "--json", help="Emit structured result JSON."),
) -> None:
    """Reconcile state and projections after installing an exact candidate wheel."""
    workspace_root = resolve_workspace_root()
    result = container.reconcile_workspace(workspace_root, expected_version=expect_version)
    payload = result.to_dict()
    if json_output:
        typer.echo(json.dumps(payload, sort_keys=True))
    elif result.ok:
        from dadaia_workspace.cli.help_digest import write_digest

        write_digest(workspace_root)  # derived help digest rider; fail-soft
        typer.echo(f"[ok] reconciled dadaia-workspace {result.actual_version}")
        for step in result.steps:
            typer.echo(f"  [ok] {step}")
    else:
        fail(result.error, result.fix)
    if not result.ok:
        raise typer.Exit(1)
