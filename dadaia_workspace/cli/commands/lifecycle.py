"""Lifecycle command group."""

from __future__ import annotations

import json
from enum import IntEnum
from pathlib import Path
from typing import Any

import typer

from dadaia_workspace.core.models.lifecycle import (
    AgentRuntimeKind,
    GateEvidenceKind,
    LifecyclePhase,
)
from dadaia_workspace.core.protocols.runtime_files import RuntimeFileRef
from dadaia_workspace.core.workspace_resolver import resolve_workspace_root
from dadaia_workspace.features.lifecycle.hygiene import HygieneCleanupResult
from dadaia_workspace.features.lifecycle.prompt_builder import PromptScope
from dadaia_workspace.features.lifecycle.service import (
    LifecycleCommandResult,
    LifecycleCommandStatus,
    LifecyclePreflightService,
)

_HARNESS_KINDS = {
    "fake": AgentRuntimeKind.FAKE,
    "codex": AgentRuntimeKind.CODEX_EXEC,
    "claude": AgentRuntimeKind.CLAUDE_SDK,
    "opencode": AgentRuntimeKind.OPENCODE_RUN,
}

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
def backlog_define(
    context: str = typer.Option("dadaia-workspace", "--context", help="Context."),
    release_id: str = typer.Option(..., "--release-id", help="Release id."),
    run_id: str = typer.Option("backlog-define", "--run-id", help="Lifecycle run id."),
    harness: str = typer.Option("fake", "--harness", help="Harness: fake|codex|claude|opencode."),
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
) -> None:
    """Run the backlog-definition step on a selectable harness."""
    _run_phase_step(
        label="backlog-define",
        role="project-manager",
        from_phase=LifecyclePhase.BACKLOG_DEFINITION,
        target_phase=LifecyclePhase.RELEASE_DEFINITION,
        context=context,
        release_id=release_id,
        run_id=run_id,
        harness=harness,
        json_output=json_output,
    )


@release_app.command("define")
def release_define(
    context: str = typer.Option("dadaia-workspace", "--context", help="Context."),
    release_id: str = typer.Option(..., "--release-id", help="Release id."),
    run_id: str = typer.Option("release-define", "--run-id", help="Lifecycle run id."),
    harness: str = typer.Option("fake", "--harness", help="Harness: fake|codex|claude|opencode."),
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
) -> None:
    """Run the release-definition step on a selectable harness."""
    _run_phase_step(
        label="release-define",
        role="product-engineer",
        from_phase=LifecyclePhase.RELEASE_DEFINITION,
        target_phase=LifecyclePhase.IMPLEMENTATION,
        context=context,
        release_id=release_id,
        run_id=run_id,
        harness=harness,
        json_output=json_output,
    )


@app.command()
def implement(
    context: str = typer.Option("dadaia-workspace", "--context", help="Context."),
    release_id: str = typer.Option(..., "--release-id", help="Release id."),
    run_id: str = typer.Option("implement", "--run-id", help="Lifecycle run id."),
    harness: str = typer.Option("fake", "--harness", help="Harness: fake|codex|claude|opencode."),
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
) -> None:
    """Run the implementation step on a selectable harness."""
    _run_phase_step(
        label="implement",
        role="software-engineer",
        from_phase=LifecyclePhase.IMPLEMENTATION,
        target_phase=LifecyclePhase.QA_REVIEW,
        context=context,
        release_id=release_id,
        run_id=run_id,
        harness=harness,
        json_output=json_output,
    )


def _resolve_harness(harness: str) -> AgentRuntimeKind:
    try:
        return _HARNESS_KINDS[harness.lower()]
    except KeyError as exc:
        choices = ", ".join(sorted(_HARNESS_KINDS))
        raise typer.BadParameter(f"unknown harness '{harness}'; choose one of: {choices}") from exc


def _run_phase_step(
    *,
    label: str,
    role: str,
    from_phase: LifecyclePhase,
    target_phase: LifecyclePhase,
    context: str,
    release_id: str,
    run_id: str,
    harness: str,
    json_output: bool,
) -> None:
    """Run one bounded lifecycle step through the engine on a selectable harness.

    Shared by every single-step lifecycle verb (backlog/release define, implement,
    review qa|security|code, close). The harness is chosen per invocation; the worker
    must emit an APPROVED handoff with an artifact_ref to advance the phase.
    """
    from dadaia_workspace import container

    workspace_root = resolve_workspace_root()
    kind = _resolve_harness(harness)
    workflow = container.build_lifecycle_phase_workflow(workspace_root, runtime_kind=kind)
    scope = PromptScope(
        role=role,
        context=context,
        release_id=release_id,
        task_id=run_id,
        prompt=(
            f"Run the {label} step for release {release_id} in context {context}. "
            "Emit a handoff whose structured_output.verdict is APPROVED or REJECTED, with an "
            "artifact_ref pointing at the handoff document."
        ),
        allowed_paths=(f".dadaia/handoff/{context}/**",),
        required_evidence=(GateEvidenceKind.HANDOFF,),
    )
    result = workflow.run(
        run_id=run_id,
        command=label,
        from_phase=from_phase,
        target_phase=target_phase,
        scope=scope,
    )
    status = (
        LifecycleCommandStatus.OK.value if result.accepted else LifecycleCommandStatus.BLOCKED.value
    )
    if json_output:
        _emit_json(
            {
                "status": status,
                "run_id": result.run_id,
                "accepted": result.accepted,
                "phase": result.phase.value,
                "runtime": result.runtime_kind.value,
                "blocked": result.blocked.to_dict() if result.blocked else None,
            }
        )
    else:
        typer.echo(
            f"{status} {label} run={result.run_id} "
            f"harness={result.runtime_kind.value} phase={result.phase.value}"
        )
    if not result.accepted:
        raise typer.Exit(LifecycleExitCode.BLOCKED)


@review_app.command("qa")
def review_qa(
    context: str = typer.Option("dadaia-workspace", "--context", help="Review context."),
    release_id: str = typer.Option(..., "--release-id", help="Release id."),
    run_id: str = typer.Option("review-qa", "--run-id", help="Lifecycle run id."),
    harness: str = typer.Option("fake", "--harness", help="Harness: fake|codex|claude|opencode."),
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
) -> None:
    """Run the QA review gate on a selectable harness."""
    _run_phase_step(
        label="qa",
        role="qa-engineer",
        from_phase=LifecyclePhase.IMPLEMENTATION,
        target_phase=LifecyclePhase.QA_REVIEW,
        context=context,
        release_id=release_id,
        run_id=run_id,
        harness=harness,
        json_output=json_output,
    )


@review_app.command("security")
def review_security(
    context: str = typer.Option("dadaia-workspace", "--context", help="Review context."),
    release_id: str = typer.Option(..., "--release-id", help="Release id."),
    run_id: str = typer.Option("review-security", "--run-id", help="Lifecycle run id."),
    harness: str = typer.Option("fake", "--harness", help="Harness: fake|codex|claude|opencode."),
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
) -> None:
    """Run the security review gate on a selectable harness."""
    _run_phase_step(
        label="security",
        role="security-reviewer",
        from_phase=LifecyclePhase.QA_REVIEW,
        target_phase=LifecyclePhase.SECURITY_REVIEW,
        context=context,
        release_id=release_id,
        run_id=run_id,
        harness=harness,
        json_output=json_output,
    )


@review_app.command("code")
def review_code(
    context: str = typer.Option("dadaia-workspace", "--context", help="Review context."),
    release_id: str = typer.Option(..., "--release-id", help="Release id."),
    run_id: str = typer.Option("review-code", "--run-id", help="Lifecycle run id."),
    harness: str = typer.Option("fake", "--harness", help="Harness: fake|codex|claude|opencode."),
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
) -> None:
    """Run the code review gate on a selectable harness."""
    _run_phase_step(
        label="code",
        role="code-reviewer",
        from_phase=LifecyclePhase.SECURITY_REVIEW,
        target_phase=LifecyclePhase.CODE_REVIEW,
        context=context,
        release_id=release_id,
        run_id=run_id,
        harness=harness,
        json_output=json_output,
    )


@app.command()
def close(
    context: str = typer.Option("dadaia-workspace", "--context", help="Context."),
    release_id: str = typer.Option(..., "--release-id", help="Release id."),
    run_id: str = typer.Option("close", "--run-id", help="Lifecycle run id."),
    harness: str = typer.Option("fake", "--harness", help="Harness: fake|codex|claude|opencode."),
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
) -> None:
    """Run the release-closure step on a selectable harness."""
    _run_phase_step(
        label="close",
        role="product-engineer",
        from_phase=LifecyclePhase.CODE_REVIEW,
        target_phase=LifecyclePhase.CLOSURE,
        context=context,
        release_id=release_id,
        run_id=run_id,
        harness=harness,
        json_output=json_output,
    )


@app.command()
def pipeline(
    context: str = typer.Option("dadaia-workspace", "--context", help="Context."),
    release_id: str = typer.Option(..., "--release-id", help="Release id."),
    run_id: str = typer.Option("pipeline", "--run-id", help="Lifecycle run id."),
    harness: str = typer.Option("fake", "--harness", help="Default harness for all steps."),
    step_harness: list[str] | None = typer.Option(
        None,
        "--step-harness",
        help="Per-step override 'label=harness' (repeatable); labels: "
        "implement, review_qa, review_security, review_code.",
    ),
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
) -> None:
    """Run the multi-step release pipeline (implement→qa→security→code) with per-step harness mixing."""
    from dataclasses import replace

    from dadaia_workspace import container
    from dadaia_workspace.features.lifecycle.pipeline import implementation_ladder

    workspace_root = resolve_workspace_root()
    default_kind = _resolve_harness(harness)
    overrides: dict[str, AgentRuntimeKind] = {}
    for item in step_harness or []:
        label, sep, kind_str = item.partition("=")
        if not sep:
            raise typer.BadParameter(f"--step-harness expects 'label=harness', got {item!r}")
        overrides[label.strip()] = _resolve_harness(kind_str.strip())

    steps = tuple(
        replace(step, runtime_kind=overrides.get(step.label, step.runtime_kind))
        for step in implementation_ladder(default_kind)
    )
    pipe = container.build_lifecycle_pipeline(
        workspace_root, context=context, release_id=release_id
    )
    result = pipe.run(run_id, steps)
    status = (
        LifecycleCommandStatus.OK.value
        if result.completed
        else LifecycleCommandStatus.BLOCKED.value
    )
    if json_output:
        _emit_json(
            {
                "status": status,
                "run_id": result.run_id,
                "completed": result.completed,
                "final_phase": result.final_phase.value,
                "steps": [
                    {
                        "label": step.label,
                        "runtime": step.runtime_kind.value,
                        "accepted": step.accepted,
                        "phase": step.phase.value,
                    }
                    for step in result.steps
                ],
                "blocked": result.blocked.to_dict() if result.blocked else None,
            }
        )
    else:
        trail = " → ".join(
            f"{s.label}[{s.runtime_kind.value}]:{'ok' if s.accepted else 'BLOCKED'}"
            for s in result.steps
        )
        typer.echo(f"{status} run={result.run_id} phase={result.final_phase.value} {trail}")
    if not result.completed:
        raise typer.Exit(LifecycleExitCode.BLOCKED)


app.add_typer(hygiene_app, name="hygiene")
app.add_typer(backlog_app, name="backlog")
app.add_typer(release_app, name="release")
app.add_typer(review_app, name="review")
