"""Anti-fake real-worker e2e — a real `pi` Layer-2 worker advances through a real review/gate step.

This is the core deliverable of releases v0.1.31 (SPEC Cluster 4 / L6, the anti-fake law)
and v0.1.32 Wave C (SPEC L6 / D-6, prove the review path live): at least ONE e2e drives a
**real** (non-fake) Layer-2 worker through a real dadaia-workflow so that a fake runtime —
which returns a canned ``{"verdict":"APPROVED"}`` regardless of the prompt — can never
again mask a worker-contract break end-to-end. v0.1.31 proved a real worker *advances past
step 1* (the two create steps that were the shipped-failure path); v0.1.32 Wave C extends
the chain to a real **review/gate step** so the Python verdict gate fires on real worker
output (A13/A14).

The chain (v0.1.32 Wave C, T-32-C-01) is ``release_scope`` → ``spec_create`` →
``spec_arch_review`` → terminal ``definition_commit_gate``, sliced VERBATIM from the
shipped ``_SEQUENCE`` (no fabricated steps). ``release_scope`` + ``spec_create`` are the
EXACT shipped-failure create path the two v0.1.31 bugs blocked; ``spec_arch_review`` is the
first real ``is_review=True`` step — the first step whose ``verdict`` the Python gate reads:

  * ``pi-headless-command-trailing-dash-breaks-layer2`` — the malformed ``pi … -p -``
    argv (now ``-p``, ``c8513fa5``) BLOCKed every PI step at the command itself;
  * ``lifecycle-workflows-never-pass-real-layer2-worker-verdict-gate`` — after the command
    fix, ``release_scope`` (a *create* step) BLOCKed with
    ``"agent result missing APPROVED verdict"`` because the always-verdict gate wrongly
    demanded a verdict from a create step. v0.1.31 Wave A scoped the verdict gate to
    **review** steps; a create step now passes on a schema-valid payload + in-scope paths,
    and a review step (``spec_arch_review``) is gated on its real APPROVED verdict.

Two e2e tests live here, both env-gated + SKIPPED by default:
  * ``test_real_pi_worker_advances_past_release_scope_to_spec_create`` (v0.1.31) — proves a
    real worker advances past the create steps with no missing-verdict block.
  * ``test_real_pi_worker_review_step_emits_approved_and_gate_passes`` (v0.1.32 Wave C /
    T-32-C-02) — proves the real worker emits a real APPROVED verdict on ``spec_arch_review``
    and the Python verdict gate fires on real output and PASSES.

Both assert CONCRETE state, NOT "no exception" (SPEC R-C / A14): the review step ran,
yielded a parsed ``SUCCEEDED`` result whose ``verdict == APPROVED`` reached the gate, and
the gate did NOT block. They are built on the REAL :class:`ReleaseDefinitionWorkflow`
driven through the truncated ``_SEQUENCE`` slice against a throwaway ``tmp_path`` specs
tree — the real ``specs/`` is never mutated. The runtime factory is the container seam
``build_agent_runtime(PI_HEADLESS, cwd=sandbox)``, so the worker is a genuine
:class:`PiHeadlessAdapter`, not a fake.

They spend operator model credits, so they are strictly OPT-IN and SKIPPED by default
(D-4/D-6 / A13/A16): a default ``pytest`` / CI run collects them and skips — fully faked +
green. They auto-SKIP unless ALL of:

  * ``DADAIA_E2E_REAL_WORKER=1`` (explicit operator consent — the single Wave-B/C gate);
  * the ``pi`` binary is present on PATH (or via ``PI_BIN``);
  * ``pi`` is authenticated — ``~/.pi/agent/auth.json`` exists (``pi login``). pi runs on
    the operator's OpenAI Codex subscription (provider ``openai-codex``), NOT on an
    ``ANTHROPIC_API_KEY``.

Run the live review-path proof on demand (from the dadaia-workspace repo root, with the
workspace venv) — A16:

    DADAIA_E2E_REAL_WORKER=1 PI_BIN="$(command -v pi)" \\
      /home/marco/workspace/dadaia/.dadaia/.venv/bin/pytest -p no:cacheprovider -q -s \\
      tests/integration/pi_live/test_real_layer2_worker_workflow_e2e.py
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytest

from dadaia_workspace import container
from dadaia_workspace.core.models.lifecycle import (
    AgentRuntimeKind,
    LifecyclePhase,
    LifecycleRun,
)
from dadaia_workspace.core.protocols.agent_runtime import AgentRuntimePort
from dadaia_workspace.core.protocols.lifecycle_run_store import LifecycleRunStoreError
from dadaia_workspace.features.lifecycle.context_selector import (
    ContextSelector,
    SpecContext,
)
from dadaia_workspace.features.lifecycle.workflows.release_definition import (
    _SEQUENCE,
    ReleaseDefinitionResult,
    ReleaseDefinitionWorkflow,
    ReleaseStep,
)

pytestmark = [pytest.mark.integration, pytest.mark.slow]

_CONTEXT = "dadaia-workspace"
_RELEASE = "v0.1.31"
_MISSING_VERDICT = "agent result missing APPROVED verdict"


def _pi_binary() -> str | None:
    explicit = os.environ.get("PI_BIN")
    if explicit:
        return explicit
    return shutil.which("pi")


def _real_worker_skip_reason() -> str | None:
    """Return a skip reason string, or None when all live preconditions hold.

    Gated on the SHARED ``DADAIA_E2E_REAL_WORKER`` flag (GRILL D-4) plus the live ``pi``
    preconditions — identical to the Wave-B command smoke so one operator opt-in enables
    both.
    """
    if os.environ.get("DADAIA_E2E_REAL_WORKER") != "1":
        return "DADAIA_E2E_REAL_WORKER != 1 (real-worker tests spend operator credits; opt-in only)"
    if _pi_binary() is None:
        return "pi binary absent (install @earendil-works/pi-coding-agent or set PI_BIN)"
    if not (Path.home() / ".pi" / "agent" / "auth.json").exists():
        return "pi not authenticated (~/.pi/agent/auth.json absent — run `pi login`)"
    return None


requires_real_worker = pytest.mark.skipif(
    _real_worker_skip_reason() is not None,
    reason=_real_worker_skip_reason() or "real-worker preconditions unmet",
)


class _MemoryRunStore:
    """In-memory ``LifecycleRunStore`` — keeps the e2e self-contained (no disk I/O)."""

    def __init__(self) -> None:
        self.saved: dict[str, LifecycleRun] = {}

    def save(self, run: LifecycleRun) -> None:
        self.saved[run.run_id] = run

    def load(self, run_id: str) -> LifecycleRun | None:
        return self.saved.get(run_id)

    def resume(self, run_id: str) -> LifecycleRun:
        run = self.saved.get(run_id)
        if run is None:
            raise LifecycleRunStoreError(message="missing", path=None)
        return run


def _sandbox_root() -> Path:
    """Throwaway worker cwd under the workspace ``.dadaia/tmp`` landing zone.

    Resolved relative to this file: tests/integration/pi_live ->
    repos/dadaia-workspace -> repos -> <workspace-root>.
    """
    workspace_root = Path(__file__).resolve().parents[5]
    root = workspace_root / ".dadaia" / "tmp" / "software-engineer" / "real_worker_e2e_harness"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _specs_tree(tmp_path: Path) -> Path:
    """A minimal throwaway specs tree the context selector resolves dynamic inputs against.

    Created under ``tmp_path`` — the real ``specs/`` is NEVER touched.
    """
    specs = tmp_path / "repos" / _CONTEXT / "specs"
    (specs / "memory" / "product").mkdir(parents=True)
    (specs / "releases" / _RELEASE).mkdir(parents=True)
    (specs / "constitution.md").write_text("# constitution\n", encoding="utf-8")
    (specs / "memory" / "architecture.md").write_text("# architecture\n", encoding="utf-8")
    (specs / "memory" / "quality-assurance.md").write_text("# qa\n", encoding="utf-8")
    (specs / "memory" / "product" / "catalog.json").write_text('{"features": []}', encoding="utf-8")
    (specs / "releases" / _RELEASE / "SPEC.md").write_text("# spec\n", encoding="utf-8")
    return specs


def _truncated_sequence() -> tuple[ReleaseStep, ...]:
    """The Wave-C chain ``release_scope`` → ``spec_create`` → ``spec_arch_review`` + commit gate.

    Sliced VERBATIM from the shipped ``_SEQUENCE`` (no fabricated steps; T-32-C-01):

      * ``release_scope`` + ``spec_create`` — the two real create steps that are the
        v0.1.31 shipped-failure path (the create-step gate must pass with no verdict);
      * ``spec_arch_review`` — the FIRST real ``is_review=True`` step (asserted below), so
        the chain now includes ≥1 review/gate step whose ``verdict`` the Python gate reads
        on real worker output (A13);
      * the terminal Python ``definition_commit_gate`` so the workflow completes cleanly
        when every prior step passes.

    The remaining review/create steps of the full 9-step sequence are omitted — the proof
    is "advances through a real review/gate step", not the whole sequence (SPEC: a full
    all-steps real run is explicitly out of scope unless PLAN selects it; PLAN selected the
    create→review pair).
    """
    by_label = {step.label: step for step in _SEQUENCE}
    release_scope = by_label["release_scope"]
    spec_create = by_label["spec_create"]
    spec_arch_review = by_label["spec_arch_review"]
    commit_gate = by_label["definition_commit_gate"]
    # Verbatim-slice invariant: ``spec_arch_review`` is the FIRST real review step in the
    # shipped sequence, so the chain genuinely exercises the verdict gate (A13). If a future
    # _SEQUENCE reorder makes a different step the first review step, this assertion fires
    # rather than the chain silently dropping its only review/gate step.
    first_review = next(step for step in _SEQUENCE if step.is_review)
    assert first_review.label == "spec_arch_review", (
        "spec_arch_review is no longer the first review step in _SEQUENCE — "
        f"first review step is now {first_review.label!r}; re-slice the Wave-C chain"
    )
    assert spec_arch_review.is_review is True
    return (release_scope, spec_create, spec_arch_review, commit_gate)


def _real_pi_factory(sandbox: Path) -> object:
    """Return a runtime factory that builds a REAL ``PiHeadlessAdapter`` per kind.

    The factory is the container seam ``build_agent_runtime`` bound to the throwaway
    sandbox cwd — the workflow asks for ``PI_HEADLESS`` (the default kind below) and gets
    a genuine subprocess-backed adapter, never the fake.
    """

    def factory(kind: AgentRuntimeKind) -> AgentRuntimePort:
        return container.build_agent_runtime(kind, cwd=sandbox)

    return factory


@requires_real_worker
def test_real_pi_worker_advances_past_release_scope_to_spec_create(tmp_path: Path) -> None:
    """A real ``pi`` worker runs ``release_scope`` and the run advances to ``spec_create``.

    Concrete post-step-1 assertions (A15) — never "no exception":
      (a) the real command executed (the worker produced a parsed result, not a fake);
      (b) ``release_scope`` is NOT blocked and yields a parsed SUCCEEDED step;
      (c) the run carries NO ``"agent result missing APPROVED verdict"`` BlockedState;
      (d) the run advanced BEYOND ``release_scope`` (``spec_create`` was reached/ran).
    """
    store = _MemoryRunStore()
    specs = _specs_tree(tmp_path)
    sandbox = _sandbox_root()
    selector = ContextSelector(
        SpecContext(specs_dir=specs, release_id=_RELEASE, handoff_dir=tmp_path / "handoff")
    )
    workflow = ReleaseDefinitionWorkflow(
        context=_CONTEXT,
        release_id=_RELEASE,
        run_store=store,
        runtime_factory=_real_pi_factory(sandbox),  # type: ignore[arg-type]
        context_selector=selector,
        # Drive the REAL PI Layer-2 worker (not the FAKE default).
        default_runtime_kind=AgentRuntimeKind.PI_HEADLESS,
    )

    result: ReleaseDefinitionResult = workflow.run(
        "real-worker-e2e-1", sequence=_truncated_sequence()
    )

    steps_by_label = {step.label: step for step in result.steps}

    # (a) the real command executed — release_scope produced a step result at all.
    assert "release_scope" in steps_by_label, "release_scope never ran (real command not executed)"
    release_scope = steps_by_label["release_scope"]

    # (b) release_scope is NOT blocked (it parsed a SUCCEEDED AgentRunResult under the
    #     review-only create-step gate).
    assert release_scope.blocked is None, (
        "release_scope BLOCKED unexpectedly: "
        f"{release_scope.blocked.reason if release_scope.blocked else ''}"
    )
    assert release_scope.accepted is True

    # (c) NO missing-APPROVED-verdict BlockedState anywhere on the run — the create step
    #     passed under D-1/D-2 with no self-reported verdict (the exact shipped failure).
    assert release_scope.blocked is None or _MISSING_VERDICT not in release_scope.blocked.reason
    final_run = store.load("real-worker-e2e-1")
    assert final_run is not None
    if final_run.blocked is not None:
        assert _MISSING_VERDICT not in final_run.blocked.reason, (
            f"run blocked on the v0.1.31 shipped-failure reason: {final_run.blocked.reason}"
        )

    # (d) the run ADVANCED BEYOND release_scope — spec_create was reached and ran.
    assert "spec_create" in steps_by_label, "run did not advance past release_scope to spec_create"
    assert final_run.phase is not LifecyclePhase.RELEASE_DEFINITION or result.completed, (
        "run never advanced beyond the first phase step"
    )


@requires_real_worker
def test_real_pi_worker_review_step_emits_approved_and_gate_passes(tmp_path: Path) -> None:
    """A real ``pi`` worker emits a real APPROVED verdict on ``spec_arch_review`` and the gate PASSES.

    The v0.1.32 Wave C core proof (T-32-C-02 / A14): the chain now reaches a real
    ``is_review=True`` step, so the Python verdict gate fires on REAL worker output. Concrete
    state, never "no exception":

      (a) ``spec_arch_review`` ran (the real review-step command executed);
      (b) it yielded a parsed ``SUCCEEDED`` result carrying ``verdict == APPROVED`` from the
          real worker — proven via the step's NOT being blocked (the verdict gate BLOCKs a
          review step unless ``structured_output["verdict"] == "APPROVED"``) AND the run's
          recorded gate verdict for the step being ``APPROVED``;
      (c) the run is NOT blocked at ``spec_arch_review`` — the verdict gate fired on real
          output and PASSED (no ``"agent result missing APPROVED verdict"`` block).

    R5 (CLOSURE residual): records whether STRICT (``schema == agent-run-result-v1``) or the
    STRUCTURAL fallback carried acceptance. The final ``AgentRunResult.structured_output``
    does not preserve the raw ``schema`` field, so the strongest observable signal here is
    whether the review step passed at all (it did → the extractor accepted the payload via
    one of the two paths) plus the printed structured_output for the operator to record the
    exact path at CLOSURE. Asserted via message + an emitted line, not a docstring (R5).
    """
    store = _MemoryRunStore()
    specs = _specs_tree(tmp_path)
    sandbox = _sandbox_root()
    selector = ContextSelector(
        SpecContext(specs_dir=specs, release_id=_RELEASE, handoff_dir=tmp_path / "handoff")
    )
    workflow = ReleaseDefinitionWorkflow(
        context=_CONTEXT,
        release_id=_RELEASE,
        run_store=store,
        runtime_factory=_real_pi_factory(sandbox),  # type: ignore[arg-type]
        context_selector=selector,
        # Drive the REAL PI Layer-2 worker (not the FAKE default).
        default_runtime_kind=AgentRuntimeKind.PI_HEADLESS,
    )

    result: ReleaseDefinitionResult = workflow.run(
        "real-worker-review-e2e-1", sequence=_truncated_sequence()
    )

    steps_by_label = {step.label: step for step in result.steps}

    # (a) spec_arch_review ran — the real review-step command executed.
    assert "spec_arch_review" in steps_by_label, (
        "spec_arch_review never ran — the run did not reach the review step "
        f"(reached: {sorted(steps_by_label)})"
    )
    review = steps_by_label["spec_arch_review"]
    assert review.is_gate is True, "spec_arch_review must be evaluated as a review/gate step"

    # (c) the verdict gate fired on REAL output and PASSED — spec_arch_review is NOT blocked.
    assert review.blocked is None, (
        "spec_arch_review BLOCKED on real worker output: "
        f"{review.blocked.reason if review.blocked else ''}"
    )
    assert review.accepted is True

    # (b) the parsed SUCCEEDED result carried verdict == APPROVED — proven by the run's
    #     recorded gate verdict for spec_arch_review being APPROVED. A review step can ONLY
    #     pass the gate when structured_output["verdict"] == "APPROVED" (agent_runner L1),
    #     so an APPROVED gate_result is exactly "a real SUCCEEDED result with verdict
    #     APPROVED reached the gate".
    final_run = store.load("real-worker-review-e2e-1")
    assert final_run is not None
    review_audit = next(
        (e for e in reversed(final_run.injected_context) if e.step == "spec_arch_review"),
        None,
    )
    assert review_audit is not None, "no prompt-composition audit recorded for spec_arch_review"
    assert review_audit.gate_result == "APPROVED", (
        "spec_arch_review gate verdict was not APPROVED on real worker output: "
        f"{review_audit.gate_result!r}"
    )

    # The run is NOT blocked anywhere on the missing-verdict reason (the v0.1.31 failure mode).
    if final_run.blocked is not None:
        assert _MISSING_VERDICT not in final_run.blocked.reason, (
            f"run blocked on the missing-APPROVED-verdict reason: {final_run.blocked.reason}"
        )

    # R5 — record whether STRICT or STRUCTURAL acceptance carried the payload. The final
    # AgentRunResult.structured_output does not preserve the raw `schema` transport id, so we
    # emit the recorded structured_output / gate verdict for the operator to classify the
    # exact path at CLOSURE. The presence of an APPROVED verdict at the gate proves the
    # extractor accepted the verdict-carrying payload via STRICT or STRUCTURAL — both are a
    # coherent-contract success; a strict-vs-fallback distinction is a CLOSURE residual (R5).
    print(  # noqa: T201 — operator-facing R5 record (run with -s)
        "[R5] spec_arch_review accepted with gate verdict "
        f"{review_audit.gate_result!r}; output_schema={review_audit.output_schema!r}; "
        "record strict-vs-structural acceptance at CLOSURE from the live worker output."
    )
