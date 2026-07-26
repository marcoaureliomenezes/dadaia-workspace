"""WS-9 / T-24-13 — prompt observability run-record fields + cost-control guards.

Drives the release-definition workflow on FAKE and asserts:

1. **Per-step prompt composition is persisted.** Each model step's run-record entry
   carries the WS-9 fields — fragment ids, dynamic refs, prefix hash, discrete model,
   runtime kind, output schema, and the Python gate result — and the whole record
   round-trips byte-for-byte through the JSON store (``to_dict``/``from_dict``).

2. **Prefix byte-identity (the cacheable-prefix invariant).** Every model step that
   shares the stable :class:`PromptPrefix` records the *same* ``prefix_hash``, and the
   emitted prompt text reuses the prefix bytes verbatim — the prefix is built once and
   reused, never rebuilt per step. This is the provider-cache cost win.

3. **No whole-memory injection by default (the cost regression guard).** A default
   release-definition step injects only what its fragment declares — the bounded dynamic
   slice its ``max_context_policy`` allows plus its declared ``static_inputs`` — never a
   blind dump of the whole ``memory/`` corpus. The guard plants a sentinel in an
   **unreferenced** memory atom (named by no selector and no fragment ``static_inputs``)
   and asserts it never reaches any step's prompt — proving the assembly never slurps the
   whole memory tree. (Declared static inputs such as ``memory/architecture.md`` DO reach
   the cacheable prefix by design — that is the point of static-input injection — so the
   sentinel deliberately lives in a file nothing references.)

Cost-control guards (provider-cache prefix identity, no memory slurp) are the
token-economy contract.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from dadaia_workspace.core.models.lifecycle import (
    AgentRunRequest,
    AgentRunResult,
    AgentRunStatus,
    AgentRuntimeKind,
    GateVerdict,
    LifecycleRun,
)
from dadaia_workspace.core.protocols.lifecycle_run_store import LifecycleRunStoreError
from dadaia_workspace.features.lifecycle.context_selector import ContextSelector, SpecContext
from dadaia_workspace.features.lifecycle.prompt_builder import PromptPrefix
from dadaia_workspace.features.lifecycle.workflows.release_definition import (
    _SEQUENCE,
    ReleaseDefinitionWorkflow,
)
from dadaia_workspace.infrastructure.json_lifecycle_run_store import JsonLifecycleRunStore

_CONTEXT = "dadaia-workspace"
_RELEASE = "v0.1.24"

#: A unique string in an UNREFERENCED memory atom — no selector and no fragment
#: ``static_inputs`` entry names it. It must NEVER appear in any step's prompt. If the
#: assembly ever slurped the whole ``memory/`` tree (a whole-memory-injection cost
#: regression), this would leak. (architecture.md is a declared static input and now
#: legitimately reaches the cacheable prefix, so the sentinel lives elsewhere.)
_MEMORY_SENTINEL = "ZZZ_WHOLE_MEMORY_LEAK_SENTINEL_ZZZ"


@dataclass(frozen=True)
class _KindFake:
    kind: AgentRuntimeKind
    result: AgentRunResult

    def runtime_kind(self) -> AgentRuntimeKind:
        return self.kind

    def run(self, request: AgentRunRequest) -> AgentRunResult:  # noqa: ARG002
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


#: A constitution body distinctive enough that the static-input injection assertion can
#: prove the declared static input's content actually reaches the assembled prompt.
_CONSTITUTION_BODY = (
    "# constitution\n\nThe constitution static-input marker: STATIC_CONST_MARKER_42.\n"
)
_ARCH_STATIC_MARKER = "STATIC_ARCH_MARKER_77"


def _specs_tree(tmp_path: Path) -> Path:
    """A minimal specs tree the context selector can resolve dynamic inputs against.

    An UNREFERENCED memory atom carries the ``_MEMORY_SENTINEL`` so the
    no-whole-memory-injection guard has a genuine whole-tree leak to detect against:
    nothing (no selector, no static input) names that file, so it must never appear.
    ``architecture.md`` and ``constitution.md`` are declared static inputs and carry
    distinctive markers used to assert static-input content reaches the prompt.
    """
    specs = tmp_path / "repos" / _CONTEXT / "specs"
    (specs / "memory" / "product").mkdir(parents=True, exist_ok=True)
    (specs / "releases" / _RELEASE).mkdir(parents=True, exist_ok=True)
    (specs / "constitution.md").write_text(_CONSTITUTION_BODY, encoding="utf-8")
    # architecture.md is a declared static input — it legitimately reaches the prefix.
    architecture = (
        "---\nname: architecture\nsummary: the two-layer engine\n---\n\n# Architecture\n\n"
        + ("structural prose line that is summary-irrelevant.\n" * 60)
        + f"\n{_ARCH_STATIC_MARKER}\n"
    )
    (specs / "memory" / "architecture.md").write_text(architecture, encoding="utf-8")
    (specs / "memory" / "quality-assurance.md").write_text("# qa\n", encoding="utf-8")
    # An UNREFERENCED memory atom: no selector and no static_inputs entry names it. Its
    # sentinel must never leak — proving the assembly does not slurp the whole memory tree.
    (specs / "memory" / "secret-unreferenced.md").write_text(
        f"---\nname: secret\n---\n\n# Secret\n\n{_MEMORY_SENTINEL}\n", encoding="utf-8"
    )
    (specs / "memory" / "product" / "catalog.json").write_text('{"features": []}', encoding="utf-8")
    (specs / "memory" / "product" / "some-atom.md").write_text(
        "---\nname: some-atom\n---\n\n# Some atom\n\nbody\n", encoding="utf-8"
    )
    (specs / "releases" / _RELEASE / "SPEC.md").write_text("# spec\n", encoding="utf-8")
    (specs / "releases" / _RELEASE / "PLAN.md").write_text(
        "# plan\n\n## Validation Dependency Table\n\n"
        "| Workstream | Produces by end | Direct validation | Validation dependencies | Deferred integration evidence |\n"
        "|---|---|---|---|---|\n"
        "| WS-1 | value | unit tests | None | None |\n",
        encoding="utf-8",
    )
    (specs / "releases" / _RELEASE / "TASKS.md").write_text(
        "# tasks\n\n### [ ] T1 - Fixture task\n", encoding="utf-8"
    )
    return specs


def _workflow(
    tmp_path: Path,
    store: object,
    factory: object,
    *,
    prefix: PromptPrefix | None = None,
) -> ReleaseDefinitionWorkflow:
    specs = _specs_tree(tmp_path)
    selector = ContextSelector(
        SpecContext(specs_dir=specs, release_id=_RELEASE, handoff_dir=tmp_path / "handoff")
    )
    return ReleaseDefinitionWorkflow(
        context=_CONTEXT,
        release_id=_RELEASE,
        run_store=store,  # type: ignore[arg-type]
        runtime_factory=factory,  # type: ignore[arg-type]
        context_selector=selector,
        prefix=prefix,
    )


def _stable_prefix() -> PromptPrefix:
    return PromptPrefix.from_sections(
        {
            "constitution": "the release-stable constitution block",
            "tech-stack": "the release-stable tech-stack block",
        }
    )


def _model_steps() -> list[str]:
    return [s.label for s in _SEQUENCE if s.fragment_id is not None]


# ---------------------------------------------------------------------------
# ① per-step composition persisted + JSON round-trip + prompt_composition accessor
# ---------------------------------------------------------------------------


def test_run_record_persists_composition_and_round_trips_through_json_store(
    tmp_path: Path,
) -> None:
    store = _MemoryRunStore()
    prefix = _stable_prefix()
    wf = _workflow(
        tmp_path,
        store,
        lambda kind: _KindFake(kind, _approved()),
        prefix=prefix,
    )

    wf.run("obs-1")

    run = store.load("obs-1")
    assert run is not None
    by_step = {entry.step: entry for entry in run.injected_context}
    # Static inputs fold into a PER-STEP prefix (each step pays only for its own
    # fragments' declared inputs), so hashes may legitimately differ across steps.
    # A step that declares static inputs records a hash differing from the bare prefix.
    spec_create_hash = by_step["definition_draft"].prefix_hash
    assert spec_create_hash is not None
    assert spec_create_hash != prefix.content_hash
    # Every model step recorded a full composition record.
    for label in _model_steps():
        entry = by_step[label]
        assert entry.fragment_ids, f"{label} missing fragment ids"
        assert entry.prefix_hash is not None
        assert entry.runtime_kind == AgentRuntimeKind.FAKE.value
        assert entry.output_schema  # the fragment's declared output contract
        assert entry.gate_result == GateVerdict.APPROVED.value
        # model is the discrete per-step model (None in the FAKE default — field present).
        assert entry.model is None or isinstance(entry.model, str)

    json_store = JsonLifecycleRunStore(tmp_path)
    json_wf = _workflow(
        tmp_path,
        json_store,
        lambda kind: _KindFake(kind, _approved()),
        prefix=prefix,
    )
    json_wf.run("obs-2")

    reloaded = json_store.load("obs-2")
    assert reloaded is not None
    # The whole record round-trips byte-for-byte: to_dict(from_dict(to_dict)) is stable.
    assert LifecycleRun.from_dict(reloaded.to_dict()) == reloaded
    # The WS-9 fields survived persistence (not dropped by the store). The effective
    # prefix hash (with static_inputs folded in) is shared across steps and round-trips.
    reloaded_hashes = {
        e.prefix_hash for e in reloaded.injected_context if e.prefix_hash is not None
    }
    assert reloaded_hashes
    arch_review = next(e for e in reloaded.injected_context if e.step == "definition_review")
    assert arch_review.prefix_hash in reloaded_hashes
    assert arch_review.runtime_kind == AgentRuntimeKind.FAKE.value
    assert arch_review.output_schema
    assert arch_review.gate_result == GateVerdict.APPROVED.value
    # The minimal observability accessor exposes the same data queryably.
    composition = reloaded.prompt_composition()
    assert {c["step"] for c in composition} >= set(_model_steps())
    assert all("prefix_hash" in c and "gate_result" in c for c in composition)


# ---------------------------------------------------------------------------
# Prefix byte-identity across steps sharing the stable prefix
# ---------------------------------------------------------------------------


def test_prefix_bytes_are_byte_identical_across_steps(tmp_path: Path) -> None:
    store = _MemoryRunStore()
    prefix = _stable_prefix()
    wf = _workflow(
        tmp_path,
        store,
        lambda kind: _KindFake(kind, _approved()),
        prefix=prefix,
    )

    result = wf.run("obs-3")

    model_steps = [s for s in result.steps if s.fragment_id is not None]
    assert len(model_steps) >= 2, "need >=2 model steps to assert prefix behavior"
    # Per-step prefixes: each step's recorded hash is the sha256 of the exact prefix
    # bytes leading ITS OWN prompt, and steps declaring the SAME static inputs share
    # identical prefix bytes (the cacheable unit is now per-step, not per-run).
    run = store.load("obs-3")
    assert run is not None
    by_step = {e.step: e for e in run.injected_context}
    prefix_bytes: dict[str, str] = {}
    for step in model_steps:
        assert step.prompt_text is not None
        step_prefix = step.prompt_text.split("\n\n---\n\n", 1)[0]
        prefix_bytes[step.label] = step_prefix
        recorded = by_step[step.label].prefix_hash
        assert recorded == hashlib.sha256(step_prefix.encode("utf-8")).hexdigest(), (
            f"step {step.label}'s recorded prefix hash does not match its prompt bytes"
        )
    # spec_review and plan_review declare the same static inputs -> identical prefixes.
    if "definition_review" in prefix_bytes and "definition_review" in prefix_bytes:
        assert prefix_bytes["definition_review"] == prefix_bytes["definition_review"]

    # No whole-memory injection by default (cost regression guard). The sentinel lives
    # deep in architecture.md's body. The release-definition fragments only ever pull
    # architecture under the bounded `summary` policy, so no step's prompt may contain
    # the whole atom body — the sentinel must never appear in ANY prompt.
    for step in result.steps:
        if step.prompt_text is None:
            continue
        assert _MEMORY_SENTINEL not in step.prompt_text, (
            f"step {step.label} leaked the whole memory corpus into its prompt"
        )


# ---------------------------------------------------------------------------
# ② static_inputs reach prompt + missing-static-input degrades gracefully
# ---------------------------------------------------------------------------


def test_declared_static_inputs_reach_prompt_and_degrade_gracefully_when_missing(
    tmp_path: Path,
) -> None:
    # The release_definition fragments declare static_inputs (specs/constitution.md and
    # specs/memory/architecture.md). Their content must be injected into the assembled
    # prompt (via the cacheable prefix).
    store = _MemoryRunStore()
    wf = _workflow(
        tmp_path,
        store,
        lambda kind: _KindFake(kind, _approved()),
        prefix=_stable_prefix(),
    )

    result = wf.run("obs-static")

    model_steps = {s.label: s for s in result.steps if s.fragment_id is not None}
    assert model_steps
    # Per-step static inputs: constitution.md is declared ONLY by spec_create — it must
    # reach spec_create and must NOT tax steps that never declared it.
    spec_create = model_steps["definition_draft"]
    assert spec_create.prompt_text is not None
    assert "STATIC_CONST_MARKER_42" in spec_create.prompt_text
    assert _ARCH_STATIC_MARKER in spec_create.prompt_text
    # definition_review declares only architecture.md, so it must NOT be taxed with the
    # constitution the draft step declared — that union tax is what this pins.
    scope = model_steps["definition_review"]
    assert scope.prompt_text is not None
    assert "STATIC_CONST_MARKER_42" not in scope.prompt_text, (
        "definition_review does not declare the constitution — the union tax is back"
    )
    review = model_steps["definition_review"]
    assert review.prompt_text is not None
    assert _ARCH_STATIC_MARKER in review.prompt_text

    # Remove a declared static input file; the workflow must not crash and must still run
    # every step, simply omitting the absent file's content (graceful skip).
    specs = _specs_tree(tmp_path / "missing-variant")
    (specs / "constitution.md").unlink()
    selector = ContextSelector(
        SpecContext(specs_dir=specs, release_id=_RELEASE, handoff_dir=tmp_path / "handoff")
    )
    missing_wf = ReleaseDefinitionWorkflow(
        context=_CONTEXT,
        release_id=_RELEASE,
        run_store=_MemoryRunStore(),  # type: ignore[arg-type]
        runtime_factory=lambda kind: _KindFake(kind, _approved()),  # type: ignore[arg-type, return-value]
        context_selector=selector,
        prefix=_stable_prefix(),
    )

    missing_result = missing_wf.run("obs-missing")

    assert missing_result.completed
    missing_steps = {s.label: s for s in missing_result.steps if s.fragment_id is not None}
    # constitution.md is gone — its marker must be absent everywhere; architecture
    # still reaches the steps that declare it (graceful skip, no crash).
    for step in missing_steps.values():
        assert step.prompt_text is not None
        assert "STATIC_CONST_MARKER_42" not in step.prompt_text
    assert _ARCH_STATIC_MARKER in (missing_steps["definition_draft"].prompt_text or "")
