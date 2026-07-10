"""Unit tests for lifecycle prompt builder.

Repo-wide/escape scope rejection is a safety boundary — keep the full path list as params.
"""

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


# --- ① scope rejection param: missing allowed_paths + escaping paths + repo-wide globs ---

_REJECTION_CASES = (
    ("empty-allowed-paths", (), "allowed_paths"),
    ("empty-string", ("",), None),
    ("dot", (".",), None),
    ("double-star", ("**",), None),
    ("star-slash-double-star", ("*/**",), None),
    ("root-slash", ("/",), None),
    ("absolute-tmp-escape", ("/tmp/file",), None),
    ("relative-escape", ("../escape",), None),
    ("repo-wide-bare", ("repos/dadaia-workspace",), "repo-wide"),
    ("repo-wide-star", ("repos/dadaia-workspace/*",), "repo-wide"),
    ("repo-wide-double-star", ("repos/dadaia-workspace/**",), "repo-wide"),
)


@pytest.mark.parametrize(
    "allowed_paths,match",
    [c[1:] for c in _REJECTION_CASES],
    ids=[c[0] for c in _REJECTION_CASES],
)
def test_scope_rejection_matrix(allowed_paths: tuple[str, ...], match: str | None) -> None:
    scope = PromptScope(
        role="software-engineer",
        context="dadaia-workspace",
        release_id="v0.1.15",
        task_id="T-015-18",
        prompt="unsafe",
        allowed_paths=allowed_paths,
    )

    if match is not None:
        with pytest.raises(PromptScopeError, match=match):
            LifecyclePromptBuilder().build(scope)
    else:
        with pytest.raises(PromptScopeError):
            LifecyclePromptBuilder().build(scope)


# --- ② threading: resolved_model + persona + persona-defaults-None -----------------------


def test_build_threads_resolved_model_persona_and_persona_defaults_none() -> None:
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
    model_scope = PromptScope(
        role="qa-engineer",
        context="dadaia-workspace",
        release_id="v0.1.28",
        task_id="run:review_qa",
        prompt="review",
        allowed_paths=(".dadaia/handoff/dadaia-workspace/**",),
        resolved_model=resolved,
    )
    built_model = LifecyclePromptBuilder().build(model_scope)
    assert built_model.request.resolved_model == resolved

    # T-44-4: PromptScope.persona flows DIRECTLY into AgentRunRequest.persona (QA advisory —
    # not only transitively via the envelope).
    mandate = "You are acting as the software-engineer. Implement with tests."
    persona_scope = PromptScope(
        role="software-engineer",
        context="dadaia-workspace",
        release_id="v0.1.44",
        task_id="run:implement",
        prompt="implement",
        allowed_paths=(".dadaia/handoff/dadaia-workspace/**",),
        persona=mandate,
    )
    built_persona = LifecyclePromptBuilder().build(persona_scope)
    assert built_persona.request.persona == mandate

    # A scope with no persona threads ``None`` — the byte-stable persona-less path.
    built_default = LifecyclePromptBuilder().build(_scope())
    assert built_default.request.persona is None
