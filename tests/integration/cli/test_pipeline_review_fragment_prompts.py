"""AC-1 — the pipeline review gates emit fragment-scoped prompts, not the generic suffix.

``pipeline.review_security`` and ``pipeline.review_code`` (v0.1.43 WS-1) now carry a
``fragment_id`` so their worker prompt is assembled from the fragment library instead of
the ``_generic_prompt`` placeholder. Static wiring alone is insufficient to prove this:
the FAKE adapter ignores the prompt, so a wrong-but-existing ``fragment_id`` would pass a
mere wiring check. This test captures the ACTUAL prompt string that reaches each worker
and asserts the built prompt CONTAINS the step's own fragment-body marker AND that the
generic ``"Run the {label} step for release"`` suffix is ABSENT — mirroring
``test_release_definition_workflow.py::test_emitted_prompts_are_fragment_scoped_not_generic``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pytest

from dadaia_workspace import container
from dadaia_workspace.core.models.lifecycle import (
    AgentRunRequest,
    AgentRunResult,
    AgentRunStatus,
    AgentRuntimeKind,
)
from dadaia_workspace.core.protocols.agent_runtime import AgentRuntimePort
from dadaia_workspace.features.lifecycle.pipeline import implementation_ladder
from dadaia_workspace.features.workspace.service import WorkspaceService
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
from dadaia_workspace.infrastructure.python_env import VenvPythonEnvironmentManager

_CONTEXT = "dadaia-workspace"
_RELEASE = "multiharness-engine-v0116"


def _init_workspace(path: Path) -> Path:
    WorkspaceService(
        public_assets=FileSystemPublicAssetManager(),
        python_env=VenvPythonEnvironmentManager(),
    ).init(path)
    return path


def _passing_result(label: str) -> AgentRunResult:
    return AgentRunResult(
        status=AgentRunStatus.SUCCEEDED,
        summary=f"fake runtime: {label} APPROVED",
        artifact_refs=(f".dadaia/handoff/{_CONTEXT}/{label}.handoff.json",),
        structured_output={"verdict": "APPROVED", "task_group": "rc-1"},
    )


@dataclass
class _RecordingFake:
    """A FAKE runtime that records the prompt string of every request it runs."""

    captured: dict[str, str] = field(default_factory=dict)

    def runtime_kind(self) -> AgentRuntimeKind:
        return AgentRuntimeKind.FAKE

    def run(self, request: AgentRunRequest) -> AgentRunResult:
        task_id = request.task_id or ""
        label = task_id.rsplit(":", 1)[-1]
        self.captured[label] = request.prompt
        result = _passing_result(label)
        # Gate verifies declared refs EXIST (bug gate-accepts-phantom-artifact-evidence).
        for ref in result.artifact_refs:
            target = Path.cwd() / ref
            if not target.exists():
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text('{"fake": true}\n', encoding="utf-8")
        return result


def _install_recording_fake(monkeypatch: pytest.MonkeyPatch) -> _RecordingFake:
    recorder = _RecordingFake()
    real_build = container.build_agent_runtime

    def fake_build(
        kind: AgentRuntimeKind, *, cwd: Path | None = None, model: object = None
    ) -> AgentRuntimePort:
        if kind is AgentRuntimeKind.FAKE:
            return recorder
        return real_build(kind, cwd=cwd)

    monkeypatch.setattr(container, "build_agent_runtime", fake_build)
    return recorder


@pytest.mark.parametrize(
    ("label", "marker"),
    [
        ("review_security", "<!-- fragment:implementation.security_review -->"),
        ("review_code", "<!-- fragment:implementation.code_review -->"),
    ],
)
def test_pipeline_review_prompt_is_fragment_scoped_not_generic(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    label: str,
    marker: str,
) -> None:
    recorder = _install_recording_fake(monkeypatch)
    workspace = _init_workspace(tmp_path)
    monkeypatch.chdir(workspace)

    pipeline = container.build_lifecycle_pipeline(
        workspace,
        context=_CONTEXT,
        release_id=_RELEASE,
    )
    ladder = implementation_ladder(AgentRuntimeKind.FAKE)
    result = pipeline.run("pipe-review-prompts", ladder)

    assert result.completed is True, result.blocked
    prompt = recorder.captured.get(label)
    assert prompt is not None, f"no prompt captured for {label}"
    # Fragment-sourced content: the step's own fragment-body marker is present.
    assert marker in prompt
    # The generic "Run the {label} step for release …" suffix never appears for any step.
    for captured_label, captured_prompt in recorder.captured.items():
        assert f"Run the {captured_label} step for release" not in captured_prompt
