"""Bug implementation-review-approves-unexecuted-validation (Hermes real game cycle).

The pipeline closed a release whose final payload listed every pytest command as
"planned / not run" — and the generated environment could not even run pytest. Closure
is a promotion decision: when an executed-test gate is wired, the `close` step now
COMPLETES only on an EXECUTED, GREEN test run (Python-owned evidence, never a worker
self-report). A workspace with no declared tests (gate yields None) is unaffected.
"""

from __future__ import annotations

from pathlib import Path

from dadaia_workspace.core.models.lifecycle import (
    AgentRunRequest,
    AgentRunResult,
    AgentRunStatus,
    AgentRuntimeKind,
    LifecycleRunStatus,
)
from dadaia_workspace.features.lifecycle.pipeline import LifecyclePipeline, implementation_ladder
from dadaia_workspace.features.lifecycle.workflow_handoffs import WorkflowHandoffResolver
from dadaia_workspace.infrastructure.json_lifecycle_run_store import JsonLifecycleRunStore
from dadaia_workspace.infrastructure.runtime_files import FilesystemRuntimeFileAdapter

_CONTEXT = "dadaia-workspace"
_RELEASE = "v0.3.1"


class _ApprovingRuntime:
    def __init__(self) -> None:
        self.received: list[AgentRunRequest] = []

    def runtime_kind(self) -> AgentRuntimeKind:
        return AgentRuntimeKind.FAKE

    def run(self, request: AgentRunRequest) -> AgentRunResult:
        self.received.append(request)
        return AgentRunResult(
            status=AgentRunStatus.SUCCEEDED,
            summary="step complete",
            artifact_refs=(f".dadaia/tmp/lifecycle-worker/{_CONTEXT}/step.step-output.json",),
            structured_output={"verdict": "APPROVED"},
        )


def _pipeline(tmp_path: Path, gate) -> LifecyclePipeline:
    resolver = WorkflowHandoffResolver(
        run_store=JsonLifecycleRunStore(tmp_path),
        payload_writer=FilesystemRuntimeFileAdapter(tmp_path),
        clock=lambda: "2026-07-17T12:00:00Z",
    )
    return LifecyclePipeline(
        context=_CONTEXT,
        release_id=_RELEASE,
        run_store=JsonLifecycleRunStore(tmp_path),
        runtime_factory=lambda kind: _ApprovingRuntime(),  # type: ignore[arg-type,return-value]
        handoff_resolver=resolver,
        executed_test_gate=gate,
    )


def test_close_blocks_when_executed_tests_are_red(tmp_path: Path) -> None:
    pipe = _pipeline(tmp_path, lambda: (False, "1 failed, 3 passed"))

    result = pipe.run("close-red", implementation_ladder(AgentRuntimeKind.FAKE))

    assert result.completed is False
    assert result.blocked is not None
    assert result.blocked.blocked_at_step == "close"
    assert "executed test validation" in result.blocked.reason
    assert "1 failed" in str(result.blocked.detail)
    reloaded = JsonLifecycleRunStore(tmp_path).load("close-red")
    assert reloaded is not None and reloaded.status is LifecycleRunStatus.BLOCKED


def test_close_completes_on_green_executed_tests(tmp_path: Path) -> None:
    pipe = _pipeline(tmp_path, lambda: (True, "12 passed"))
    result = pipe.run("close-green", implementation_ladder(AgentRuntimeKind.FAKE))
    assert result.completed is True


def test_close_unaffected_when_no_tests_are_declared(tmp_path: Path) -> None:
    pipe = _pipeline(tmp_path, lambda: (None, "no test paths declared"))
    result = pipe.run("close-none", implementation_ladder(AgentRuntimeKind.FAKE))
    assert result.completed is True


def test_close_runs_memory_catalog_regenerator(tmp_path: Path) -> None:
    """Bug closure-catalog-references-missing-memory-atom: the catalog is DERIVED from
    memory atoms — closure regenerates it deterministically, so a hand-edited phantom
    entry (feature in catalog.json with no atom) cannot survive the cycle.
    """
    calls: list[str] = []
    resolver = WorkflowHandoffResolver(
        run_store=JsonLifecycleRunStore(tmp_path),
        payload_writer=FilesystemRuntimeFileAdapter(tmp_path),
        clock=lambda: "2026-07-18T12:00:00Z",
    )
    pipe = LifecyclePipeline(
        context=_CONTEXT,
        release_id=_RELEASE,
        run_store=JsonLifecycleRunStore(tmp_path),
        runtime_factory=lambda kind: _ApprovingRuntime(),  # type: ignore[arg-type,return-value]
        handoff_resolver=resolver,
        memory_catalog_regenerator=lambda: calls.append("regenerated"),
    )

    result = pipe.run("close-regen", implementation_ladder(AgentRuntimeKind.FAKE))

    assert result.completed is True
    assert calls == ["regenerated"]


def test_close_blocks_when_memory_lint_gate_fails(tmp_path: Path) -> None:
    """Bug closure-allows-memory-doctor-warnings: closure leaves memory lint-clean or
    refuses — a worker-authored atom with invalid headings never rides a green close.
    """
    resolver = WorkflowHandoffResolver(
        run_store=JsonLifecycleRunStore(tmp_path),
        payload_writer=FilesystemRuntimeFileAdapter(tmp_path),
        clock=lambda: "2026-07-18T12:00:00Z",
    )
    pipe = LifecyclePipeline(
        context=_CONTEXT,
        release_id=_RELEASE,
        run_store=JsonLifecycleRunStore(tmp_path),
        runtime_factory=lambda kind: _ApprovingRuntime(),  # type: ignore[arg-type,return-value]
        handoff_resolver=resolver,
        memory_lint_gate=lambda: (False, "WARN: unknown '## Historia' heading"),
    )

    result = pipe.run("close-memlint", implementation_ladder(AgentRuntimeKind.FAKE))

    assert result.completed is False
    assert result.blocked is not None and result.blocked.blocked_at_step == "close"
    assert "memory" in result.blocked.reason


def test_close_runs_repo_hygiene_sweeper_on_completion(tmp_path: Path) -> None:
    """Bug lifecycle-workflows-leave-python-bytecode-in-repo: a completed cycle sweeps
    cache dirs (__pycache__, .pytest_cache, ...) out of the context repo.
    """
    calls: list[str] = []
    resolver = WorkflowHandoffResolver(
        run_store=JsonLifecycleRunStore(tmp_path),
        payload_writer=FilesystemRuntimeFileAdapter(tmp_path),
        clock=lambda: "2026-07-18T12:00:00Z",
    )
    pipe = LifecyclePipeline(
        context=_CONTEXT,
        release_id=_RELEASE,
        run_store=JsonLifecycleRunStore(tmp_path),
        runtime_factory=lambda kind: _ApprovingRuntime(),  # type: ignore[arg-type,return-value]
        handoff_resolver=resolver,
        repo_hygiene_sweeper=lambda: calls.append("swept"),
    )

    result = pipe.run("close-sweep", implementation_ladder(AgentRuntimeKind.FAKE))

    assert result.completed is True
    assert calls == ["swept"]


def test_pipeline_resume_from_close_keeps_upstream_ledger(tmp_path: Path) -> None:
    """Bug implementation-reviews-resume-token-without-cli-resume: a blocked run resumes
    from the named step; upstream ledger records survive and only the resumed step
    onward re-executes.
    """
    resolver = WorkflowHandoffResolver(
        run_store=JsonLifecycleRunStore(tmp_path),
        payload_writer=FilesystemRuntimeFileAdapter(tmp_path),
        clock=lambda: "2026-07-18T12:00:00Z",
    )
    gate_results = iter([(False, "1 failed"), (True, "12 passed")])
    pipe = LifecyclePipeline(
        context=_CONTEXT,
        release_id=_RELEASE,
        run_store=JsonLifecycleRunStore(tmp_path),
        runtime_factory=lambda kind: _ApprovingRuntime(),  # type: ignore[arg-type,return-value]
        handoff_resolver=resolver,
        executed_test_gate=lambda: next(gate_results),
    )

    first = pipe.run("resume-close", implementation_ladder(AgentRuntimeKind.FAKE))
    assert first.completed is False and first.blocked is not None
    assert first.blocked.blocked_at_step == "close"

    resumed = pipe.run(
        "resume-close", implementation_ladder(AgentRuntimeKind.FAKE), resume_from="close"
    )
    assert resumed.completed is True
    run = JsonLifecycleRunStore(tmp_path).load("resume-close")
    assert run is not None
    producers = {r.producer_step for r in run.workflow_steps.records}
    assert "implement" in producers, sorted(producers)


def _seed_close_zone(tmp_path: Path) -> Path:
    specs = tmp_path / "repos" / _CONTEXT / "specs"
    (specs / "memory").mkdir(parents=True, exist_ok=True)
    (specs / "releases" / _RELEASE).mkdir(parents=True, exist_ok=True)
    (specs / "memory" / "architecture.md").write_text("# arch original\n", encoding="utf-8")
    (specs / "releases" / "ACTIVE.md").write_text(
        f"release: {_RELEASE}\nphase: IMPLEMENTATION\n", encoding="utf-8"
    )
    return specs


class _ClosureWritingRuntime(_ApprovingRuntime):
    """Approves every step; the close step ALSO mutates the closure zone (the live shape)."""

    def __init__(self, specs: Path) -> None:
        super().__init__()
        self._specs = specs

    def run(self, request: AgentRunRequest) -> AgentRunResult:
        label = (request.task_id or "").split(":")[1] if ":" in (request.task_id or "") else ""
        if label == "close":
            (self._specs / "releases" / _RELEASE / "CLOSURE.md").write_text(
                "# CLOSURE draft\n", encoding="utf-8"
            )
            (self._specs / "memory" / "architecture.md").write_text(
                "# arch REWRITTEN by close worker\n", encoding="utf-8"
            )
        return super().run(request)


def test_blocked_close_is_transactional_and_preserves_active(tmp_path: Path) -> None:
    """Bugs blocked-close-materializes-closure-and-leaves-specs-incoherent +
    implementation-close-block-resets-active-release-and-breaks-resume: a BLOCKED close
    rolls back the closure-zone writes (CLOSURE.md, memory) and never touches ACTIVE.md.
    """
    specs = _seed_close_zone(tmp_path)
    resolver = WorkflowHandoffResolver(
        run_store=JsonLifecycleRunStore(tmp_path),
        payload_writer=FilesystemRuntimeFileAdapter(tmp_path),
        clock=lambda: "2026-07-18T12:00:00Z",
    )
    pipe = LifecyclePipeline(
        context=_CONTEXT,
        release_id=_RELEASE,
        run_store=JsonLifecycleRunStore(tmp_path),
        runtime_factory=lambda kind: _ClosureWritingRuntime(specs),  # type: ignore[arg-type,return-value]
        handoff_resolver=resolver,
        specs_dir=specs,
        memory_lint_gate=lambda: (False, "WARN: bad heading"),
    )

    result = pipe.run("close-txn", implementation_ladder(AgentRuntimeKind.FAKE))

    assert result.completed is False
    assert result.blocked is not None and result.blocked.blocked_at_step == "close"
    # Transactional rollback: closure artifacts gone, memory restored, ACTIVE intact.
    assert not (specs / "releases" / _RELEASE / "CLOSURE.md").exists()
    assert (specs / "memory" / "architecture.md").read_text(encoding="utf-8") == (
        "# arch original\n"
    )
    active = (specs / "releases" / "ACTIVE.md").read_text(encoding="utf-8")
    assert _RELEASE in active and "IMPLEMENTATION" in active


def test_completed_close_resets_active_md_python_owned(tmp_path: Path) -> None:
    """ACTIVE.md is a Python-owned effect of a SUCCESSFUL close — never the worker's."""
    specs = _seed_close_zone(tmp_path)
    resolver = WorkflowHandoffResolver(
        run_store=JsonLifecycleRunStore(tmp_path),
        payload_writer=FilesystemRuntimeFileAdapter(tmp_path),
        clock=lambda: "2026-07-18T12:00:00Z",
    )
    pipe = LifecyclePipeline(
        context=_CONTEXT,
        release_id=_RELEASE,
        run_store=JsonLifecycleRunStore(tmp_path),
        runtime_factory=lambda kind: _ClosureWritingRuntime(specs),  # type: ignore[arg-type,return-value]
        handoff_resolver=resolver,
        specs_dir=specs,
    )

    result = pipe.run("close-active", implementation_ladder(AgentRuntimeKind.FAKE))

    assert result.completed is True
    active = (specs / "releases" / "ACTIVE.md").read_text(encoding="utf-8")
    assert "release: none" in active and "phase: none" in active


def test_memory_lint_gate_rejects_atom_without_heading(tmp_path: Path) -> None:
    """Bug closure-generates-memory-atom-without-heading: the close gate must catch a
    heading-less atom (doctor SPEC-DOC-002) — not only allowlist violations.
    """
    from dadaia_workspace.container import _memory_lint_gate

    specs = tmp_path / "specs"
    (specs / "memory").mkdir(parents=True)
    (specs / "memory" / "architecture.md").write_text(
        "---\nslug: architecture\ntitle: A\ncategory: core\ntldr: t\nsummary: s\n"
        'tags: [a]\ntoken_estimate: 10\nlast_updated: "2026-01-01"\n'
        "release_origin: x\n---\n\nCorpo sem nenhum heading markdown.\n",
        encoding="utf-8",
    )

    gate = _memory_lint_gate(specs)
    assert gate is not None
    ok, evidence = gate()
    assert ok is False
    assert "heading" in evidence.lower()


def test_memory_lint_gate_rejects_product_atom_without_heading(tmp_path: Path) -> None:
    """The EXACT live shape: a product-area atom with valid frontmatter and a body
    carrying no markdown heading at all (doctor SPEC-DOC-002)."""
    from dadaia_workspace.container import _memory_lint_gate

    specs = tmp_path / "specs"
    area = specs / "memory" / "product" / "console-game"
    area.mkdir(parents=True)
    (area / "valgame-console-game.md").write_text(
        "---\nslug: valgame-console-game\ntitle: Valgame\ncategory: product\ntldr: t\n"
        'summary: s\ntags: [game]\ntoken_estimate: 10\nlast_updated: "2026-01-01"\n'
        "release_origin: v0.1.0\n---\n\nDescricao do jogo sem nenhum heading.\n",
        encoding="utf-8",
    )

    gate = _memory_lint_gate(specs)
    assert gate is not None
    ok, evidence = gate()
    assert ok is False, evidence
    assert "heading" in evidence.lower()
