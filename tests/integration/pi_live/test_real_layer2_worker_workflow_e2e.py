"""Anti-fake real-worker e2e — a real `pi` Layer-2 worker advances past step 1 (T-31-C-01).

This is the core deliverable of release v0.1.31 (SPEC Cluster 4 / L6, the anti-fake law):
at least ONE e2e drives a **real** (non-fake) Layer-2 worker through a real
dadaia-workflow so that a fake runtime — which returns a canned ``{"verdict":"APPROVED"}``
regardless of the prompt — can never again mask a worker-contract break end-to-end.

The chain is the **fixed minimal** ``release_scope`` → ``spec_create`` — the EXACT
shipped-failure path the two bugs blocked (GRILL OQ-3, fixed by QA review; no alternative
chain):

  * ``pi-headless-command-trailing-dash-breaks-layer2`` — the malformed ``pi … -p -``
    argv (now ``-p``, ``c8513fa5``) BLOCKed every PI step at the command itself;
  * ``lifecycle-workflows-never-pass-real-layer2-worker-verdict-gate`` — after the command
    fix, ``release_scope`` (a *create* step) BLOCKed with
    ``"agent result missing APPROVED verdict"`` because the always-verdict gate wrongly
    demanded a verdict from a create step. Wave A scoped the verdict gate to **review**
    steps; a create step now passes on a schema-valid payload + in-scope paths.

This e2e asserts CONCRETE post-step-1 state, NOT "no exception" (SPEC R-C / A15):
  (a) the real ``pi`` command actually executed (catches the D-3 class of bug);
  (b) the ``release_scope`` step is NOT blocked and yields a parsed ``SUCCEEDED`` result;
  (c) the run carries NO ``"agent result missing APPROVED verdict"`` BlockedState;
  (d) the run advanced BEYOND ``release_scope`` (reached / ran ``spec_create``).

It is built on the REAL :class:`ReleaseDefinitionWorkflow` driven through a truncated
``_SEQUENCE`` (``release_scope`` → ``spec_create`` → terminal Python commit gate) against a
throwaway ``tmp_path`` specs tree — the real ``specs/`` is never mutated. The runtime
factory is the container seam ``build_agent_runtime(PI_HEADLESS, cwd=sandbox)``, so the
worker is a genuine :class:`PiHeadlessAdapter`, not a fake.

It spends operator model credits, so it is strictly OPT-IN and SKIPPED by default (D-4 /
A14 / A17): a default ``pytest`` / CI run collects it and skips — fully faked + green. It
auto-SKIPs unless ALL of:

  * ``DADAIA_E2E_REAL_WORKER=1`` (explicit operator consent — the single Wave-B/C gate);
  * the ``pi`` binary is present on PATH (or via ``PI_BIN``);
  * ``ANTHROPIC_API_KEY`` is set (pi is authenticated).

Run it on demand (from the dadaia-workspace repo root, with the workspace venv):

    DADAIA_E2E_REAL_WORKER=1 PI_BIN="$(command -v pi)" ANTHROPIC_API_KEY=... \\
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
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return "ANTHROPIC_API_KEY absent (pi is not authenticated)"
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
    """The fixed minimal chain ``release_scope`` → ``spec_create`` + terminal commit gate.

    Sliced verbatim from the shipped ``_SEQUENCE`` (no fabricated steps): the two real
    create steps that are the shipped-failure path, plus the terminal Python
    ``definition_commit_gate`` so the workflow can complete cleanly when both pass. The
    intermediate review steps are omitted — the proof is "advances past step 1", not the
    whole 9-step sequence (SPEC: a full all-steps real run is explicitly out of scope).
    """
    by_label = {step.label: step for step in _SEQUENCE}
    release_scope = by_label["release_scope"]
    spec_create = by_label["spec_create"]
    commit_gate = by_label["definition_commit_gate"]
    return (release_scope, spec_create, commit_gate)


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
