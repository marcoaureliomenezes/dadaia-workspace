"""Unit tests for lifecycle prompt builder."""

from __future__ import annotations

import json

import pytest

from dadaia_workspace.core.models.lifecycle import AgentRuntimeKind, GateEvidenceKind
from dadaia_workspace.features.lifecycle.prompt_builder import (
    LifecyclePromptBuilder,
    PromptScope,
    PromptScopeError,
)


def _scope() -> PromptScope:
    return PromptScope(
        role="software-engineer",
        context="dadaia-workspace",
        release_id="v0.1.15",
        task_id="T-015-18",
        prompt="Implement only the scoped prompt builder.",
        allowed_paths=("dadaia_workspace/features/lifecycle/prompt_builder.py",),
        forbidden_paths=("repos/other-project/src/**",),
        required_evidence=(GateEvidenceKind.HANDOFF, GateEvidenceKind.DIRTY_DIFF),
        model_profile="dispatch",
    )


def test_builds_runtime_request_and_matching_json_prompt() -> None:
    built = LifecyclePromptBuilder().build(_scope(), runtime=AgentRuntimeKind.CODEX_EXEC)

    assert built.request.role == "software-engineer"
    assert built.request.context == "dadaia-workspace"
    assert built.request.release_id == "v0.1.15"
    assert built.request.task_id == "T-015-18"
    assert built.request.allowed_paths == ("dadaia_workspace/features/lifecycle/prompt_builder.py",)
    assert built.request.forbidden_paths == ("repos/other-project/src/**",)
    assert built.request.required_evidence == (
        GateEvidenceKind.HANDOFF,
        GateEvidenceKind.DIRTY_DIFF,
    )

    payload = json.loads(built.prompt_text)
    assert payload["role"] == built.request.role
    assert payload["context"] == built.request.context
    assert payload["release_id"] == built.request.release_id
    assert payload["task_id"] == built.request.task_id
    assert payload["write_scope"]["allowed_paths"] == list(built.request.allowed_paths)
    assert payload["write_scope"]["forbidden_paths"] == list(built.request.forbidden_paths)
    assert payload["expected_schema"] == "agent-run-result-v1"
    assert payload["required_evidence"] == ["handoff", "dirty_diff"]


def test_rejects_missing_allowed_paths() -> None:
    scope = PromptScope(
        role="software-engineer",
        context="dadaia-workspace",
        release_id="v0.1.15",
        task_id="T-015-18",
        prompt="unsafe",
        allowed_paths=(),
    )

    with pytest.raises(PromptScopeError, match="allowed_paths"):
        LifecyclePromptBuilder().build(scope)


@pytest.mark.parametrize("path", ("", ".", "**", "*/**", "/", "/tmp/file", "../escape"))
def test_rejects_whole_workspace_or_escaping_paths(path: str) -> None:
    scope = PromptScope(
        role="software-engineer",
        context="dadaia-workspace",
        release_id="v0.1.15",
        task_id="T-015-18",
        prompt="unsafe",
        allowed_paths=(path,),
    )

    with pytest.raises(PromptScopeError):
        LifecyclePromptBuilder().build(scope)


@pytest.mark.parametrize(
    "path",
    (
        "repos/dadaia-workspace",
        "repos/dadaia-workspace/*",
        "repos/dadaia-workspace/**",
    ),
)
def test_rejects_repo_wide_scope(path: str) -> None:
    scope = PromptScope(
        role="software-engineer",
        context="dadaia-workspace",
        release_id="v0.1.15",
        task_id="T-015-18",
        prompt="unsafe",
        allowed_paths=(path,),
    )

    with pytest.raises(PromptScopeError, match="repo-wide"):
        LifecyclePromptBuilder().build(scope)


def test_build_threads_resolved_model_into_request() -> None:
    # T-28-A-07: PromptScope.resolved_model flows into AgentRunRequest.resolved_model.
    from dadaia_workspace.core.models.workflow_execution import (
        PolicySource,
        ResolvedModelConfig,
    )

    resolved = ResolvedModelConfig(
        profile_id="codex-review-deep",
        harness="codex",
        model="gpt-5.5",
        reasoning="high",
        source=PolicySource.DEFAULT_OVERLAY,
    )
    scope = PromptScope(
        role="qa-engineer",
        context="dadaia-workspace",
        release_id="v0.1.28",
        task_id="run:review_qa",
        prompt="review",
        allowed_paths=(".dadaia/handoff/dadaia-workspace/**",),
        resolved_model=resolved,
    )
    built = LifecyclePromptBuilder().build(scope)
    assert built.request.resolved_model == resolved


def test_build_threads_persona_into_request() -> None:
    # T-44-4: PromptScope.persona flows DIRECTLY into AgentRunRequest.persona (QA advisory —
    # not only transitively via the envelope).
    mandate = "You are acting as the software-engineer. Implement with tests."
    scope = PromptScope(
        role="software-engineer",
        context="dadaia-workspace",
        release_id="v0.1.44",
        task_id="run:implement",
        prompt="implement",
        allowed_paths=(".dadaia/handoff/dadaia-workspace/**",),
        persona=mandate,
    )
    built = LifecyclePromptBuilder().build(scope)
    assert built.request.persona == mandate


def test_build_persona_defaults_to_none() -> None:
    # A scope with no persona threads ``None`` — the byte-stable persona-less path.
    built = LifecyclePromptBuilder().build(_scope())
    assert built.request.persona is None
