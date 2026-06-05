"""dadaia orchestrate subcommands."""

import os

import typer
from rich.console import Console
from rich.table import Table

from dadaia_workspace import container
from dadaia_workspace.core.exceptions import (
    OrchestrationUnsupportedError,
    RunNotFoundError,
    WorkflowNotFoundError,
    WorkflowSchemaError,
    WorkspaceNotInitializedError,
)
from dadaia_workspace.core.specs_resolver import resolve_bound_context_name
from dadaia_workspace.core.workspace_resolver import resolve_workspace_root
from dadaia_workspace.features.orchestration.service import OrchestrationService

app = typer.Typer(help="Run and manage multi-agent workflows.")
console = Console()
err_console = Console(stderr=True)


def _service(runtime: str | None = None) -> OrchestrationService:
    try:
        return container.build_orchestration_service(resolve_workspace_root(), runtime=runtime)
    except WorkspaceNotInitializedError:
        err_console.print(
            "[red]Error:[/red] Workspace not initialized. Run [bold]dadaia init[/bold] first."
        )
        raise typer.Exit(1) from None


def _resolve_context(explicit: str | None) -> str:
    return resolve_bound_context_name(explicit) or ""


def _parse_inputs(items: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for item in items:
        if "=" not in item:
            raise typer.BadParameter(f"--input value '{item}' must be in 'key=value' form")
        key, _, value = item.partition("=")
        out[key.strip()] = value.strip()
    return out


@app.command(name="list")
def list_workflows(json_out: bool = typer.Option(False, "--json")) -> None:
    """List installed workflows."""
    service = _service()
    workflows = service.list_workflows()
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
        wf = service.show_workflow(name)
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


@app.command()
def run(
    workflow: str = typer.Argument(..., help="Workflow name"),
    context: str = typer.Option("", "--context", help="Spec context name"),
    runtime: str = typer.Option(
        "",
        "--runtime",
        help="claude | opencode | codex | cli (default: env DADAIA_AGENT_RUNTIME or cli)",
    ),
    input_kv: list[str] = typer.Option([], "--input", help="key=value workflow inputs"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Validate without persisting state"),
) -> None:
    """Start a new run of WORKFLOW under the active context."""
    ctx = _resolve_context(context or None)
    if not ctx:
        err_console.print(
            "[red]Error:[/red] no active context. "
            "Run [bold]eval $(dadaia context bind <name> --mode read)[/bold] or pass --context."
        )
        raise typer.Exit(2)
    service = _service(runtime or None)
    runtime_label = runtime or os.environ.get("DADAIA_AGENT_RUNTIME") or "cli"
    try:
        inputs = _parse_inputs(input_kv)
    except typer.BadParameter as e:
        err_console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(2) from None
    if dry_run:
        try:
            service.show_workflow(workflow)
        except (WorkflowNotFoundError, WorkflowSchemaError) as e:
            err_console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(2) from None
        console.print("[green]✓[/green] dry-run validated")
        return
    try:
        manifest, invocations = service.start_run(
            workflow, context=ctx, runtime=runtime_label, inputs=inputs
        )
    except (WorkflowNotFoundError, WorkflowSchemaError, OrchestrationUnsupportedError) as e:
        err_console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(2) from None
    console.print(
        f"[green]✓[/green] run [bold]{manifest.run_id}[/bold] started "
        f"(workflow={manifest.workflow_name}, runtime={runtime_label}, context={ctx})"
    )
    if invocations:
        console.print("\nNext invocations prepared:")
        for inv in invocations:
            console.print(f"  - {inv.invocation_path}")
        console.print(f"\nWhen done, run [bold]dadaia orchestrate resume {manifest.run_id}[/bold].")


@app.command()
def status(
    run_id: str = typer.Argument("", help="Run id (omit to list all runs)"),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    """Show run state without mutating any file."""
    service = _service()
    if not run_id:
        runs = service.list_runs()
        if json_out:
            console.print_json(
                data=[
                    {
                        "run_id": r.run_id,
                        "workflow": r.workflow_name,
                        "status": r.status.value,
                        "started_at": r.started_at,
                    }
                    for r in runs
                ]
            )
            return
        if not runs:
            console.print("Sem runs registradas.")
            return
        table = Table(title="Runs")
        table.add_column("Run id", style="bold")
        table.add_column("Workflow")
        table.add_column("Status")
        table.add_column("Started")
        for r in runs:
            table.add_row(r.run_id, r.workflow_name, r.status.value, r.started_at)
        console.print(table)
        return

    try:
        manifest = service.get_run_status(run_id)
    except RunNotFoundError as e:
        err_console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(2) from None
    if json_out:
        console.print_json(
            data={
                "run_id": manifest.run_id,
                "workflow": manifest.workflow_name,
                "status": manifest.status.value,
                "context": manifest.context,
                "runtime": manifest.runtime,
                "started_at": manifest.started_at,
                "finished_at": manifest.finished_at,
                "stages": [
                    {
                        "id": s.id,
                        "agent": s.agent,
                        "status": s.status.value,
                        "started_at": s.started_at,
                        "finished_at": s.finished_at,
                        "output_path": s.output_path,
                    }
                    for s in manifest.stages
                ],
            }
        )
        return

    console.print(
        f"[bold]{manifest.workflow_name}[/bold]  run={manifest.run_id}  "
        f"status={manifest.status.value}  runtime={manifest.runtime}"
    )
    table = Table()
    table.add_column("Stage")
    table.add_column("Agent")
    table.add_column("Status")
    table.add_column("Started")
    table.add_column("Finished")
    for s in manifest.stages:
        table.add_row(
            s.id,
            s.agent,
            s.status.value,
            s.started_at or "—",
            s.finished_at or "—",
        )
    console.print(table)


@app.command()
def resume(run_id: str = typer.Argument(..., help="Run id to resume")) -> None:
    """Resume a run paused on a gate or recover from failure."""
    service = _service()
    try:
        manifest, invocations = service.resume_run(run_id)
    except RunNotFoundError as e:
        err_console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(2) from None
    if manifest.status.value == "completed" and not invocations:
        console.print("run já concluído")
        return
    console.print(
        f"[green]✓[/green] resumed (status={manifest.status.value}, "
        f"new_invocations={len(invocations)})"
    )
    for inv in invocations:
        console.print(f"  - {inv.invocation_path}")
