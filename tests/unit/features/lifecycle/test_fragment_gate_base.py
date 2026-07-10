"""AC-2 — the ``FragmentGateWorkflow`` base is the single dedup seam (v0.1.57 FR1 / T-57-11).

Three properties the golden lock cannot catch (the golden run uses each body's module-global
``_SEQUENCE``, so a module-global-vs-threaded regression is invisible to it):

* **Run-scoped iteration.** ``_produce_payload`` + ``_graph_completeness_block`` iterate the
  sequence THREADED through ``run()``, never a module-global ``_SEQUENCE``. A base subclass run
  with a **custom** sequence produces + validates THAT sequence — the exact single-seam defect
  the dedup removes (AC-10(a) sabotages this: point ``_produce_payload`` back at a module-global
  ``_SEQUENCE`` ⇒ this test FAILS).
* **Converged ``_scope`` threads the resolved model (grill Problem #8).** ``backlog_definition``
  previously dropped ``model_profile`` / ``resolved_model`` from its ``PromptScope`` although
  ``BacklogStep`` carries them; the shared mixin ``_scope`` threads them. RED-first: pre-fix the
  backlog worker request had ``resolved_model is None``.
* **Shared members exist ONCE in the base (no per-body copy remains).** Grep evidence: the four
  handoff-ledger body modules no longer define the shared assembly/gate methods, and
  ``backlog_definition`` no longer defines the assembly helpers — they live once in
  ``_fragment_gate.py``.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from dadaia_workspace.core.models.backlog import SubjectKind
from dadaia_workspace.core.models.lifecycle import (
    AgentRunRequest,
    AgentRunResult,
    AgentRunStatus,
    AgentRuntimeKind,
)
from dadaia_workspace.core.models.workflow_execution import ResolvedModelConfig
from dadaia_workspace.features.backlog.classifier import BoundItem
from dadaia_workspace.features.backlog.subject_registry import Registry, build_registry
from dadaia_workspace.features.lifecycle.context_selector import ContextSelector, SpecContext
from dadaia_workspace.features.lifecycle.workflow_handoffs import WorkflowHandoffResolver
from dadaia_workspace.features.lifecycle.workflows import (
    audit,
    backlog_definition,
    bug_report,
    release_definition,
    research,
)
from dadaia_workspace.features.lifecycle.workflows.backlog_definition import (
    AuthoredItem,
    BacklogDefinitionWorkflow,
    BacklogDemand,
    BacklogStepKind,
    ProposedIntent,
)
from dadaia_workspace.features.lifecycle.workflows.release_definition import (
    ReleaseDefinitionWorkflow,
    ReleaseStep,
)
from dadaia_workspace.infrastructure.json_lifecycle_run_store import JsonLifecycleRunStore
from dadaia_workspace.infrastructure.runtime_files import FilesystemRuntimeFileAdapter

pytestmark = pytest.mark.unit

_CONTEXT = "dadaia-workspace"
_RELEASE = "v0.1.57"
_ANCHOR_A = "pkg/a.py#A"
_WORKFLOWS_DIR = Path(release_definition.__file__).resolve().parent


class _ScopeFake:
    """Scope-aware fake recording requests; keeps every step in-scope so the run completes."""

    def __init__(self) -> None:
        self.received_requests: list[AgentRunRequest] = []

    def runtime_kind(self) -> AgentRuntimeKind:
        return AgentRuntimeKind.FAKE

    def run(self, request: AgentRunRequest) -> AgentRunResult:
        self.received_requests.append(request)
        allowed = request.allowed_paths[0] if request.allowed_paths else ".dadaia/handoff/x/**"
        return AgentRunResult(
            status=AgentRunStatus.SUCCEEDED,
            summary="ok",
            artifact_refs=(allowed.replace("**", "step.handoff.json"),),
            structured_output={"verdict": "APPROVED"},
        )


def _seed(tmp_path: Path) -> Path:
    (tmp_path / ".dadaia" / "states").mkdir(parents=True)
    (tmp_path / ".dadaia" / "states" / "spec_contexts.json").write_text("{}", encoding="utf-8")
    (tmp_path / "repos").mkdir()
    specs = tmp_path / "repos" / _CONTEXT / "specs"
    (specs / "memory" / "product").mkdir(parents=True)
    (specs / "backlog").mkdir(parents=True)
    (specs / "releases" / _RELEASE).mkdir(parents=True)
    (specs / "constitution.md").write_text("# c\n", encoding="utf-8")
    (specs / "memory" / "architecture.md").write_text("# a\n", encoding="utf-8")
    (specs / "memory" / "quality-assurance.md").write_text("# q\n", encoding="utf-8")
    (specs / "memory" / "product" / "catalog.json").write_text('{"features": []}', encoding="utf-8")
    for art in ("SPEC.md", "PLAN.md", "TASKS.md"):
        (specs / "releases" / _RELEASE / art).write_text(f"# {art}\n", encoding="utf-8")
    return specs


def _selector(specs: Path, tmp_path: Path) -> ContextSelector:
    return ContextSelector(
        SpecContext(
            specs_dir=specs, release_id=_RELEASE, handoff_dir=tmp_path / ".dadaia" / "handoff"
        )
    )


def _resolver(tmp_path: Path) -> WorkflowHandoffResolver:
    return WorkflowHandoffResolver(
        run_store=JsonLifecycleRunStore(tmp_path),
        payload_writer=FilesystemRuntimeFileAdapter(tmp_path),
        clock=lambda: "2026-06-27T12:00:00Z",
    )


# ---------------------------------------------------------------------------
# AC-2 — run-scoped iteration (NOT a module-global _SEQUENCE)
# ---------------------------------------------------------------------------


def test_base_iterates_run_scoped_sequence_not_module_global(tmp_path: Path) -> None:
    """A base subclass run with a CUSTOM sequence produces/validates THAT sequence.

    The custom sequence's producer + consumer labels (``cs_a`` / ``cs_b``) exist in NO
    module-global ``_SEQUENCE``. Run-scoped iteration ⇒ the run completes (graph whole) AND the
    ``cs_a`` payload records ``cs_b`` as its declared consumer. If ``_produce_payload`` /
    ``_graph_completeness_block`` iterated a module-global ``_SEQUENCE`` (the removed defect):
    ``cs_a``'s declared_consumers would be empty (no module step consumes ``cs_a``) AND the gate
    would BLOCK (the module producers never ran) — both assertions below would FAIL (AC-10(a)).
    """
    specs = _seed(tmp_path)
    fake = _ScopeFake()
    resolver = _resolver(tmp_path)
    wf = ReleaseDefinitionWorkflow(
        context=_CONTEXT,
        release_id=_RELEASE,
        run_store=JsonLifecycleRunStore(tmp_path),
        runtime_factory=lambda kind: fake,  # type: ignore[arg-type,return-value]
        context_selector=_selector(specs, tmp_path),
        handoff_resolver=resolver,
    )
    custom = (
        ReleaseStep(
            label="cs_a",
            role="product-engineer",
            fragment_id="release_definition.release_scope",
            produces="release-scope-handoff-v1",
        ),
        ReleaseStep(
            label="cs_b",
            role="product-engineer",
            fragment_id="release_definition.spec_create",
            shared_fragment_ids=("shared.output_handoff",),
            produces="generic-step-handoff-v1",
            consumes=("cs_a",),
        ),
        ReleaseStep(label="cs_gate", role="python", fragment_id=None),
    )

    result = wf.run("cs-run", sequence=custom)

    # Graph-completeness iterated the RUN-SCOPED custom sequence → the run completed.
    assert result.completed is True
    run = JsonLifecycleRunStore(tmp_path).load("cs-run")
    assert run is not None
    a_record = run.workflow_steps.find("cs_a", 0)
    assert a_record is not None
    # _produce_payload computed declared_consumers from the RUN-SCOPED sequence: cs_b consumes
    # cs_a. A module-global iteration would yield () here.
    assert a_record.declared_consumers == ("cs_b",)
    assert run.workflow_steps.find("cs_b", 0) is not None


# ---------------------------------------------------------------------------
# AC-2 — converged _scope threads the resolved model (grill Problem #8, RED-first)
# ---------------------------------------------------------------------------


def _registry(tmp_path: Path, specs: Path) -> Registry:
    root = specs.parent
    (root / "pkg").mkdir()
    (root / "pkg" / "a.py").write_text("class A:\n    pass\n", encoding="utf-8")
    return build_registry(
        source_root=root,
        catalog_path=specs / "memory" / "product" / "catalog.json",
        alias_map_path=tmp_path / ".dadaia" / "states" / "backlog_subject_aliases.txt",
        specs_dir=specs,
        cli_anchors=frozenset(),
    )


def _clean_demand() -> BacklogDemand:
    return BacklogDemand(
        proposed_intents=(ProposedIntent(kind=SubjectKind.CODE, ref=_ANCHOR_A, change="add A"),),
        existing=(),
        authored=AuthoredItem(
            slug="new-item",
            is_new=True,
            bound=BoundItem(slug="new-item", anchor_changes={_ANCHOR_A: "add A"}),
        ),
    )


def test_backlog_scope_threads_resolved_model(tmp_path: Path) -> None:
    """RED-first (grill Problem #8): the backlog worker request carries the resolved model.

    Before the mixin ``_scope`` convergence, ``backlog_definition._scope`` dropped
    ``model_profile`` / ``resolved_model``, so the worker ran on the wrong model. With the
    resolved model set on the model steps, every backlog worker request must now carry it.
    Pre-fix this asserted ``resolved_model is None`` — it FAILED.
    """
    specs = _seed(tmp_path)
    fake = _ScopeFake()
    wf = BacklogDefinitionWorkflow(
        context=_CONTEXT,
        release_id=_RELEASE,
        run_store=JsonLifecycleRunStore(tmp_path),
        runtime_factory=lambda kind: fake,  # type: ignore[arg-type,return-value]
        context_selector=_selector(specs, tmp_path),
        registry=_registry(tmp_path, specs),
    )
    cfg = ResolvedModelConfig(profile_id="p", harness="codex", model="gpt-x", reasoning="high")
    sequence = tuple(
        replace(step, resolved_model=cfg) if step.kind is BacklogStepKind.MODEL else step
        for step in backlog_definition._SEQUENCE
    )

    result = wf.run("bd-model", _clean_demand(), sequence=sequence)

    assert result.completed is True
    assert fake.received_requests, "no backlog worker request was recorded"
    for req in fake.received_requests:
        assert req.resolved_model is not None, (
            "backlog _scope dropped the resolved model — the converged mixin _scope must thread "
            "model_profile/resolved_model (grill Problem #8)"
        )
        assert req.resolved_model == cfg


# ---------------------------------------------------------------------------
# AC-2 — shared members exist ONCE in the base (no per-body copy remains)
# ---------------------------------------------------------------------------

_GATE_MEMBERS = (
    "_run_sequence",
    "_run_model_step",
    "_run_terminal_gate",
    "_resolve_upstream",
    "_record_consumptions",
    "_produce_payload",
    "_graph_completeness_block",
    "_payload_from_result",
    "_with_step_outcome",
)
_ASSEMBLY_MEMBERS = (
    "_prefix_with_static_inputs",
    "_collect_static_inputs",
    "_fragment_bundle",
    "_select_context",
    "_render_selection",
)


def _defs(module_name: str) -> str:
    return (_WORKFLOWS_DIR / f"{module_name}.py").read_text(encoding="utf-8")


def test_shared_members_exist_once_in_base_with_no_per_body_copies() -> None:
    """Grep evidence that the FR1 dedup landed and stayed landed:

    * the base defines every shared gate/assembly member + ``_scope``;
    * no handoff-ledger body (release_definition/audit/research/bug_report) redefines a
      shared gate/assembly member — except bug_report, which overrides ONLY ``_scope``
      (its ADDITIVE bug_write special-case);
    * backlog_definition mixes in the assembly helpers via ``_FragmentAssemblyMixin`` with
      no local copy of any of them;
    * every body keeps its module-global ``_SEQUENCE`` (Q3) — the guardrail suites import it.
    """
    base = _defs("_fragment_gate")
    for member in (*_GATE_MEMBERS, *_ASSEMBLY_MEMBERS, "_scope"):
        assert f"def {member}(" in base, f"base must define {member}"

    for body in ("release_definition", "audit", "research", "bug_report"):
        src = _defs(body)
        for member in (*_GATE_MEMBERS, *_ASSEMBLY_MEMBERS):
            assert f"def {member}(" not in src, f"{body} still defines shared member {member}"
    assert "def _scope(" in _defs("bug_report")
    for body in ("release_definition", "audit", "research"):
        assert "def _scope(" not in _defs(body), f"{body} must not redefine _scope"

    backlog_src = _defs("backlog_definition")
    assert "_FragmentAssemblyMixin" in backlog_src, "backlog must mix in _FragmentAssemblyMixin"
    for member in (*_ASSEMBLY_MEMBERS, "_scope"):
        assert f"def {member}(" not in backlog_src, (
            f"backlog still defines assembly member {member}"
        )

    for module in (release_definition, audit, research, bug_report, backlog_definition):
        assert hasattr(module, "_SEQUENCE"), (
            f"{module.__name__} dropped its module-global _SEQUENCE"
        )
        assert module._SEQUENCE, f"{module.__name__}._SEQUENCE is empty"
