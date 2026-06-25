"""WS-7 — the cacheable prompt prefix is deterministic and prepended verbatim."""

from __future__ import annotations

from dadaia_workspace.core.models.lifecycle import AgentRuntimeKind, GateEvidenceKind
from dadaia_workspace.features.lifecycle.prompt_builder import (
    LifecyclePromptBuilder,
    PromptPrefix,
    PromptScope,
)


def _scope() -> PromptScope:
    return PromptScope(
        role="qa-engineer",
        context="dadaia-workspace",
        release_id="multiharness-engine-v0116",
        task_id="t1",
        prompt="do the qa step",
        allowed_paths=(".dadaia/handoff/dadaia-workspace/**",),
        required_evidence=(GateEvidenceKind.HANDOFF,),
    )


def test_prefix_is_deterministic_and_order_independent() -> None:
    a = PromptPrefix.from_sections({"constitution": "C", "memory": "M"})
    b = PromptPrefix.from_sections({"memory": "M", "constitution": "C"})
    assert a.text == b.text  # sorted assembly → byte-identical regardless of input order
    assert a.content_hash == b.content_hash
    assert len(a.content_hash) == 64  # sha256 hex


def test_build_without_prefix_is_unchanged() -> None:
    built = LifecyclePromptBuilder().build(_scope(), runtime=AgentRuntimeKind.FAKE)
    assert built.prefix_hash is None
    assert built.request.prompt == "do the qa step"


def test_build_with_prefix_prepends_verbatim_and_records_hash() -> None:
    prefix = PromptPrefix.from_sections({"constitution": "law", "spec": "the spec"})
    built = LifecyclePromptBuilder().build(_scope(), runtime=AgentRuntimeKind.FAKE, prefix=prefix)
    assert built.prefix_hash == prefix.content_hash
    assert built.request.prompt.startswith(prefix.text)
    assert built.request.prompt.endswith("do the qa step")
    assert built.prompt_text.startswith(prefix.text)
