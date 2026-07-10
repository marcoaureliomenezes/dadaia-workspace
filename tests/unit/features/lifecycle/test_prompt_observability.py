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
        artifact_refs=(f".dadaia/handoff/{_CONTEXT}/step.handoff.json",),
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
    (specs / "releases" / _RELEASE / "PLAN.md").write_text("# plan\n", encoding="utf-8")
    (specs / "releases" / _RELEASE / "TASKS.md").write_text("# tasks\n", encoding="utf-8")
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
    # The workflow folds the fragments' static_inputs into the cacheable prefix, so the
    # effective prefix hash is shared by every step (one value) — not necessarily the
    # hash of the bare input prefix.
    effective_hashes = {by_step[label].prefix_hash for label in _model_steps()}
    assert len(effective_hashes) == 1
    effective_hash = next(iter(effective_hashes))
    assert effective_hash is not None
    # Static inputs were folded in, so the effective hash differs from the bare prefix.
    assert effective_hash != prefix.content_hash
    # Every model step recorded a full composition record.
    for label in _model_steps():
        entry = by_step[label]
        assert entry.fragment_ids, f"{label} missing fragment ids"
        assert entry.prefix_hash == effective_hash
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
    assert len(reloaded_hashes) == 1
    arch_review = next(e for e in reloaded.injected_context if e.step == "spec_arch_review")
    assert arch_review.prefix_hash == next(iter(reloaded_hashes))
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
    assert len(model_steps) >= 2, "need >=2 model steps to assert prefix reuse"
    # The workflow folds the fragments' static_inputs into the cacheable prefix once, so the
    # effective prefix is re-derived; every step must still record exactly ONE prefix hash...
    run = store.load("obs-3")
    assert run is not None
    hashes = {e.prefix_hash for e in run.injected_context if e.prefix_hash is not None}
    assert len(hashes) == 1, "prefix hash differs across steps — not cacheable"
    effective_hash = next(iter(hashes))
    # ...and the SAME prefix BYTES lead every emitted prompt verbatim (built once, reused).
    leading = model_steps[0].prompt_text
    assert leading is not None
    common_prefix = leading.split("\n\n---\n\n", 1)[0]
    for step in model_steps:
        assert step.prompt_text is not None
        assert step.prompt_text.startswith(common_prefix), (
            f"step {step.label} did not reuse the cacheable prefix bytes verbatim"
        )
    # The recorded hash is sha256 of those exact shared prefix bytes (cacheable invariant).
    assert effective_hash == hashlib.sha256(common_prefix.encode("utf-8")).hexdigest()


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

    model_steps = [s for s in result.steps if s.fragment_id is not None]
    assert model_steps
    for step in model_steps:
        assert step.prompt_text is not None
        # constitution.md is a static input of spec_create; architecture.md of several steps.
        assert "STATIC_CONST_MARKER_42" in step.prompt_text, (
            f"step {step.label} did not receive the constitution static-input content"
        )
        assert _ARCH_STATIC_MARKER in step.prompt_text, (
            f"step {step.label} did not receive the architecture static-input content"
        )

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
    missing_model_steps = [s for s in missing_result.steps if s.fragment_id is not None]
    for step in missing_model_steps:
        assert step.prompt_text is not None
        # constitution.md is gone — its marker must be absent, but architecture remains.
        assert "STATIC_CONST_MARKER_42" not in step.prompt_text
        assert _ARCH_STATIC_MARKER in step.prompt_text


# ---------------------------------------------------------------------------
# No whole-memory injection by default (cost regression guard)
# ---------------------------------------------------------------------------


def test_default_step_does_not_inject_whole_memory_corpus(tmp_path: Path) -> None:
    store = _MemoryRunStore()
    wf = _workflow(
        tmp_path,
        store,
        lambda kind: _KindFake(kind, _approved()),
        prefix=_stable_prefix(),
    )

    result = wf.run("obs-4")

    # The sentinel lives deep in architecture.md's body. The release-definition fragments
    # only ever pull architecture under the bounded `summary` policy, so no step's prompt
    # may contain the whole atom body — the sentinel must never appear in ANY prompt.
    for step in result.steps:
        if step.prompt_text is None:
            continue
        assert _MEMORY_SENTINEL not in step.prompt_text, (
            f"step {step.label} leaked the whole memory corpus into its prompt"
        )
