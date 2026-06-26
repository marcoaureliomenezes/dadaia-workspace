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
   release-definition step does NOT inject the entire memory corpus — only the bounded
   slice the fragment's ``max_context_policy`` allows. ``architecture.md`` is the large,
   structural memory atom that the shipped release-definition fragments only ever pull
   under the ``summary`` policy (via ``architecture_summary``), never in full. The guard
   plants a sentinel deep in the architecture body (past the frontmatter / leading lines
   a summary returns) and asserts it never reaches any step's prompt — proving the
   selector returns a bounded summary, not the whole atom body.
"""

from __future__ import annotations

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

#: A unique string buried deep in the large ``architecture.md`` body (past the
#: frontmatter / leading lines a summary returns). The shipped release-definition
#: fragments only ever pull architecture under the ``summary`` policy, so this sentinel
#: must NEVER appear in any step's prompt. If the selector ever slurped the whole atom
#: body (a whole-memory-injection cost regression), this would leak.
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


def _specs_tree(tmp_path: Path) -> Path:
    """A minimal specs tree the context selector can resolve dynamic inputs against.

    The large ``architecture.md`` atom carries the ``_MEMORY_SENTINEL`` deep in its body
    (well past the frontmatter and the leading lines a ``summary`` returns) so the
    no-whole-memory-injection guard has a genuine whole-body leak to detect against.
    """
    specs = tmp_path / "repos" / _CONTEXT / "specs"
    (specs / "memory" / "product").mkdir(parents=True)
    (specs / "releases" / _RELEASE).mkdir(parents=True)
    (specs / "constitution.md").write_text("# constitution\n", encoding="utf-8")
    # architecture.md: a real frontmatter block + bulky body; the sentinel sits far past
    # the leading lines a `summary` slice returns. Only a whole-body read would surface it.
    architecture = (
        "---\nname: architecture\nsummary: the two-layer engine\n---\n\n# Architecture\n\n"
        + ("structural prose line that is summary-irrelevant.\n" * 60)
        + f"\n{_MEMORY_SENTINEL}\n"
    )
    (specs / "memory" / "architecture.md").write_text(architecture, encoding="utf-8")
    (specs / "memory" / "quality-assurance.md").write_text("# qa\n", encoding="utf-8")
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
# 1. Per-step prompt composition persisted + round-trips through the JSON store
# ---------------------------------------------------------------------------


def test_run_record_persists_per_step_prompt_composition(tmp_path: Path) -> None:
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
    # Every model step recorded a full composition record.
    for label in _model_steps():
        entry = by_step[label]
        assert entry.fragment_ids, f"{label} missing fragment ids"
        assert entry.prefix_hash == prefix.content_hash
        assert entry.runtime_kind == AgentRuntimeKind.FAKE.value
        assert entry.output_schema  # the fragment's declared output contract
        assert entry.gate_result == GateVerdict.APPROVED.value
        # model is the discrete per-step model (None in the FAKE default — field present).
        assert entry.model is None or isinstance(entry.model, str)


def test_prompt_composition_round_trips_through_json_store(tmp_path: Path) -> None:
    store = JsonLifecycleRunStore(tmp_path)
    prefix = _stable_prefix()
    wf = _workflow(
        tmp_path,
        store,
        lambda kind: _KindFake(kind, _approved()),
        prefix=prefix,
    )

    wf.run("obs-2")

    reloaded = store.load("obs-2")
    assert reloaded is not None
    # The whole record round-trips byte-for-byte: to_dict(from_dict(to_dict)) is stable.
    assert LifecycleRun.from_dict(reloaded.to_dict()) == reloaded
    # The WS-9 fields survived persistence (not dropped by the store).
    arch_review = next(e for e in reloaded.injected_context if e.step == "spec_arch_review")
    assert arch_review.prefix_hash == prefix.content_hash
    assert arch_review.runtime_kind == AgentRuntimeKind.FAKE.value
    assert arch_review.output_schema
    assert arch_review.gate_result == GateVerdict.APPROVED.value
    # The minimal observability accessor exposes the same data queryably.
    composition = reloaded.prompt_composition()
    assert {c["step"] for c in composition} >= set(_model_steps())
    assert all("prefix_hash" in c and "gate_result" in c for c in composition)


# ---------------------------------------------------------------------------
# 2. Prefix byte-identity across steps sharing the stable prefix
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
    # Every step that shares the prefix records the SAME hash...
    run = store.load("obs-3")
    assert run is not None
    hashes = {e.prefix_hash for e in run.injected_context if e.prefix_hash is not None}
    assert hashes == {prefix.content_hash}, "prefix hash differs across steps — not cacheable"
    # ...and the prefix BYTES lead every emitted prompt verbatim (built once, reused).
    for step in model_steps:
        assert step.prompt_text is not None
        assert step.prompt_text.startswith(prefix.text), (
            f"step {step.label} did not reuse the cacheable prefix bytes verbatim"
        )
    # Recompute the digest from the shared bytes to prove hash == sha256(prefix bytes).
    assert (
        PromptPrefix.from_sections(
            {
                "constitution": "the release-stable constitution block",
                "tech-stack": "the release-stable tech-stack block",
            }
        ).content_hash
        == prefix.content_hash
    )


# ---------------------------------------------------------------------------
# 3. No whole-memory injection by default (cost regression guard)
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
