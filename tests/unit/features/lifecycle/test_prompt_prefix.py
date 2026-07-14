"""WS-7 — the cacheable prompt prefix is deterministic and prepended verbatim."""

from __future__ import annotations

from dadaia_workspace.core.models.lifecycle import AgentRuntimeKind, GateEvidenceKind
from dadaia_workspace.features.lifecycle.prompt_builder import (
    LifecyclePromptBuilder,
    PromptPrefix,
    PromptScope,
    canonical_worker_output_ref,
    filter_context_spec_paths,
)


def _scope() -> PromptScope:
    return PromptScope(
        role="qa-engineer",
        context="dadaia-workspace",
        release_id="multiharness-engine-v0116",
        task_id="t1",
        prompt="do the qa step",
        allowed_paths=(".dadaia/tmp/lifecycle-worker/dadaia-workspace/**",),
        required_evidence=(GateEvidenceKind.HANDOFF,),
    )


def test_prefix_is_deterministic_and_order_independent() -> None:
    a = PromptPrefix.from_sections({"constitution": "C", "memory": "M"})
    b = PromptPrefix.from_sections({"memory": "M", "constitution": "C"})
    assert a.text == b.text  # sorted assembly → byte-identical regardless of input order
    assert a.content_hash == b.content_hash
    assert len(a.content_hash) == 64  # sha256 hex


def test_build_assigns_exact_handoff_and_prepends_prefix_verbatim() -> None:
    without = LifecyclePromptBuilder().build(_scope(), runtime=AgentRuntimeKind.FAKE)
    assert without.prefix_hash is None
    handoff_ref = canonical_worker_output_ref("dadaia-workspace", "t1")
    assert without.request.prompt.startswith("do the qa step")
    assert f"create exactly `{handoff_ref}`" in without.request.prompt
    assert f"include exactly `{handoff_ref}`" in without.request.prompt
    assert "read it back" in without.request.prompt

    prefix = PromptPrefix.from_sections({"constitution": "law", "spec": "the spec"})
    with_prefix = LifecyclePromptBuilder().build(
        _scope(), runtime=AgentRuntimeKind.FAKE, prefix=prefix
    )
    assert with_prefix.prefix_hash == prefix.content_hash
    assert with_prefix.request.prompt.startswith(prefix.text)
    assert "do the qa step" in with_prefix.request.prompt
    assert with_prefix.request.prompt.endswith(
        "workflow handoff ledger."
    )
    assert with_prefix.prompt_text.startswith(prefix.text)


def test_canonical_worker_output_ref_is_stable_and_collision_resistant() -> None:
    first = canonical_worker_output_ref("demo", "run:review qa")
    again = canonical_worker_output_ref("demo", "run:review qa")
    similar = canonical_worker_output_ref("demo", "run-review-qa")

    assert first == again
    assert first.startswith(".dadaia/tmp/lifecycle-worker/demo/run-review-qa-")
    assert first.endswith(".step-output.json")
    assert "/handoff/" not in first
    assert first != similar


def test_production_scope_keeps_only_resolved_context_specs_tree(tmp_path) -> None:
    context_specs = tmp_path / "repos" / "demo" / "specs"
    context_specs.mkdir(parents=True)
    paths = (
        "repos/demo/specs/releases/v1/**",
        "specs/releases/v1/**",
        ".dadaia/handoff/demo/**",
    )

    assert filter_context_spec_paths(
        paths, workspace_root=tmp_path, specs_dir=context_specs
    ) == (
        "repos/demo/specs/releases/v1/**",
        ".dadaia/handoff/demo/**",
    )
    assert filter_context_spec_paths(paths, workspace_root=None, specs_dir=None) == paths
