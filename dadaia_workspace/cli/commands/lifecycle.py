"""Lifecycle command group."""

from __future__ import annotations

import json
from collections.abc import Callable
from enum import IntEnum
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol

import typer

from dadaia_workspace.core.models.lifecycle import (
    AgentRuntimeKind,
    BlockedState,
    GateEvidenceKind,
    LifecyclePhase,
)
from dadaia_workspace.core.models.workflow_execution import WorkflowPolicySnapshot
from dadaia_workspace.core.protocols.runtime_files import RuntimeFileRef
from dadaia_workspace.core.session_env import entry_harness
from dadaia_workspace.core.workspace_resolver import resolve_workspace_root
from dadaia_workspace.features.lifecycle.hygiene import HygieneCleanupResult
from dadaia_workspace.features.lifecycle.personas.loader import resolve_persona_for_role
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

if TYPE_CHECKING:
    from dadaia_workspace.core.protocols.agent_runtime import AgentRuntimePort
    from dadaia_workspace.features.lifecycle.pipeline import (
        ImplementReviewLoopResult,
        LifecyclePipeline,
        RuntimeFactory,
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
        "auto",
        "--harness",
        help="Default Layer-2 harness: auto (entry session) | fake | codex | pi (claude is Layer-1 only).",
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
        help="Per-step model override 'step=profile-id' (repeatable). Profile ids ONLY "
        "(D-3) — a raw '<id>:<effort>' string is rejected; see 'lifecycle workflow "
        "profiles list'.",
    ),
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
) -> None:
    """Run the backlog-definition workflow (§4) as a fragment-driven sequence.

    Python owns step order and the typed gates; each model step's prompt is assembled
    from its fragment bundle + selected dynamic context + output schema + the discrete
    ``(harness, model)``. The §4 Python steps (``subject_bind``, ``existing_backlog_review``,
    ``reconcile_decision``, ``backlog_review_gate``) dispose deterministically via the R1
    registry + classifier; a blocked gate stops the sequence. ``--harness fake`` walks the
    whole sequence; ``claude`` is rejected (LAW 1); the per-step model is profile-ids-only
    via ``--step-model`` (D-3) — the legacy ``--model`` flag was removed in v0.1.57 (FR6).
    """
    harness = _resolve_default_harness(harness)
    from dataclasses import replace as _replace

    from dadaia_workspace import container
    from dadaia_workspace.features.backlog.classifier import BoundItem
    from dadaia_workspace.features.lifecycle.pipeline import apply_resolved_policy
    from dadaia_workspace.features.lifecycle.workflows.backlog_definition import (
        _SEQUENCE,
        AuthoredItem,
        BacklogDemand,
    )

    workspace_root = resolve_workspace_root()
    default_kind = _resolve_harness(harness)

    # Per-step harness overrides, keyed by the §4 model-step labels.
    valid_labels = {step.label for step in _SEQUENCE if step.fragment_id is not None}
    step_harness_kinds, step_harness_names = _parse_step_harness_overrides(
        step_harness, valid_labels=valid_labels, verb="backlog-definition"
    )

    # FR1: resolve the frozen policy snapshot through the shared resolver; seed each base
    # step's runtime_kind (FAKE for a fake run) BEFORE applying (R-3) so apply_resolved_policy
    # — the sole runtime_kind author — preserves FAKE while recording the governed harness.
    snapshot = _resolve_workflow_snapshot(
        workspace_root,
        workflow_id="backlog_definition",
        context=context,
        harness=harness,
        step_model=step_model,
        step_harness_names=step_harness_names,
    )
    base = tuple(
        _replace(step, runtime_kind=step_harness_kinds.get(step.label, default_kind))
        for step in _SEQUENCE
    )
    sequence = apply_resolved_policy(base, snapshot)

    workflow = container.build_backlog_definition_workflow(
        workspace_root,
        context=context,
        release_id=release_id,
        default_runtime_kind=default_kind,
        policy_snapshot=snapshot,
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
    harness: str = typer.Option(
        "auto",
        "--harness",
        help="Default Layer-2 harness: auto (entry session) | fake | codex | pi (claude is Layer-1 only).",
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
        help="Per-step model override 'step=profile-id' (repeatable). Profile ids ONLY "
        "(D-3) — a raw '<id>:<effort>' string is rejected; see 'lifecycle workflow "
        "profiles list'.",
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
    harness = _resolve_default_harness(harness)
    from dataclasses import replace as _replace

    from dadaia_workspace import container
    from dadaia_workspace.features.lifecycle.pipeline import apply_resolved_policy
    from dadaia_workspace.features.lifecycle.workflows.release_definition import _SEQUENCE

    workspace_root = resolve_workspace_root()
    default_kind = _resolve_harness(harness)

    # Per-step harness overrides, keyed by the §6.1 step label.
    valid_labels = {step.label for step in _SEQUENCE if step.fragment_id is not None}
    step_harness_kinds, step_harness_names = _parse_step_harness_overrides(
        step_harness, valid_labels=valid_labels, verb="release-definition"
    )

    # FR1: resolve the frozen policy snapshot through the shared resolver; seed each base
    # step's runtime_kind (FAKE for a fake run) BEFORE applying (R-3) so apply_resolved_policy
    # — the sole runtime_kind author — preserves FAKE while recording the governed harness.
    snapshot = _resolve_workflow_snapshot(
        workspace_root,
        workflow_id="release_definition",
        context=context,
        harness=harness,
        step_model=step_model,
        step_harness_names=step_harness_names,
    )
    base = tuple(
        _replace(step, runtime_kind=step_harness_kinds.get(step.label, default_kind))
        for step in _SEQUENCE
    )
    sequence = apply_resolved_policy(base, snapshot)

    workflow = container.build_release_definition_workflow(
        workspace_root,
        context=context,
        release_id=release_id,
        default_runtime_kind=default_kind,
        policy_snapshot=snapshot,
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
        "auto",
        "--harness",
        help="Layer-2 harness: auto (entry session) | fake | codex | pi (claude is Layer-1 only).",
    ),
    step_model: list[str] | None = typer.Option(
        None,
        "--step-model",
        help="Per-step model override 'implement=profile-id' (repeatable). Profile ids "
        "ONLY (D-3); see 'lifecycle workflow profiles list'.",
    ),
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
) -> None:
    """Run the implementation step on a selectable harness."""
    harness = _resolve_default_harness(harness)
    _run_phase_step(
        label="implement",
        role="software-engineer",
        from_phase=LifecyclePhase.IMPLEMENTATION,
        target_phase=LifecyclePhase.QA_REVIEW,
        context=context,
        release_id=release_id,
        run_id=run_id,
        harness=harness,
        workflow_id="implementation",
        catalog_step_label="implement",
        step_model=step_model,
        json_output=json_output,
    )


def _resolve_default_harness(harness: str) -> str:
    """Resolve the ``auto`` default sentinel to a concrete Layer-2 harness name (FR3).

    The single shim behind every ``--harness`` option (12 sites, default ``"auto"``):
    an explicit value passes through unchanged; ``auto`` resolves to
    :func:`~dadaia_workspace.core.session_env.entry_harness` (``DADAIA_ENTRY_HARNESS``
    pin > ``CODEX_SESSION_ID`` ⇒ codex) or the previous default ``"fake"`` when no entry
    signal is present. Auto-defaulting a REAL worker (codex/pi) is never silent: the
    loud echo prints BEFORE any spawn, on **stderr** so ``--json`` stdout stays pure.
    Resolving to ``fake`` (or an explicit value) prints nothing — current behavior
    preserved. Kind validation (incl. the LAW-1 ``claude`` rejection) stays in
    :func:`_resolve_harness`, which each verb calls on the returned name.
    """
    if harness.lower() != "auto":
        return harness
    resolved = entry_harness() or "fake"
    if resolved != "fake":
        typer.echo(
            f"[harness] auto-default: {resolved} (from entry session; pass --harness to override)",
            err=True,
        )
    return resolved


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


def _parse_step_harness_overrides(
    step_harness: list[str] | None,
    *,
    valid_labels: set[str],
    verb: str,
) -> tuple[dict[str, AgentRuntimeKind], dict[str, str]]:
    """Parse ``--step-harness 'label=harness'`` items into ``(kinds, names)`` maps.

    ``kinds`` drives the base-sequence seeding (fake-vs-real sentinel); ``names`` is threaded
    into the governed resolver as per-step harness overrides. An unknown step label or a
    malformed item is a clean ``BadParameter``.
    """
    kinds: dict[str, AgentRuntimeKind] = {}
    names: dict[str, str] = {}
    for item in step_harness or []:
        label, sep, kind_str = item.partition("=")
        if not sep:
            raise typer.BadParameter(f"--step-harness expects 'step=harness', got {item!r}")
        clean_label = label.strip()
        if clean_label not in valid_labels:
            raise typer.BadParameter(
                f"unknown {verb} step {clean_label!r}; "
                f"valid steps: {', '.join(sorted(valid_labels))}"
            )
        clean_name = kind_str.strip().lower()
        kinds[clean_label] = _resolve_harness(clean_name)
        names[clean_label] = clean_name
    return kinds, names


def _resolve_workflow_snapshot(
    workspace_root: Path,
    *,
    workflow_id: str,
    context: str,
    harness: str,
    step_model: list[str] | None,
    step_harness_names: dict[str, str],
) -> WorkflowPolicySnapshot:
    """Resolve a workflow's frozen policy snapshot through the shared resolver (FR1).

    ``--step-model`` is profile-ids-only (D-3, raw ``<id>:<effort>`` rejected via
    :func:`_parse_step_profile_overrides`). ``fake`` is the dry-run sentinel — never threaded
    into ``resolve`` as a governed harness (the base sequence seeded on FAKE is preserved by
    ``apply_resolved_policy``). This is the one seam every run-a-worker verb resolves through.
    """
    from dadaia_workspace import container
    from dadaia_workspace.features.lifecycle.policy_resolver import (
        PolicyResolutionError,
        StepHarnessOverride,
        StepOverride,
    )

    cli_overrides = _parse_step_profile_overrides(step_model)
    typed_overrides: tuple[StepOverride, ...] = tuple(
        ov for ov in cli_overrides if isinstance(ov, StepOverride)
    )
    default_harness_name = harness.lower()
    resolve_default_harness = None if default_harness_name == "fake" else default_harness_name
    typed_step_harness: tuple[StepHarnessOverride, ...] = tuple(
        StepHarnessOverride(step=label, harness=name)
        for label, name in step_harness_names.items()
        if name != "fake"
    )
    resolver = container.build_workflow_policy_resolver(workspace_root, context=context)
    try:
        return resolver.resolve(
            workflow_id,
            context="default",
            cli_overrides=typed_overrides,
            default_harness=resolve_default_harness,
            step_harness_overrides=typed_step_harness,
        )
    except PolicyResolutionError as exc:
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
    workflow_id: str,
    catalog_step_label: str,
    json_output: bool,
    step_model: list[str] | None = None,
    post_step: Callable[[PhaseWorkflowResult], dict[str, Any] | None] | None = None,
) -> None:
    """Run one bounded lifecycle step through the engine on a selectable harness.

    Shared by every single-step lifecycle verb (implement, review qa|security|code, close).
    The harness is chosen per invocation (LAW 1: pi/codex/fake only — ``claude`` is
    rejected). FR1: the step's model is governed — the verb resolves the ``workflow_id``
    snapshot through the shared resolver, selects its ``catalog_step_label`` entry, and calls
    :func:`apply_entry_to_step` ONCE (there is no step object to iterate) to author its local
    ``runtime_kind`` (FAKE preserved for a dry-run) + ``resolved_model``. ``--step-model`` is
    profile-ids-only (D-3); the legacy ``--model`` flag was removed in v0.1.57 (FR6). The frozen
    snapshot is passed to ``LifecyclePhaseWorkflow.run`` so the run records it (LAW 7). The
    worker must emit an APPROVED handoff with an artifact_ref to advance the phase.
    """
    from dadaia_workspace import container
    from dadaia_workspace.features.lifecycle.pipeline import apply_entry_to_step

    workspace_root = resolve_workspace_root()
    kind = _resolve_harness(harness)
    snapshot = _resolve_workflow_snapshot(
        workspace_root,
        workflow_id=workflow_id,
        context=context,
        harness=harness,
        step_model=step_model,
        step_harness_names={},
    )
    entry = snapshot.step(catalog_step_label)
    if entry is None:
        raise typer.BadParameter(
            f"workflow {workflow_id!r} has no governed step {catalog_step_label!r}"
        )
    # apply_entry_to_step is the SOLE runtime_kind author (no step object here): FAKE is
    # preserved for a fake run while the snapshot still records the governed harness/model.
    local_kind, resolved_model = apply_entry_to_step(
        entry, base_kind=kind, preserve_fake=(harness.lower() == "fake")
    )
    workflow = container.build_lifecycle_phase_workflow(workspace_root, runtime_kind=local_kind)
    scope = PromptScope(
        role=role,
        context=context,
        release_id=release_id,
        task_id=run_id,
        prompt=_phase_step_prompt(label, release_id, context, target_phase),
        allowed_paths=(f".dadaia/handoff/{context}/**",),
        required_evidence=(GateEvidenceKind.HANDOFF,),
        model_profile=entry.model_profile,
        resolved_model=resolved_model,
        persona=resolve_persona_for_role(role),
    )
    result = workflow.run(
        run_id=run_id,
        command=label,
        from_phase=from_phase,
        target_phase=target_phase,
        scope=scope,
        policy_snapshot=snapshot,
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
        "auto",
        "--harness",
        help="Layer-2 harness: auto (entry session) | fake | codex | pi (claude is Layer-1 only).",
    ),
    step_model: list[str] | None = typer.Option(
        None,
        "--step-model",
        help="Per-step model override 'review_qa=profile-id' (repeatable). Profile ids "
        "ONLY (D-3); see 'lifecycle workflow profiles list'.",
    ),
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
) -> None:
    """Run the QA review gate on a selectable harness."""
    harness = _resolve_default_harness(harness)
    _run_phase_step(
        label="qa",
        role="qa-engineer",
        from_phase=LifecyclePhase.IMPLEMENTATION,
        target_phase=LifecyclePhase.QA_REVIEW,
        context=context,
        release_id=release_id,
        run_id=run_id,
        harness=harness,
        workflow_id="implementation",
        catalog_step_label="review_qa",
        step_model=step_model,
        json_output=json_output,
    )


@review_app.command("security")
def review_security(
    context: str = typer.Option("dadaia-workspace", "--context", help="Review context."),
    release_id: str = typer.Option(..., "--release-id", help="Release id."),
    run_id: str = typer.Option("review-security", "--run-id", help="Lifecycle run id."),
    harness: str = typer.Option(
        "auto",
        "--harness",
        help="Layer-2 harness: auto (entry session) | fake | codex | pi (claude is Layer-1 only).",
    ),
    step_model: list[str] | None = typer.Option(
        None,
        "--step-model",
        help="Per-step model override 'review_security=profile-id' (repeatable). Profile "
        "ids ONLY (D-3); see 'lifecycle workflow profiles list'.",
    ),
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
) -> None:
    """Run the security review gate on a selectable harness."""
    harness = _resolve_default_harness(harness)
    _run_phase_step(
        label="security",
        role="security-reviewer",
        from_phase=LifecyclePhase.QA_REVIEW,
        target_phase=LifecyclePhase.SECURITY_REVIEW,
        context=context,
        release_id=release_id,
        run_id=run_id,
        harness=harness,
        workflow_id="implementation",
        catalog_step_label="review_security",
        step_model=step_model,
        json_output=json_output,
    )


@review_app.command("code")
def review_code(
    context: str = typer.Option("dadaia-workspace", "--context", help="Review context."),
    release_id: str = typer.Option(..., "--release-id", help="Release id."),
    run_id: str = typer.Option("review-code", "--run-id", help="Lifecycle run id."),
    harness: str = typer.Option(
        "auto",
        "--harness",
        help="Layer-2 harness: auto (entry session) | fake | codex | pi (claude is Layer-1 only).",
    ),
    step_model: list[str] | None = typer.Option(
        None,
        "--step-model",
        help="Per-step model override 'review_code=profile-id' (repeatable). Profile ids "
        "ONLY (D-3); see 'lifecycle workflow profiles list'.",
    ),
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
) -> None:
    """Run the code review gate on a selectable harness."""
    harness = _resolve_default_harness(harness)
    _run_phase_step(
        label="code",
        role="code-reviewer",
        from_phase=LifecyclePhase.SECURITY_REVIEW,
        target_phase=LifecyclePhase.CODE_REVIEW,
        context=context,
        release_id=release_id,
        run_id=run_id,
        harness=harness,
        workflow_id="implementation",
        catalog_step_label="review_code",
        step_model=step_model,
        json_output=json_output,
    )


@app.command()
def close(
    context: str = typer.Option("dadaia-workspace", "--context", help="Context."),
    release_id: str = typer.Option(..., "--release-id", help="Release id."),
    run_id: str = typer.Option("close", "--run-id", help="Lifecycle run id."),
    harness: str = typer.Option(
        "auto",
        "--harness",
        help="Layer-2 harness: auto (entry session) | fake | codex | pi (claude is Layer-1 only).",
    ),
    step_model: list[str] | None = typer.Option(
        None,
        "--step-model",
        help="Per-step model override 'close=profile-id' (repeatable). Profile ids ONLY "
        "(D-3); see 'lifecycle workflow profiles list'.",
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
    harness = _resolve_default_harness(harness)

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
        workflow_id="closure",
        catalog_step_label="close",
        step_model=step_model,
        json_output=json_output,
        post_step=_apply_closure_removal,
    )


# -- FR2: wire audit / research / bug_report as invocable, resolver-governed verbs -------


class _WireStepResult(Protocol):
    """Structural read view of one Wave-E workflow step result (audit/research/bug_report)."""

    @property
    def label(self) -> str: ...
    @property
    def is_gate(self) -> bool: ...
    @property
    def fragment_id(self) -> str | None: ...
    @property
    def accepted(self) -> bool: ...
    @property
    def runtime_kind(self) -> AgentRuntimeKind | None: ...


class _WireWorkflowResult(Protocol):
    """Structural read view of a Wave-E workflow result, shared across the three FR2 verbs.

    ``AuditResult`` / ``ResearchResult`` / ``BugReportResult`` satisfy this Protocol
    field-for-field, so one emitter serves all three verbs without a per-type union.
    """

    @property
    def run_id(self) -> str: ...
    @property
    def completed(self) -> bool: ...
    @property
    def final_phase(self) -> LifecyclePhase: ...
    @property
    def steps(self) -> tuple[_WireStepResult, ...]: ...
    @property
    def blocked(self) -> BlockedState | None: ...


def _emit_wire_result(verb: str, result: _WireWorkflowResult, *, json_output: bool) -> None:
    """Emit an FR2 wire-verb result (JSON or human) + set the exit code (BLOCKED on failure)."""
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
        trail = " → ".join(f"{s.label}:{'ok' if s.accepted else 'BLOCKED'}" for s in result.steps)
        typer.echo(f"{status} {verb} run={result.run_id} phase={result.final_phase.value} {trail}")
    if not result.completed:
        raise typer.Exit(LifecycleExitCode.BLOCKED)


@app.command("audit")
def audit(
    context: str = typer.Option("dadaia-workspace", "--context", help="Context."),
    release_id: str = typer.Option(..., "--release-id", help="Release id."),
    run_id: str = typer.Option("audit", "--run-id", help="Lifecycle run id."),
    harness: str = typer.Option(
        "auto",
        "--harness",
        help="Layer-2 harness: auto (entry session) | fake | codex | pi (claude is Layer-1 only).",
    ),
    step_model: list[str] | None = typer.Option(
        None,
        "--step-model",
        help="Per-step model override 'step=profile-id' (repeatable). Profile ids ONLY "
        "(D-3); steps: audit_scope, drift_scan, triage. See 'lifecycle workflow profiles list'.",
    ),
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
) -> None:
    """Run the audit workflow (scope→drift-scan→triage) as a fragment-driven sequence.

    Born resolver-governed (v0.1.56 / FR2): the per-step model is resolved through the shared
    ``WorkflowExecutionPolicyResolver`` and the frozen snapshot is recorded on the run before
    step 1 (LAW 7). ``--harness fake`` walks the whole sequence; ``--step-model`` is
    profile-ids-only (D-3); the legacy ``--model`` flag was removed in v0.1.57 (FR6).
    """
    harness = _resolve_default_harness(harness)
    from dataclasses import replace as _replace

    from dadaia_workspace import container
    from dadaia_workspace.features.lifecycle.pipeline import apply_resolved_policy
    from dadaia_workspace.features.lifecycle.workflows.audit import _SEQUENCE

    workspace_root = resolve_workspace_root()
    default_kind = _resolve_harness(harness)

    # FR2: resolve the frozen snapshot through the shared resolver; seed each base step's
    # runtime_kind (FAKE for a fake run) BEFORE applying (R-3), then let apply_resolved_policy
    # — the sole runtime_kind author — preserve FAKE while recording the governed harness.
    snapshot = _resolve_workflow_snapshot(
        workspace_root,
        workflow_id="audit",
        context=context,
        harness=harness,
        step_model=step_model,
        step_harness_names={},
    )
    base = tuple(_replace(step, runtime_kind=default_kind) for step in _SEQUENCE)
    sequence = apply_resolved_policy(base, snapshot)

    workflow = container.build_audit_workflow(
        workspace_root,
        context=context,
        release_id=release_id,
        default_runtime_kind=default_kind,
        policy_snapshot=snapshot,
    )
    result = workflow.run(run_id, sequence=sequence)
    _emit_wire_result("audit", result, json_output=json_output)


@app.command("research")
def research(
    context: str = typer.Option("dadaia-workspace", "--context", help="Context."),
    release_id: str = typer.Option(..., "--release-id", help="Release id."),
    run_id: str = typer.Option("research", "--run-id", help="Lifecycle run id."),
    harness: str = typer.Option(
        "auto",
        "--harness",
        help="Layer-2 harness: auto (entry session) | fake | codex | pi (claude is Layer-1 only).",
    ),
    step_model: list[str] | None = typer.Option(
        None,
        "--step-model",
        help="Per-step model override 'step=profile-id' (repeatable). Profile ids ONLY "
        "(D-3); steps: research_scope, investigate, synthesis. See 'lifecycle workflow "
        "profiles list'.",
    ),
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
) -> None:
    """Run the research workflow (scope→investigate→synthesis) as a fragment-driven sequence.

    Born resolver-governed (v0.1.56 / FR2), mirroring ``audit``: the frozen snapshot is
    recorded on the run before step 1; ``--step-model`` is profile-ids-only (D-3); the legacy
    ``--model`` flag was removed in v0.1.57 (FR6).
    """
    harness = _resolve_default_harness(harness)
    from dataclasses import replace as _replace

    from dadaia_workspace import container
    from dadaia_workspace.features.lifecycle.pipeline import apply_resolved_policy
    from dadaia_workspace.features.lifecycle.workflows.research import _SEQUENCE

    workspace_root = resolve_workspace_root()
    default_kind = _resolve_harness(harness)

    snapshot = _resolve_workflow_snapshot(
        workspace_root,
        workflow_id="research",
        context=context,
        harness=harness,
        step_model=step_model,
        step_harness_names={},
    )
    base = tuple(_replace(step, runtime_kind=default_kind) for step in _SEQUENCE)
    sequence = apply_resolved_policy(base, snapshot)

    workflow = container.build_research_workflow(
        workspace_root,
        context=context,
        release_id=release_id,
        default_runtime_kind=default_kind,
        policy_snapshot=snapshot,
    )
    result = workflow.run(run_id, sequence=sequence)
    _emit_wire_result("research", result, json_output=json_output)


@app.command("bug_report")
def bug_report(
    context: str = typer.Option("dadaia-workspace", "--context", help="Context."),
    release_id: str = typer.Option(..., "--release-id", help="Release id."),
    run_id: str = typer.Option("bug-report", "--run-id", help="Lifecycle run id."),
    harness: str = typer.Option(
        "auto",
        "--harness",
        help="Layer-2 harness: auto (entry session) | fake | codex | pi (claude is Layer-1 only).",
    ),
    step_model: list[str] | None = typer.Option(
        None,
        "--step-model",
        help="Per-step model override 'step=profile-id' (repeatable). Profile ids ONLY "
        "(D-3); steps: bug_intake, dedupe, bug_write. See 'lifecycle workflow profiles list'.",
    ),
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
) -> None:
    """Run the bug-report workflow (intake→dedupe→bug_write) as a fragment-driven sequence.

    Born resolver-governed (v0.1.56 / FR2). The verb's real ``bug_write`` target is the
    ADDITIVE ``specs/bugs/`` path class — it takes no MUTATING lease by construction. Under
    ``--harness fake`` a step-aware driving fake keeps the ADDITIVE ``bug_write`` step in-scope
    so the run reaches COMPLETED. ``--step-model`` is profile-ids-only (D-3); the legacy
    ``--model`` flag was removed in v0.1.57 (FR6).
    """
    harness = _resolve_default_harness(harness)
    from dataclasses import replace as _replace

    from dadaia_workspace import container
    from dadaia_workspace.features.lifecycle.pipeline import apply_resolved_policy
    from dadaia_workspace.features.lifecycle.workflows.bug_report import _SEQUENCE

    workspace_root = resolve_workspace_root()
    default_kind = _resolve_harness(harness)

    snapshot = _resolve_workflow_snapshot(
        workspace_root,
        workflow_id="bug_report",
        context=context,
        harness=harness,
        step_model=step_model,
        step_harness_names={},
    )
    base = tuple(_replace(step, runtime_kind=default_kind) for step in _SEQUENCE)
    sequence = apply_resolved_policy(base, snapshot)

    workflow = container.build_bug_report_workflow(
        workspace_root,
        context=context,
        release_id=release_id,
        default_runtime_kind=default_kind,
        policy_snapshot=snapshot,
    )
    result = workflow.run(run_id, sequence=sequence)
    _emit_wire_result("bug_report", result, json_output=json_output)


# -- FR3: implement/review attempt loop as an invocable, resolver-governed verb ----------


def _implement_review_runtime_factory(
    workspace_root: Path,
    *,
    context: str,
) -> RuntimeFactory:
    """Per-step runtime factory for the implement/review loop verb (FR3).

    ``FAKE`` resolves to a *driving* fake returning an APPROVED handoff with an in-scope
    ``.dadaia/handoff/<ctx>/**`` artifact_ref, so ``--harness fake`` drives the loop to
    COMPLETED deterministically (both workers pass the structural gate; the review's APPROVED
    verdict completes the loop) — mirroring the audit/research driving fakes. Real harnesses
    (pi/codex) resolve to their live adapters; the policy-resolved concrete model reaches each
    adapter through ``request.resolved_model`` (threaded by ``apply_resolved_policy``).

    Kept a module-level seam so a CLI test can inject a scripted-verdict fake (the all-REJECTED
    → BLOCK path) without bypassing the real snapshot-freezing wiring in
    :func:`_build_implement_review_pipeline`.
    """
    from dadaia_workspace import container
    from dadaia_workspace.core.models.lifecycle import AgentRunResult, AgentRunStatus
    from dadaia_workspace.infrastructure.fake_runtime import FakeAgentRuntime

    approving = AgentRunResult(
        status=AgentRunStatus.SUCCEEDED,
        summary="fake implement/review worker: APPROVED",
        artifact_refs=(f".dadaia/handoff/{context}/implement-review-step.handoff.json",),
        structured_output={"verdict": "APPROVED"},
    )

    def factory(kind: AgentRuntimeKind) -> AgentRuntimePort:
        if kind is AgentRuntimeKind.FAKE:
            return FakeAgentRuntime(result=approving)
        return container.build_agent_runtime(kind, cwd=workspace_root)

    return factory


def _build_implement_review_pipeline(
    workspace_root: Path,
    *,
    context: str,
    release_id: str,
    snapshot: WorkflowPolicySnapshot,
    max_review_retries: int,
) -> LifecyclePipeline:
    """Compose the loop pipeline with the wired ``handoff_resolver`` the loop requires (FR3).

    The run store + workflow-step handoff resolver come from the container seams; the frozen
    ``snapshot`` is passed as ``policy_snapshot`` so the run records it before step 1 (LAW 7).
    The runtime factory is resolved through :func:`_implement_review_runtime_factory` (the
    monkeypatch seam), so the snapshot-freezing path is exercised on both the APPROVED and the
    all-REJECTED test drives.
    """
    from dadaia_workspace import container
    from dadaia_workspace.features.lifecycle.pipeline import LifecyclePipeline

    return LifecyclePipeline(
        context=context,
        release_id=release_id,
        run_store=container.build_lifecycle_run_store(workspace_root),
        runtime_factory=_implement_review_runtime_factory(workspace_root, context=context),
        handoff_resolver=container.build_workflow_handoff_resolver(workspace_root),
        policy_snapshot=snapshot,
        max_review_retries=max_review_retries,
    )


def _emit_implement_review_result(result: ImplementReviewLoopResult, *, json_output: bool) -> None:
    """Emit the loop result (JSON or human) + set the exit code (BLOCKED on failure)."""
    status = (
        LifecycleCommandStatus.OK.value
        if result.completed
        else LifecycleCommandStatus.BLOCKED.value
    )
    final_verdict = result.rounds[-1].review_verdict if result.rounds else None
    if json_output:
        _emit_json(
            {
                "status": status,
                "run_id": result.run_id,
                "completed": result.completed,
                "attempts": result.attempts,
                "final_verdict": final_verdict,
                "rounds": [
                    {"attempt": r.attempt, "review_verdict": r.review_verdict}
                    for r in result.rounds
                ],
                "blocked": result.blocked.to_dict() if result.blocked else None,
            }
        )
    else:
        trail = " → ".join(f"#{r.attempt}:{r.review_verdict}" for r in result.rounds)
        typer.echo(
            f"{status} implement-review run={result.run_id} "
            f"attempts={result.attempts} verdict={final_verdict} {trail}"
        )
    if not result.completed:
        raise typer.Exit(LifecycleExitCode.BLOCKED)


@app.command("implement-review")
def implement_review(
    context: str = typer.Option("dadaia-workspace", "--context", help="Context."),
    release_id: str = typer.Option(..., "--release-id", help="Release id."),
    run_id: str = typer.Option("implement-review", "--run-id", help="Lifecycle run id."),
    harness: str = typer.Option(
        "auto",
        "--harness",
        help="Layer-2 harness: auto (entry session) | fake | codex | pi (claude is Layer-1 only).",
    ),
    step_model: list[str] | None = typer.Option(
        None,
        "--step-model",
        help="Per-step model override 'implement|review_qa=profile-id' (repeatable). Profile "
        "ids ONLY (D-3); see 'lifecycle workflow profiles list'.",
    ),
    max_review_retries: int = typer.Option(
        2,
        "--max-review-retries",
        help="Bounded retry count: after this many REJECTED rounds the loop BLOCKS.",
    ),
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
) -> None:
    """Run the implement/review attempt loop (implement → review, bounded retry) on a harness.

    Born resolver-governed (v0.1.56 / FR3): the per-step model is resolved through the shared
    ``WorkflowExecutionPolicyResolver`` (the ``implementation`` workflow snapshot) and the
    frozen snapshot is recorded on the run before step 1 (LAW 7). Each REJECTED review injects
    a COMPACT rejection digest into the next implement prompt; every loop worker is gated on
    EVIDENCE ONLY (non-SUCCEEDED / empty artifact_refs / out-of-scope ⇒ BLOCK), never on the
    review verdict. An APPROVED review COMPLETES the loop; exhausting ``--max-review-retries``
    REJECTED rounds BLOCKS it. ``--harness fake`` drives it deterministically; ``--step-model``
    is profile-ids-only (D-3); the legacy ``--model`` flag was removed in v0.1.57 (FR6).
    """
    harness = _resolve_default_harness(harness)
    from dadaia_workspace.features.lifecycle.pipeline import (
        PipelineStep,
        apply_resolved_policy,
    )

    workspace_root = resolve_workspace_root()
    default_kind = _resolve_harness(harness)

    # FR3: resolve the ``implementation`` snapshot through the shared resolver; seed each base
    # step's runtime_kind (FAKE for a fake run) BEFORE applying (R-3), then let
    # apply_resolved_policy — the sole runtime_kind author — preserve FAKE while recording the
    # governed harness/model onto the implement + review steps.
    snapshot = _resolve_workflow_snapshot(
        workspace_root,
        workflow_id="implementation",
        context=context,
        harness=harness,
        step_model=step_model,
        step_harness_names={},
    )
    implement_step = PipelineStep(
        label="implement",
        role="software-engineer",
        from_phase=LifecyclePhase.IMPLEMENTATION,
        target_phase=LifecyclePhase.QA_REVIEW,
        runtime_kind=default_kind,
    )
    review_step = PipelineStep(
        label="review_qa",
        role="qa-engineer",
        from_phase=LifecyclePhase.QA_REVIEW,
        target_phase=LifecyclePhase.SECURITY_REVIEW,
        runtime_kind=default_kind,
        is_review=True,
    )
    implement_step, review_step = apply_resolved_policy((implement_step, review_step), snapshot)

    pipeline = _build_implement_review_pipeline(
        workspace_root,
        context=context,
        release_id=release_id,
        snapshot=snapshot,
        max_review_retries=max_review_retries,
    )
    result = pipeline.run_implement_review_loop(
        run_id, implement_step=implement_step, review_step=review_step
    )
    _emit_implement_review_result(result, json_output=json_output)


@app.command()
def pipeline(
    context: str = typer.Option("dadaia-workspace", "--context", help="Context."),
    release_id: str = typer.Option(..., "--release-id", help="Release id."),
    run_id: str = typer.Option("pipeline", "--run-id", help="Lifecycle run id."),
    harness: str = typer.Option(
        "auto",
        "--harness",
        help="Default harness for all steps: auto (entry session) | fake | codex | pi (claude is Layer-1 only).",
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
    harness = _resolve_default_harness(harness)
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
    """Run the lifecycle governance + fragment-coherence doctors (WMP-* + FRAG-COH-*).

    The WMP-* governance doctor checks the governed catalog + built-in profile registry +
    persisted overlay for: workflow/step id uniqueness, default-profile resolution + harness
    match, fragment + output-schema resolution, overlay override validity, and any
    ``claude``/``opencode`` Layer-2 residue. The FRAG-COH-* coherence doctor (v0.1.57 FR3) adds
    the fragment-file surface: fragment role→persona resolution (FRAG-COH-1), selector-wired
    main-fragment ``dynamic_inputs`` registration (FRAG-COH-2), orphan/dangling fragments
    (FRAG-COH-3), and role→atom-map coverage across the FR2 delivery surfaces (FRAG-COH-4). An
    invalid overlay state file is reported as an actionable error and never crashes. Exit 1 if
    any ERROR finding is present in either doctor.
    """
    from dadaia_workspace import container
    from dadaia_workspace.features.lifecycle.fragment_coherence_doctor import (
        Severity as CoherenceSeverity,
    )
    from dadaia_workspace.features.lifecycle.fragment_coherence_doctor import (
        run_fragment_coherence_doctor,
    )
    from dadaia_workspace.features.lifecycle.policy_doctor import (
        Severity,
        run_policy_doctor,
    )

    workspace_root = resolve_workspace_root()
    store = container.build_workflow_model_policy_store(workspace_root)
    findings = run_policy_doctor(store=store)
    coherence = run_fragment_coherence_doctor()
    if json_output:
        _emit_json(
            {
                "findings": [f.to_dict() for f in findings],
                "coherence": [f.to_dict() for f in coherence.findings],
            }
        )
    else:
        if not findings:
            typer.echo("[ok] workflow-model-policy (no governance issues)")
        for finding in findings:
            typer.echo(f"[{finding.severity.value}] {finding.code.value}: {finding.message}")
        if coherence.ok and not coherence.findings:
            typer.echo("[ok] fragment-coherence (no coherence issues)")
        for coh in coherence.findings:
            typer.echo(f"[{coh.severity.value}] {coh.code.value}: {coh.message}")
    has_error = any(f.severity is Severity.ERROR for f in findings) or any(
        c.severity is CoherenceSeverity.ERROR for c in coherence.findings
    )
    if has_error:
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
app.add_typer(review_app, name="review")
app.add_typer(workflow_app, name="workflow")
