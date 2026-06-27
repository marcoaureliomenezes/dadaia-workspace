"""Pin the coherent worker-output contract on the suffix builder + generic prompt (Wave A).

These tests pin three facets of the v0.1.32 coherent contract (D-1/D-2/D-3, A1/A2/A4b):

- A1: ``build_fragment_suffix`` is step-kind-aware. A **review** step (``is_review=True``)
  instructs ``structured_output.verdict`` = APPROVED/REJECTED + evidence; a **create** step
  (``is_review=False``) does NOT instruct a verdict.
- A2: the assembled "## Required output" names exactly ONE schema target — the literal field
  ``schema`` set to ``agent-run-result-v1`` — and does NOT surface the fragment's domain
  ``output_schema`` as a competing schema-to-emit.
- A4b / C6: ``pipeline._generic_prompt`` is step-kind-aware too (review -> verdict instruction;
  create -> no self-verdict) — the second stale surface.
"""

from __future__ import annotations

from dadaia_workspace.core.models.lifecycle import (
    AgentRunRequest,
    AgentRunResult,
    AgentRunStatus,
    AgentRuntimeKind,
    LifecyclePhase,
    LifecycleRun,
)
from dadaia_workspace.features.lifecycle.pipeline import LifecyclePipeline, PipelineStep
from dadaia_workspace.features.lifecycle.prompt_builder import (
    FragmentBundle,
    build_fragment_suffix,
)

_TRANSPORT_SCHEMA = "agent-run-result-v1"
_DOMAIN_SCHEMA = "release-scope-handoff-v1"


def _bundle() -> FragmentBundle:
    return FragmentBundle(
        fragment_id="spec.create",
        role="product-engineer",
        body="Author the SPEC.",
        output_schema=_DOMAIN_SCHEMA,
        shared_bodies=("Emit a structured handoff.",),
        shared_ids=("shared.output_handoff",),
    )


def _required_output_section(suffix: str) -> str:
    marker = "## Required output"
    assert marker in suffix, "suffix must carry a '## Required output' section"
    return suffix[suffix.index(marker) :]


# --- A1: step-kind-aware verdict instruction ---------------------------------------


def test_review_step_suffix_instructs_verdict() -> None:
    suffix = build_fragment_suffix(_bundle(), selected_context="", is_review=True)
    section = _required_output_section(suffix)
    assert "structured_output.verdict" in section
    assert "APPROVED" in section and "REJECTED" in section


def test_create_step_suffix_does_not_instruct_verdict() -> None:
    suffix = build_fragment_suffix(_bundle(), selected_context="", is_review=False)
    section = _required_output_section(suffix)
    assert "verdict" not in section.lower()
    # A create step still emits an artifact + artifact_refs.
    assert "artifact_refs" in section


# --- A2: exactly one schema target, the transport id in `schema` --------------------


def test_required_output_names_only_the_transport_schema() -> None:
    for is_review in (True, False):
        suffix = build_fragment_suffix(_bundle(), selected_context="", is_review=is_review)
        section = _required_output_section(suffix)
        # The transport id is the single emit target, named via the `schema` field.
        assert _TRANSPORT_SCHEMA in section
        assert "`schema`" in section
        # The fragment's domain schema is NOT surfaced as a competing schema-to-emit.
        assert _DOMAIN_SCHEMA not in section


# --- A4b / C6: pipeline._generic_prompt is step-kind-aware --------------------------


class _MemoryRunStore:
    def __init__(self) -> None:
        self.saved: dict[str, LifecycleRun] = {}

    def save(self, run: LifecycleRun) -> None:
        self.saved[run.run_id] = run

    def load(self, run_id: str) -> LifecycleRun | None:
        return self.saved.get(run_id)

    def resume(self, run_id: str) -> LifecycleRun:  # pragma: no cover - unused here
        raise NotImplementedError


def _fake_result() -> AgentRunResult:
    return AgentRunResult(status=AgentRunStatus.SUCCEEDED, summary="ok")


def _factory(_kind: AgentRuntimeKind) -> object:
    class _Fake:
        def runtime_kind(self) -> AgentRuntimeKind:
            return _kind

        def run(self, request: AgentRunRequest) -> AgentRunResult:
            return _fake_result()

    return _Fake()


def _pipeline() -> LifecyclePipeline:
    return LifecyclePipeline(
        context="dadaia-workspace",
        release_id="v0.1.32",
        run_store=_MemoryRunStore(),
        runtime_factory=_factory,  # type: ignore[arg-type]
    )


def _generic_step(*, is_review: bool) -> PipelineStep:
    return PipelineStep(
        label="some_step",
        role="software-engineer",
        from_phase=LifecyclePhase.RELEASE_DEFINITION,
        target_phase=LifecyclePhase.RELEASE_DEFINITION,
        runtime_kind=AgentRuntimeKind.CODEX_EXEC,
        is_review=is_review,
    )


def test_generic_prompt_review_step_instructs_verdict() -> None:
    pipeline = _pipeline()
    prompt = pipeline._generic_prompt(_generic_step(is_review=True))
    assert "structured_output.verdict" in prompt
    assert "APPROVED" in prompt and "REJECTED" in prompt


def test_generic_prompt_create_step_does_not_instruct_verdict() -> None:
    pipeline = _pipeline()
    prompt = pipeline._generic_prompt(_generic_step(is_review=False))
    assert "verdict" not in prompt.lower()
