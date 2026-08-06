"""Bug implementation-review-approves-unexecuted-validation (Consumer real game cycle).

The pipeline closed a release whose final payload listed every pytest command as
"planned / not run" — and the generated environment could not even run pytest. Closure
is a promotion decision: when an executed-test gate is wired, the `close` step now
COMPLETES only on an EXECUTED, GREEN test run (Python-owned evidence, never a worker
self-report). A workspace with no declared tests (gate yields None) is unaffected.
"""

from __future__ import annotations

from pathlib import Path

import pytest

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


def test_pipeline_emits_step_progress_on_stderr(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Bug release-definition-codex-hangs-after-spec-create (operator-visible half):
    a multi-minute live run used to be SILENT until the end, so validators killed
    healthy workers. Every engine now emits per-step progress on stderr (stdout stays
    machine-pure for --json).
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
    )

    result = pipe.run("progress-run", implementation_ladder(AgentRuntimeKind.CODEX_EXEC))

    assert result.completed is True
    err = capsys.readouterr().err
    assert "[lifecycle]" in err
    assert "implement" in err and "close" in err
    assert "1/3" in err and "3/3" in err


def test_implement_requires_delivery_inside_declared_write_set(tmp_path: Path) -> None:
    """Bug lifecycle-worker-executes-at-workspace-root-not-context-repo: an implement
    worker that writes OUTSIDE the release write set (workspace-root src/ instead of
    repos/<ctx>/) used to be accepted on its step-output envelope alone. When the step
    declares a write set, at least one delivered path must fall inside it.
    """
    from dataclasses import replace as _replace

    resolver = WorkflowHandoffResolver(
        run_store=JsonLifecycleRunStore(tmp_path),
        payload_writer=FilesystemRuntimeFileAdapter(tmp_path),
        clock=lambda: "2026-07-18T12:00:00Z",
    )

    class _MaterializingRuntime(_ApprovingRuntime):
        def run(self, request: AgentRunRequest) -> AgentRunResult:
            result = super().run(request)
            for ref in result.artifact_refs:
                target = tmp_path / ref
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text('{"fake": true}', encoding="utf-8")
            return result

    pipe = LifecyclePipeline(
        context=_CONTEXT,
        release_id=_RELEASE,
        run_store=JsonLifecycleRunStore(tmp_path),
        runtime_factory=lambda kind: _MaterializingRuntime(),  # type: ignore[arg-type,return-value]
        handoff_resolver=resolver,
        artifact_root=tmp_path,
    )
    ladder = tuple(
        _replace(step, extra_allowed_paths=(f"repos/{_CONTEXT}/src/**",))
        if step.label == "implement"
        else step
        for step in implementation_ladder(AgentRuntimeKind.FAKE)
    )

    result = pipe.run("impl-zone", ladder)

    assert result.completed is False
    assert result.blocked is not None and result.blocked.blocked_at_step == "implement"
    assert "deliverable" in result.blocked.reason


def test_implement_accepts_delivery_qualified_with_context_repo(tmp_path: Path) -> None:
    """Bug implementation-deliverable-zone-misses-context-repo: a TASKS write set in
    repo-relative form (src/**) must match a delivery reported workspace-relative
    (repos/<ctx>/src/...) — both spellings name the same zone.
    """
    from dataclasses import replace as _replace

    resolver = WorkflowHandoffResolver(
        run_store=JsonLifecycleRunStore(tmp_path),
        payload_writer=FilesystemRuntimeFileAdapter(tmp_path),
        clock=lambda: "2026-07-18T12:00:00Z",
    )

    class _InRepoRuntime(_ApprovingRuntime):
        def run(self, request: AgentRunRequest) -> AgentRunResult:
            result = super().run(request)
            refs = list(result.artifact_refs)
            label = (request.task_id or "").split(":")[1] if ":" in (request.task_id or "") else ""
            if label == "implement":
                refs.append(f"repos/{_CONTEXT}/src/game.py")
            if label == "close":
                refs.append(f"repos/{_CONTEXT}/specs/releases/{_RELEASE}/CLOSURE.md")
            for ref in refs:
                target = tmp_path / ref
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text("x = 1\n", encoding="utf-8")
            return AgentRunResult(
                status=result.status,
                summary=result.summary,
                artifact_refs=tuple(refs),
                structured_output=result.structured_output,
            )

    pipe = LifecyclePipeline(
        context=_CONTEXT,
        release_id=_RELEASE,
        run_store=JsonLifecycleRunStore(tmp_path),
        runtime_factory=lambda kind: _InRepoRuntime(),  # type: ignore[arg-type,return-value]
        handoff_resolver=resolver,
        artifact_root=tmp_path,
    )
    ladder = tuple(
        _replace(step, extra_allowed_paths=("src/**",)) if step.label == "implement" else step
        for step in implementation_ladder(AgentRuntimeKind.FAKE)
    )

    result = pipe.run("impl-qualified", ladder)

    assert result.completed is True, result.blocked.reason if result.blocked else result


def test_completed_close_runs_closure_committer(tmp_path: Path) -> None:
    """Bug implementation-closure-leaves-uncommitted-release-tree: a completed cycle
    commits the context repo (Python-owned, post-success); a blocked close does not.
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
        closure_committer=lambda: calls.append("committed"),
    )

    result = pipe.run("close-commit", implementation_ladder(AgentRuntimeKind.FAKE))

    assert result.completed is True
    assert calls == ["committed"]


def test_blocked_close_never_commits(tmp_path: Path) -> None:
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
        memory_lint_gate=lambda: (False, "WARN: x"),
        closure_committer=lambda: calls.append("committed"),
    )

    result = pipe.run("close-nocommit", implementation_ladder(AgentRuntimeKind.FAKE))

    assert result.completed is False
    assert calls == []


def test_pipeline_resume_injects_prior_rejection_digest(tmp_path: Path) -> None:
    """Parity with the fragment-gate engines: resuming a run that blocked on a review
    rejection feeds the rejection digest into the resumed step's prompt — otherwise
    the worker re-implements blind and the reviewer repeats the identical findings.
    """
    resolver = WorkflowHandoffResolver(
        run_store=JsonLifecycleRunStore(tmp_path),
        payload_writer=FilesystemRuntimeFileAdapter(tmp_path),
        clock=lambda: "2026-07-18T12:00:00Z",
    )

    class _RejectingReview(_ApprovingRuntime):
        def run(self, request: AgentRunRequest) -> AgentRunResult:
            result = super().run(request)
            if ":review_combined:" in (request.task_id or ""):
                return AgentRunResult(
                    status=result.status,
                    summary="review verdict REJECTED: RF-07 not satisfied",
                    artifact_refs=result.artifact_refs,
                    structured_output={
                        "verdict": "REJECTED",
                        "verdict_reason": "RF-07 not satisfied",
                    },
                )
            return result

    pipe = LifecyclePipeline(
        context=_CONTEXT,
        release_id=_RELEASE,
        run_store=JsonLifecycleRunStore(tmp_path),
        runtime_factory=lambda kind: _RejectingReview(),  # type: ignore[arg-type,return-value]
        handoff_resolver=resolver,
        max_review_retries=0,
    )
    first = pipe.run("resume-digest", implementation_ladder(AgentRuntimeKind.FAKE))
    assert first.completed is False and first.blocked is not None

    approving = _ApprovingRuntime()
    pipe2 = LifecyclePipeline(
        context=_CONTEXT,
        release_id=_RELEASE,
        run_store=JsonLifecycleRunStore(tmp_path),
        runtime_factory=lambda kind: approving,  # type: ignore[arg-type,return-value]
        handoff_resolver=resolver,
        max_review_retries=0,
    )
    resumed = pipe2.run(
        "resume-digest", implementation_ladder(AgentRuntimeKind.FAKE), resume_from="implement"
    )
    assert resumed.completed is True
    implement_prompt = approving.received[0].prompt
    assert "RF-07 not satisfied" in implement_prompt, implement_prompt[-500:]


def test_prompt_scope_error_is_clean_dadaia_error() -> None:
    """A scope violation must surface as ONE clean CLI line, never a traceback."""
    from dadaia_workspace.core.exceptions import DadaiaError
    from dadaia_workspace.features.lifecycle.prompt_builder import PromptScopeError

    assert issubclass(PromptScopeError, DadaiaError)
    assert issubclass(PromptScopeError, ValueError)
