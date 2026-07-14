"""T-26-05 — the BacklogDefinitionWorkflow runs the §4 sequence with Python-owned gates.

End-to-end on the FAKE harness. Proves the keystone behaviours (acceptance §3.7.1-5),
mirroring ReleaseDefinitionWorkflow's gate semantics:

- the full §4 sequence (intake_grill -> subject_bind -> existing_backlog_review ->
  reconcile_decision -> [conflict_resolution_grill] -> backlog_author -> backlog_review_gate)
  runs in order, stops at the first blocked gate, advances only on success;
- ``subject_bind`` HALTs on an unresolved subject (no silent NEW);
- the R1 classifier (model OFFLINE) catches a C->D / C->E divergence and routes to the grill;
- ``reconcile_decision`` blocks NEW unless every existing item is UNRELATED — both directions;
- ``backlog_review_gate`` blocks a dirty authored result.

Gate behaviours are ONE parameterized step-matrix test (§3.7.11), not per-step copies.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

import pytest

from dadaia_workspace.core.models.backlog import SubjectKind
from dadaia_workspace.core.models.lifecycle import (
    AgentRunRequest,
    AgentRunResult,
    AgentRunStatus,
    AgentRuntimeKind,
    LifecyclePhase,
    LifecycleRun,
)
from dadaia_workspace.core.protocols.lifecycle_run_store import LifecycleRunStoreError
from dadaia_workspace.features.backlog.classifier import BoundItem
from dadaia_workspace.features.backlog.subject_registry import Registry, build_registry
from dadaia_workspace.features.lifecycle.context_selector import (
    ContextSelector,
    SpecContext,
)
from dadaia_workspace.features.lifecycle.workflows.backlog_definition import (
    _SEQUENCE,
    AuthoredItem,
    BacklogDefinitionWorkflow,
    BacklogDemand,
    ProposedIntent,
)

_CONTEXT = "dadaia-workspace"
_RELEASE = "v0.1.26"

_ANCHOR_A = "pkg/a.py#A"
_ANCHOR_C = "pkg/c.py#C"


@dataclass(frozen=True)
class _KindFake:
    kind: AgentRuntimeKind
    result: AgentRunResult
    root: Path

    def runtime_kind(self) -> AgentRuntimeKind:
        return self.kind

    def run(self, request: AgentRunRequest) -> AgentRunResult:
        for ref in self.result.artifact_refs:
            path = self.root / ref
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('{"fake": true}\n', encoding="utf-8")
        return self.result


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


def _approved() -> AgentRunResult:
    return AgentRunResult(
        status=AgentRunStatus.SUCCEEDED,
        summary="ok",
        artifact_refs=(f".dadaia/tmp/lifecycle-worker/{_CONTEXT}/step.step-output.json",),
        structured_output={"verdict": "APPROVED"},
    )


def _registry(tmp_path: Path) -> Registry:
    """A registry that binds pkg/a.py#A and pkg/c.py#C (planted source) — nothing else."""
    specs = tmp_path / "specs"
    (specs / "memory" / "product").mkdir(parents=True)
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "a.py").write_text("class A:\n    pass\n", encoding="utf-8")
    (pkg / "c.py").write_text("class C:\n    pass\n", encoding="utf-8")
    return build_registry(
        source_root=tmp_path,
        catalog_path=specs / "memory" / "product" / "catalog.json",
        alias_map_path=tmp_path / ".dadaia" / "states" / "backlog_subject_aliases.txt",
        specs_dir=specs,
        cli_anchors=frozenset(),
    )


def _workflow(
    tmp_path: Path, store: _MemoryRunStore, registry: Registry
) -> BacklogDefinitionWorkflow:
    specs = tmp_path / "specs"
    (specs / "backlog").mkdir(parents=True, exist_ok=True)
    selector = ContextSelector(
        SpecContext(specs_dir=specs, release_id=_RELEASE, handoff_dir=tmp_path / "handoff")
    )
    return BacklogDefinitionWorkflow(
        context=_CONTEXT,
        release_id=_RELEASE,
        run_store=store,
        runtime_factory=lambda kind: _KindFake(kind, _approved(), tmp_path),
        context_selector=selector,
        registry=registry,
    )


def _new_demand(**over: object) -> BacklogDemand:
    """A clean NEW demand: a single resolvable subject, no existing overlap, clean author."""
    base = BacklogDemand(
        proposed_intents=(ProposedIntent(kind=SubjectKind.CODE, ref=_ANCHOR_A, change="add A"),),
        existing=(),
        authored=AuthoredItem(
            slug="new-item",
            is_new=True,
            bound=BoundItem(slug="new-item", anchor_changes={_ANCHOR_A: "add A"}),
        ),
    )
    return replace(base, **over)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Happy path — full sequence runs in order and advances
# ---------------------------------------------------------------------------


def test_full_sequence_completes_fragment_prompt_and_sequence_labels(tmp_path: Path) -> None:
    """Happy path (full sequence completes+advances) + emitted prompt carries the
    fragment (not generic) + the shipped _SEQUENCE matches the §4 seven-step order."""
    store = _MemoryRunStore()
    wf = _workflow(tmp_path, store, _registry(tmp_path))

    result = wf.run("bd-1", _new_demand())

    assert result.completed is True
    assert result.final_phase is LifecyclePhase.RELEASE_DEFINITION
    labels = [s.label for s in result.steps]
    # The conditional grill is skipped on a clean demand; every other step ran in order.
    assert labels[0] == "intake_grill"
    assert labels[-1] == "backlog_review_gate"
    grill = next(s for s in result.steps if s.label == "conflict_resolution_grill")
    assert grill.skipped is True

    intake = next(s for s in result.steps if s.label == "intake_grill")
    assert intake.prompt_text is not None
    assert "backlog_definition.intake_grill" in intake.prompt_text
    assert "Run the intake_grill step" not in intake.prompt_text
    # Coherent worker-output contract (v0.1.32 / D-1): the single transport schema is the
    # worker emit target via `schema`; the fragment's domain schema is NOT surfaced as a
    # competing schema-to-emit in the "## Required output" section.
    required = intake.prompt_text[intake.prompt_text.index("## Required output") :]
    assert "agent-run-result-v1" in required
    assert "backlog-demand-v1" not in required

    expected_sequence = [
        "intake_grill",
        "subject_bind",
        "existing_backlog_review",
        "reconcile_decision",
        "conflict_resolution_grill",
        "backlog_author",
        "backlog_review_gate",
    ]
    assert [s.label for s in _SEQUENCE] == expected_sequence


# ---------------------------------------------------------------------------
# Parameterized Python-gate step-matrix (§3.7.11) — one matrix, not per-step copies
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _Case:
    name: str
    demand_kw: dict[str, object]
    blocks_at: str | None  # step label that blocks, or None for full completion
    grill_runs: bool = False


_C_TO_D = BoundItem(slug="existing-cd", anchor_changes={_ANCHOR_C: "C becomes D"})


_CASES = [
    # subject_bind HALT — unresolved subject (acceptance §3.7.2).
    _Case(
        name="unresolved_subject_halts",
        demand_kw={
            "proposed_intents": (
                ProposedIntent(kind=SubjectKind.CODE, ref="pkg/ghost.py#Nope", change="x"),
            ),
        },
        blocks_at="subject_bind",
    ),
    # DIVERGENT_CONFLICT offline → routes to grill, then reconcile blocks NEW (§3.7.3/4).
    _Case(
        name="divergent_conflict_routes_to_grill_then_blocks_new",
        demand_kw={
            "proposed_intents": (
                ProposedIntent(kind=SubjectKind.CODE, ref=_ANCHOR_C, change="C becomes E"),
            ),
            "existing": (_C_TO_D,),
            "authored": AuthoredItem(
                slug="new-item",
                is_new=True,
                bound=BoundItem(slug="new-item", anchor_changes={_ANCHOR_C: "C becomes E"}),
            ),
        },
        blocks_at="reconcile_decision",
        grill_runs=True,
    ),
    # reconcile_decision permits NEW when every existing item is UNRELATED (§3.7.4 +).
    _Case(
        name="all_unrelated_permits_new",
        demand_kw={
            "existing": (BoundItem(slug="other", anchor_changes={_ANCHOR_C: "unrelated"}),),
        },
        blocks_at=None,
    ),
    # backlog_review_gate blocks a dirty authored result — a DUPLICATE in the result (§3.7.5).
    _Case(
        name="review_gate_blocks_dirty_result",
        demand_kw={
            "proposed_intents": (
                ProposedIntent(kind=SubjectKind.CODE, ref=_ANCHOR_A, change="add A"),
            ),
            # author folds into an EDIT, but the result duplicates a sibling left in backlog.
            "existing": (),
            "authored": AuthoredItem(
                slug="dup-item",
                is_new=True,
                bound=BoundItem(slug="dup-item", anchor_changes={_ANCHOR_A: "add A"}),
                rest_of_backlog=(BoundItem(slug="sibling", anchor_changes={_ANCHOR_A: "add A"}),),
            ),
        },
        blocks_at="backlog_review_gate",
    ),
]


@pytest.mark.parametrize("case", _CASES, ids=[c.name for c in _CASES])
def test_python_gate_matrix(tmp_path: Path, case: _Case) -> None:
    store = _MemoryRunStore()
    wf = _workflow(tmp_path, store, _registry(tmp_path))

    result = wf.run(f"bd-{case.name}", _new_demand(**case.demand_kw))

    labels = [s.label for s in result.steps]
    grill = next((s for s in result.steps if s.label == "conflict_resolution_grill"), None)

    if case.blocks_at is None:
        assert result.completed is True, f"{case.name} should complete"
        assert result.final_phase is LifecyclePhase.RELEASE_DEFINITION
    else:
        assert result.completed is False, f"{case.name} should block"
        assert result.blocked is not None
        assert labels[-1] == case.blocks_at, f"{case.name} should stop at {case.blocks_at}"
        assert result.steps[-1].accepted is False

    if case.grill_runs and grill is not None:
        assert grill.skipped is False, f"{case.name} should RUN the conflict grill"
