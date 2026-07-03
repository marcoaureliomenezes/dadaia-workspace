"""dadaia orchestrate subcommands.

Read-only catalog surface over the markdown workflow definitions. Workflow
*execution* lives in the lifecycle engine (``dadaia lifecycle``); the ``.workflow.md``
files are reference documents only. The ``list``/``show`` verbs read the shared
``MarkdownWorkflowStore`` (via a ``features/workflows`` accessor that preserves
``stage.gate.kind`` and every ``WorkflowInput`` field). The former ``run``/``status``/
``resume`` verbs — honest no-ops backed by the retired ``features/orchestration``
package — were removed in v0.1.53.
"""

import typer
from rich.console import Console
from rich.table import Table

from dadaia_workspace import container
from dadaia_workspace.core.exceptions import (
    WorkflowNotFoundError,
    WorkspaceNotInitializedError,
)
from dadaia_workspace.core.workspace_resolver import resolve_workspace_root
from dadaia_workspace.features.workflows.service import WorkflowsService

app = typer.Typer(help="Inspect multi-agent workflow reference docs (execution: dadaia lifecycle).")
console = Console()
err_console = Console(stderr=True)


def _service() -> WorkflowsService:
    try:
        return container.build_orchestration_catalog_service(resolve_workspace_root())
    except WorkspaceNotInitializedError:
        err_console.print(
            "[red]Error:[/red] Workspace not initialized. Run [bold]dadaia init[/bold] first."
        )
        raise typer.Exit(1) from None


@app.command(name="list")
def list_workflows(json_out: bool = typer.Option(False, "--json")) -> None:
    """List installed workflows."""
    service = _service()
    workflows = service.list_definitions()
    if json_out:
        payload = [
            {"name": w.name, "version": w.version, "description": w.description} for w in workflows
        ]
        console.print_json(data=payload)
        return
    if not workflows:
        console.print("Nenhum workflow instalado.")
        return
    table = Table(title="Workflows")
    table.add_column("Name", style="bold")
    table.add_column("Version")
    table.add_column("Description")
    for w in workflows:
        table.add_row(w.name, w.version, w.description)
    console.print(table)


@app.command()
def show(
    name: str = typer.Argument(..., help="Workflow name"),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    """Show a workflow's declared inputs, stages, and exit criteria."""
    service = _service()
    try:
        wf = service.get_definition(name)
    except WorkflowNotFoundError as e:
        err_console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(2) from None

    if json_out:
        console.print_json(
            data={
                "name": wf.name,
                "version": wf.version,
                "description": wf.description,
                "inputs": [
                    {
                        "name": i.name,
                        "type": i.type,
                        "required": i.required,
                        "default": i.default,
                    }
                    for i in wf.inputs
                ],
                "stages": [
                    {
                        "id": s.id,
                        "agent": s.agent,
                        "needs": list(s.needs),
                        "parallel_group": s.parallel_group,
                        "gate": (s.gate.kind if s.gate else None),
                    }
                    for s in wf.stages
                ],
            }
        )
        return

    console.print(f"[bold]{wf.name}[/bold]  v{wf.version}")
    console.print(wf.description)
    if wf.inputs:
        console.print("\n[underline]Inputs[/underline]")
        for i in wf.inputs:
            req = "required" if i.required else f"default={i.default!r}"
            console.print(f"  - {i.name} ({i.type}, {req})")
    console.print("\n[underline]Stages[/underline]")
    for s in wf.stages:
        bits = [s.id, f"agent={s.agent}"]
        if s.needs:
            bits.append(f"needs={list(s.needs)}")
        if s.parallel_group:
            bits.append(f"parallel_group={s.parallel_group}")
        if s.gate:
            bits.append(f"gate={s.gate.kind}")
        console.print("  - " + "  ".join(bits))
