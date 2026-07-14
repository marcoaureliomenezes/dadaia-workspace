"""T-26-06 — existing_backlog_review feeds the R1 classifier + the model downgrade seam.

Step 2 calls R1 ``classify(new, existing, *, downgrade)`` over the bound intents (step 1b)
and every existing item's bound intents. Python disposes every deterministic verdict; the
model is invoked ONLY through the ``downgrade`` seam for a same-anchor differing-change pair,
**fail-closed** -> DIVERGENT_CONFLICT absent an explicit structured proven-compatible merge
(SPEC §3.3, ADR-B). This test proves the offline default and a stubbed compatible-merge
downgrade, asserting the overlap-report-v1 carried on the workflow result.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from dadaia_workspace.core.models.backlog import SubjectKind
from dadaia_workspace.core.models.lifecycle import (
    AgentRunRequest,
    AgentRunResult,
    AgentRunStatus,
    AgentRuntimeKind,
    LifecycleRun,
)
from dadaia_workspace.core.protocols.lifecycle_run_store import LifecycleRunStoreError
from dadaia_workspace.features.backlog.classifier import BoundItem, Verdict
from dadaia_workspace.features.backlog.subject_registry import Registry, build_registry
from dadaia_workspace.features.lifecycle.context_selector import (
    ContextSelector,
    SpecContext,
)
from dadaia_workspace.features.lifecycle.workflows.backlog_definition import (
    AuthoredItem,
    BacklogDefinitionWorkflow,
    BacklogDemand,
    ProposedIntent,
)

_CONTEXT = "dadaia-workspace"
_RELEASE = "v0.1.26"
_ANCHOR_C = "pkg/c.py#C"


@dataclass(frozen=True)
class _KindFake:
    kind: AgentRuntimeKind
    root: Path

    def runtime_kind(self) -> AgentRuntimeKind:
        return self.kind

    def run(self, request: AgentRunRequest) -> AgentRunResult:
        artifact_ref = f".dadaia/tmp/lifecycle-worker/{_CONTEXT}/step.step-output.json"
        path = self.root / artifact_ref
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('{"fake": true}\n', encoding="utf-8")
        return AgentRunResult(
            status=AgentRunStatus.SUCCEEDED,
            summary="ok",
            artifact_refs=(artifact_ref,),
            structured_output={"verdict": "APPROVED"},
        )


class _MemoryRunStore:
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


def _registry(tmp_path: Path) -> Registry:
    specs = tmp_path / "specs"
    (specs / "memory" / "product").mkdir(parents=True)
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "c.py").write_text("class C:\n    pass\n", encoding="utf-8")
    return build_registry(
        source_root=tmp_path,
        catalog_path=specs / "memory" / "product" / "catalog.json",
        alias_map_path=tmp_path / ".dadaia" / "states" / "backlog_subject_aliases.txt",
        specs_dir=specs,
        cli_anchors=frozenset(),
    )


def _workflow(
    tmp_path: Path, registry: Registry, downgrade: object | None = None
) -> BacklogDefinitionWorkflow:
    specs = tmp_path / "specs"
    (specs / "backlog").mkdir(parents=True, exist_ok=True)
    selector = ContextSelector(
        SpecContext(specs_dir=specs, release_id=_RELEASE, handoff_dir=tmp_path / "handoff")
    )
    kwargs: dict[str, object] = {
        "context": _CONTEXT,
        "release_id": _RELEASE,
        "run_store": _MemoryRunStore(),
        "runtime_factory": lambda kind: _KindFake(kind, tmp_path),
        "context_selector": selector,
        "registry": registry,
    }
    if downgrade is not None:
        kwargs["downgrade"] = downgrade
    return BacklogDefinitionWorkflow(**kwargs)  # type: ignore[arg-type]


def _cd_demand() -> BacklogDemand:
    """A C->E demand against an existing C->D item: same anchor, differing change."""
    return BacklogDemand(
        proposed_intents=(
            ProposedIntent(kind=SubjectKind.CODE, ref=_ANCHOR_C, change="C becomes E"),
        ),
        existing=(BoundItem(slug="existing-cd", anchor_changes={_ANCHOR_C: "C becomes D"}),),
        authored=AuthoredItem(
            slug="new",
            is_new=False,  # an UPDATE, so reconcile does not block on the conflict here.
            bound=BoundItem(slug="new", anchor_changes={_ANCHOR_C: "C becomes E"}),
        ),
    )


def test_offline_defaults_to_divergent_conflict(tmp_path: Path) -> None:
    """Model OFFLINE (default no_downgrade): the C->D/C->E twin is DIVERGENT_CONFLICT."""
    wf = _workflow(tmp_path, _registry(tmp_path))
    result = wf.run("bd-offline", _cd_demand())
    verdicts = [c.verdict for c in result.overlap]
    assert Verdict.DIVERGENT_CONFLICT in verdicts


def test_stubbed_compatible_merge_downgrades(tmp_path: Path) -> None:
    """A stubbed proven-compatible merge downgrades the same-anchor pair to OVERLAP."""

    def proven_compatible(_new: str, _existing: str) -> Verdict | None:
        return Verdict.OVERLAP

    wf = _workflow(tmp_path, _registry(tmp_path), downgrade=proven_compatible)
    result = wf.run("bd-downgrade", _cd_demand())
    verdicts = [c.verdict for c in result.overlap]
    assert Verdict.OVERLAP in verdicts
    assert Verdict.DIVERGENT_CONFLICT not in verdicts


def test_operator_demand_reaches_every_model_step_prompt(tmp_path: Path) -> None:
    """Bug backlog-define-has-no-demand-input-channel: the raw demand text the intake
    grill exists to interrogate is injected into the model steps' prompts."""
    captured: list[str] = []

    @dataclass
    class _PromptCapturingFake:
        kind: AgentRuntimeKind
        root: Path

        def runtime_kind(self) -> AgentRuntimeKind:
            return self.kind

        def run(self, request: AgentRunRequest) -> AgentRunResult:
            captured.append(request.prompt)
            artifact_ref = f".dadaia/tmp/lifecycle-worker/{_CONTEXT}/step.step-output.json"
            path = self.root / artifact_ref
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('{"fake": true}\n', encoding="utf-8")
            return AgentRunResult(
                status=AgentRunStatus.SUCCEEDED,
                summary="ok",
                artifact_refs=(artifact_ref,),
                structured_output={"verdict": "APPROVED"},
            )

    specs = tmp_path / "specs"
    (specs / "backlog").mkdir(parents=True, exist_ok=True)
    selector = ContextSelector(
        SpecContext(specs_dir=specs, release_id=_RELEASE, handoff_dir=tmp_path / "handoff")
    )
    wf = BacklogDefinitionWorkflow(
        context=_CONTEXT,
        release_id=_RELEASE,
        run_store=_MemoryRunStore(),  # type: ignore[arg-type]
        runtime_factory=lambda kind: _PromptCapturingFake(kind, tmp_path),  # type: ignore[arg-type, return-value]
        context_selector=selector,
        registry=_registry(tmp_path),
    )
    demand_text = "Quero um jogo de corrida navegador-first para o Tauan."
    wf.run("demand-run", _cd_demand(), operator_demand=demand_text)

    assert captured, "at least one model step must have run"
    assert all("## Operator demand" in prompt for prompt in captured)
    assert all(demand_text in prompt for prompt in captured)
