"""CLI adapter for exact-version post-install workspace reconciliation."""

from __future__ import annotations

import json

import typer

from dadaia_workspace import container
from dadaia_workspace.core.workspace_resolver import resolve_workspace_root
from dadaia_workspace.features.reconcile import reconcile_workspace


def reconcile(
    expect_version: str = typer.Option(
        ..., "--expect-version", help="Exact installed dadaia-workspace version to certify."
    ),
    json_output: bool = typer.Option(False, "--json", help="Emit structured result JSON."),
) -> None:
    """Reconcile state and projections after installing an exact candidate wheel."""
    workspace_root = resolve_workspace_root()
    result = reconcile_workspace(
        workspace_root,
        expected_version=expect_version,
        public_service=container.build_public_service(),
        doctor_service=container.build_doctor_service(workspace_root),
    )
    payload = result.to_dict()
    if json_output:
        typer.echo(json.dumps(payload, sort_keys=True))
    elif result.ok:
        typer.echo(f"[ok] reconciled dadaia-workspace {result.actual_version}")
        for step in result.steps:
            typer.echo(f"  [ok] {step}")
    else:
        typer.echo(f"[error] reconciliation failed: {result.error}", err=True)
        if result.rollback_required:
            typer.echo(
                "[rollback-required] reinstall the previous exact provider version, then run "
                "its matching 'dadaia public stage' and 'dadaia public install --target all'.",
                err=True,
            )
    if not result.ok:
        raise typer.Exit(1)
