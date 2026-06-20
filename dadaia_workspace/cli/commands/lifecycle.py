"""Lifecycle command group."""

from __future__ import annotations

import json
from enum import IntEnum
from pathlib import Path
from typing import Any

import typer

from dadaia_workspace.core.protocols.runtime_files import RuntimeFileRef
from dadaia_workspace.core.workspace_resolver import resolve_workspace_root
from dadaia_workspace.features.lifecycle.hygiene import HygieneCleanupResult
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


def _emit_json(payload: dict[str, Any]) -> None:
    typer.echo(json.dumps(payload, sort_keys=True))


def _command_result_payload(result: LifecycleCommandResult) -> dict[str, Any]:
    return {
        "status": result.status.value,
        "message": result.message,
        "blocked": result.blocked.to_dict() if result.blocked else None,
    }


def _emit_command_result(result: LifecycleCommandResult, *, json_output: bool = False) -> None:
    if json_output:
        _emit_json(_command_result_payload(result))
    else:
        is_error = result.status is LifecycleCommandStatus.INTERNAL_ERROR
        typer.echo(f"{result.status.value} {result.message}", err=is_error)
    _exit_for_command_result(result)


def _exit_for_command_result(result: LifecycleCommandResult) -> None:
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


def _relative_path_refs(workspace_root: Path, paths: tuple[Path, ...]) -> list[str]:
    refs: list[str] = []
    for path in paths:
        try:
            refs.append(path.relative_to(workspace_root).as_posix())
        except ValueError:
            refs.append(path.as_posix())
    return refs


def _cleanup_result_payload(
    result: HygieneCleanupResult, *, workspace_root: Path
) -> dict[str, Any]:
    return {
        "status": LifecycleCommandStatus.OK.value,
        "dry_run": result.dry_run,
        "candidate_count": len(result.candidates),
        "candidates": [candidate.to_dict() for candidate in result.candidates],
        "deleted_paths": _relative_path_refs(workspace_root, result.deleted_paths),
        "skipped_paths": _relative_path_refs(workspace_root, result.skipped_paths),
        "pruned_dirs": _relative_path_refs(workspace_root, result.pruned_dirs),
    }


def _runtime_ref_payload(ref: RuntimeFileRef) -> dict[str, object]:
    return {
        "kind": ref.kind.value,
        "path": ref.path,
        "content_hash": ref.content_hash,
        "ttl_seconds": ref.ttl_seconds,
    }


@app.command()
def status(
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
) -> None:
    """Show lifecycle status."""
    from dadaia_workspace import container

    workspace_root = resolve_workspace_root()
    service = container.build_lifecycle_hygiene_service(workspace_root)
    counters = service.status()
    if json_output:
        _emit_json(
            {
                "status": LifecycleCommandStatus.OK.value,
                "counters": counters.to_dict(),
            }
        )
        return
    typer.echo(f"OK cleanup_candidates={counters.cleanup_candidate_count}")


@app.command()
def preflight(
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
) -> None:
    """Run lifecycle preflight."""
    service = _preflight_service()
    _emit_command_result(service.unresolved_runtime_preflight(), json_output=json_output)


@app.command()
def report(
    context: str = typer.Option("dadaia-workspace", "--context", help="Report context."),
    release_id: str = typer.Option("v0.1.15", "--release-id", help="Release id."),
    run_id: str = typer.Option("lifecycle-report", "--run-id", help="Lifecycle run id."),
    apply_cleanup: bool = typer.Option(
        False,
        "--apply-cleanup",
        help="Apply hygiene cleanup after writing the report.",
    ),
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
) -> None:
    """Run lifecycle report workflow."""
    from dadaia_workspace import container

    workspace_root = resolve_workspace_root()
    result = container.build_lifecycle_report_workflow(workspace_root).run(
        context=context,
        release_id=release_id,
        run_id=run_id,
        apply_cleanup=apply_cleanup,
    )
    if json_output:
        _emit_json(
            {
                "status": LifecycleCommandStatus.OK.value,
                "report": _runtime_ref_payload(result.report),
                "handoff": _runtime_ref_payload(result.handoff),
                "baseline_snapshot": _runtime_ref_payload(result.baseline_snapshot),
                "final_snapshot": _runtime_ref_payload(result.final_snapshot),
                "cleanup_dry_run": result.cleanup.dry_run,
                "cleanup_candidate_count": len(result.cleanup.candidates),
                "validation_valid": result.validation.valid,
                "validation_hash_status": result.validation.hash_status,
            }
        )
        return
    typer.echo(f"OK report={result.report.path} handoff={result.handoff.path}")


@app.command()
def resume(run_id: str) -> None:
    """Resume a lifecycle run by id."""
    from dadaia_workspace import container

    workspace_root = resolve_workspace_root()
    store = container.build_lifecycle_run_store(workspace_root)
    service = container.build_lifecycle_preflight_service(workspace_root)
    _emit_command_result(service.resume_run(store, run_id))


@hygiene_app.command("status")
def hygiene_status(
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
) -> None:
    """Show lifecycle hygiene status."""
    from dadaia_workspace import container

    workspace_root = resolve_workspace_root()
    counters = container.build_lifecycle_hygiene_service(workspace_root).status()
    if json_output:
        _emit_json(
            {
                "status": LifecycleCommandStatus.OK.value,
                "counters": counters.to_dict(),
            }
        )
        return
    typer.echo(f"OK cleanup_candidates={counters.cleanup_candidate_count}")


@hygiene_app.command("clean")
def hygiene_clean(
    dry_run: bool = typer.Option(
        True,
        "--dry-run/--apply",
        help="Preview cleanup or apply it explicitly.",
    ),
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
) -> None:
    """Run lifecycle hygiene cleanup."""
    from dadaia_workspace import container

    workspace_root = resolve_workspace_root()
    result = container.build_lifecycle_hygiene_service(workspace_root).cleanup(dry_run=dry_run)
    if json_output:
        _emit_json(_cleanup_result_payload(result, workspace_root=workspace_root))
        return
    mode = "dry-run" if dry_run else "applied"
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
