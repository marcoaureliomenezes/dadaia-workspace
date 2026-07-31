"""Lifecycle command group."""

from __future__ import annotations

import contextlib
import dataclasses
import json
import re
from collections.abc import Callable, Iterator, Sequence
from enum import IntEnum
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol

import typer

from dadaia_workspace.cli._specs_resolution import repo_slug_for_context
from dadaia_workspace.core.exceptions import ReleaseNotFoundError, ScopeNotConsumedError
from dadaia_workspace.core.lifecycle_recovery import resume_command
from dadaia_workspace.core.models.lifecycle import (
    HARNESS_CLI_NAMES,
    AgentRuntimeKind,
    BlockedState,
    LifecyclePhase,
)
from dadaia_workspace.core.models.workflow_execution import WorkflowPolicySnapshot
from dadaia_workspace.core.session_env import entry_harness
from dadaia_workspace.core.specs_version import RELEASE_SEMVER_RE
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
#: Derived from the ONE canonical map in core so the parser and every prescribed-remedy
#: renderer can never disagree about what '--harness codex' means.
_HARNESS_KINDS = {name: kind for kind, name in HARNESS_CLI_NAMES.items()}

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

    resolved = resolve_context_for_cli(context)
    _refuse_dead_context(resolved)
    return resolved


def _refuse_dead_context(context: str) -> None:
    """Refuse to run a lifecycle workflow on a context the operator took out of service.

    Bug ``r16-lifecycle-allows-dead-context``: after ``context alive`` failed for an
    explicit DEAD context, ``backlog-definition`` still dispatched and completed. A DEAD
    context is a deliberate operator decision — its specs tree may be un-materialized,
    stale, or archived — so authoring into it produces work in a place nobody is watching.

    Unregistered contexts are deliberately NOT refused here: ``resolve_context_for_cli``
    has a documented terminal fallback to the self-hosting slug for a workspace with
    nothing registered, and breaking that would turn a bare verb invocation into an error.
    Only a context that IS registered and IS dead is refused.
    """
    from dadaia_workspace.core.exceptions import DadaiaError
    from dadaia_workspace.core.models.spec_context import ContextState
    from dadaia_workspace.core.workspace_resolver import resolve_workspace_root

    record = None
    try:
        from dadaia_workspace import container

        service = container.build_spec_context_service(resolve_workspace_root())
        record = next((c for c in service.list_all() if c.name == context), None)
    except Exception:  # noqa: BLE001
        # A registry this guard cannot READ (legacy v1 schema awaiting `dadaia migrate`,
        # missing, corrupt) means it cannot JUDGE — and refusing on ignorance would break
        # every workspace that has not migrated yet. The real command surfaces that error
        # itself a moment later; this guard stays silent rather than pre-empting it with a
        # wrong diagnosis. The refusal below is raised OUTSIDE this block, so it can never
        # be swallowed by it.
        return
    if record is not None and record.state is ContextState.DEAD:
        raise DadaiaError(
            f"context {context!r} is DEAD — lifecycle workflows do not run on a context "
            "that was taken out of service, because its specs tree may be "
            f"un-materialized or archived. Bring it back with `dadaia context alive "
            f"{context}`, or pass --context for a live one."
        )


def _authoritative_backlog_prefix(
    workspace_root: Path,
    *,
    context: str,
    release_id: str,
    backlog_run_ids: Sequence[str] = (),
) -> PromptPrefix | None:
    """Resolve the exact completed backlog-definition producers for release scope.

    Direct release definition remains valid when no matching backlog workflow exists. When
    any exist, their run-scoped ``backlog_author`` payloads are authoritative: EVERY
    completed producer for this context+release contributes its authored item paths, so a
    release can consume the SET of items that N backlog-definition runs authored
    (bug release-definition-refuses-multiple-backlog-producers — multiplicity used to be a
    usage error, which made that flow unreachable and forced N-1 items to be discarded).

    Multiplicity is not ambiguity: the paths come from producer evidence, so there is no
    stale candidate for a model to choose between. ``backlog_run_ids`` narrows the set;
    every id named must be a completed producer, or it is a loud usage error.
    """
    from dadaia_workspace import container
    from dadaia_workspace.core.models.lifecycle import LifecycleRunStatus
    from dadaia_workspace.features.lifecycle.prompt_builder import PromptPrefix
    from dadaia_workspace.features.lifecycle.workflow_handoffs import (
        MalformedHandoffError,
        RequiredHandoffMissingError,
    )

    run_store = container.build_lifecycle_run_store(workspace_root)
    completed = [
        run
        for run in run_store.list_runs()
        if run.command == "backlog_definition"
        and run.context == context
        and run.release_id == release_id
        and run.status is LifecycleRunStatus.COMPLETED
    ]
    requested = tuple(dict.fromkeys(backlog_run_ids))
    if requested:
        available = {run.run_id for run in completed}
        unknown = [run_id for run_id in requested if run_id not in available]
        if unknown:
            known = ", ".join(sorted(available)) or "(none)"
            raise typer.BadParameter(
                f"--backlog-run-id {', '.join(repr(i) for i in unknown)} is not a completed "
                f"backlog-definition run for context={context!r}, release={release_id!r}. "
                f"Completed producers: {known}"
            )
        matches = [run for run in completed if run.run_id in set(requested)]
    else:
        matches = completed
    if not matches:
        return None
    matches.sort(key=lambda run: run.run_id)

    resolver = container.build_workflow_handoff_resolver(workspace_root)
    resolved_payloads = []
    for upstream in matches:
        try:
            resolved_payloads.append(
                (
                    upstream,
                    resolver.resolve_required(
                        upstream,
                        producer_step="backlog_author",
                        attempt=upstream.workflow_steps.live_attempt("backlog_author"),
                    ),
                )
            )
        except (RequiredHandoffMissingError, MalformedHandoffError) as exc:
            raise typer.BadParameter(
                f"backlog-definition run {upstream.run_id!r} has no valid backlog_author "
                f"payload: {exc}"
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

    root = workspace_root.resolve()
    # Every producer is swept, and a producer that authored nothing is a loud error rather
    # than a silent hole in the release scope — the union being non-empty is not enough.
    for upstream, resolved in resolved_payloads:
        before = set(authored_paths)
        _walk_payload(resolved.payload)
        raw_refs = resolved.payload.get("artifact_refs")
        refs = (
            tuple(ref for ref in raw_refs if isinstance(ref, str))
            if isinstance(raw_refs, list)
            else ()
        )
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
        if authored_paths == before:
            raise typer.BadParameter(
                f"backlog-definition run {upstream.run_id!r} produced no exact specs/backlog "
                "artifact path in its backlog_author evidence"
            )

    producers = ", ".join(f"`{upstream.run_id}`" for upstream, _ in resolved_payloads)
    paths = "\n".join(f"- `{path}`" for path in sorted(authored_paths))
    directive = (
        f"Exact producer run(s): {producers}.\n"
        "The following authored backlog artifact(s) are the authoritative scope input "
        "for this release:\n"
        f"{paths}\n"
        "Pick these items — ALL of them. Candidate-backlog scanning may sanitize or "
        "identify stale neighbors, but it must not substitute a different candidate for, "
        "or drop any of, this exact producer output."
    )
    return PromptPrefix.from_sections({"authoritative-backlog-definition": directive})


# The ONE central canon (bug lifecycle-accepts-noncanonical-release-id retest: every
# public validator shares this contract — see core.specs_version.RELEASE_SEMVER_RE).
_CANONICAL_RELEASE_ID_RE = RELEASE_SEMVER_RE


def _require_canonical_release_id(release_id: str) -> None:
    """Refuse a noncanonical release id BEFORE any run or write.

    Bug lifecycle-accepts-noncanonical-release-id-then-generates-invalid-memory-slug:
    an id like 'valgame-v0.1.0' sailed through definition, then closure derived an
    invalid memory slug and the release could never close. The canonical shape is the
    same one specs doctor pins (SPEC-DOC-027): vMAJOR.MINOR.PATCH with an optional
    -suffix segment (e.g. v0.1.0, v1.2.3-rc1).
    """
    if _CANONICAL_RELEASE_ID_RE.fullmatch(release_id) is None:
        raise typer.BadParameter(
            f"--release-id {release_id!r} is not canonical. Use vMAJOR.MINOR.PATCH "
            "(optionally with a -suffix), e.g. v0.1.0 or v1.2.3-rc1 — noncanonical ids "
            "break downstream closure/memory slugs.",
            param_hint="--release-id",
        )


def _echo_block_reason(result: object) -> None:
    """Print WHY a run stopped, in the human output, not only under --json.

    A blocked line that names only the step ("backlog_review_gate:BLOCKED") forces the
    operator to re-run the whole command with --json just to read the reason — and a
    reason nobody reads is a remedy nobody follows. Every block already carries its
    prescribed recovery; this puts it where the operator is looking.
    """
    blocked = getattr(result, "blocked", None)
    if blocked is None:
        return
    reason = getattr(blocked, "reason", "") or ""
    if reason:
        typer.echo(f"\n{reason}")
    remedy = getattr(blocked, "operator_command", "") or ""
    if remedy:
        typer.echo(f"\nRecovery: {remedy}")


#: The CLI verb that runs each persisted workflow command. The implementation workflow
#: persists ``"pipeline"``, which an earlier version of this map did not carry — so the
#: fallback GUESSED, and an implementation run was handed a `release-definition` command
#: (bug r22-lifecycle-status-pipeline-recovery-wrong-verb). A wrong command is worse than
#: no command: the operator runs it, and it does something else.
@contextlib.contextmanager
def _sealing_run(workspace_root: Path, run_id: str) -> Iterator[None]:
    """Seal a still-RUNNING run on the way out, however the body ends.

    The previous version of this guard sat AFTER the workflow returned, so it never fired
    when the workflow RAISED — an invalid Codex sandbox mode, for instance, aborted step
    two and left the ledger `running` with no block
    (bug r22-codex-sandbox-invalid-mode-traceback, evidence half). That is the same class
    arriving by yet another route, which is what a `finally` exists for: the guarantee
    must not depend on the body succeeding.
    """
    try:
        yield
    finally:
        with contextlib.suppress(Exception):
            _seal_non_terminal_run(workspace_root, run_id)


def _resume_command_for(run: object, step: str) -> str:
    """A full, pasteable resume line for THIS run — never prose around a flag.

    Bug ``r21-killed-driver-leaves-running-ledger`` (second half): the seal's remedy read
    "re-run the same command with --resume-from X", which the operator has to reassemble
    from memory precisely when something has already gone wrong. Every field needed is on
    the run record, so there is no reason to make them retype it.
    """
    return resume_command(
        command=str(getattr(run, "command", "")),
        run_id=str(getattr(run, "run_id", "")),
        step=step,
        context=str(getattr(run, "context", "") or ""),
        release_id=str(getattr(run, "release_id", "") or ""),
    )


def _seal_non_terminal_run(workspace_root: Path, run_id: str) -> str | None:
    """Convert a run left RUNNING into a BLOCKED one carrying a diagnosis and a remedy.

    Three separate reports — ``r11-release-definition-exits-success-interrupted``,
    ``r15-release-definition-running-after-accepted-draft``,
    ``r20-release-definition-returns-success-while-running`` — are the same class arriving
    by different routes: the verb returns, and the run on disk is still ``running`` with
    nothing that explains it. Each earlier fix patched the route it was reported on. A
    class that keeps coming back through new routes is a class that needs a CHOKEPOINT,
    not another patch.

    This is that chokepoint: whatever happened inside — completion, block, an exception
    that escaped, a worker that never answered — the command does not return while the
    persisted run claims to still be going. Terminal states are untouched; only the
    ambiguous one is sealed.
    """
    from dadaia_workspace import container
    from dadaia_workspace.core.models.lifecycle import (
        BlockedState,
        LifecyclePhase,
        LifecycleRunStatus,
    )

    try:
        store = container.build_lifecycle_run_store(workspace_root)
        run = store.load(run_id)
    except Exception:  # noqa: BLE001 — a seal must never eclipse the command's own error
        return None
    if run is None or run.status is not LifecycleRunStatus.RUNNING:
        return None
    if run.blocked is not None:
        # A RECORDED block is the real diagnosis, written by whatever actually stopped the
        # run. Sealing over it would replace a specific reason and remedy with a generic
        # one — the seal exists to resolve AMBIGUITY, and a run carrying a block is not
        # ambiguous. (Caught immediately by the test that pins recorded-block precedence,
        # which is why that test exists.)
        return None

    step = run.current_step or "<step>"
    reason = (
        f"this run was left RUNNING at step {step!r} — the step never reached a terminal "
        "outcome and recorded no block of its own. Either the command returned without "
        "finishing it, or the driver was killed before it could. Inspect the run's step "
        "payload for the worker's last output."
    )
    sealed = dataclasses.replace(
        run,
        phase=LifecyclePhase.BLOCKED,
        status=LifecycleRunStatus.BLOCKED,
        blocked=BlockedState(
            reason=reason,
            blocked_at_step=step,
            resume_token=run.idempotency_key,
            operator_command=_resume_command_for(run, step),
            detail={"step": step, "gate": "non-terminal-seal-v1"},
        ),
    )
    with contextlib.suppress(Exception):
        store.save(sealed)
    return reason


def _seal_post_step_failure(workspace_root: Path, run_id: str, error: str) -> None:
    """Record a post-step failure on the run the command has just refused to call a success.

    Bug ``r22-release-definition-completes-with-consumes-bind-error``: the workflow
    completed, the producer post-step raised (a ``**Consumes:**`` slug that is not a live
    backlog item), and the command correctly printed BLOCKED and exited 3 — while the
    ledger kept saying COMPLETED. Both halves were right and nothing joined them, so the
    operator was told one thing and every later reader (``lifecycle status``, the panel,
    the next preflight) was told the other. The ledger wins by default, because it is what
    tooling reads; a false COMPLETED lets the next phase start on a definition that never
    consumed its backlog.

    :func:`_persisted_disagrees_with_success` guards the mirror direction — the command
    claims success the disk does not support. This is the same law pointing the other way.
    """
    from dadaia_workspace import container
    from dadaia_workspace.core.models.lifecycle import (
        BlockedState,
        LifecyclePhase,
        LifecycleRunStatus,
    )

    try:
        store = container.build_lifecycle_run_store(workspace_root)
        run = store.load(run_id)
    except OSError:
        # Narrow deliberately. A blanket `except Exception` here swallowed a NameError from
        # a missing local import and this guard silently did nothing while looking applied —
        # the same shape that made an earlier dead-context guard a no-op. Only I/O against
        # the ledger is legitimately survivable; a programming error must not be absorbed
        # by the thing that exists to stop failures from being invisible.
        return
    # A recorded block is the more specific diagnosis; the generic post-step reason must
    # never replace it (same precedence rule the non-terminal seal obeys).
    if run is None or run.blocked is not None:
        return
    step = run.current_step or "<step>"
    # FAILED, not BLOCKED. The store refuses to move a run OUT of a terminal state, and it
    # is right to: that monotonicity is what makes concurrent drivers safe to accept
    # (r14-implementation-recovery-reverts-terminal-run). FAILED is terminal, so this is a
    # legal terminal→terminal transition — and it is also the honest word. The run is over
    # and it did not succeed; the recovery rides on the `blocked` field, which every reader
    # already consults for the reason and the command.
    sealed = dataclasses.replace(
        run,
        phase=LifecyclePhase.BLOCKED,
        status=LifecycleRunStatus.FAILED,
        blocked=BlockedState(
            reason=(
                f"the workflow completed but its post-step failed: {error}. The definition "
                "is not consumable until this resolves."
            ),
            blocked_at_step=step,
            resume_token=run.idempotency_key,
            operator_command=_resume_command_for(run, step),
            detail={"post_step_error": error, "gate": "post-step-seal-v1"},
        ),
    )
    with contextlib.suppress(Exception):
        store.save(sealed)


def _persisted_disagrees_with_success(workspace_root: Path, run_id: str) -> str | None:
    """Return a message when the CLI is about to claim success the DISK does not support.

    Bug ``r11-release-definition-exits-success-interrupted``: release-definition exited 0
    after an accepted ``definition_draft`` while the run persisted as ``running`` — the
    in-memory result said completed and the store said interrupted. An exit code that
    disagrees with the state on disk is worse than a failure: the caller moves on, and
    the next command trips over a run nobody knows is unfinished.

    Disk wins. It is what every later step, and every operator, actually reads.
    """
    from dadaia_workspace import container
    from dadaia_workspace.core.models.lifecycle import LifecycleRunStatus

    try:
        run = container.build_lifecycle_run_store(workspace_root).load(run_id)
    except Exception:  # noqa: BLE001 — a store read must never mask the command's own result
        return None
    if run is None or run.status is LifecycleRunStatus.COMPLETED:
        return None
    return (
        f"the command reports success but run {run_id!r} is persisted as "
        f"{run.status.value.upper()} at step {run.current_step or '<step>'} — refusing to "
        f"report OK. Inspect it with `dadaia lifecycle status --run-id {run_id}`"
    )


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
    _require_canonical_release_id(release_id)
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
    with _sealing_run(workspace_root, run_id):
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
        _echo_block_reason(result)
    if not result.completed:
        raise typer.Exit(LifecycleExitCode.BLOCKED)


@app.command("release-definition")
def release_define(
    context: str | None = typer.Option(
        None, "--context", help="Context. Default: resolved via the bind-resolution seam."
    ),
    release_id: str = typer.Option(..., "--release-id", help="Release id."),
    run_id: str = typer.Option("release-define", "--run-id", help="Lifecycle run id."),
    demand: str | None = typer.Option(
        None,
        "--demand",
        help="Operator guidance injected into every executed model step as an "
        "'## Operator demand' block — the channel for supplying the decision a "
        "review asked for when resuming after a REJECTED verdict.",
    ),
    backlog_run_id: list[str] | None = typer.Option(
        None,
        "--backlog-run-id",
        help="Completed backlog-definition run(s) to consume (repeatable). Default: every "
        "completed producer for this context and release.",
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
        "step labels (definition_draft, definition_review).",
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
    steps behind Python-checked gates (a MISSING review blocks advancement; a REJECTED
    review blocks only while the revision budget lasts — once spent it is recorded as
    an advisory warning and the step proceeds, so a model verdict can never deadlock a
    release) and
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
    _require_canonical_release_id(release_id)
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
        backlog_run_ids=tuple(backlog_run_id or ()),
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
    with _sealing_run(workspace_root, run_id):
        result = workflow.run(
            run_id,
            sequence,
            resume_from=resume_from,
            skip_scope=upstream_prefix is not None,
            operator_demand=demand,
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
                workspace_root,
                context=context,
                release_id=release_id,
                scope_slugs=_scope_slugs(upstream_prefix),
            )
        except Exception as exc:  # noqa: BLE001 — surface, never swallow; do not corrupt the run.
            post_step_error = f"{type(exc).__name__}: {exc}"

    # A post-step failure is a FAILURE of this command, not a footnote on a success. The
    # status used to come purely from result.completed and the non-zero exit only from a
    # blocked run, so a release whose post-step raised (e.g. it consumed none of the
    # backlog its own scope directive declared mandatory) still reported status OK and
    # exited 0 — the detection was real and the verdict was not
    # (bug r6f-release-completes-with-unconsumed-authoritative-backlog, reported by the
    # consumer-side validator against a live worker).
    succeeded = result.completed and post_step_error is None
    # Unconditional, not success-only: a run left RUNNING is ambiguous whatever this
    # command thinks happened, and three reports of that class arrived by three different
    # routes before it got a chokepoint instead of another patch.
    sealed = _seal_non_terminal_run(workspace_root, result.run_id)
    if sealed is not None:
        succeeded = False
        post_step_error = sealed
    elif post_step_error is not None:
        # The run is COMPLETED and this command is about to call it BLOCKED. Write that
        # back, or the ledger every later reader consults will contradict what the
        # operator was just told (bug r22-release-definition-completes-with-consumes-bind-error).
        _seal_post_step_failure(workspace_root, result.run_id, post_step_error)
    elif succeeded:
        disagreement = _persisted_disagrees_with_success(workspace_root, result.run_id)
        if disagreement is not None:
            succeeded = False
            post_step_error = disagreement
    status = LifecycleCommandStatus.OK.value if succeeded else LifecycleCommandStatus.BLOCKED.value
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
                "warnings": list(getattr(result, "warnings", ())),
            }
        )
    else:
        trail = " → ".join(f"{s.label}:{'ok' if s.accepted else 'BLOCKED'}" for s in result.steps)
        typer.echo(
            f"{status} release-define run={result.run_id} phase={result.final_phase.value} {trail}"
        )
        _echo_block_reason(result)
        if post_step_result is not None:
            typer.echo(f"  post_step: {post_step_result}")
        if post_step_error is not None:
            typer.echo(f"  post_step ERROR: {post_step_error}")
        for warning in getattr(result, "warnings", ()):
            typer.secho(f"  {warning}", fg=typer.colors.YELLOW, err=True)
    if not succeeded:
        raise typer.Exit(LifecycleExitCode.BLOCKED)


#: Matches an authored backlog item path inside the authoritative-scope directive.
_SCOPE_ITEM_RE = re.compile(r"`(?:[^`]*/)?specs/backlog/(?P<slug>[a-z][a-z0-9-]*)\.md`")


def _scope_slugs(prefix: PromptPrefix | None) -> tuple[str, ...]:
    """The backlog slugs the run declared as mandatory release scope (empty when none)."""
    if prefix is None:
        return ()
    return tuple(dict.fromkeys(m.group("slug") for m in _SCOPE_ITEM_RE.finditer(prefix.text)))


def _apply_release_consume(
    workspace_root: Path,
    *,
    context: str,
    release_id: str,
    scope_slugs: Sequence[str] = (),
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

    # A run that declared an authoritative scope must consume it. Reporting success with an
    # empty ledger while the run's own directive named N mandatory items is the
    # declared-but-never-verified failure mode (bug
    # release-definition-consumes-nothing-while-scope-declares-items): the operator cannot
    # tell a definition that consumed the set from one that silently dropped it.
    dropped = [slug for slug in scope_slugs if slug not in set(slugs)]
    if dropped:
        raise ScopeNotConsumedError(
            f"release {release_id!r} declared {len(scope_slugs)} backlog item(s) as "
            f"authoritative scope but its SPEC does not consume: {', '.join(dropped)}. "
            "Add them to the SPEC's `**Consumes:**` line, or narrow the scope with "
            "--backlog-run-id."
        )

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
    result: dict[str, Any] = {
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
    # Bug r18-closure-leaves-consumed-backlog-item: on a live chain the SPEC declared its
    # Consumes line and the ledger was written correctly, yet the item stayed in the live
    # backlog — and closure said nothing, so the operator only learned of it later, from
    # `backlog doctor` reporting BL-STALE on a release it believed was finished.
    #
    # So the gate now checks its own work: every slug the ledger claims was consumed must
    # be gone from specs/backlog/. Reporting a leftover is not the same as fixing whatever
    # left it there, but a silent leftover is what turns a closed release into a stale tree
    # nobody expects.
    leftovers = _consumed_slugs_still_present(
        workspace_root, context=context, release_id=release_id
    )
    if leftovers:
        result["stale_after_closure"] = leftovers
    return result


def _consumed_slugs_still_present(
    workspace_root: Path, *, context: str, release_id: str
) -> list[str]:
    """Slugs the consumed-backlog ledger claims, that are STILL under specs/backlog/."""
    import json as _json

    from dadaia_workspace import container

    try:
        specs_dir = container._context_specs_dir(workspace_root, context)
    except Exception:  # noqa: BLE001 — a self-check must never break the closure it audits
        return []
    ledger = specs_dir / "_archive" / release_id / "consumed_backlog.json"
    try:
        recorded = _json.loads(ledger.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    claimed = [
        str(entry.get("slug"))
        for entry in recorded.get("consumed", [])
        if isinstance(entry, dict) and entry.get("slug")
    ]
    backlog = specs_dir / "backlog"
    return [slug for slug in claimed if (backlog / f"{slug}.md").is_file()]


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
    _require_canonical_release_id(release_id)
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
    with _sealing_run(workspace_root, run_id):
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
        # Bug r17-r20-preflight-block-missing-recovery: the preflight has its OWN output
        # path, so it printed the reason and swallowed the remedy while every other block
        # in the workflow printed both. A remedy that exists in the payload and never
        # reaches the terminal is a remedy nobody follows — the fifth report of this class.
        # Only the remedy is added: the reason is already in `message` above, and printing
        # it twice trains the reader to skim.
        remedy = result.blocked.operator_command
        if remedy:
            typer.echo(f"\nRecovery: {remedy}")
    raise typer.Exit(LifecycleExitCode.BLOCKED)


def _implementation_runtime_factory(
    workspace_root: Path,
    *,
    context: str,
    release_id: str | None = None,
) -> Callable[[AgentRuntimeKind], AgentRuntimePort]:
    """Per-step runtime factory for the implementation-reviews workflow.

    ``FAKE`` resolves to a driving APPROVED result carrying artifact evidence, so
    ``implementation-reviews --harness fake`` is a deterministic workflow-wiring smoke test
    instead of always blocking at ``implement`` with ``agent result missing artifact
    evidence``. The driving fake is STEP-AWARE (bug
    certification-passes-without-complete-workflow-chain): the declared ref lives in the
    worker raw-output zone (`.dadaia/tmp/lifecycle-worker/<ctx>/**` — the previous
    `.dadaia/handoff/...` ref was out-of-scope and always blocked the implement step),
    and the terminal ``close`` step also materializes its declared CLOSURE.md
    deliverable, so ``--harness fake`` walks the whole implement→review→close ladder.
    Real harnesses (pi/codex) resolve to their live adapters; the policy-resolved
    concrete model reaches each adapter through ``request.resolved_model``.

    Seam-preserving: FAKE still routes THROUGH ``container.build_agent_runtime`` — a
    test-injected scripted fake (monkeypatched builder: custom result or on_run hook) is
    respected verbatim; only the PLAIN default fake is upgraded to the driving result.
    """
    from dadaia_workspace import container
    from dadaia_workspace.core.models.lifecycle import (
        AgentRunRequest,
        AgentRunResult,
        AgentRunStatus,
    )
    from dadaia_workspace.infrastructure import fake_runtime

    step_output_ref = f".dadaia/tmp/lifecycle-worker/{context}/pipeline-step.step-output.json"

    def _driving_result(request: AgentRunRequest) -> AgentRunResult:
        task_id = request.task_id or ""
        parts = task_id.split(":")
        label = parts[1] if len(parts) > 1 else ""
        refs = [step_output_ref]
        if label == "close" and release_id is not None:
            # The repo DIRECTORY is the registered slug, not the context name — using the
            # name put CLOSURE.md outside the declared write scope, so the close step was
            # refused (bug a2-fake-implementation-close-closure-out-of-scope).
            slug = repo_slug_for_context(workspace_root, context)
            specs_prefix = (
                f"repos/{slug}/specs"
                if (workspace_root / "repos" / slug / "specs").is_dir()
                else "specs"
            )
            closure_ref = f"{specs_prefix}/releases/{release_id}/CLOSURE.md"
            refs.append(closure_ref)
            closure = workspace_root / closure_ref
            if not closure.exists():
                closure.parent.mkdir(parents=True, exist_ok=True)
                closure.write_text(
                    "# CLOSURE: driving-fake stub\n\n> **Status:** Draft\n\n"
                    "Deterministic driving-fake closure deliverable.\n",
                    encoding="utf-8",
                )
        target = workspace_root / step_output_ref
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(
                '{"fake": true, "summary": "driving-fake stub artifact"}\n', encoding="utf-8"
            )
        return AgentRunResult(
            status=AgentRunStatus.SUCCEEDED,
            summary="fake pipeline worker: APPROVED",
            artifact_refs=tuple(refs),
            structured_output={"verdict": "APPROVED"},
        )

    class _ImplementationDrivingFake:
        def runtime_kind(self) -> AgentRuntimeKind:
            return AgentRuntimeKind.FAKE

        def run(self, request: AgentRunRequest) -> AgentRunResult:
            return _driving_result(request)

    def factory(kind: AgentRuntimeKind) -> AgentRuntimePort:
        runtime = container.build_agent_runtime(kind, cwd=workspace_root)
        if (
            kind is AgentRuntimeKind.FAKE
            and isinstance(runtime, fake_runtime.FakeAgentRuntime)
            and runtime.is_plain_default
        ):
            return _ImplementationDrivingFake()
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
    resume_from: str | None = typer.Option(
        None,
        "--resume-from",
        help="Resume a BLOCKED run from this step (implement | review_combined | close): "
        "upstream ledger payloads are kept; only the named step onward re-executes.",
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
    _require_canonical_release_id(release_id)
    context = _resolve_context_option(context)
    harness = _resolve_default_harness(harness)
    from dataclasses import replace

    from dadaia_workspace import container
    from dadaia_workspace.features.lifecycle.pipeline import (
        InvalidResumeStepError,
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
    # …including --resume-from (bug r24-invalid-resume-implementation-preflight-mask):
    # whether a token names a real step is knowable without reading one byte of workspace
    # state. Validating it after the preflight sent the operator off to fix a context bind
    # for a command that could never have run, and only revealed the real mistake on the
    # next attempt. The definition verbs already reject it up front; this one did not.
    if resume_from is not None:
        labels = tuple(step.label for step in implementation_ladder(default_kind))
        if resume_from not in labels:
            raise InvalidResumeStepError.for_labels(resume_from, labels)
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
        runtime_factory=_implementation_runtime_factory(
            workspace_root, context=context, release_id=release_id
        ),
        max_review_retries=max_review_retries,
    )
    with _sealing_run(workspace_root, run_id):
        result = pipe.run(run_id, steps, resume_from=resume_from)
    closure_gate = (
        _apply_closure_removal_for_release(workspace_root, context=context, release_id=release_id)
        if result.completed
        else None
    )
    # Same chokepoint on the implementation path — the class was reported here too.
    _seal_non_terminal_run(workspace_root, result.run_id)
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
        _echo_block_reason(result)
    if not result.completed:
        raise typer.Exit(LifecycleExitCode.BLOCKED)


def _policy_snapshot_payload(snapshot: object) -> dict[str, Any]:
    """Project a ``WorkflowPolicySnapshot`` to a JSON-serializable dict for CLI output."""
    from dadaia_workspace.core.models.workflow_execution import WorkflowPolicySnapshot

    assert isinstance(snapshot, WorkflowPolicySnapshot)
    return snapshot.to_dict()


@app.command("status")
def lifecycle_status(
    run_id: str = typer.Option(..., "--run-id", help="Lifecycle run id to inspect."),
    workspace: Path | None = typer.Option(
        None, "--workspace", "-w", help="Workspace root (default: resolved from cwd)."
    ),
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
) -> None:
    """Report a run's state and, when it cannot proceed, how to recover it.

    Bugs ``r9-r11-release-running-without-recovery`` /
    ``r9-r12-backlog-running-without-recovery``: an interrupted run is persisted as
    ``running`` — not finished, not failed, carrying no block and therefore no remedy.
    ``refuse_blocked_restart`` already knew the recovery, but only spoke when the operator
    happened to re-run the identical command and trip the refusal. Whoever INSPECTED the
    run got a status word and nothing else, and there was no verb to ask. Guidance that is
    only reachable by triggering an error is not guidance.

    Read-only, and exit 0 for any run it can describe: this is a query, and a query that
    fails because its answer is bad news is a query you stop trusting. An unknown run id
    is a different thing — that is a usage error, and it is loud.
    """
    from dadaia_workspace import container
    from dadaia_workspace.core.models.lifecycle import LifecycleRunStatus

    workspace_root = workspace or resolve_workspace_root()
    # Bug r21-killed-driver-leaves-running-ledger: the end-of-verb chokepoint cannot fire
    # when the driver is KILLED — no in-process code runs at all. This verb is what the
    # operator runs afterwards, so it is the only place that can still seal the ledger.
    # Inspecting a dead run therefore RESOLVES it instead of merely describing it.
    _seal_non_terminal_run(workspace_root, run_id)
    run = container.build_lifecycle_run_store(workspace_root).load(run_id)
    if run is None:
        raise typer.BadParameter(f"no lifecycle run {run_id!r} found under {workspace_root}")

    # A RECORDED block is the stronger evidence and wins over the status field: something
    # deliberately wrote a reason and a remedy, whereas a stale `running` is what a crash
    # leaves behind. Checking the enum first announced "interrupted at intake_grill" for a
    # run actually blocked at backlog_author — wrong state, wrong step, and it sent the
    # operator to resume from a step that had already succeeded
    # (bug r12-lifecycle-status-mislabels-blocked-run).
    blocked_state = run.blocked
    step = (
        (blocked_state.blocked_at_step if blocked_state else None) or run.current_step or "<step>"
    )
    interrupted = blocked_state is None and run.status is LifecycleRunStatus.RUNNING
    recovery: str | None = None
    detail: str | None = None
    if interrupted:
        detail = (
            "interrupted before reaching a terminal state (a killed driver or an orphaned "
            "worker leaves this)"
        )
        recovery = _resume_command_for(run, step)
    elif blocked_state is not None:
        detail = blocked_state.reason
        # The fallback used to be prose ("re-run with --resume-from X"), which is the exact
        # shape reported five times and ratcheted against in `features/lifecycle` — where
        # the ratchet could not see it, because it never scanned `cli/`. A last-resort
        # branch is precisely where an unpasteable remedy hides.
        recovery = blocked_state.operator_command or _resume_command_for(
            run, blocked_state.blocked_at_step
        )

    if json_output:
        typer.echo(
            json.dumps(
                {
                    "run_id": run.run_id,
                    "command": run.command,
                    "context": run.context,
                    "release_id": run.release_id,
                    "status": run.status.value,
                    "current_step": step,
                    "interrupted": interrupted,
                    "detail": detail,
                    "recovery": recovery,
                },
                indent=2,
            )
        )
        return

    typer.echo(f"run={run.run_id} command={run.command} status={run.status.value.upper()}")
    typer.echo(f"step={step} context={run.context} release={run.release_id}")
    if detail:
        typer.echo(f"\n{detail}")
    if recovery:
        typer.echo(f"\nRecovery: {recovery}")
