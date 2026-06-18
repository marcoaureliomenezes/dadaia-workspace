"""Lifecycle command group."""

from __future__ import annotations

from enum import IntEnum

import typer

from dadaia_workspace.core.workspace_resolver import resolve_workspace_root
from dadaia_workspace.features.lifecycle.service import (
    LifecycleCommandResult,
    LifecycleCommandStatus,
    LifecyclePreflightService,
)

app = typer.Typer(help="Deterministic lifecycle workflow commands.", no_args_is_help=True)
hygiene_app = typer.Typer(help="Lifecycle hygiene commands.", no_args_is_help=True)
review_app = typer.Typer(help="Lifecycle review commands.", no_args_is_help=True)
backlog_app = typer.Typer(help="Lifecycle backlog commands.", no_args_is_help=True)
release_app = typer.Typer(help="Lifecycle release commands.", no_args_is_help=True)


class LifecycleExitCode(IntEnum):
    OK = 0
    INTERNAL_ERROR = 1
    USAGE_ERROR = 2
    BLOCKED = 3


def _emit_command_result(result: LifecycleCommandResult) -> None:
    is_error = result.status is LifecycleCommandStatus.INTERNAL_ERROR
    typer.echo(f"{result.status.value} {result.message}", err=is_error)
    if result.status is LifecycleCommandStatus.OK:
        return
    if result.status is LifecycleCommandStatus.INTERNAL_ERROR:
        raise typer.Exit(LifecycleExitCode.INTERNAL_ERROR)
    raise typer.Exit(LifecycleExitCode.BLOCKED)


def _preflight_service() -> LifecyclePreflightService:
    from dadaia_workspace import container

    workspace_root = resolve_workspace_root()
    return container.build_lifecycle_preflight_service(workspace_root)


def _emit_unavailable_workflow(workflow: str) -> None:
    service = _preflight_service()
    _emit_command_result(service.unavailable_workflow(workflow))


@app.command()
def status() -> None:
    """Show lifecycle status."""
    from dadaia_workspace import container

    workspace_root = resolve_workspace_root()
    service = container.build_lifecycle_hygiene_service(workspace_root)
    counters = service.status()
    typer.echo(f"OK cleanup_candidates={counters.cleanup_candidate_count}")


@app.command()
def preflight() -> None:
    """Run lifecycle preflight."""
    service = _preflight_service()
    _emit_command_result(service.unresolved_runtime_preflight())


@app.command()
def report() -> None:
    """Run lifecycle report workflow."""
    _emit_unavailable_workflow("report")


@app.command()
def resume(run_id: str) -> None:
    """Resume a lifecycle run by id."""
    from dadaia_workspace import container

    workspace_root = resolve_workspace_root()
    store = container.build_lifecycle_run_store(workspace_root)
    service = container.build_lifecycle_preflight_service(workspace_root)
    _emit_command_result(service.resume_run(store, run_id))


@hygiene_app.command("status")
def hygiene_status() -> None:
    """Show lifecycle hygiene status."""
    from dadaia_workspace import container

    workspace_root = resolve_workspace_root()
    counters = container.build_lifecycle_hygiene_service(workspace_root).status()
    typer.echo(f"OK cleanup_candidates={counters.cleanup_candidate_count}")


@hygiene_app.command("clean")
def hygiene_clean(
    apply: bool = typer.Option(False, "--apply", help="Apply cleanup. Default is dry-run."),
) -> None:
    """Run lifecycle hygiene cleanup."""
    from dadaia_workspace import container

    workspace_root = resolve_workspace_root()
    result = container.build_lifecycle_hygiene_service(workspace_root).cleanup(dry_run=not apply)
    mode = "applied" if apply else "dry-run"
    typer.echo(f"OK {mode} candidates={len(result.candidates)}")


@backlog_app.command("define")
def backlog_define() -> None:
    """Define backlog through the lifecycle workflow."""
    _emit_unavailable_workflow("backlog definition")


@release_app.command("define")
def release_define() -> None:
    """Define a release through the lifecycle workflow."""
    _emit_unavailable_workflow("release definition")


@app.command()
def implement() -> None:
    """Run lifecycle implementation workflow."""
    _emit_unavailable_workflow("implementation")


@review_app.command("qa")
def review_qa() -> None:
    """Run QA review gate."""
    _emit_unavailable_workflow("QA review")


@review_app.command("security")
def review_security() -> None:
    """Run security review gate."""
    _emit_unavailable_workflow("security review")


@review_app.command("code")
def review_code() -> None:
    """Run code review gate."""
    _emit_unavailable_workflow("code review")


@app.command()
def close() -> None:
    """Close the active lifecycle release."""
    _emit_unavailable_workflow("release closure")


app.add_typer(hygiene_app, name="hygiene")
app.add_typer(backlog_app, name="backlog")
app.add_typer(release_app, name="release")
app.add_typer(review_app, name="review")
