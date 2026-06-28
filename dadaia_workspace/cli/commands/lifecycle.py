"""Lifecycle command group."""

from __future__ import annotations

import json
from collections.abc import Callable
from enum import IntEnum
from pathlib import Path
from typing import Any

import typer

from dadaia_workspace.core.harness_models import (
    CODEX_HARNESS,
    PI_HARNESS,
    HarnessModelOption,
)
from dadaia_workspace.core.harness_models import (
    validate as validate_harness_model,
)
from dadaia_workspace.core.models.lifecycle import (
    AgentRuntimeKind,
    GateEvidenceKind,
    LifecyclePhase,
)
from dadaia_workspace.core.protocols.runtime_files import RuntimeFileRef
from dadaia_workspace.core.workspace_resolver import resolve_workspace_root
from dadaia_workspace.features.lifecycle.hygiene import HygieneCleanupResult
from dadaia_workspace.features.lifecycle.phase_workflow import (
    PhaseWorkflowResult,
    is_review_phase,
)
from dadaia_workspace.features.lifecycle.prompt_builder import PromptScope
from dadaia_workspace.features.lifecycle.service import (
    LifecycleCommandResult,
    LifecycleCommandStatus,
    LifecyclePreflightService,
)

# Layer-2 workflow harnesses (LAW 1, ADR-A): pi/codex run as workers; fake is the
# deterministic test adapter. ``claude`` is intentionally ABSENT — Claude Code is a
# Layer-1 entry harness; running it as a Layer-2 worker spends credits outside the
# operator's subscription. The CLAUDE_SDK adapter + enum value remain in code (Layer-1)
# but are not selectable as a workflow harness.
_HARNESS_KINDS = {
    "fake": AgentRuntimeKind.FAKE,
    "codex": AgentRuntimeKind.CODEX_EXEC,
    "pi": AgentRuntimeKind.PI_HEADLESS,
}

# Harness names → the CLI ``--harness`` value that selects a discrete model catalog
# (LAW 2). ``fake`` carries no model. Used to map a chosen harness to its catalog key.
_HARNESS_CATALOG_KEY = {
    "codex": CODEX_HARNESS,
    "pi": PI_HARNESS,
}

# Harness names rejected as Layer-2 workflow harnesses (LAW 1) with a pointer. Claude is a
# Layer-1 entry harness; OpenCode was removed as a Layer-2 worker in v0.1.24. Layer-2
# workers are pi or codex only; ``fake`` is the deterministic test adapter.
_LAYER1_ONLY_HARNESSES = {
    "claude",
    "claude_sdk",
    "claude-sdk",
    "opencode",
    "open-code",
}

app = typer.Typer(help="Deterministic lifecycle workflow commands.", no_args_is_help=True)
hygiene_app = typer.Typer(help="Lifecycle hygiene commands.", no_args_is_help=True)
review_app = typer.Typer(help="Lifecycle review commands.", no_args_is_help=True)
backlog_app = typer.Typer(help="Lifecycle backlog commands.", no_args_is_help=True)
release_app = typer.Typer(help="Lifecycle release commands.", no_args_is_help=True)
bug_app = typer.Typer(help="Lifecycle bug-report commands.", no_args_is_help=True)
workflow_app = typer.Typer(
    help="Read-only workflow model-governance inspection.", no_args_is_help=True
)
handoffs_app = typer.Typer(help="Workflow-step handoff ledger inspection.", no_args_is_help=True)


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
def slop(
    limit: int = typer.Option(10, "--limit", help="Number of top offenders to show."),
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
) -> None:
    """Show the directory-aware anti-slop metric (read-only).

    Unlike file-only hygiene, a directory tree counts as ONE entry with its recursive
    byte size — so stray venvs/caches no longer hide from the metric. Never deletes.
    """
    from dadaia_workspace import container

    workspace_root = resolve_workspace_root()
    report = container.build_slop_report(workspace_root)
    if json_output:
        payload = report.to_dict()
        payload["status"] = LifecycleCommandStatus.OK.value
        payload["top_offenders"] = [entry.to_dict() for entry in report.top_offenders(limit)]
        _emit_json(payload)
        return
    typer.echo(
        f"OK entries={report.total_entries} stale={report.stale_count} "
        f"reclaimable_bytes={report.reclaimable_bytes}"
    )
    for entry in report.top_offenders(limit):
        marker = "dir " if entry.is_dir else "file"
        typer.echo(f"  [{entry.kind.value}] {marker} {entry.size_bytes:>12} B  {entry.path}")


@app.command()
def clean(
    apply: bool = typer.Option(
        False,
        "--apply",
        help="Actually reclaim (delete). Default is dry-run preview only.",
    ),
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
) -> None:
    """Directory-aware retention SWEEP (D5) — the guarded deleter.

    Reclaims past-TTL / non-canonical entries from the recognised swept ``.dadaia/`` zones:
    whole directory trees via rmtree (the stray-venv case the file-only cleanup misses) and
    files via unlink. DRY-RUN BY DEFAULT — pass ``--apply`` to actually delete. Never touches
    a live lifecycle run's tmp, an operator-marked-important report, a canonical/durable
    path, anything outside ``.dadaia/``, or a symlink whose target escapes ``.dadaia/``.
    """
    from dadaia_workspace import container

    workspace_root = resolve_workspace_root()
    result = container.build_retention_sweep(workspace_root).sweep(apply=apply)
    if json_output:
        payload = result.to_dict()
        payload["status"] = LifecycleCommandStatus.OK.value
        _emit_json(payload)
        return
    mode = "applied" if result.applied else "dry-run"
    typer.echo(
        f"OK {mode} reclaimed={len(result.reclaimed_paths)} "
        f"reclaimed_bytes={result.reclaimed_bytes} skipped={len(result.skipped)}"
    )
    for rel in result.reclaimed_paths:
        typer.echo(f"  reclaim {rel}")
    for rel, reason in result.skipped:
        typer.echo(f"  skip [{reason.value}] {rel}")


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
    harness: str = typer.Option(
        "fake", "--harness", help="Default Layer-2 harness: fake|codex|pi (claude is Layer-1 only)."
    ),
    model: str | None = typer.Option(
        None,
        "--model",
        help="Default discrete Layer-2 model '<id>:<effort>' (pi/codex only; LAW 2).",
    ),
    step_harness: list[str] | None = typer.Option(
        None,
        "--step-harness",
        help="Per-step harness override 'step=harness' (repeatable); steps are the §4 "
        "model-step labels (intake_grill, conflict_resolution_grill, backlog_author).",
    ),
    step_model: list[str] | None = typer.Option(
        None,
        "--step-model",
        help="Per-step model override 'step=model' (repeatable); model is "
        "'<id>:<effort>' valid for that step's harness (LAW 2).",
    ),
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
) -> None:
    """Run the backlog-definition workflow (§4) as a fragment-driven sequence.

    Python owns step order and the typed gates; each model step's prompt is assembled
    from its fragment bundle + selected dynamic context + output schema + the discrete
    ``(harness, model)``. The §4 Python steps (``subject_bind``, ``existing_backlog_review``,
    ``reconcile_decision``, ``backlog_review_gate``) dispose deterministically via the R1
    registry + classifier; a blocked gate stops the sequence. ``--harness fake`` walks the
    whole sequence; ``claude`` is rejected (LAW 1); an invalid ``--model`` is rejected (LAW 2).
    """
    from dataclasses import replace as _replace

    from dadaia_workspace import container
    from dadaia_workspace.features.backlog.classifier import BoundItem
    from dadaia_workspace.features.lifecycle.workflows.backlog_definition import (
        _SEQUENCE,
        AuthoredItem,
        BacklogDemand,
    )

    workspace_root = resolve_workspace_root()
    default_kind = _resolve_harness(harness)

    # Per-step harness overrides, keyed by the §4 model-step labels.
    valid_labels = {step.label for step in _SEQUENCE if step.fragment_id is not None}
    overrides: dict[str, AgentRuntimeKind] = {}
    harness_by_label: dict[str, str] = {}
    for item in step_harness or []:
        label, sep, kind_str = item.partition("=")
        if not sep:
            raise typer.BadParameter(f"--step-harness expects 'step=harness', got {item!r}")
        clean_label = label.strip()
        if clean_label not in valid_labels:
            raise typer.BadParameter(
                f"unknown backlog-definition step {clean_label!r}; "
                f"valid steps: {', '.join(sorted(valid_labels))}"
            )
        overrides[clean_label] = _resolve_harness(kind_str.strip())
        harness_by_label[clean_label] = kind_str.strip()

    # LAW 2 — resolve the discrete model per runtime kind.
    models: dict[AgentRuntimeKind, HarnessModelOption] = {}
    default_model = _resolve_model(harness, model)
    if default_model is not None:
        models[default_kind] = default_model
    for item in step_model or []:
        label, sep, model_str = item.partition("=")
        if not sep:
            raise typer.BadParameter(f"--step-model expects 'step=model', got {item!r}")
        clean_label = label.strip()
        step_harness_name = harness_by_label.get(clean_label, harness)
        resolved = _resolve_model(step_harness_name, model_str.strip())
        if resolved is not None:
            models[_resolve_harness(step_harness_name)] = resolved

    workflow = container.build_backlog_definition_workflow(
        workspace_root,
        context=context,
        release_id=release_id,
        default_runtime_kind=default_kind,
        models=models,
    )
    sequence = tuple(
        _replace(step, runtime_kind=overrides.get(step.label, step.runtime_kind))
        for step in _SEQUENCE
    )
    # The CLI verb walks the §4 sequence on the chosen harness; absent a structured demand
    # source it threads an empty demand (no proposed intents, an empty authored result) so
    # the Python gates dispose deterministically and the sequence completes on ``fake``.
    demand = BacklogDemand(
        proposed_intents=(),
        existing=(),
        authored=AuthoredItem(
            slug=run_id,
            is_new=True,
            bound=BoundItem(slug=run_id, anchor_changes={}),
        ),
    )
    result = workflow.run(run_id, demand, sequence=sequence)

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
                        "kind": step.kind.value,
                        "fragment_id": step.fragment_id,
                        "accepted": step.accepted,
                        "skipped": step.skipped,
                        "runtime": step.runtime_kind.value if step.runtime_kind else None,
                    }
                    for step in result.steps
                ],
                "blocked": result.blocked.to_dict() if result.blocked else None,
            }
        )
    else:
        trail = " → ".join(
            f"{s.label}:{'skip' if s.skipped else ('ok' if s.accepted else 'BLOCKED')}"
            for s in result.steps
        )
        typer.echo(
            f"{status} backlog-define run={result.run_id} phase={result.final_phase.value} {trail}"
        )
    if not result.completed:
        raise typer.Exit(LifecycleExitCode.BLOCKED)


@release_app.command("define")
def release_define(
    context: str = typer.Option("dadaia-workspace", "--context", help="Context."),
    release_id: str = typer.Option(..., "--release-id", help="Release id."),
    run_id: str = typer.Option("release-define", "--run-id", help="Lifecycle run id."),
    intent: str | None = typer.Option(
        None,
        "--intent",
        help="Explicit operator intent for this release. Never inferred from run id.",
    ),
    backlog: list[str] | None = typer.Option(
        None,
        "--backlog",
        help="Selected backlog slug for release scope. Repeatable.",
    ),
    bug: list[str] | None = typer.Option(
        None,
        "--bug",
        help="Selected bug slug for release scope. Repeatable.",
    ),
    audit: list[str] | None = typer.Option(
        None,
        "--audit",
        help="Selected audit finding/ref for release scope. Repeatable.",
    ),
    harness: str = typer.Option(
        "fake", "--harness", help="Default Layer-2 harness: fake|codex|pi (claude is Layer-1 only)."
    ),
    model: str | None = typer.Option(
        None,
        "--model",
        help="Default discrete Layer-2 model '<id>:<effort>' (pi/codex only; LAW 2).",
    ),
    step_harness: list[str] | None = typer.Option(
        None,
        "--step-harness",
        help="Per-step harness override 'step=harness' (repeatable); steps are the "
        "§6.1 labels (release_scope, spec_create, spec_arch_review, ...).",
    ),
    step_model: list[str] | None = typer.Option(
        None,
        "--step-model",
        help="Per-step model override 'step=model' (repeatable); model is "
        "'<id>:<effort>' valid for that step's harness (LAW 2).",
    ),
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
) -> None:
    """Run the release-definition workflow (§6.1) as a fragment-driven sequence.

    Python owns step order and the typed gates; each model step's prompt is assembled
    from its fragment bundle + selected dynamic context + output schema + the discrete
    ``(harness, model)`` — there is no generic "Run the step" suffix. A REJECTED or
    missing review handoff BLOCKS advancement; the terminal ``definition_commit_gate``
    advances the release to IMPLEMENTATION only when every gate passed.
    """
    from dadaia_workspace import container
    from dadaia_workspace.features.lifecycle.workflows.release_definition import (
        _SEQUENCE,
        ReleaseDefinitionScopeInput,
    )

    workspace_root = resolve_workspace_root()
    default_kind = _resolve_harness(harness)

    # Per-step harness overrides, keyed by the §6.1 step label.
    valid_labels = {step.label for step in _SEQUENCE if step.fragment_id is not None}
    overrides: dict[str, AgentRuntimeKind] = {}
    harness_by_label: dict[str, str] = {}
    for item in step_harness or []:
        label, sep, kind_str = item.partition("=")
        if not sep:
            raise typer.BadParameter(f"--step-harness expects 'step=harness', got {item!r}")
        clean_label = label.strip()
        if clean_label not in valid_labels:
            raise typer.BadParameter(
                f"unknown release-definition step {clean_label!r}; "
                f"valid steps: {', '.join(sorted(valid_labels))}"
            )
        overrides[clean_label] = _resolve_harness(kind_str.strip())
        harness_by_label[clean_label] = kind_str.strip()

    # LAW 2 — resolve the discrete model per runtime kind for the default, and per label
    # for explicit --step-model overrides. Label-specific models are threaded into the
    # request as resolved_model so two steps on the same harness can use different models.
    models: dict[AgentRuntimeKind, HarnessModelOption] = {}
    step_models: dict[str, HarnessModelOption] = {}
    default_model = _resolve_model(harness, model)
    if default_model is not None:
        models[default_kind] = default_model
    for item in step_model or []:
        label, sep, model_str = item.partition("=")
        if not sep:
            raise typer.BadParameter(f"--step-model expects 'step=model', got {item!r}")
        clean_label = label.strip()
        step_harness_name = harness_by_label.get(clean_label, harness)
        resolved = _resolve_model(step_harness_name, model_str.strip())
        if resolved is not None:
            step_models[clean_label] = resolved

    workflow = container.build_release_definition_workflow(
        workspace_root,
        context=context,
        release_id=release_id,
        default_runtime_kind=default_kind,
        models=models,
        step_models=step_models,
        scope_input=ReleaseDefinitionScopeInput(
            intent=intent,
            backlog_slugs=tuple(backlog or ()),
            bug_slugs=tuple(bug or ()),
            audit_refs=tuple(audit or ()),
        ),
    )
    from dataclasses import replace as _replace

    sequence = tuple(
        _replace(step, runtime_kind=overrides.get(step.label, step.runtime_kind))
        for step in _SEQUENCE
    )
    result = workflow.run(run_id, sequence)

    # Producer post-step (SPEC §3.2): on a COMPLETED definition, parse the release SPEC's
    # **Consumes:** line, bind the declared slugs' anchors through the R1 registry, and write
    # the consumed_backlog ledger via BacklogRemovalLifecycle.consume — symmetric with the
    # close verb's _apply_closure_removal. `release_define` has no post_step seam (it calls
    # workflow.run directly), so the guard is inlined here with the same try/except shape: it
    # runs ONLY when the definition completed, and a bind error surfaces as post_step_error
    # (never a silent skip) without corrupting the already-accepted definition result.
    post_step_result: dict[str, Any] | None = None
    post_step_error: str | None = None
    if result.completed:
        try:
            post_step_result = _apply_release_consume(
                workspace_root, context=context, release_id=release_id
            )
        except Exception as exc:  # noqa: BLE001 — surface, never swallow; do not corrupt the run.
            post_step_error = f"{type(exc).__name__}: {exc}"

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
                        "is_gate": step.is_gate,
                        "fragment_id": step.fragment_id,
                        "accepted": step.accepted,
                        "runtime": step.runtime_kind.value if step.runtime_kind else None,
                    }
                    for step in result.steps
                ],
                "blocked": result.blocked.to_dict() if result.blocked else None,
                "post_step": post_step_result,
                "post_step_error": post_step_error,
            }
        )
    else:
        trail = " → ".join(f"{s.label}:{'ok' if s.accepted else 'BLOCKED'}" for s in result.steps)
        typer.echo(
            f"{status} release-define run={result.run_id} phase={result.final_phase.value} {trail}"
        )
        if post_step_result is not None:
            typer.echo(f"  post_step: {post_step_result}")
        if post_step_error is not None:
            typer.echo(f"  post_step ERROR: {post_step_error}")
    if not result.completed:
        raise typer.Exit(LifecycleExitCode.BLOCKED)


@bug_app.command("report")
def bug_report(
    context: str = typer.Option("dadaia-workspace", "--context", help="Context."),
    release_id: str = typer.Option(..., "--release-id", help="Release id."),
    run_id: str = typer.Option("bug-report", "--run-id", help="Lifecycle run id."),
    summary: str = typer.Option(..., "--summary", help="Short reported symptom."),
    details: str | None = typer.Option(None, "--details", help="Additional bug details."),
    repro: str | None = typer.Option(None, "--repro", help="Reproduction command or steps."),
    expected: str | None = typer.Option(None, "--expected", help="Expected behavior."),
    actual: str | None = typer.Option(None, "--actual", help="Actual behavior."),
    severity: str | None = typer.Option(None, "--severity", help="Operator severity hint."),
    harness: str = typer.Option(
        "fake", "--harness", help="Default Layer-2 harness: fake|codex|pi (claude is Layer-1 only)."
    ),
    model: str | None = typer.Option(
        None,
        "--model",
        help="Default discrete Layer-2 model '<id>:<effort>' (pi/codex only; LAW 2).",
    ),
    step_harness: list[str] | None = typer.Option(
        None,
        "--step-harness",
        help="Per-step harness override 'step=harness' (repeatable); steps are the "
        "bug_report model-step labels (bug_intake, dedupe, bug_write).",
    ),
    step_model: list[str] | None = typer.Option(
        None,
        "--step-model",
        help="Per-step model override 'step=model' (repeatable); model is "
        "'<id>:<effort>' valid for that step's harness (LAW 2).",
    ),
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
) -> None:
    """Run the bug-report workflow as intake -> dedupe -> bug_write -> gate."""
    from dataclasses import replace as _replace

    from dadaia_workspace import container
    from dadaia_workspace.features.lifecycle.workflows.bug_report import (
        _SEQUENCE,
        BugReportInput,
    )

    workspace_root = resolve_workspace_root()
    default_kind = _resolve_harness(harness)

    valid_labels = {step.label for step in _SEQUENCE if step.fragment_id is not None}
    overrides: dict[str, AgentRuntimeKind] = {}
    harness_by_label: dict[str, str] = {}
    for item in step_harness or []:
        label, sep, kind_str = item.partition("=")
        if not sep:
            raise typer.BadParameter(f"--step-harness expects 'step=harness', got {item!r}")
        clean_label = label.strip()
        if clean_label not in valid_labels:
            raise typer.BadParameter(
                f"unknown bug-report step {clean_label!r}; "
                f"valid steps: {', '.join(sorted(valid_labels))}"
            )
        overrides[clean_label] = _resolve_harness(kind_str.strip())
        harness_by_label[clean_label] = kind_str.strip()

    models: dict[AgentRuntimeKind, HarnessModelOption] = {}
    default_model = _resolve_model(harness, model)
    if default_model is not None:
        models[default_kind] = default_model
    for item in step_model or []:
        label, sep, model_str = item.partition("=")
        if not sep:
            raise typer.BadParameter(f"--step-model expects 'step=model', got {item!r}")
        clean_label = label.strip()
        step_harness_name = harness_by_label.get(clean_label, harness)
        resolved = _resolve_model(step_harness_name, model_str.strip())
        if resolved is not None:
            models[_resolve_harness(step_harness_name)] = resolved

    workflow = container.build_bug_report_workflow(
        workspace_root,
        context=context,
        release_id=release_id,
        default_runtime_kind=default_kind,
        models=models,
        bug_input=BugReportInput(
            summary=summary,
            details=details,
            repro=repro,
            expected=expected,
            actual=actual,
            severity=severity,
        ),
    )
    sequence = tuple(
        _replace(step, runtime_kind=overrides.get(step.label, step.runtime_kind))
        for step in _SEQUENCE
    )
    result = workflow.run(run_id, sequence=sequence)

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
                        "is_gate": step.is_gate,
                        "fragment_id": step.fragment_id,
                        "accepted": step.accepted,
                        "runtime": step.runtime_kind.value if step.runtime_kind else None,
                    }
                    for step in result.steps
                ],
                "blocked": result.blocked.to_dict() if result.blocked else None,
            }
        )
    else:
        trail = " -> ".join(f"{s.label}:{'ok' if s.accepted else 'BLOCKED'}" for s in result.steps)
        typer.echo(
            f"{status} bug-report run={result.run_id} phase={result.final_phase.value} {trail}"
        )
    if not result.completed:
        raise typer.Exit(LifecycleExitCode.BLOCKED)


def _apply_release_consume(
    workspace_root: Path,
    *,
    context: str,
    release_id: str,
) -> dict[str, Any]:
    """Write the consumed_backlog ledger from the release SPEC's ``**Consumes:**`` line.

    Resolves ``<specs_dir>/releases/<release_id>/SPEC.md`` (container seam, no cwd), parses
    its ``**Consumes:**`` slugs, binds them to the union shipped-anchor set through the R1
    registry, and calls ``BacklogRemovalLifecycle.consume`` to write the ledger under
    ``specs/_archive/<release_id>/``. An absent/empty ``**Consumes:**`` line no-ops cleanly
    (empty slug list ⇒ empty shipped set ⇒ a ledger with no entries). A declared slug that
    does not resolve raises ``ConsumesBindError``, surfaced by the caller as
    ``post_step_error`` — never a silent skip.
    """
    from dadaia_workspace import container
    from dadaia_workspace.features.backlog.consumes import parse_consumes_line, shipped_anchors_for

    spec_path = container.build_release_spec_path(
        workspace_root, context=context, release_id=release_id
    )
    spec_text = spec_path.read_text(encoding="utf-8") if spec_path.exists() else ""
    slugs = parse_consumes_line(spec_text)

    lifecycle = container.build_backlog_removal_lifecycle(workspace_root, context=context)
    shipped = shipped_anchors_for(
        slugs, backlog_dir=lifecycle.backlog_dir, registry=lifecycle.registry
    )
    ledger_path = lifecycle.consume(release_id=release_id, shipped_anchors=shipped)
    try:
        ledger_rel = ledger_path.relative_to(workspace_root).as_posix()
    except ValueError:
        ledger_rel = str(ledger_path)
    return {
        "consumed_slugs": list(slugs),
        "shipped_anchors": sorted(shipped),
        "ledger": ledger_rel,
    }


@app.command()
def implement(
    context: str = typer.Option("dadaia-workspace", "--context", help="Context."),
    release_id: str = typer.Option(..., "--release-id", help="Release id."),
    run_id: str = typer.Option("implement", "--run-id", help="Lifecycle run id."),
    harness: str = typer.Option(
        "fake", "--harness", help="Layer-2 harness: fake|codex|pi (claude is Layer-1 only)."
    ),
    model: str | None = typer.Option(
        None,
        "--model",
        help="Discrete Layer-2 model '<id>:<effort>' (pi/codex only; LAW 2).",
    ),
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
        model=model,
        json_output=json_output,
    )


def _resolve_harness(harness: str) -> AgentRuntimeKind:
    key = harness.lower()
    if key in _LAYER1_ONLY_HARNESSES:
        raise typer.BadParameter(
            f"'{harness}' is not a Layer-2 workflow harness (LAW 1). Claude Code is a "
            "Layer-1 harness; Layer-2 workers are pi or codex. Use 'pi' or 'codex' here, "
            "and run Claude Code directly at Layer 1."
        )
    try:
        return _HARNESS_KINDS[key]
    except KeyError as exc:
        choices = ", ".join(sorted(_HARNESS_KINDS))
        raise typer.BadParameter(f"unknown harness '{harness}'; choose one of: {choices}") from exc


def _resolve_model(harness: str, model: str | None) -> HarnessModelOption | None:
    """Validate a ``(harness, model)`` selection against the discrete catalog (LAW 2).

    Returns ``None`` when no model is requested (adapter keeps its default), or when the
    harness has no catalog (``fake``). An invalid pair raises a ``BadParameter`` whose
    message lists the harness's valid options.
    """
    if model is None:
        return None
    key = _HARNESS_CATALOG_KEY.get(harness.lower())
    if key is None:
        raise typer.BadParameter(
            f"harness '{harness}' takes no --model; only pi and codex select a discrete model"
        )
    try:
        return validate_harness_model(key, model)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc


def _looks_like_raw_model(value: str) -> bool:
    """Return whether *value* looks like a raw ``<id>:<effort>`` discrete model string.

    D-3: ``--step-model`` accepts a registry **profile id** only. A raw model string (it
    contains a ``:`` separating id and effort) must be rejected with an actionable message
    rather than silently accepted.
    """
    return ":" in value


def _parse_step_profile_overrides(step_model: list[str] | None) -> tuple[object, ...]:
    """Parse ``--step-model 'step=profile-id'`` items into resolver ``StepOverride``s (D-3).

    Profile ids ONLY: a raw ``<id>:<effort>`` model string, or an id that is not a built-in
    profile, is rejected here with an actionable ``BadParameter`` (the resolver re-validates
    harness match / deprecation against the catalog). Returns a tuple of ``StepOverride``.
    """
    from dadaia_workspace.features.lifecycle import model_profiles
    from dadaia_workspace.features.lifecycle.model_profiles import UnknownProfileError
    from dadaia_workspace.features.lifecycle.policy_resolver import StepOverride

    overrides: list[object] = []
    for item in step_model or []:
        label, sep, profile_id = item.partition("=")
        if not sep:
            raise typer.BadParameter(f"--step-model expects 'step=profile-id', got {item!r}")
        clean_label = label.strip()
        clean_profile = profile_id.strip()
        if _looks_like_raw_model(clean_profile):
            valid = ", ".join(p.id for p in model_profiles.list_profiles())
            raise typer.BadParameter(
                f"--step-model takes a profile id, not a raw model string {clean_profile!r} "
                f"(D-3). Valid profiles: {valid}"
            )
        try:
            model_profiles.resolve(clean_profile)
        except UnknownProfileError as exc:
            raise typer.BadParameter(str(exc)) from exc
        overrides.append(StepOverride(step=clean_label, profile_id=clean_profile))
    return tuple(overrides)


def _phase_step_prompt(
    label: str, release_id: str, context: str, target_phase: LifecyclePhase
) -> str:
    """Step-kind-aware worker instruction for a single-step lifecycle verb (v0.1.32 D-2/L1).

    The CLI single-step verbs are the third worker-prompt surface (after
    ``build_fragment_suffix`` and ``pipeline._generic_prompt``). A review-phase verb
    (qa/security/code) is verdict-gated and must emit a verdict; a create verb
    (implement/close/backlog|release define) produces an artifact and must NOT self-verdict
    — its verdict is ignored by the review-only gate, and instructing it to self-verdict is
    the Drift-1 incoherence this release eliminates.
    """
    if is_review_phase(target_phase):
        output_instruction = (
            "Emit a handoff whose structured_output.verdict is APPROVED or REJECTED, with an "
            "artifact_ref pointing at the handoff document."
        )
    else:
        output_instruction = (
            "Emit a handoff with an artifact_ref pointing at the handoff document (the "
            "artifact you produced). Do not self-verdict — create steps are not verdict-gated."
        )
    return (
        f"Run the {label} step for release {release_id} in context {context}. {output_instruction}"
    )


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
    model: str | None = None,
    post_step: Callable[[PhaseWorkflowResult], dict[str, Any] | None] | None = None,
) -> None:
    """Run one bounded lifecycle step through the engine on a selectable harness.

    Shared by every single-step lifecycle verb (backlog/release define, implement,
    review qa|security|code, close). The harness is chosen per invocation (LAW 1:
    pi/codex/fake only — ``claude`` is rejected); ``--model`` selects the discrete
    Layer-2 model (LAW 2). The worker must emit an APPROVED handoff with an
    artifact_ref to advance the phase.
    """
    from dadaia_workspace import container

    workspace_root = resolve_workspace_root()
    kind = _resolve_harness(harness)
    resolved_model = _resolve_model(harness, model)
    workflow = container.build_lifecycle_phase_workflow(
        workspace_root, runtime_kind=kind, model=resolved_model
    )
    scope = PromptScope(
        role=role,
        context=context,
        release_id=release_id,
        task_id=run_id,
        prompt=_phase_step_prompt(label, release_id, context, target_phase),
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
    # Post-step action (e.g. closure-time backlog removal). Runs ONLY when the phase step
    # was accepted, so a blocked step never triggers side effects. Guarded so a post-step
    # error surfaces clearly without corrupting the already-accepted phase result.
    post_step_result: dict[str, Any] | None = None
    post_step_error: str | None = None
    if result.accepted and post_step is not None:
        try:
            post_step_result = post_step(result)
        except Exception as exc:  # noqa: BLE001 — surface, never swallow; do not corrupt the step.
            post_step_error = f"{type(exc).__name__}: {exc}"
    if json_output:
        _emit_json(
            {
                "status": status,
                "run_id": result.run_id,
                "accepted": result.accepted,
                "phase": result.phase.value,
                "runtime": result.runtime_kind.value,
                "blocked": result.blocked.to_dict() if result.blocked else None,
                "post_step": post_step_result,
                "post_step_error": post_step_error,
            }
        )
    else:
        typer.echo(
            f"{status} {label} run={result.run_id} "
            f"harness={result.runtime_kind.value} phase={result.phase.value}"
        )
        if post_step_result is not None:
            typer.echo(f"  post_step: {post_step_result}")
        if post_step_error is not None:
            typer.echo(f"  post_step ERROR: {post_step_error}")
    if not result.accepted:
        raise typer.Exit(LifecycleExitCode.BLOCKED)


@review_app.command("qa")
def review_qa(
    context: str = typer.Option("dadaia-workspace", "--context", help="Review context."),
    release_id: str = typer.Option(..., "--release-id", help="Release id."),
    run_id: str = typer.Option("review-qa", "--run-id", help="Lifecycle run id."),
    harness: str = typer.Option(
        "fake", "--harness", help="Layer-2 harness: fake|codex|pi (claude is Layer-1 only)."
    ),
    model: str | None = typer.Option(
        None,
        "--model",
        help="Discrete Layer-2 model '<id>:<effort>' (pi/codex only; LAW 2).",
    ),
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
        model=model,
        json_output=json_output,
    )


@review_app.command("security")
def review_security(
    context: str = typer.Option("dadaia-workspace", "--context", help="Review context."),
    release_id: str = typer.Option(..., "--release-id", help="Release id."),
    run_id: str = typer.Option("review-security", "--run-id", help="Lifecycle run id."),
    harness: str = typer.Option(
        "fake", "--harness", help="Layer-2 harness: fake|codex|pi (claude is Layer-1 only)."
    ),
    model: str | None = typer.Option(
        None,
        "--model",
        help="Discrete Layer-2 model '<id>:<effort>' (pi/codex only; LAW 2).",
    ),
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
        model=model,
        json_output=json_output,
    )


@review_app.command("code")
def review_code(
    context: str = typer.Option("dadaia-workspace", "--context", help="Review context."),
    release_id: str = typer.Option(..., "--release-id", help="Release id."),
    run_id: str = typer.Option("review-code", "--run-id", help="Lifecycle run id."),
    harness: str = typer.Option(
        "fake", "--harness", help="Layer-2 harness: fake|codex|pi (claude is Layer-1 only)."
    ),
    model: str | None = typer.Option(
        None,
        "--model",
        help="Discrete Layer-2 model '<id>:<effort>' (pi/codex only; LAW 2).",
    ),
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
        model=model,
        json_output=json_output,
    )


@app.command()
def close(
    context: str = typer.Option("dadaia-workspace", "--context", help="Context."),
    release_id: str = typer.Option(..., "--release-id", help="Release id."),
    run_id: str = typer.Option("close", "--run-id", help="Lifecycle run id."),
    harness: str = typer.Option(
        "fake", "--harness", help="Layer-2 harness: fake|codex|pi (claude is Layer-1 only)."
    ),
    model: str | None = typer.Option(
        None,
        "--model",
        help="Discrete Layer-2 model '<id>:<effort>' (pi/codex only; LAW 2).",
    ),
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
) -> None:
    """Run the release-closure step on a selectable harness.

    On a successful closure phase step, mechanically applies residual-aware
    backlog removal over the consumed-ledger (SPEC §3.6): items whose intents
    fully shipped are archived-then-removed; partially-shipped items are
    rewritten to their residual. If no consumed ledger exists, removal is a
    no-op (``remove_at_closure`` reads an empty ledger). The removal runs as a
    guarded post-step so a removal error surfaces clearly without corrupting the
    closure result.
    """

    def _apply_closure_removal(_result: PhaseWorkflowResult) -> dict[str, Any]:
        from dadaia_workspace import container

        workspace_root = resolve_workspace_root()
        lifecycle = container.build_backlog_removal_lifecycle(workspace_root, context=context)
        removal = lifecycle.remove(release_id=release_id)
        return {
            "removed": [
                a.slug for a in removal.actions if a.action.value == "archived_and_removed"
            ],
            "rewritten": [a.slug for a in removal.actions if a.action.value == "rewritten"],
            "unchanged": [a.slug for a in removal.actions if a.action.value == "unchanged"],
        }

    _run_phase_step(
        label="close",
        role="product-engineer",
        from_phase=LifecyclePhase.CODE_REVIEW,
        target_phase=LifecyclePhase.CLOSURE,
        context=context,
        release_id=release_id,
        run_id=run_id,
        harness=harness,
        model=model,
        json_output=json_output,
        post_step=_apply_closure_removal,
    )


@app.command()
def pipeline(
    context: str = typer.Option("dadaia-workspace", "--context", help="Context."),
    release_id: str = typer.Option(..., "--release-id", help="Release id."),
    run_id: str = typer.Option("pipeline", "--run-id", help="Lifecycle run id."),
    harness: str = typer.Option("fake", "--harness", help="Default harness for all steps."),
    model: str | None = typer.Option(
        None,
        "--model",
        help="Default discrete Layer-2 model '<id>:<effort>' for the default harness (LAW 2).",
    ),
    step_harness: list[str] | None = typer.Option(
        None,
        "--step-harness",
        help="Per-step override 'label=harness' (repeatable); labels: "
        "implement, review_qa, review_security, review_code.",
    ),
    step_model: list[str] | None = typer.Option(
        None,
        "--step-model",
        help="Per-step model override 'label=profile-id' (repeatable). Profile ids ONLY "
        "(D-3) — a raw '<id>:<effort>' string is rejected; see 'lifecycle workflow "
        "profiles list'.",
    ),
    show_policy: bool = typer.Option(
        False,
        "--show-policy",
        help="Print the resolved per-step model policy and exit without running.",
    ),
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
) -> None:
    """Run the multi-step release pipeline (implement→qa→security→code) with per-step harness mixing.

    The per-step model is governed: ``--step-model label=profile-id`` selects a built-in
    model profile (D-3), resolved through the shared ``WorkflowExecutionPolicyResolver``
    (CLI > overlay > library default). The resolved policy is snapshotted onto the run
    before the first step (LAW 7). ``--show-policy`` prints the resolved policy and exits.
    """
    from dataclasses import replace

    from dadaia_workspace import container
    from dadaia_workspace.features.lifecycle.pipeline import (
        apply_resolved_policy,
        implementation_ladder,
    )
    from dadaia_workspace.features.lifecycle.policy_resolver import (
        PolicyResolutionError,
        StepHarnessOverride,
        StepOverride,
    )

    workspace_root = resolve_workspace_root()
    default_kind = _resolve_harness(harness)
    _ = model  # legacy discrete --model is superseded by profile-id --step-model (D-3).

    # Parse --step-harness into label→(kind, name). The kind drives the base ladder's
    # dry-run sentinel (fake vs real); the name is threaded into the governed resolver.
    step_harness_kinds: dict[str, AgentRuntimeKind] = {}
    step_harness_names: dict[str, str] = {}
    for item in step_harness or []:
        label, sep, kind_str = item.partition("=")
        if not sep:
            raise typer.BadParameter(f"--step-harness expects 'label=harness', got {item!r}")
        clean_label = label.strip()
        clean_name = kind_str.strip().lower()
        step_harness_kinds[clean_label] = _resolve_harness(clean_name)
        step_harness_names[clean_label] = clean_name

    # D-1 (T-29-A-07): thread harness inputs INTO the shared resolver so the governed
    # snapshot — not just the execution adapter — reflects the chosen harness. ``fake`` is
    # the dry-run sentinel: it is never a *resolved* governed harness, so it is NOT threaded
    # into resolve (the base ladder built on FAKE is preserved by apply_resolved_policy).
    default_harness_name = harness.lower()
    resolve_default_harness = None if default_harness_name == "fake" else default_harness_name
    typed_step_harness: tuple[StepHarnessOverride, ...] = tuple(
        StepHarnessOverride(step=label, harness=name)
        for label, name in step_harness_names.items()
        if name != "fake"
    )

    # D-3: --step-model takes profile ids only; the shared resolver applies precedence and
    # validates each override against the catalog (step id + profile id + harness match).
    cli_overrides = _parse_step_profile_overrides(step_model)
    typed_overrides: tuple[StepOverride, ...] = tuple(
        ov for ov in cli_overrides if isinstance(ov, StepOverride)
    )
    resolver = container.build_workflow_policy_resolver(workspace_root, context=context)
    try:
        snapshot = resolver.resolve(
            "implementation",
            context="default",
            cli_overrides=typed_overrides,
            default_harness=resolve_default_harness,
            step_harness_overrides=typed_step_harness,
        )
    except PolicyResolutionError as exc:
        raise typer.BadParameter(str(exc)) from exc

    if show_policy:
        _emit_json(_policy_snapshot_payload(snapshot)) if json_output else _print_policy(snapshot)
        return

    # D-2: apply_resolved_policy is the SINGLE author of runtime_kind — it sets each step's
    # kind from the resolved harness, preserving FAKE for a fake dry-run. The base ladder
    # carries only the fake-vs-real selection (so `--harness fake` drives the fake adapter
    # while the snapshot still records the governed harness); there is no separate
    # post-resolve runtime_kind swap.
    base = tuple(
        replace(step, runtime_kind=step_harness_kinds.get(step.label, default_kind))
        for step in implementation_ladder(default_kind)
    )
    steps = apply_resolved_policy(base, snapshot)

    pipe = container.build_lifecycle_pipeline(
        workspace_root,
        context=context,
        release_id=release_id,
        policy_snapshot=snapshot,
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
                "workflow_policy": _policy_snapshot_payload(snapshot),
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


def _policy_snapshot_payload(snapshot: object) -> dict[str, Any]:
    """Project a ``WorkflowPolicySnapshot`` to a JSON-serializable dict for CLI output."""
    from dadaia_workspace.core.models.workflow_execution import WorkflowPolicySnapshot

    assert isinstance(snapshot, WorkflowPolicySnapshot)
    return snapshot.to_dict()


def _print_policy(snapshot: object) -> None:
    """Print a resolved policy snapshot as a human-readable step table."""
    from dadaia_workspace.core.models.workflow_execution import WorkflowPolicySnapshot

    assert isinstance(snapshot, WorkflowPolicySnapshot)
    typer.echo(f"OK workflow={snapshot.workflow_id} policy={snapshot.policy_id}")
    for entry in snapshot.steps:
        typer.echo(
            f"  {entry.step}: profile={entry.model_profile} harness={entry.harness} "
            f"model={entry.model} reasoning={entry.reasoning} source={entry.source.value}"
        )


workflow_policy_app = typer.Typer(help="Workflow policy inspection.", no_args_is_help=True)
workflow_profiles_app = typer.Typer(help="Model-profile inspection.", no_args_is_help=True)


@workflow_policy_app.command("show")
def workflow_policy_show(
    workflow: str = typer.Argument("implementation", help="Workflow id to resolve."),
    context: str = typer.Option("dadaia-workspace", "--context", help="Context."),
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
) -> None:
    """Show the resolved model policy for a workflow (read-only).

    Resolves through the shared ``WorkflowExecutionPolicyResolver`` (overlay > library
    default) with no CLI overrides — what a run would use today before any ``--step-model``.
    """
    from dadaia_workspace import container
    from dadaia_workspace.features.lifecycle.policy_resolver import PolicyResolutionError

    workspace_root = resolve_workspace_root()
    resolver = container.build_workflow_policy_resolver(workspace_root, context=context)
    try:
        snapshot = resolver.resolve(workflow, context="default")
    except PolicyResolutionError as exc:
        raise typer.BadParameter(str(exc)) from exc
    if json_output:
        _emit_json(_policy_snapshot_payload(snapshot))
    else:
        _print_policy(snapshot)


@workflow_profiles_app.command("list")
def workflow_profiles_list(
    harness: str | None = typer.Option(None, "--harness", help="Filter to a harness (codex|pi)."),
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
) -> None:
    """List the built-in model profiles (read-only) — the valid ``--step-model`` ids (D-3)."""
    from dadaia_workspace.features.lifecycle import model_profiles

    profiles = model_profiles.profiles_for(harness) if harness else model_profiles.list_profiles()
    if json_output:
        _emit_json({"profiles": [p.to_dict() for p in profiles]})
        return
    for profile in profiles:
        flag = " [deprecated]" if profile.deprecated else ""
        typer.echo(
            f"  {profile.id}: harness={profile.harness} model={profile.model_id}:{profile.effort} "
            f"— {profile.purpose}{flag}"
        )


@workflow_app.command("doctor")
def workflow_doctor(
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
) -> None:
    """Run the workflow-model-policy governance doctor (WMP-* invariants, AC-10).

    Checks the governed catalog + built-in profile registry + persisted overlay for:
    workflow/step id uniqueness, default-profile resolution + harness match, fragment +
    output-schema resolution, overlay override validity, and any ``claude``/``opencode``
    Layer-2 residue. An invalid overlay state file is reported as an actionable error and
    never crashes. Exit 1 if any ERROR finding is present.
    """
    from dadaia_workspace.features.lifecycle.policy_doctor import (
        Severity,
        run_policy_doctor,
    )

    workspace_root = resolve_workspace_root()
    findings = run_policy_doctor(workspace_root=workspace_root)
    if json_output:
        _emit_json({"findings": [f.to_dict() for f in findings]})
    else:
        if not findings:
            typer.echo("[ok] workflow-model-policy (no governance issues)")
        for finding in findings:
            typer.echo(f"[{finding.severity.value}] {finding.code.value}: {finding.message}")
    if any(f.severity is Severity.ERROR for f in findings):
        raise typer.Exit(LifecycleExitCode.INTERNAL_ERROR)


@handoffs_app.command("doctor")
def handoffs_doctor(
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
) -> None:
    """Reconcile the workflow-step handoff ledger against on-disk payloads (A26).

    Fails (exit 3) on any orphan / malformed / stale / undeclared / unconsumed-required
    workflow-step payload; exit 0 when the ledger and the data plane are coherent.
    """
    from dadaia_workspace import container

    workspace_root = resolve_workspace_root()
    report = container.build_workflow_handoff_doctor(workspace_root).run()
    if json_output:
        _emit_json({"status": "ok" if report.ok else "blocked", **report.to_dict()})
    else:
        if report.ok:
            typer.echo("OK workflow-step handoff ledger coherent")
        else:
            for finding in report.findings:
                typer.echo(f"[{finding.kind.value}] {finding.ref}: {finding.message}")
    if not report.ok:
        raise typer.Exit(LifecycleExitCode.BLOCKED)


workflow_app.add_typer(workflow_policy_app, name="policy")
workflow_app.add_typer(workflow_profiles_app, name="profiles")

app.add_typer(hygiene_app, name="hygiene")
app.add_typer(handoffs_app, name="handoffs")
app.add_typer(backlog_app, name="backlog")
app.add_typer(release_app, name="release")
app.add_typer(bug_app, name="bug")
app.add_typer(review_app, name="review")
app.add_typer(workflow_app, name="workflow")
