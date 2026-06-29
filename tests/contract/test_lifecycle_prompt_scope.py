"""Contract tests for lifecycle worker prompt scope."""

from __future__ import annotations

import json

from dadaia_workspace.core.models.lifecycle import GateEvidenceKind
from dadaia_workspace.features.lifecycle.prompt_builder import (
    LifecyclePromptBuilder,
    PromptScope,
)


def test_prompt_contract_excludes_whole_workspace_context() -> None:
    built = LifecyclePromptBuilder().build(
        PromptScope(
            role="software-engineer",
            context="dadaia-workspace",
            release_id="v0.1.15",
            task_id="T-015-18",
            prompt="Implement the prompt builder only.",
            allowed_paths=(
                "dadaia_workspace/features/lifecycle/prompt_builder.py",
                "tests/contract/test_lifecycle_prompt_scope.py",
            ),
            forbidden_paths=("repos/other-project/src/**", "specs/_archive/**"),
            required_evidence=(GateEvidenceKind.HANDOFF,),
        )
    )

    payload = json.loads(built.prompt_text)

    assert "memory" not in payload
    assert "workspace_tree" not in payload
    assert "all_specs" not in payload
    assert payload["write_scope"] == {
        "allowed_paths": [
            "dadaia_workspace/features/lifecycle/prompt_builder.py",
            "tests/contract/test_lifecycle_prompt_scope.py",
        ],
        "forbidden_paths": ["repos/other-project/src/**", "specs/_archive/**"],
    }
    assert built.request.allowed_paths == tuple(payload["write_scope"]["allowed_paths"])
    assert built.request.forbidden_paths == tuple(payload["write_scope"]["forbidden_paths"])


def test_lifecycle_worker_prompt_forbids_nested_lifecycle_invocation() -> None:
    built = LifecyclePromptBuilder().build(
        PromptScope(
            role="security-reviewer",
            context="dadaia-workspace",
            release_id="v0.1.37",
            task_id="T-037-1",
            prompt="Review the scoped change.",
            allowed_paths=(".dadaia/handoff/dadaia-workspace/**",),
            required_evidence=(GateEvidenceKind.HANDOFF,),
        )
    )

    assert "You are already running as a bounded Layer-2 worker" in built.request.prompt
    assert "Do not invoke `dadaia lifecycle ...`" in built.request.prompt
    payload = json.loads(built.prompt_text)
    assert "Do not invoke `dadaia lifecycle ...`" in payload["instructions"]
