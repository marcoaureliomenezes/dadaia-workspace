"""Lifecycle agent runner that validates runtime output before transitions."""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Mapping
from dataclasses import dataclass, replace
from pathlib import Path

from dadaia_workspace.core.lifecycle_recovery import resume_command
from dadaia_workspace.core.models.lifecycle import (
    AgentRunRequest,
    AgentRunResult,
    AgentRunStatus,
    BlockedState,
    GateEvidence,
    GateRequirement,
    GateVerdict,
    InjectedContext,
    LifecyclePhase,
    LifecycleRun,
)
from dadaia_workspace.core.protocols.agent_runtime import AgentRuntimePort
from dadaia_workspace.core.protocols.runtime_files import RuntimeFilePort
from dadaia_workspace.core.scope_match import out_of_scope_paths
from dadaia_workspace.features.lifecycle.context_selector import SelectionAudit
from dadaia_workspace.features.lifecycle.prompt_builder import canonical_worker_output_ref
from dadaia_workspace.features.lifecycle.state_machine import (
    LifecycleStateMachine,
    TransitionDecision,
    TransitionInput,
)


def record_injected_context(
    lifecycle_run: LifecycleRun,
    audit: SelectionAudit,
) -> LifecycleRun:
    """Append a context-selection audit entry to the run record.

    Returns a new :class:`LifecycleRun` whose ``injected_context`` carries the
    fragment ids and resolved dynamic-context refs that were injected for a step,
    making context selection auditable (epic §8.8). The run record is the persisted
    audit seam — callers persist the returned run via the lifecycle run store.
    """
    entry = audit.to_injected_context()
    return replace_injected_context(lifecycle_run, (*lifecycle_run.injected_context, entry))


def record_prompt_composition(
    lifecycle_run: LifecycleRun,
    step: str,
    *,
    prefix_hash: str | None,
    model: str | None,
    runtime_kind: str | None,
    output_schema: str | None,
    gate_result: str | None,
) -> LifecycleRun:
    """Enrich the run's *step* audit entry with WS-9 prompt-composition fields.

    The WS-4 seam (:func:`record_injected_context`) records fragment ids + resolved
    refs before the worker runs; this completes the same entry once the step's prompt
    is built and its gate has decided, persisting the prefix hash, discrete model,
    runtime kind, output schema, and gate verdict. It updates the existing entry for
    *step* (the most recent one) in place rather than appending a duplicate, so the run
    record carries exactly one composition record per step.
    """
    entries = list(lifecycle_run.injected_context)
    target = next((i for i in reversed(range(len(entries))) if entries[i].step == step), None)
    enriched = InjectedContext(
        step=step,
        fragment_ids=entries[target].fragment_ids if target is not None else (),
        refs=entries[target].refs if target is not None else (),
        policies=entries[target].policies if target is not None else (),
        prefix_hash=prefix_hash,
        model=model,
        runtime_kind=runtime_kind,
        output_schema=output_schema,
        gate_result=gate_result,
    )
    if target is None:
        entries.append(enriched)
    else:
        entries[target] = enriched
    return replace_injected_context(lifecycle_run, tuple(entries))


def replace_injected_context(
    lifecycle_run: LifecycleRun,
    entries: tuple[InjectedContext, ...],
) -> LifecycleRun:
    """Return a copy of *lifecycle_run* with its ``injected_context`` replaced.

    Uses ``dataclasses.replace`` so every other field — including the additive
    ``workflow_policy`` governance snapshot (T-28-A-07) — is preserved verbatim. A manual
    reconstruction here previously dropped any new field, which would silently erase the
    run's resolved-policy snapshot.
    """
    return replace(lifecycle_run, injected_context=entries)


def _compact_block_detail(detail: dict[str, str], *, limit: int = 8000) -> str:
    """Render a blocked-detail map as a bounded correction-attempt brief.

    Bounded (bug impl-reviews-retry-prompt-exceeds-codex-window): each value is
    compacted and the whole brief is capped — an unbounded findings dump once pushed
    the retry prompt past the Codex context window. The full findings stay reachable
    through the artifact/diagnostic refs the gate persists in the detail map.
    """

    def _compact(value: str, cap: int = 320) -> str:
        compact = " ".join(value.split())
        if len(compact) <= cap:
            return compact
        return compact[: cap - 3].rstrip() + "..."

    rendered = "\n".join(f"- {key}: {_compact(value)}" for key, value in sorted(detail.items()))
    if len(rendered) > limit:
        rendered = (
            rendered[:limit]
            + "\n- [digest truncated: full findings at the artifact/diagnostic refs above]"
        )
    return rendered


#: Signature fragments that mean the block was caused by an uncreatable Codex sandbox.
#: Matched together, never singly, so prose that merely mentions a sandbox cannot trip it —
#: a false positive here hands the operator a privilege downgrade they never needed.
_SANDBOX_SIGNATURE = ("sandbox-failure signature", "namespace")


#: Environment variables whose absence or wrong value can CAUSE a worker block. When a
#: block's reason names one of these, its remedy has to carry it: an operator pasting the
#: line into a fresh shell has none of the failing run's environment.
_CAUSAL_ENV_VARS = ("CODEX_HOME", "KIMI_CODE_HOME", "CLAUDE_CONFIG_DIR")


def remedy_env_for_reason(reason: str, env: Mapping[str, str]) -> tuple[str, ...]:
    """Every environment assignment a block's remedy must carry, given its reason.

    Bug ``r23-sandbox-block-operator-command-omits-required-bypass``: the block explained
    that ``DADAIA_CODEX_SANDBOX=danger-bypass`` was the fix and then printed a command
    without it, so pasting the command re-ran into the identical failure. That was fixed
    for that one variable — and bug
    ``r25-block-remedy-omits-the-env-var-its-own-reason-names`` is the same defect one
    round later with a different name on it: a live block reading "CODEX_HOME points to a
    directory that did not exist" emitted a remedy with no ``CODEX_HOME`` on it.

    Teaching this function one variable at a time is how the class survives, so the rule is
    now the class: if the reason names a causal variable AND that variable was actually set
    for the failing run, the remedy reproduces it. A variable the reason does not blame is
    never dragged in — the remedy reproduces the CAUSE, it does not dump the environment —
    and one that was never set is never emitted as an empty assignment, which would hand
    back the fill-in-the-blank remedy of ``r18-r20-missing-spec-recovery-placeholder``.

    Detection lives HERE, where the block is built, rather than at each call site. Every
    recovery defect in this ledger got its second life from a rule that lived somewhere the
    next construction site did not have to visit.
    """
    assignments: list[str] = []
    lowered = reason.lower()
    if all(part in lowered for part in _SANDBOX_SIGNATURE):
        assignments.append("DADAIA_CODEX_SANDBOX=danger-bypass")
    for name in _CAUSAL_ENV_VARS:
        if name not in reason:
            continue
        value = env.get(name)
        if value:
            assignments.append(f"{name}={value}")
    return tuple(assignments)


def _safe_filename_segment(value: str) -> str:
    """Sanitize *value* into a single filesystem-safe filename segment.

    ``current_step`` values are internal labels (``"implement"``, ``"review_qa"``, ...)
    but this stays defensive: any character outside ``[A-Za-z0-9._-]`` is replaced with
    ``_`` and path separators can never smuggle a traversal into the run's artifact zone
    (``FilesystemRuntimeFileAdapter._safe_segment`` is the hard backstop either way).
    """
    return "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in value) or "step"


@dataclass(frozen=True)
class AgentRunnerInput:
    """Inputs required to advance a lifecycle run through an agent result."""

    request: AgentRunRequest
    target_phase: LifecyclePhase
    requirements: tuple[GateRequirement, ...] = ()
    resume_token: str | None = None
    current_step: str | None = None
    # Deliverable-zone globs (bug create-step-gate-accepts-refusal-handoff-as-success):
    # when non-empty, at least one artifact ref or changed path must fall INSIDE this
    # zone or the gate BLOCKs — a step whose worker only wrote an explanatory handoff
    # never counts as having delivered.
    deliverable_globs: tuple[str, ...] = ()
    # Delta mode (bug codex-backlog-author-no-materialization-regression-040): when set
    # to a ``{zone-relative-posix-path: sha256}`` map captured BEFORE the step runs, the
    # deliverable check requires a file in the zone that is NEW or whose hash CHANGED —
    # zone-mere-existence (e.g. scaffold files) can never satisfy it. ``None`` keeps the
    # legacy existence semantics for every other step.
    deliverable_before_hashes: dict[str, str] | None = None
    # Whether this is a REVIEW step (v0.1.31 / L1). The verdict gate
    # (``structured_output["verdict"] == "APPROVED"``) applies ONLY to review steps. A
    # create step (``is_review=False``) passes on a schema-valid payload — which is what
    # populates ``artifact_refs`` — + in-scope paths, regardless of the ``verdict`` field
    # (L2 / GRILL D-1/D-2). Threaded from each step's review signal at every call site.
    is_review: bool = False


class LifecycleAgentRunner:
    """Execute one bounded agent request and gate state transitions on evidence."""

    def __init__(
        self,
        *,
        runtime: AgentRuntimePort,
        state_machine: LifecycleStateMachine | None = None,
        runtime_files: RuntimeFilePort | None = None,
        artifact_root: Path | None = None,
    ) -> None:
        self._runtime = runtime
        self._state_machine = state_machine or LifecycleStateMachine()
        # Bug gate-accepts-phantom-artifact-evidence: when injected (production builders
        # pass the workspace root), every declared artifact ref must EXIST under this
        # root or the step BLOCKs — a fabricated ref (e.g. a read-only-sandbox worker
        # that "declared" a handoff it never wrote) is fake evidence, worse than none.
        # ``None`` (unit fixtures) keeps behavior byte-identical.
        self._artifact_root = artifact_root
        # v0.1.78 T-D / FR-D: additive-optional run-artifact writer. When injected, a
        # worker attempt that ends blocked-for-noncompliance AND carries a
        # ``result.diagnostic`` persists it under the run's step-artifact zone and
        # references its path from ``BlockedState.detail["diagnostic_ref"]``. ``None`` (every
        # pre-existing caller) keeps behavior byte-identical — the block still fires, just
        # with no diagnostic_ref (nothing to reference).
        self._runtime_files = runtime_files

    def evaluate_gate(
        self, lifecycle_run: LifecycleRun, data: AgentRunnerInput
    ) -> BlockedState | None:
        """Run the request and return the gate's :class:`BlockedState`, or ``None`` if it passes.

        This is the gate decision *without* a phase transition — used by multi-step
        workflows (WS-5) where several bounded worker steps run inside one phase before
        a single terminal step transitions the release. ``None`` means the gate passed;
        a non-``None`` :class:`BlockedState` carries the rejection/missing-evidence
        reason. The pass condition is **review-only** for the verdict (v0.1.31 / L1): a
        **review** step (``data.is_review``) passes only on an APPROVED verdict with
        in-scope artifact evidence; a **create** step passes on a schema-valid payload
        (populated ``artifact_refs``) + in-scope paths, regardless of the ``verdict``
        field. The pass/block logic is the same as :meth:`run` so reviews gate
        identically whether or not a transition follows.
        """
        _result, blocked = self._execute_with_structural_retry(lifecycle_run, data)
        return blocked

    def evaluate_gate_with_result(
        self, lifecycle_run: LifecycleRun, data: AgentRunnerInput
    ) -> tuple[AgentRunResult, BlockedState | None]:
        """Run the request ONCE and return both the worker result and the gate decision.

        Used by the release-definition workflow (T-30-D-05) when the workflow-step handoff
        resolver is wired: the workflow needs the worker's ``structured_output`` to write
        the immutable step payload, AND the same single run's gate decision. Running the
        worker once and returning both avoids a double execution while keeping the gate
        logic identical to :meth:`evaluate_gate`.
        """
        return self._execute_with_structural_retry(lifecycle_run, data)

    def run(self, lifecycle_run: LifecycleRun, data: AgentRunnerInput) -> TransitionDecision:
        decision, _result = self.run_with_result(lifecycle_run, data)
        return decision

    def run_with_result(
        self, lifecycle_run: LifecycleRun, data: AgentRunnerInput
    ) -> tuple[TransitionDecision, AgentRunResult]:
        """Run the worker ONCE and return both the phase transition AND the raw result.

        v0.1.78 T-B / FR-B: :meth:`run` is the pre-existing transition-only entry point,
        now a thin delegator so every existing caller is byte-identical. A caller that also
        needs the worker's ``AgentRunResult`` (e.g. :class:`LifecyclePipeline` to build a
        run-scoped handoff-ledger payload — the full-pipeline analogue of what
        the implementation workflow gets from
        :meth:`evaluate_gate_with_result`) uses this instead of running the worker a second
        time.
        """
        result, blocked = self._execute_with_structural_retry(lifecycle_run, data)
        if blocked is not None:
            decision = self._state_machine.transition(
                lifecycle_run,
                TransitionInput(
                    target_phase=LifecyclePhase.BLOCKED,
                    blocked_state=blocked,
                    current_step=data.current_step,
                ),
            )
            return decision, result

        decision = self._state_machine.transition(
            lifecycle_run,
            TransitionInput(
                target_phase=data.target_phase,
                evidence=self._evidence_from_result(data.request, result),
                requirements=data.requirements,
                resume_token=data.resume_token,
                current_step=data.current_step,
            ),
        )
        return decision, result

    def _execute_with_structural_retry(
        self, lifecycle_run: LifecycleRun, data: AgentRunnerInput
    ) -> tuple[AgentRunResult, BlockedState | None]:
        """Run once, then make one bounded correction attempt for shape/evidence defects.

        A model can finish a turn without materializing its handoff even though tools are
        available.  That is not a substantive review verdict and should not require an
        operator restart.  The first failed attempt keeps its immutable diagnostic; the
        second receives the exact Python gate reason.  Scope violations, explicit
        REJECTED verdicts, runtime failures, and security findings are never retried here.
        """
        result = self._normalize_context_spec_refs(
            self._recover_exact_worker_output(self._runtime.run(data.request), data.request),
            data.request,
        )
        blocked = self._blocked_result(lifecycle_run, data, result)
        if blocked is None or blocked.reason not in {
            "agent result missing artifact evidence",
            "agent result references nonexistent artifact(s)",
            "agent result missing APPROVED verdict",
            "agent result carries no deliverable in the step's declared zone",
            "agent result carries no NEW or CHANGED deliverable in the step's declared zone",
        }:
            return result, blocked
        detail = _compact_block_detail(blocked.detail)
        correction = (
            "## Automatic structural correction attempt (2 of 2)\n"
            f"The Python gate rejected the first attempt: {blocked.reason}.\n"
            f"{detail}\n"
            "Complete the original step now. Materialize and read back the exact assigned "
            "evidence path, then return one compliant result object. Do not return prose, "
            "a plan, or another unmaterialized reference."
        )
        retry_request = replace(
            data.request,
            prompt=f"{data.request.prompt}\n\n{correction}",
        )
        retry_data = replace(data, request=retry_request)
        retry_result = self._normalize_context_spec_refs(
            self._recover_exact_worker_output(self._runtime.run(retry_request), retry_request),
            retry_request,
        )
        return retry_result, self._blocked_result(lifecycle_run, retry_data, retry_result)

    @staticmethod
    def _materialize_from_parsed(result: AgentRunResult, target: Path) -> bool:
        """Write the canonical worker-output file Python-side from the parsed payload.

        The single most common weak-model failure is emitting a perfectly valid result
        envelope on stdout while skipping the write-the-file ritual. The adapter already
        parsed that envelope into ``domain_payload``/``structured_output`` — blocking
        (or re-running a full worker session) to re-obtain data Python is holding is
        pure waste. When the parsed payload is substantive, Python materializes the
        file itself and the normal promotion path proceeds. Returns True when written.
        """
        # Only a SUBSTANTIVE parsed payload is worth materializing: a bare
        # structured_output (e.g. the adapter's changed-paths stub) would manufacture a
        # vacuous envelope that the named domain validator then rejects — blocking with
        # a confusing schema error instead of the honest missing-artifact retry.
        if not isinstance(result.domain_payload, dict) or not result.domain_payload:
            return False
        payload = dict(result.domain_payload)
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(
                json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )
        except OSError:
            return False
        return True

    def _recover_exact_worker_output(
        self, result: AgentRunResult, request: AgentRunRequest
    ) -> AgentRunResult:
        """Promote the exact assigned raw output into the parsed worker result.

        The on-disk document is authoritative even when the harness final message only
        reports its path. Reading only the Python-assigned path keeps recovery exact;
        recursively redacting secret-named environment values keeps the credential
        boundary intact before the document can enter durable workflow state.
        """
        if self._artifact_root is None or not request.task_id:
            return result
        ref = canonical_worker_output_ref(request.context, request.task_id)
        target = self._artifact_root / ref
        if not target.is_file() and not self._materialize_from_parsed(result, target):
            return result
        try:
            document = json.loads(target.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return result
        if not isinstance(document, dict):
            return result

        secret_values = tuple(
            value
            for key, value in os.environ.items()
            if value
            and any(
                part in key.upper() for part in ("TOKEN", "KEY", "SECRET", "PASSWORD", "CREDENTIAL")
            )
        )

        def redact(value: object) -> object:
            if isinstance(value, str):
                for secret in secret_values:
                    value = value.replace(secret, "[REDACTED]")
                return value
            if isinstance(value, list):
                return [redact(item) for item in value]
            if isinstance(value, dict):
                return {str(key): redact(item) for key, item in value.items()}
            return value

        domain_payload = redact(document)
        assert isinstance(domain_payload, dict)
        structured = dict(result.structured_output)
        for key in ("verdict", "verdict_reason", "commit_sha", "task_group"):
            value = domain_payload.get(key)
            if isinstance(value, str) and value.strip():
                structured[key] = value.strip()
        findings = domain_payload.get("findings")
        if isinstance(findings, list) and findings:
            structured["findings"] = json.dumps(findings, sort_keys=True)
        summary = domain_payload.get("summary")
        if not isinstance(summary, str) or not summary.strip():
            handoff = domain_payload.get("handoff")
            summary = handoff.get("summary") if isinstance(handoff, dict) else None
        if not isinstance(summary, str) or not summary.strip():
            summary = result.summary
        return replace(
            result,
            summary=summary,
            artifact_refs=tuple(dict.fromkeys((*result.artifact_refs, ref))),
            structured_output=structured,
            domain_payload=domain_payload,
            diagnostic=None,
        )

    def _normalize_context_spec_refs(
        self, result: AgentRunResult, request: AgentRunRequest
    ) -> AgentRunResult:
        """Map context-relative ``specs/`` refs to one existing allowed workspace ref.

        Workers operating on a context repo commonly report ``specs/releases/...``
        even though the workflow contract is workspace-relative.  Rewriting is allowed
        only when the request's allowlist yields exactly one existing in-scope candidate;
        this cannot widen scope or make phantom evidence pass.
        """
        if self._artifact_root is None or not result.artifact_refs:
            return result
        normalized: list[str] = []
        changed = False
        root_prefix = str(self._artifact_root.resolve()) + "/"
        for ref in result.artifact_refs:
            # A worker citing its assigned path ABSOLUTELY (under the workspace root)
            # meant the same file — normalize to workspace-relative instead of letting
            # the scope gate reject the run over citation form. Absolute refs outside
            # the workspace root stay as-is and still fail the scope gate.
            if ref.startswith(root_prefix):
                ref = ref[len(root_prefix) :]
                changed = True
            if not ref.startswith("specs/") or (self._artifact_root / ref).exists():
                normalized.append(ref)
                continue
            candidates: set[str] = set()
            for allowed in request.allowed_paths:
                marker = allowed.find("specs/")
                if marker < 0:
                    continue
                candidate = f"{allowed[:marker]}{ref}"
                if (self._artifact_root / candidate).exists() and not out_of_scope_paths(
                    (candidate,),
                    allowed=request.allowed_paths,
                    forbidden=request.forbidden_paths,
                ):
                    candidates.add(candidate)
            if len(candidates) == 1:
                normalized.append(next(iter(candidates)))
                changed = True
            else:
                normalized.append(ref)
        if not changed:
            return result
        return replace(result, artifact_refs=tuple(dict.fromkeys(normalized)))

    def _blocked_result(
        self,
        lifecycle_run: LifecycleRun,
        data: AgentRunnerInput,
        result: AgentRunResult,
    ) -> BlockedState | None:
        if result.status is not AgentRunStatus.SUCCEEDED:
            return self._blocked(lifecycle_run, data, result.error or result.summary, result=result)
        # L1/L2 (v0.1.31): the verdict requirement is a REVIEW concept. A review step must
        # carry ``verdict == "APPROVED"``; a create step (``is_review=False``) is never
        # gated on a self-reported verdict — it passes on a schema-valid payload (which
        # populates ``artifact_refs``) + in-scope paths, regardless of the ``verdict``
        # field. The ``artifact_refs`` check below still BLOCKs a no-op create worker.
        if data.is_review and result.structured_output.get("verdict") != "APPROVED":
            # Diagnostic contract: an explicit non-APPROVED verdict (e.g. REJECTED) is a
            # different operator situation than an absent one — the review *worked* and
            # said no. Name the verdict (and its reason) instead of misreporting it as
            # missing; reserve the "missing" wording for a genuinely absent verdict.
            verdict = result.structured_output.get("verdict")
            if verdict:
                verdict_reason = result.structured_output.get("verdict_reason")
                reason = f"review verdict {verdict}"
                verdict_detail = {"verdict": str(verdict)}
                if verdict_reason:
                    reason = f"{reason}: {verdict_reason}"
                    verdict_detail["verdict_reason"] = str(verdict_reason)
                if result.artifact_refs:
                    # Pointer to the rejecting reviewer's own handoff (full findings) —
                    # consumed by the resume-feedback digest so a revision worker can
                    # open it (bug resumed-definition-step-blind-to-rejecting-review-feedback).
                    verdict_detail["review_artifact_refs"] = ",".join(result.artifact_refs)
                return self._blocked(
                    lifecycle_run, data, reason, detail=verdict_detail, result=result
                )
            return self._blocked(
                lifecycle_run, data, "agent result missing APPROVED verdict", result=result
            )
        if not result.artifact_refs:
            # FR1 (v0.1.68): the FR8 (v0.1.66) role-keyed disk-glob enrichment is RETIRED —
            # it could never be run-scoped (``.dadaia/handoff/<ctx>/*.handoff.json`` files
            # carry no run_id/step in their name or emitter contract, and the per-run
            # step-payload ledger is a different data plane holding no ``.handoff.json``
            # path), so it structurally surfaced an ARBITRARY historical handoff by the same
            # role from a previous task/run — actively misdirecting the operator. When the
            # worker produced no in-result artifact, there is, by construction, no current-run
            # handoff to surface: the detail carries an honest ``no_current_artifact`` marker
            # naming the run and step instead of a fabricated cross-run pointer. This NEVER
            # converts the block into a pass (FR2's no-op invariant is untouched: artifact_refs
            # is still empty, the gate still BLOCKs).
            detail: dict[str, str] = {
                "no_current_artifact": f"{lifecycle_run.run_id}:{data.current_step or lifecycle_run.current_step}"
            }
            return self._blocked(
                lifecycle_run,
                data,
                "agent result missing artifact evidence",
                detail=detail,
                result=result,
            )
        # Bug review-step-out-of-scope-blocks-cited-reviewed-artifact: a review step's
        # artifact_refs CITE what it reviewed (the handoff schema requires artifact.path
        # to name the reviewed artifact) — citations are evidence, not writes. Scope-check
        # a review's actual writes (changed_paths) only; a create step's artifact_refs
        # remain its deliverables and stay fully scope-checked.
        scope_candidates = (
            tuple(self._changed_paths(result))
            if data.is_review
            else (*result.artifact_refs, *self._changed_paths(result))
        )
        out_of_scope = self._out_of_scope_paths(data.request, scope_candidates)
        if out_of_scope:
            return self._blocked(
                lifecycle_run,
                data,
                "agent result contains out-of-scope paths",
                detail={"out_of_scope": ",".join(out_of_scope)},
                result=result,
            )
        if self._artifact_root is not None:
            missing = [
                ref for ref in result.artifact_refs if not (self._artifact_root / ref).exists()
            ]
            if missing:
                return self._blocked(
                    lifecycle_run,
                    data,
                    "agent result references nonexistent artifact(s)",
                    detail={"missing_artifacts": ",".join(missing)},
                    result=result,
                )
        if data.deliverable_globs and self._artifact_root is not None:
            if data.deliverable_before_hashes is not None:
                # Delta mode (bug codex-backlog-author-no-materialization-regression-040):
                # disk truth ONLY — a file in the zone must be NEW or hash-CHANGED vs the
                # pre-step snapshot. Self-reported refs never satisfy this mode, and a
                # zone that was already non-empty (scaffold files) cannot either: a
                # do-nothing worker BLOCKS at THIS step and gets the structural retry.
                delivered = self._zone_delta_files(
                    data.deliverable_globs, data.deliverable_before_hashes
                )
                if not delivered:
                    return self._blocked(
                        lifecycle_run,
                        data,
                        "agent result carries no NEW or CHANGED deliverable in the step's declared zone",
                        detail={"deliverable_zone": ",".join(data.deliverable_globs)},
                        result=result,
                    )
                return None
            candidates = (*result.artifact_refs, *self._changed_paths(result))
            outside = out_of_scope_paths(candidates, allowed=data.deliverable_globs, forbidden=())
            delivered = [path for path in candidates if path not in set(outside)]
            if not delivered:
                # Disk truth beats self-reporting: a worker that wrote its deliverable
                # without citing it in artifact_refs — or one that verified a valid
                # deliverable already present from a prior attempt of this run — still
                # leaves the zone genuinely non-empty. The gate's job is "a deliverable
                # exists for the next review to judge", not "the model repeated the
                # citation ritual". The zone is release-scoped, so a different release's
                # artifacts can never satisfy it.
                delivered = self._zone_files(data.deliverable_globs)
            if not delivered:
                return self._blocked(
                    lifecycle_run,
                    data,
                    "agent result carries no deliverable in the step's declared zone",
                    detail={"deliverable_zone": ",".join(data.deliverable_globs)},
                    result=result,
                )
        return None

    def _zone_files(self, deliverable_globs: tuple[str, ...]) -> list[str]:
        """Files currently present in the step's deliverable zone."""
        if self._artifact_root is None:
            return []
        found: list[str] = []
        for pattern in deliverable_globs:
            clean = pattern.strip().lstrip("/")
            if not clean or ".." in clean.split("/"):
                continue
            # Python 3.13 changed ``**`` to also match files (3.12 matches only
            # directories) — expand explicitly so the disk-truth check is
            # deterministic across interpreter versions.
            variants = {clean}
            if clean.endswith("**"):
                variants.add(clean + "/*")
                variants.add(clean.removesuffix("**") + "*")
            matches_iter: list[Path] = []
            for variant in variants:
                try:
                    matches_iter.extend(self._artifact_root.glob(variant))
                except (OSError, ValueError):
                    continue
            matches = matches_iter
            for path in matches:
                try:
                    if path.is_file():
                        found.append(path.relative_to(self._artifact_root).as_posix())
                except OSError:
                    continue
        return found

    def _zone_delta_files(
        self, deliverable_globs: tuple[str, ...], before_hashes: dict[str, str]
    ) -> list[str]:
        """Zone files that are NEW or whose sha256 CHANGED vs *before_hashes*.

        ``before_hashes`` keys are the same artifact-root-relative posix paths
        :meth:`_zone_files` returns. A file that cannot be read is NOT counted as
        delivered (fail-strict: an unreadable candidate never fakes a deliverable).
        """
        import hashlib

        delivered: list[str] = []
        if self._artifact_root is None:
            return delivered
        for rel in self._zone_files(deliverable_globs):
            before = before_hashes.get(rel)
            if before is None:
                delivered.append(rel)  # NEW file in the zone
                continue
            try:
                current = hashlib.sha256((self._artifact_root / rel).read_bytes()).hexdigest()
            except OSError:
                continue
            if current != before:
                delivered.append(rel)  # CHANGED file in the zone
        return delivered

    def _blocked(
        self,
        lifecycle_run: LifecycleRun,
        data: AgentRunnerInput,
        reason: str,
        *,
        detail: dict[str, str] | None = None,
        result: AgentRunResult | None = None,
    ) -> BlockedState:
        full_detail = dict(detail or {})
        # v0.1.78 T-D / FR-D: persist the worker's diagnostic (when the adapter attached
        # one) and reference its path from the block detail. Additive-optional on BOTH
        # axes — no injected writer, or no diagnostic on this result — leaves the detail
        # exactly as before.
        if self._runtime_files is not None and result is not None and result.diagnostic is not None:
            ref = self._persist_diagnostic(lifecycle_run, data, result.diagnostic)
            if ref is not None:
                full_detail["diagnostic_ref"] = ref
        step = data.current_step or lifecycle_run.current_step
        return BlockedState(
            # Bug r22-release-review-rejection-deadlocks: this is the single most-hit
            # block in the product — every worker-noncompliance path funnels through it —
            # and it prescribed prose ("re-run the workflow with --resume-from X; inspect
            # the step payload ..."), so the validator's stuck review had a correct block
            # and nothing to paste. The run record already carries every field the command
            # needs.
            operator_command=resume_command(
                command=lifecycle_run.command,
                run_id=lifecycle_run.run_id,
                step=step,
                context=lifecycle_run.context,
                release_id=lifecycle_run.release_id or "",
                # An environment-caused block needs its cause ON the line, or pasting the
                # remedy reproduces the failure it came from (r23-sandbox-block-operator-
                # command-omits-required-bypass, then r25-block-remedy-omits-the-env-var-
                # its-own-reason-names for CODEX_HOME).
                env=remedy_env_for_reason(reason, os.environ),
                # The note DESCRIBES what the command does. It used to read "inspect the
                # step payload for the worker's own output first" — an instruction to go
                # do something ELSE before running the line, appended to the one field
                # whose entire contract is "paste this and it fixes it"
                # (r25-block-remedy-omits-the-env-var-its-own-reason-names, same report).
                note="re-runs this step; the earlier attempt stays in the ledger",
            ),
            reason=reason,
            blocked_at_step=step,
            resume_token=lifecycle_run.idempotency_key,
            detail=full_detail,
        )

    def _persist_diagnostic(
        self,
        lifecycle_run: LifecycleRun,
        data: AgentRunnerInput,
        diagnostic: object,
    ) -> str | None:
        """Write *diagnostic* under the run's step-artifact zone; return its workspace ref.

        Never raises: a write failure (e.g. a fixture writer with no real filesystem
        behind it) degrades to ``None`` — an evidence-persistence failure must never crash
        the gate decision itself.
        """
        assert self._runtime_files is not None
        step = data.current_step or lifecycle_run.current_step
        payload = diagnostic.to_dict()  # type: ignore[attr-defined]
        content = json.dumps(payload, indent=2, sort_keys=True) + "\n"
        digest = hashlib.sha256(f"{lifecycle_run.run_id}:{step}:{content}".encode()).hexdigest()[
            :12
        ]
        filename = f"{_safe_filename_segment(step)}-noncompliance-{digest}.json"
        try:
            ref = self._runtime_files.write_run_artifact(
                run_id=lifecycle_run.run_id,
                filename=filename,
                content=content,
            )
        except Exception:  # noqa: BLE001 — evidence persistence is best-effort, never fatal.
            return None
        return ref.path

    @staticmethod
    def _out_of_scope_paths(
        request: AgentRunRequest,
        paths: tuple[str, ...],
    ) -> tuple[str, ...]:
        return out_of_scope_paths(
            paths,
            allowed=request.allowed_paths,
            forbidden=request.forbidden_paths,
        )

    @staticmethod
    def _changed_paths(result: AgentRunResult) -> tuple[str, ...]:
        changed_paths = result.structured_output.get("changed_paths")
        if changed_paths is None or not changed_paths.strip():
            return ()
        return tuple(path.strip() for path in changed_paths.split(",") if path.strip())

    @staticmethod
    def _verdict_from_result(result: AgentRunResult) -> GateVerdict | None:
        verdict = result.structured_output.get("verdict")
        if verdict == GateVerdict.APPROVED.value:
            return GateVerdict.APPROVED
        if verdict == GateVerdict.REJECTED.value:
            return GateVerdict.REJECTED
        return None

    @staticmethod
    def _evidence_from_result(
        request: AgentRunRequest,
        result: AgentRunResult,
    ) -> tuple[GateEvidence, ...]:
        commit_sha = result.structured_output.get("commit_sha")
        task_group = result.structured_output.get("task_group") or request.task_id
        verdict = LifecycleAgentRunner._verdict_from_result(result)
        return tuple(
            GateEvidence(
                evidence_kind=kind,
                source=source,
                context=request.context,
                release_id=request.release_id,
                agent=request.role,
                verdict=verdict,
                commit_sha=commit_sha,
                task_group=task_group,
                metrics={"summary": result.summary},
            )
            for kind, source in zip(request.required_evidence, result.artifact_refs, strict=False)
        )
