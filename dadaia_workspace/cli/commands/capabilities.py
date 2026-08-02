"""CLI adapter for the versioned provider capability contract."""

from __future__ import annotations

import json

import typer
from rich.console import Console
from rich.table import Table

from dadaia_workspace.features.capabilities import build_capabilities

console = Console()


def capabilities(
    json_output: bool = typer.Option(False, "--json", help="Emit the stable JSON contract."),
) -> None:
    """Describe public dadaia-workspace features supported by this installation."""
    payload = build_capabilities()
    if json_output:
        typer.echo(json.dumps(payload, sort_keys=True))
        return

    provider = payload["provider"]
    table = Table(title="dadaia-workspace capabilities")
    table.add_column("Surface", style="bold")
    table.add_column("Supported contract")
    table.add_row(
        "Provider",
        f"{provider['name']} {provider['distribution_version']} ({payload['schema_version']})",
    )
    table.add_row("Specs", f"pattern v{payload['specs']['pattern_version']}")
    table.add_row(
        "Contexts",
        ", ".join(payload["contexts"]["commands"]),
    )
    table.add_row(
        "SDD lifecycle",
        ", ".join(step["command"] for step in payload["sdd_lifecycle"]),
    )
    table.add_row("Machine output", "dadaia capabilities --json")
    console.print(table)
