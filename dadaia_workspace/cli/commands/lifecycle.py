"""Lifecycle command group."""

from __future__ import annotations

import json
from collections.abc import Callable
from enum import IntEnum
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol

import typer

from dadaia_workspace.core.exceptions import ReleaseNotFoundError
from dadaia_workspace.core.models.lifecycle import (
    AgentRuntimeKind,
    BlockedState,
    LifecyclePhase,
)
from dadaia_workspace.core.models.workflow_execution import WorkflowPolicySnapshot
from dadaia_workspace.core.session_env import entry_harness
from dadaia_workspace.core.workspace_resolver import resolve_workspace_root
from dadaia_workspace.features.lifecycle.service import LifecycleCommandStatus

if TYPE_CHECKING:
    from dadaia_workspace.core.protocols.agent_runtime import AgentRuntimePort
    from dadaia_workspace.features.lifecycle.prompt_builder import PromptPrefix

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


class LifecycleExitCode(IntEnum):
    OK = 0
    INTERNAL_ERROR = 1
    USAGE_ERROR = 2
    BLOCKED = 3


def _emit_json(payload: dict[str, Any]) -> None:
    typer.echo(json.dumps(payload, sort_keys=True))


def _resolve_context_option(context: str | None) -> str:
    """Resolve a lifecycle verb's ``--context`` through the single bind-resolution seam
    (SPEC v0.1.77 FR1/FR2). Every lifecycle verb below unsets its Typer default to
    ``None`` and calls this at the top of its body — the ~15-verb hardcoded literal
    ``"dadaia-workspace"`` default (never consulting a bind) is retired for good (FR4: no
    further per-command patches accepted for recurrence family F2).

    ``resolve_context_for_cli`` always returns a non-empty string (explicit -> env ->
    bound session -> first-ALIVE -> the self-hosting-workspace slug terminal fallback),
    so a bare verb invocation with no context registered at all keeps its long-standing
    behavior (degrading to the self-hosting slug, which every downstream ``container``
    factory already resolves gracefully); a real bind or a real ALIVE context now
    correctly takes priority over that fallback, which is the FR1 bug this release fixes.
    """
    from dadaia_workspace.cli._specs_resolution import resolve_context_for_cli

    return resolve_context_for_cli(context)


def _authoritative_backlog_prefix(
    workspace_root: Path,
    *,
    context: str,
    release_id: str,
    backlog_run_id: str | None,
) -> PromptPrefix | None:
    """Resolve one exact completed backlog-definition producer for release scope.

    Direct release definition remains valid when no matching backlog workflow exists.
    When one does exist, its run-scoped ``backlog_author`` payload is authoritative;
    ambiguity is an operator-visible usage error rather than a model choice over stale
    candidates.
    """
    from dadaia_workspace import container
    from dadaia_workspace.core.models.lifecycle import LifecycleRunStatus
    from dadaia_workspace.features.lifecycle.prompt_builder import PromptPrefix
    from dadaia_workspace.features.lifecycle.workflow_handoffs import (
        MalformedHandoffError,
        RequiredHandoffMissingError,
    )

    run_store = container.build_lifecycle_run_store(workspace_root)
    matches = [
        run
        for run in run_store.list_runs()
        if run.command == "backlog_definition"
        and run.context == context
        and run.release_id == release_id
        and run.status is LifecycleRunStatus.COMPLETED
        and (backlog_run_id is None or run.run_id == backlog_run_id)
    ]
    if backlog_run_id is not None and not matches:
        raise typer.BadParameter(
            f"--backlog-run-id {backlog_run_id!r} is not a completed backlog-definition "
            f"run for context={context!r}, release={release_id!r}"
        )
    if not matches:
        return None
    if len(matches) != 1:
        ids = ", ".join(sorted(run.run_id for run in matches))
        raise typer.BadParameter(
            "multiple completed backlog-definition runs match this release; pass "
            f"--backlog-run-id explicitly ({ids})"
        )
    upstream = matches[0]
    try:
        resolved = container.build_workflow_handoff_resolver(workspace_root).resolve_required(
            upstream, producer_step="backlog_author", attempt=0
        )
    except (RequiredHandoffMissingError, MalformedHandoffError) as exc:
        raise typer.BadParameter(
            f"backlog-definition run {upstream.run_id!r} has no valid backlog_author payload: {exc}"
        ) from exc

    authored_paths: set[str] = set()

    def _record_backlog_path(value: object) -> None:
        if not isinstance(value, str):
            return
        clean = value.strip().lstrip("/")
        if clean.startswith("specs/backlog/") or "/specs/backlog/" in clean:
            authored_paths.add(clean)

    # Tolerant extraction: workers nest the authored path differently (top-level
    # artifact_refs, result.artifact, handoff.artifact.path, ...). Any string value
    # anywhere in the payload that names a specs/backlog path counts.
    def _walk_payload(value: object) -> None:
        if isinstance(value, str):
            _record_backlog_path(value)
        elif isinstance(value, list):
            for item in value:
                _walk_payload(item)
        elif isinstance(value, dict):
            for item in value.values():
                _walk_payload(item)

    _walk_payload(resolved.payload)
    raw_refs = resolved.payload.get("artifact_refs")
    refs = (
        tuple(ref for ref in raw_refs if isinstance(ref, str)) if isinstance(raw_refs, list) else ()
    )
    root = workspace_root.resolve()
    for ref in refs:
        _record_backlog_path(ref)
        target = (root / ref).resolve()
        if root not in target.parents or not target.is_file() or not ref.endswith(".json"):
            continue
        try:
            document = json.loads(target.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        artifact = document.get("artifact") if isinstance(document, dict) else None
        if isinstance(artifact, dict):
            _record_backlog_path(artifact.get("path"))
    if not authored_paths:
        raise typer.BadParameter(
            f"backlog-definition run {upstream.run_id!r} produced no exact specs/backlog "
            "artifact path in its backlog_author evidence"
        )
    paths = "\n".join(f"- `{path}`" for path in sorted(authored_paths))
    directive = (
        f"Exact producer run: `{upstream.run_id}`.\n"
        "The following authored backlog artifact(s) are the authoritative scope input "
        "for this release:\n"
        f"{paths}\n"
        "Pick these items. Candidate-backlog scanning may sanitize or identify stale "
        "neighbors, but it must not substitute a different candidate for this exact "
        "producer output."
    )
    return PromptPrefix.from_sections({"authoritative-backlog-definition": directive})


@app.command("backlog-definition")
def backlog_define(
    context: str | None = typer.Option(
        None, "--context", help="Context. Default: resolved via the bind-resolution seam."
    ),
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
        help="Per-step harness override 'step=harness' (repeatable); steps are the "
        "model-step labels (intake_grill, backlog_author).",
    ),
    step_model: list[str] | None = typer.Option(
        None,
        "--step-model",
        help="Per-step model override 'step=profile-id' (repeatable). Profile ids ONLY "
        "(D-3) — a raw '<id>:<effort>' string is rejected; see "
        "'dadaia reports workflow-profiles'.",
    ),
    demand: str | None = typer.Option(
        None,
        "--demand",
        help="Raw operator demand text injected into every model step's prompt as an "
        "'## Operator demand' block — the author's primary input.",
    ),
    grill: bool = typer.Option(
        False,
        "--grill",
        help="Opt-in: run the intake_grill step before authoring (default path is "
        "author-only — one model call). The grill's payload digest is injected into "
        "the author prompt.",
    ),
    resume_from: str | None = typer.Option(
        None,
        "--resume-from",
        help="Re-execute an existing blocked run from this step label onward without "
        "re-running completed model steps.",
    ),
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
) -> None:
    """Turn an operator demand into one refined backlog item (interview, dedupe, author).

    This is one of the four lifecycle workflows; it runs a fixed sequence of AI worker
    steps behind Python-checked gates and stops if a gate blocks. Use ``--harness fake``
    to walk the whole sequence deterministically with no model calls.

    (Internal contract, constitution §4.) Python owns step order and the typed gates; each
    model step's prompt is assembled
    from its fragment bundle + selected dynamic context + output schema + the discrete
    ``(harness, model)``. The §4 Python steps (``subject_bind``, ``existing_backlog_review``,
    ``reconcile_decision``, ``backlog_review_gate``) dispose deterministically via the R1
    registry + classifier; a blocked gate stops the sequence. ``--harness fake`` walks the
    whole sequence; ``claude`` is rejected (LAW 1); the per-step model is profile-ids-only
    via ``--step-model`` (D-3) — the legacy ``--model`` flag was removed in v0.1.57 (FR6).
    v0.1.77 FR1/FR2: an unset ``--context`` resolves through the single bind-resolution
    seam instead of a hardcoded literal default.
    """
    context = _resolve_context_option(context)
    harness = _resolve_default_harness(harness)
    from dataclasses import replace as _replace

    from dadaia_workspace import container
    from dadaia_workspace.features.lifecycle.pipeline import apply_resolved_policy
    from dadaia_workspace.features.lifecycle.workflows.backlog_definition import (
        _SEQUENCE,
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
    # The author-first default path: ONE model call (backlog_author) + the REAL
    # post-authoring Python gate over what landed on disk (bug
    # backlog-definition-empty-demand-wiring). --grill opts into the intake step.
    result = workflow.run(
        run_id,
        sequence=sequence,
        operator_demand=demand,
        grill=grill,
        resume_from=resume_from,
    )

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


@app.command("release-definition")
def release_define(
    context: str | None = typer.Option(
        None, "--context", help="Context. Default: resolved via the bind-resolution seam."
    ),
    release_id: str = typer.Option(..., "--release-id", help="Release id."),
    run_id: str = typer.Option("release-define", "--run-id", help="Lifecycle run id."),
    backlog_run_id: str | None = typer.Option(
        None,
        "--backlog-run-id",
        help="Exact completed backlog-definition run to consume. Auto-resolves only when unique.",
    ),
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
        "(D-3) — a raw '<id>:<effort>' string is rejected; see "
        "'dadaia reports workflow-profiles'.",
    ),
    resume_from: str | None = typer.Option(
        None,
        "--resume-from",
        help="Re-execute the existing run from this step label onward (bug "
        "blocked-definition-run-cannot-resume-from-step): already-approved upstream "
        "steps are NOT re-run; their ledger payloads stay addressable.",
    ),
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
) -> None:
    """Turn a picked backlog set into an approved SPEC/PLAN/TASKS release, review-gated.

    This is one of the four lifecycle workflows; it runs a fixed sequence of AI worker
    steps behind Python-checked gates (a rejected or missing review blocks advancement) and
    only reaches IMPLEMENTATION when every gate passes. ``--harness fake`` walks it with no
    model calls.

    (Internal contract, constitution §6.1.) Python owns step order and the typed gates;
    each model step's prompt is assembled
    from its fragment bundle + selected dynamic context + output schema + the discrete
    ``(harness, model)`` — there is no generic "Run the step" suffix. A REJECTED or
    missing review handoff BLOCKS advancement; the terminal ``definition_commit_gate``
    advances the release to IMPLEMENTATION only when every gate passed. v0.1.77 FR1/FR2:
    an unset ``--context`` resolves through the single bind-resolution seam instead of a
    hardcoded literal default.
    """
    context = _resolve_context_option(context)
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

    upstream_prefix = _authoritative_backlog_prefix(
        workspace_root,
        context=context,
        release_id=release_id,
        backlog_run_id=backlog_run_id,
    )
    workflow = container.build_release_definition_workflow(
        workspace_root,
        context=context,
        release_id=release_id,
        default_runtime_kind=default_kind,
        prefix=upstream_prefix,
        policy_snapshot=snapshot,
    )
    # Small-release fast path: a consumed authoritative backlog pick already fixed the
    # scope (it rides the prompt prefix) — the release_scope model step is a redundant
    # restatement and is skipped, saving one worker session. Applied on RESUME too:
    # the resumed sequence must keep the shape of the original run (which never
    # produced a release_scope payload to consume).
    result = workflow.run(
        run_id,
        sequence,
        resume_from=resume_from,
        skip_scope=upstream_prefix is not None,
    )

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

    if not slugs:
        return {"consumed_slugs": [], "shipped_anchors": [], "ledger": None}

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


def _apply_closure_removal_for_release(
    workspace_root: Path, *, context: str, release_id: str
) -> dict[str, Any]:
    """Apply the implementation workflow's terminal backlog-removal gate."""
    from dadaia_workspace import container

    lifecycle = container.build_backlog_removal_lifecycle(workspace_root, context=context)
    removal = lifecycle.remove(release_id=release_id)
    return {
        "removed": [
            action.slug
            for action in removal.actions
            if action.action.value == "archived_and_removed"
        ],
        "rewritten": [
            action.slug for action in removal.actions if action.action.value == "rewritten"
        ],
        "unchanged": [
            action.slug for action in removal.actions if action.action.value == "unchanged"
        ],
    }


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


# -- Audit workflow emitter ------------------------------------------------------------


class _WireStepResult(Protocol):
    """Structural read view of one audit workflow step result."""

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
    """Structural read view of an audit workflow result."""

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
    """Emit an audit result and set the exit code."""
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
    context: str | None = typer.Option(
        None, "--context", help="Context. Default: resolved via the bind-resolution seam."
    ),
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
        "(D-3); steps: audit_report. See 'dadaia reports workflow-profiles'.",
    ),
    resume_from: str | None = typer.Option(
        None,
        "--resume-from",
        help="Re-execute an existing blocked run from this step label onward without "
        "re-buying completed worker sessions.",
    ),
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
) -> None:
    """Produce a governance audit report of the project, with a Python disposition gate.

    This is one of the four lifecycle workflows; it runs one AI audit-report step and a
    Python gate that dispositions the findings. ``--harness fake`` walks it with no model
    calls.

    (Internal contract.) Born resolver-governed (v0.1.56 / FR2): the per-step model is
    resolved through the shared
    ``WorkflowExecutionPolicyResolver`` and the frozen snapshot is recorded on the run before
    step 1 (LAW 7). ``--harness fake`` walks the whole sequence; ``--step-model`` is
    profile-ids-only (D-3); the legacy ``--model`` flag was removed in v0.1.57 (FR6).
    v0.1.77 FR1/FR2: an unset ``--context`` resolves through the single bind-resolution
    seam instead of a hardcoded literal default.
    """
    context = _resolve_context_option(context)
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

    try:
        workflow = container.build_audit_workflow(
            workspace_root,
            context=context,
            release_id=release_id,
            default_runtime_kind=default_kind,
            policy_snapshot=snapshot,
        )
    except ReleaseNotFoundError as exc:
        # Reject an undefined --release-id with a concise, actionable error — never a
        # traceback, and without synthesizing a specs/releases/<id>/ tree.
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(3) from None
    result = workflow.run(run_id, sequence=sequence, resume_from=resume_from)
    _emit_wire_result("audit", result, json_output=json_output)


def _enforce_preflight_gate(
    workspace_root: Path,
    *,
    context: str,
    release_id: str,
    skip: bool,
    json_output: bool,
) -> None:
    """v0.1.72 FR6 (bug ``workflow-verbs-run-despite-blocked-preflight``): release-mutating
    worker verbs enforce the SAME preflight gate the ``preflight`` command reports.

    A blocked preflight refuses the verb BEFORE any lifecycle run is created — a gate
    that reports "unsafe" while the verb proceeds is theater. ``--skip-preflight`` is the
    explicit, visible operator override (wiring smoke tests on throwaway contexts that
    have no full git topology; deliberate operator judgment) — never a silent default.
    """
    if skip:
        if not json_output:
            # Human runs get the visible notice; --json keeps the stream machine-pure.
            typer.echo("[preflight] SKIPPED by --skip-preflight (operator override)", err=True)
        return
    from dadaia_workspace import container

    data = container.build_lifecycle_preflight_input(
        workspace_root, context=context, release_id=release_id
    )
    result = container.build_lifecycle_preflight_service(workspace_root).preflight(data)
    if result.ok:
        return
    assert result.blocked is not None
    message = f"preflight blocked: {result.blocked.reason}"
    if json_output:
        _emit_json(
            {
                "status": LifecycleCommandStatus.BLOCKED.value,
                "message": message,
                "blocked": result.blocked.to_dict(),
            }
        )
    else:
        typer.echo(f"{LifecycleCommandStatus.BLOCKED.value} {message}")
    raise typer.Exit(LifecycleExitCode.BLOCKED)


def _implementation_runtime_factory(
    workspace_root: Path,
    *,
    context: str,
) -> Callable[[AgentRuntimeKind], AgentRuntimePort]:
    """Per-step runtime factory for the implementation-reviews workflow.

    ``FAKE`` resolves to a driving APPROVED result carrying artifact evidence, so
    ``implementation-reviews --harness fake`` is a deterministic workflow-wiring smoke test
    instead of always blocking at ``implement`` with ``agent result missing artifact
    evidence``. Real harnesses (pi/codex) resolve to their live adapters; the
    policy-resolved concrete model reaches each adapter through
    ``request.resolved_model`` (threaded by ``apply_resolved_policy``).

    Seam-preserving: FAKE still routes THROUGH ``container.build_agent_runtime`` — a
    test-injected scripted fake (monkeypatched builder: custom result or on_run hook) is
    respected verbatim; only the PLAIN default fake is upgraded to the driving result.
    """
    from dadaia_workspace import container
    from dadaia_workspace.core.models.lifecycle import AgentRunResult, AgentRunStatus
    from dadaia_workspace.infrastructure import fake_runtime

    approving = AgentRunResult(
        status=AgentRunStatus.SUCCEEDED,
        summary="fake pipeline worker: APPROVED",
        artifact_refs=(f".dadaia/handoff/{context}/pipeline-step.handoff.json",),
        structured_output={"verdict": "APPROVED"},
    )

    def factory(kind: AgentRuntimeKind) -> AgentRuntimePort:
        runtime = container.build_agent_runtime(kind, cwd=workspace_root)
        if (
            kind is AgentRuntimeKind.FAKE
            and isinstance(runtime, fake_runtime.FakeAgentRuntime)
            and runtime.is_plain_default
        ):
            # Attribute access (not a from-import) so test seams patching the CLASS on
            # the infrastructure module are honored here too.
            return fake_runtime.FakeAgentRuntime(result=approving, materialize_root=workspace_root)
        return runtime

    return factory


@app.command("implementation-reviews")
def pipeline(
    context: str | None = typer.Option(
        None, "--context", help="Context. Default: resolved via the bind-resolution seam."
    ),
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
        "implement, review_combined, close.",
    ),
    step_model: list[str] | None = typer.Option(
        None,
        "--step-model",
        help="Per-step model override 'label=profile-id' (repeatable). Profile ids ONLY "
        "(D-3) — a raw '<id>:<effort>' string is rejected; see "
        "'dadaia reports workflow-profiles'.",
    ),
    write_scope: list[str] | None = typer.Option(
        None,
        "--write-scope",
        help="Extra write-scope path glob for the implement step ONLY (repeatable). "
        "FR7 (T-66-08): unions with the handoff-dir scope so an implement worker may "
        "legally edit the given production/test path(s); review steps are never "
        "widened. The approved release's incomplete TASKS.md write sets are derived "
        "automatically — this flag is an additive escape hatch, not a "
        "requirement.",
    ),
    max_review_retries: int = typer.Option(
        2,
        "--max-review-retries",
        min=0,
        help="Maximum automatic correction rounds after a rejected review.",
    ),
    show_policy: bool = typer.Option(
        False,
        "--show-policy",
        help="Print the resolved per-step model policy and exit without running.",
    ),
    skip_preflight: bool = typer.Option(
        False,
        "--skip-preflight",
        help="Explicit operator override: run WITHOUT the preflight gate (wiring smoke "
        "tests / deliberate judgment). Never silently skipped.",
    ),
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
) -> None:
    """Implement an approved release, run bounded review-correction rounds, then close it.

    This is one of the four lifecycle workflows; it runs the implement + review AI steps
    with a capped number of automatic correction rounds and ends at closure.
    ``--harness fake`` walks it with no model calls; ``--show-policy`` prints the resolved
    per-step model policy and exits without running.

    (Internal contract.) The per-step model is governed: ``--step-model label=profile-id``
    selects a built-in
    model profile (D-3), resolved through the shared ``WorkflowExecutionPolicyResolver``
    (CLI > overlay > library default). The resolved policy is snapshotted onto the run
    before the first step (LAW 7). ``--show-policy`` prints the resolved policy and exits.
    v0.1.77 FR1/FR2: an unset ``--context`` resolves through the single bind-resolution
    seam instead of a hardcoded literal default.
    """
    context = _resolve_context_option(context)
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
    # Argument validation FIRST (bad --harness fails fast regardless of preflight state)…
    default_kind = _resolve_harness(harness)
    # …then v0.1.72 FR6: enforce the preflight gate BEFORE any run is created
    # (--show-policy is a read-only print — never gated).
    if not show_policy:
        _enforce_preflight_gate(
            workspace_root,
            context=context,
            release_id=release_id,
            skip=skip_preflight,
            json_output=json_output,
        )

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
            "implementation_reviews",
            context="default",
            cli_overrides=typed_overrides,
            default_harness=resolve_default_harness,
            step_harness_overrides=typed_step_harness,
        )
    except PolicyResolutionError as exc:
        raise typer.BadParameter(str(exc)) from exc

    if show_policy:
        payload = _policy_snapshot_payload(snapshot)
        if json_output:
            _emit_json(payload)
        else:
            typer.echo(json.dumps(payload, indent=2, sort_keys=True))
        return

    # D-2: apply_resolved_policy is the SINGLE author of runtime_kind — it sets each step's
    # kind from the resolved harness, preserving FAKE for a fake dry-run. The base ladder
    # carries only the fake-vs-real selection (so `--harness fake` drives the fake adapter
    # while the snapshot still records the governed harness); there is no separate
    # post-resolve runtime_kind swap.
    # FR3 (v0.1.68): derive the implement step's write scope from the reserved TASKS.md
    # task's declared `Write set:` globs, unioned BEFORE any --write-scope extras (FR3.2).
    # Additive-optional: an absent/ambiguous TASKS.md degrades to () with no crash (AC3.2),
    # so a fixture/dry-run pipeline with no real TASKS.md behaves exactly as before.
    from dadaia_workspace.features.lifecycle.tasks_write_scope import (
        write_scope_from_release_tasks,
    )

    specs_dir = container.resolve_context_specs_dir(workspace_root, context)
    tasks_paths = write_scope_from_release_tasks(specs_dir, release_id)
    # FR7 (T-66-08): --write-scope threads into extra_allowed_paths for non-review steps
    # ONLY (gated on step.is_review is False, not a label match — ARCHITECT MEDIUM-2);
    # review steps are never widened. Today the ladder has exactly one non-review step
    # (implement); this stays structurally correct if the ladder grows another create step.
    extra_paths = tuple(tasks_paths) + tuple(write_scope or ())
    base = tuple(
        replace(
            step,
            runtime_kind=step_harness_kinds.get(step.label, default_kind),
            extra_allowed_paths=(
                extra_paths if step.label == "implement" else step.extra_allowed_paths
            ),
        )
        for step in implementation_ladder(default_kind)
    )
    steps = apply_resolved_policy(base, snapshot)

    pipe = container.build_lifecycle_pipeline(
        workspace_root,
        context=context,
        release_id=release_id,
        policy_snapshot=snapshot,
        # The driving-fake-aware factory lets `--harness fake` complete the smoke path
        # with artifact evidence.
        runtime_factory=_implementation_runtime_factory(workspace_root, context=context),
        max_review_retries=max_review_retries,
    )
    result = pipe.run(run_id, steps)
    closure_gate = (
        _apply_closure_removal_for_release(workspace_root, context=context, release_id=release_id)
        if result.completed
        else None
    )
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
                        "attempt": step.attempt,
                    }
                    for step in result.steps
                ],
                "blocked": result.blocked.to_dict() if result.blocked else None,
                "closure_gate": closure_gate,
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
