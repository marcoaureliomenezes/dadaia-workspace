"""Declarative role→atom map + phase threading + single-sourced injection (v0.1.57 FR2 / W2).

Covers:

* **role_atoms unit** — :func:`resolve_role_atoms` / :func:`inject_role_atoms`: mapped role
  reads + appends + records; multi-role comma-split; unmapped role, missing atom file, and
  un-wired ``specs_dir`` all fail open; merge-into-existing vs create-new ``InjectedContext``.
* **AC-3 (map delivers grounding, all three surfaces)** — the ``FragmentGateWorkflow`` base
  (a ``qa-engineer`` step records ``quality-assurance.md``, a ``software-architect`` step
  records ``architecture.md``, a ``product-engineer`` step records the catalog, a multi-role
  step records both), the selector-less ``LifecyclePipeline`` ``review_qa`` step, and the
  single-step ``LifecyclePhaseWorkflow`` path.
* **AC-3 (A1) PRODUCTION-builder wiring** — ``build_lifecycle_pipeline`` +
  ``build_lifecycle_phase_workflow`` construct instances whose role-atom resolver is wired with
  a REAL ``specs_dir`` (asserted on the constructed object), not just fixture pipelines.
* **AC-4 (phase threading)** — ``SpecContext.phase`` reaches from a fixture ``ACTIVE.md`` via
  every one of the 5 container builders; absent + malformed ``ACTIVE.md`` degrade to ``None``.
* **single-sourced (A1)** — the map DATA + resolve-and-inject LOGIC live in ``role_atoms.py``
  only; all three surfaces consume :func:`inject_role_atoms`, never a copy.
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path

import pytest

from dadaia_workspace import container
from dadaia_workspace.core.models.lifecycle import (
    AgentRunRequest,
    AgentRunResult,
    AgentRunStatus,
    AgentRuntimeKind,
    GateEvidenceKind,
    InjectedContext,
    LifecyclePhase,
    LifecycleRun,
    LifecycleRunStatus,
)
from dadaia_workspace.features.lifecycle import phase_workflow as phase_workflow_mod
from dadaia_workspace.features.lifecycle import pipeline as pipeline_mod
from dadaia_workspace.features.lifecycle import role_atoms
from dadaia_workspace.features.lifecycle.context_selector import ContextSelector, SpecContext
from dadaia_workspace.features.lifecycle.phase_workflow import LifecyclePhaseWorkflow
from dadaia_workspace.features.lifecycle.pipeline import (
    LifecyclePipeline,
    implementation_ladder,
)
from dadaia_workspace.features.lifecycle.prompt_builder import PromptScope
from dadaia_workspace.features.lifecycle.role_atoms import (
    ROLE_ATOM_MAP,
    inject_role_atoms,
    resolve_role_atoms,
)
from dadaia_workspace.features.lifecycle.workflows import _fragment_gate
from dadaia_workspace.features.lifecycle.workflows.release_definition import (
    ReleaseDefinitionWorkflow,
)
from dadaia_workspace.infrastructure.json_lifecycle_run_store import JsonLifecycleRunStore

pytestmark = pytest.mark.unit

_CONTEXT = "dadaia-workspace"
_RELEASE = "v0.1.57"
_QA_REF = "specs/memory/quality-assurance.md"
_ARCH_REF = "specs/memory/architecture.md"
_CATALOG_REF = "specs/memory/product/catalog.json"


# ---------------------------------------------------------------------------
# fixtures / fakes
# ---------------------------------------------------------------------------


class _RecordingFake:
    """Scope-aware deterministic ``AgentRuntimePort`` recording every request in call order.

    Its single ``artifact_ref`` is derived from the request's first ``allowed_path`` so every
    step is in-scope and the sequence completes (mirrors the golden fake).
    """

    def __init__(self) -> None:
        self.received_requests: list[AgentRunRequest] = []

    def runtime_kind(self) -> AgentRuntimeKind:
        return AgentRuntimeKind.FAKE

    def run(self, request: AgentRunRequest) -> AgentRunResult:
        self.received_requests.append(request)
        allowed = request.allowed_paths[0] if request.allowed_paths else ".dadaia/handoff/x/**"
        artifact = allowed.replace("**", "step.handoff.json")
        return AgentRunResult(
            status=AgentRunStatus.SUCCEEDED,
            summary="role-atom step ok",
            artifact_refs=(artifact,),
            structured_output={"verdict": "APPROVED"},
        )

    def request_for(self, step_label: str) -> AgentRunRequest:
        for req in self.received_requests:
            if (req.task_id or "").endswith(f":{step_label}"):
                return req
        raise AssertionError(f"no request captured for step {step_label!r}")


def _seed_specs(tmp_path: Path, *, active_phase: str | None = "IMPLEMENTATION") -> Path:
    """Author a deterministic ``repos/<ctx>/specs`` tree; return the specs dir."""
    (tmp_path / ".dadaia" / "states").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".dadaia" / "states" / "spec_contexts.json").write_text(
        json.dumps({"version": "1", "contexts": []}), encoding="utf-8"
    )
    specs = tmp_path / "repos" / _CONTEXT / "specs"
    (specs / "memory" / "product").mkdir(parents=True)
    (specs / "backlog").mkdir(parents=True)
    (specs / "bugs").mkdir(parents=True)
    (specs / "audits").mkdir(parents=True)
    (specs / "releases" / _RELEASE).mkdir(parents=True)
    (specs / "constitution.md").write_text("# Constitution\n\nBody.\n", encoding="utf-8")
    (specs / "memory" / "architecture.md").write_text(
        "# Architecture\n\nFIXTURE ARCH BODY.\n", encoding="utf-8"
    )
    (specs / "memory" / "quality-assurance.md").write_text(
        "# Quality Assurance\n\nFIXTURE QA BODY.\n", encoding="utf-8"
    )
    (specs / "memory" / "product" / "catalog.json").write_text(
        '{"features": [{"slug": "demo", "tldr": "FIXTURE CATALOG BODY"}]}\n', encoding="utf-8"
    )
    for art in ("SPEC.md", "PLAN.md", "TASKS.md"):
        (specs / "releases" / _RELEASE / art).write_text(f"# {art}\n\nBody.\n", encoding="utf-8")
    if active_phase is not None:
        (specs / "releases" / "ACTIVE.md").write_text(
            f"release: {_RELEASE}\nphase: {active_phase}\n", encoding="utf-8"
        )
    return specs


def _selector(specs: Path, tmp_path: Path) -> ContextSelector:
    return ContextSelector(
        SpecContext(
            specs_dir=specs, release_id=_RELEASE, handoff_dir=tmp_path / ".dadaia" / "handoff"
        )
    )


def _run_from_store(tmp_path: Path, run_id: str) -> LifecycleRun:
    run = JsonLifecycleRunStore(tmp_path).load(run_id)
    assert run is not None
    return run


def _refs_for(run: LifecycleRun, step_label: str) -> tuple[str, ...]:
    for entry in run.injected_context:
        if entry.step == step_label:
            return entry.refs
    raise AssertionError(f"no injected_context entry for step {step_label!r}")


# ---------------------------------------------------------------------------
# role_atoms unit — resolve + inject fail-open behaviour
# ---------------------------------------------------------------------------


def test_resolve_role_atoms_reads_mapped_atom(tmp_path: Path) -> None:
    specs = _seed_specs(tmp_path)
    atoms = resolve_role_atoms("qa-engineer", specs)
    assert len(atoms) == 1
    role_name, ref, content = atoms[0]
    assert role_name == "qa-engineer"
    assert ref == _QA_REF
    assert "FIXTURE QA BODY." in content


def test_resolve_role_atoms_multi_role_comma_split(tmp_path: Path) -> None:
    specs = _seed_specs(tmp_path)
    atoms = resolve_role_atoms("qa-engineer, software-architect", specs)
    assert [ref for _, ref, _ in atoms] == [_QA_REF, _ARCH_REF]


def test_resolve_role_atoms_unmapped_role_yields_nothing(tmp_path: Path) -> None:
    specs = _seed_specs(tmp_path)
    assert resolve_role_atoms("security-reviewer", specs) == ()
    assert resolve_role_atoms("python", specs) == ()


def test_resolve_role_atoms_missing_atom_file_fails_open(tmp_path: Path) -> None:
    specs = _seed_specs(tmp_path)
    (specs / "memory" / "quality-assurance.md").unlink()
    # qa-engineer maps to the now-absent file → no injection, no crash.
    assert resolve_role_atoms("qa-engineer", specs) == ()


def test_resolve_role_atoms_none_specs_dir_yields_nothing() -> None:
    assert resolve_role_atoms("qa-engineer", None) == ()


def _bare_run() -> LifecycleRun:
    return LifecycleRun(
        run_id="r",
        context=_CONTEXT,
        release_id=_RELEASE,
        command="c",
        phase=LifecyclePhase.IMPLEMENTATION,
        status=LifecycleRunStatus.RUNNING,
        current_step="s",
    )


def test_inject_role_atoms_appends_block_and_records_ref(tmp_path: Path) -> None:
    specs = _seed_specs(tmp_path)
    run, prompt = inject_role_atoms(
        run=_bare_run(),
        step_label="s",
        role="qa-engineer",
        specs_dir=specs,
        prompt="BASE PROMPT",
    )
    assert prompt.startswith("BASE PROMPT")
    assert f"<!-- role-atom:qa-engineer:{_QA_REF} -->" in prompt
    assert "FIXTURE QA BODY." in prompt
    assert _refs_for(run, "s") == (_QA_REF,)


def test_inject_role_atoms_noop_when_unmapped(tmp_path: Path) -> None:
    specs = _seed_specs(tmp_path)
    run, prompt = inject_role_atoms(
        run=_bare_run(), step_label="s", role="python", specs_dir=specs, prompt="P"
    )
    assert prompt == "P"
    assert run.injected_context == ()


def test_inject_role_atoms_merges_into_existing_entry(tmp_path: Path) -> None:
    specs = _seed_specs(tmp_path)
    base = _bare_run()
    seeded = LifecycleRun(  # entry already present (e.g. selector audit) — refs must merge
        **{
            **{f.name: getattr(base, f.name) for f in base.__dataclass_fields__.values()},
            "injected_context": (
                InjectedContext(step="s", fragment_ids=("frag",), refs=("existing-ref",)),
            ),
        }
    )
    run, _ = inject_role_atoms(
        run=seeded, step_label="s", role="qa-engineer", specs_dir=specs, prompt="P"
    )
    assert len(run.injected_context) == 1
    entry = run.injected_context[0]
    assert entry.fragment_ids == ("frag",)  # preserved
    assert entry.refs == ("existing-ref", _QA_REF)  # merged


# ---------------------------------------------------------------------------
# AC-3 — the base surface delivers grounding for every mapped role
# ---------------------------------------------------------------------------


def test_ac3_base_records_and_injects_each_mapped_role(tmp_path: Path) -> None:
    specs = _seed_specs(tmp_path)
    fake = _RecordingFake()
    wf = ReleaseDefinitionWorkflow(
        context=_CONTEXT,
        release_id=_RELEASE,
        run_store=JsonLifecycleRunStore(tmp_path),
        runtime_factory=lambda kind: fake,  # type: ignore[arg-type,return-value]
        context_selector=_selector(specs, tmp_path),
    )
    assert wf.run("rd").completed is True
    run = _run_from_store(tmp_path, "rd")

    # product-engineer step records the catalog ref; software-architect → architecture.md;
    # qa-engineer → quality-assurance.md; the multi-role plan_review records BOTH.
    assert _CATALOG_REF in _refs_for(run, "release_scope")
    assert _ARCH_REF in _refs_for(run, "spec_arch_review")
    assert _QA_REF in _refs_for(run, "spec_qa_review")
    assert _QA_REF in _refs_for(run, "plan_review")
    assert _ARCH_REF in _refs_for(run, "plan_review")

    # the atom CONTENT appears in the assembled prompt for the mapped steps.
    assert "FIXTURE QA BODY." in fake.request_for("spec_qa_review").prompt
    assert "FIXTURE ARCH BODY." in fake.request_for("spec_arch_review").prompt
    assert "FIXTURE CATALOG BODY" in fake.request_for("release_scope").prompt


# ---------------------------------------------------------------------------
# AC-3 — the selector-less pipeline review_qa step (RED-first: absent without the map)
# ---------------------------------------------------------------------------


def _pipeline(tmp_path: Path, specs: Path | None) -> tuple[LifecyclePipeline, _RecordingFake]:
    fake = _RecordingFake()
    pipe = LifecyclePipeline(
        context=_CONTEXT,
        release_id=_RELEASE,
        run_store=JsonLifecycleRunStore(tmp_path),
        runtime_factory=lambda kind: fake,  # type: ignore[arg-type,return-value]
        context_selector=None,  # mirror production: no selector wired
        specs_dir=specs,
    )
    return pipe, fake


def test_ac3_pipeline_review_qa_grounding(tmp_path: Path) -> None:
    specs = _seed_specs(tmp_path)
    pipe, fake = _pipeline(tmp_path, specs)
    assert pipe.run("pl", implementation_ladder(AgentRuntimeKind.FAKE)).completed is True

    review_qa = fake.request_for("review_qa")
    assert "FIXTURE QA BODY." in review_qa.prompt
    assert f"<!-- role-atom:qa-engineer:{_QA_REF} -->" in review_qa.prompt
    assert _QA_REF in _refs_for(_run_from_store(tmp_path, "pl"), "review_qa")
    # an unmapped step (implement → software-engineer) is NOT grounded.
    assert "FIXTURE QA BODY." not in fake.request_for("implement").prompt


def test_ac3_pipeline_review_qa_absent_without_map(tmp_path: Path) -> None:
    """RED-anchor: with the pipeline un-wired (no specs_dir) the QA atom is absent.

    This pins the pre-map / production-inert state the FR2 map fixes: an un-wired pipeline is
    exactly the selector-less production path before this release, and its ``review_qa`` prompt
    carries no ``quality-assurance.md`` grounding.
    """
    _seed_specs(tmp_path)
    pipe, fake = _pipeline(tmp_path, None)  # no specs_dir → map inert
    assert pipe.run("pl0", implementation_ladder(AgentRuntimeKind.FAKE)).completed is True
    assert "FIXTURE QA BODY." not in fake.request_for("review_qa").prompt


# ---------------------------------------------------------------------------
# AC-3 — the single-step phase workflow path
# ---------------------------------------------------------------------------


def test_ac3_phase_workflow_grounding(tmp_path: Path) -> None:
    specs = _seed_specs(tmp_path)
    fake = _RecordingFake()
    wf = LifecyclePhaseWorkflow(
        runtime=fake,  # type: ignore[arg-type]
        run_store=JsonLifecycleRunStore(tmp_path),
        specs_dir_resolver=lambda ctx: specs if ctx == _CONTEXT else None,
    )
    scope = PromptScope(
        role="qa-engineer",
        context=_CONTEXT,
        release_id=_RELEASE,
        task_id="pw",
        prompt="Run the qa step.",
        allowed_paths=(f".dadaia/handoff/{_CONTEXT}/**",),
        required_evidence=(GateEvidenceKind.HANDOFF,),
    )
    result = wf.run(
        run_id="pw",
        command="review-qa",
        from_phase=LifecyclePhase.IMPLEMENTATION,
        target_phase=LifecyclePhase.QA_REVIEW,
        scope=scope,
        current_step="review_qa",
    )
    assert result.accepted is True
    assert "FIXTURE QA BODY." in fake.received_requests[0].prompt
    assert _QA_REF in _refs_for(_run_from_store(tmp_path, "pw"), "review_qa")


# ---------------------------------------------------------------------------
# AC-3 (A1) — the PRODUCTION builders wire the resolver with a REAL specs_dir
# ---------------------------------------------------------------------------


def test_ac3_a1_production_pipeline_builder_wires_real_specs_dir(tmp_path: Path) -> None:
    specs = _seed_specs(tmp_path)
    pipe = container.build_lifecycle_pipeline(tmp_path, context=_CONTEXT, release_id=_RELEASE)
    # constructed object carries the REAL specs tree (not a fixture / None).
    assert pipe._specs_dir == specs


def test_ac3_a1_production_phase_workflow_builder_wires_real_resolver(tmp_path: Path) -> None:
    specs = _seed_specs(tmp_path)
    wf = container.build_lifecycle_phase_workflow(tmp_path, runtime_kind=AgentRuntimeKind.FAKE)
    assert wf._specs_dir_resolver is not None
    assert wf._specs_dir_resolver(_CONTEXT) == specs


# ---------------------------------------------------------------------------
# AC-4 — phase threading into SpecContext (via _active_phase + the 5 builders)
# ---------------------------------------------------------------------------


def test_ac4_active_phase_reads_fixture(tmp_path: Path) -> None:
    specs = _seed_specs(tmp_path, active_phase="IMPLEMENTATION")
    assert container._active_phase(specs) == "IMPLEMENTATION"


def test_ac4_active_phase_absent_is_none(tmp_path: Path) -> None:
    specs = _seed_specs(tmp_path, active_phase=None)  # no ACTIVE.md written
    assert not (specs / "releases" / "ACTIVE.md").exists()
    assert container._active_phase(specs) is None


def test_ac4_active_phase_malformed_is_none(tmp_path: Path) -> None:
    specs = _seed_specs(tmp_path, active_phase=None)
    # malformed: a body with neither a release: nor a phase: line.
    (specs / "releases" / "ACTIVE.md").write_text("garbage: not-a-pointer\n", encoding="utf-8")
    assert container._active_phase(specs) is None


_BUILDERS = (
    "build_release_definition_workflow",
    "build_backlog_definition_workflow",
    "build_audit_workflow",
    "build_research_workflow",
    "build_bug_report_workflow",
)


@pytest.mark.parametrize("builder_name", _BUILDERS)
def test_ac4_each_builder_threads_phase_into_spec_context(
    tmp_path: Path, builder_name: str
) -> None:
    _seed_specs(tmp_path, active_phase="IMPLEMENTATION")
    builder = getattr(container, builder_name)
    wf = builder(tmp_path, context=_CONTEXT, release_id=_RELEASE)
    assert wf._selector.spec_context.phase == "IMPLEMENTATION"


@pytest.mark.parametrize("builder_name", _BUILDERS)
def test_ac4_each_builder_fail_open_when_active_absent(tmp_path: Path, builder_name: str) -> None:
    _seed_specs(tmp_path, active_phase=None)  # no ACTIVE.md → phase must be None
    builder = getattr(container, builder_name)
    wf = builder(tmp_path, context=_CONTEXT, release_id=_RELEASE)
    assert wf._selector.spec_context.phase is None


# ---------------------------------------------------------------------------
# single-sourced (A1) — the map + inject logic live in role_atoms.py only
# ---------------------------------------------------------------------------


def test_inject_helper_is_single_sourced_across_three_surfaces() -> None:
    surfaces = (_fragment_gate, pipeline_mod, phase_workflow_mod)
    for mod in surfaces:
        src = inspect.getsource(mod)
        assert "inject_role_atoms" in src, f"{mod.__name__} does not consume inject_role_atoms"
        # the map DATA must NOT be copy-pasted into a consuming surface (single-sourced).
        assert "ROLE_ATOM_MAP" not in src, (
            f"{mod.__name__} re-declares the map (not single-sourced)"
        )
    assert "ROLE_ATOM_MAP" in inspect.getsource(role_atoms)
    assert set(ROLE_ATOM_MAP) == {"software-architect", "qa-engineer", "product-engineer"}
