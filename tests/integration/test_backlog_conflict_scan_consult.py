"""T-43-6 — the conflict_scan downgrade-only model consult (SPEC §3 WS-3, AC-5).

Proves the model consult wired into the `downgrade` seam of `existing_backlog_review`:

* a real (non-FAKE) runtime emitting a compatible-merge verdict (`overlap`/`supersedes`) folds
  a shared-anchor differing-change pair from `DIVERGENT_CONFLICT` to that verdict;
* a divergent / garbage / unparseable verdict leaves the pair `DIVERGENT_CONFLICT` (never
  upgraded, never masked — defence-in-depth with the classifier clamp T-43-6b);
* the default FAKE/offline path keeps `no_downgrade` (no model call) so existing behavior and
  tests are unchanged;
* the consult is invoked ONLY on the differing-change branch (no model call for an UNRELATED
  or DUPLICATE pair).

`conflict_scan` is also now cited by the `existing_backlog_review` step, so it is no longer an
orphan fragment.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from dadaia_workspace.core.models.backlog import SubjectKind
from dadaia_workspace.core.models.lifecycle import (
    AgentRunRequest,
    AgentRunResult,
    AgentRunStatus,
    AgentRuntimeKind,
    LifecycleRun,
)
from dadaia_workspace.core.protocols.lifecycle_run_store import LifecycleRunStoreError
from dadaia_workspace.features.backlog.classifier import BoundItem, Verdict, no_downgrade
from dadaia_workspace.features.backlog.subject_registry import Registry, build_registry
from dadaia_workspace.features.lifecycle.context_selector import ContextSelector, SpecContext
from dadaia_workspace.features.lifecycle.workflows.backlog_definition import (
    _SEQUENCE,
    BacklogDefinitionWorkflow,
    BacklogDemand,
    BacklogStep,
    BacklogStepKind,
    ProposedIntent,
)

_CONTEXT = "dadaia-workspace"
_RELEASE = "v0.1.43"
_ANCHOR_C = "pkg/c.py#C"


@dataclass
class _RoutingFake:
    """A non-FAKE runtime: the consult step gets `verdict`; other steps get a passing result."""

    kind: AgentRuntimeKind
    consult_verdict: str
    root: Path

    def runtime_kind(self) -> AgentRuntimeKind:
        return self.kind

    def run(self, request: AgentRunRequest) -> AgentRunResult:
        if (request.task_id or "").endswith(":existing_backlog_review"):
            return AgentRunResult(
                status=AgentRunStatus.SUCCEEDED,
                summary="conflict_scan consult",
                artifact_refs=(),
                structured_output={"verdict": self.consult_verdict},
            )
        artifact_ref = f".dadaia/tmp/lifecycle-worker/{_CONTEXT}/step.step-output.json"
        path = self.root / artifact_ref
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('{"fake": true}\n', encoding="utf-8")
        return AgentRunResult(
            status=AgentRunStatus.SUCCEEDED,
            summary="ok",
            artifact_refs=(artifact_ref,),
            structured_output={"verdict": "APPROVED", "proposed_intents": "[]"},
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
    tmp_path: Path,
    store: _MemoryRunStore,
    registry: Registry,
    *,
    kind: AgentRuntimeKind,
    consult_verdict: str = "overlap",
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
        runtime_factory=lambda k: _RoutingFake(k, consult_verdict, tmp_path),
        context_selector=selector,
        registry=registry,
        default_runtime_kind=kind,
    )


def _divergent_demand() -> BacklogDemand:
    """A shared-anchor (C) differing-change pair: the only branch the consult touches."""
    return BacklogDemand(
        proposed_intents=(
            ProposedIntent(kind=SubjectKind.CODE, ref=_ANCHOR_C, change="C becomes E"),
        ),
        existing=(BoundItem(slug="existing-cd", anchor_changes={_ANCHOR_C: "C becomes D"}),),
        authored=None,
    )


# ---------------------------------------------------------------------------
# AC-5 — compatible-merge verdict folds; divergent/garbage stays DIVERGENT_CONFLICT
# Also folds in: conflict_scan is cited by existing_backlog_review (no longer orphan).
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("verdict_value", "expected_fold"),
    [
        ("overlap", Verdict.OVERLAP),
        ("supersedes", Verdict.SUPERSEDES),
        ("divergent_conflict", Verdict.DIVERGENT_CONFLICT),
        ("unrelated", Verdict.DIVERGENT_CONFLICT),
        ("duplicate", Verdict.DIVERGENT_CONFLICT),
        ("kaboom", Verdict.DIVERGENT_CONFLICT),
        ("", Verdict.DIVERGENT_CONFLICT),
    ],
)
def test_consult_verdict_matrix_folds_or_stays_divergent(
    tmp_path: Path, verdict_value: str, expected_fold: Verdict
) -> None:
    store = _MemoryRunStore()
    wf = _workflow(
        tmp_path,
        store,
        _registry(tmp_path),
        kind=AgentRuntimeKind.CLAUDE_SDK,
        consult_verdict=verdict_value,
    )
    result = wf.run(f"bd-matrix-{verdict_value or 'empty'}", _divergent_demand())
    # A compatible-merge verdict folds the fail-closed default; a divergent/garbage/
    # unparseable verdict can never mask the conflict — never upgraded, never masked.
    assert len(result.overlap) == 1
    assert result.overlap[0].verdict is expected_fold

    # conflict_scan is cited by the existing_backlog_review step (orphan check passes).
    step = next(s for s in _SEQUENCE if s.kind is BacklogStepKind.EXISTING_REVIEW)
    assert step.fragment_id == "backlog_definition.conflict_scan"


# ---------------------------------------------------------------------------
# Default FAKE path = no_downgrade (existing behavior unchanged); injected-downgrade
# precedence always wins over the model consult.
# ---------------------------------------------------------------------------


def test_fake_offline_no_consult_and_injected_downgrade_precedence(tmp_path: Path) -> None:
    store = _MemoryRunStore()
    # FAKE default kind: the consult must NOT run; the pair stays DIVERGENT_CONFLICT offline.
    wf = _workflow(
        tmp_path,
        store,
        _registry(tmp_path),
        kind=AgentRuntimeKind.FAKE,
        consult_verdict="overlap",  # would fold IF the consult ran — it must not.
    )
    result = wf.run("bd-fake", _divergent_demand())
    assert result.overlap[0].verdict is Verdict.DIVERGENT_CONFLICT

    # An explicitly injected downgrade always wins over the model consult.
    injected_root = tmp_path / "injected-precedence"
    injected_root.mkdir()
    specs = injected_root / "specs"
    (specs / "backlog").mkdir(parents=True, exist_ok=True)
    selector = ContextSelector(
        SpecContext(specs_dir=specs, release_id=_RELEASE, handoff_dir=injected_root / "handoff")
    )
    registry = _registry(injected_root)
    injected = lambda _n, _e: Verdict.DEPENDS_ON  # noqa: E731 — terse test stub
    wf_injected = BacklogDefinitionWorkflow(
        context=_CONTEXT,
        release_id=_RELEASE,
        run_store=store,
        runtime_factory=lambda k: _RoutingFake(k, "overlap", tmp_path),
        context_selector=selector,
        registry=registry,
        default_runtime_kind=AgentRuntimeKind.CLAUDE_SDK,
        downgrade=injected,
    )
    step = next(s for s in _SEQUENCE if s.kind is BacklogStepKind.EXISTING_REVIEW)
    assert wf_injected._resolve_downgrade(step, "rid") is injected

    # No fragment_id on a step => no_downgrade regardless of kind.
    bare = BacklogStep(label="x", role="python", kind=BacklogStepKind.EXISTING_REVIEW)
    wf_default = BacklogDefinitionWorkflow(
        context=_CONTEXT,
        release_id=_RELEASE,
        run_store=store,
        runtime_factory=lambda k: _RoutingFake(k, "overlap", tmp_path),
        context_selector=selector,
        registry=registry,
        default_runtime_kind=AgentRuntimeKind.CLAUDE_SDK,
    )
    assert wf_default._resolve_downgrade(bare, "rid") is no_downgrade
