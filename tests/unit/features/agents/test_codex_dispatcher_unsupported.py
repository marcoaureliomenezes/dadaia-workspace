"""T-12 — CodexAgentDispatcher unsupported capability raises OrchestrationUnsupportedError (AC6)."""

from pathlib import Path

import pytest

from dadaia_workspace.core.exceptions import OrchestrationUnsupportedError
from dadaia_workspace.core.models.run_state import StageInvocation
from dadaia_workspace.infrastructure.codex_agent_dispatcher import CodexAgentDispatcher


def _make_invocation(tmp_path: Path, stage_id: str = "gate-stage") -> StageInvocation:
    return StageInvocation(
        run_id="run-unspported-42",
        stage_id=stage_id,
        workflow_name="gated-workflow",
        agent="security-reviewer",
        inputs={"target": "api"},
        expected_output_path=f"out/{stage_id}.md",
        must_include=(),
        parallel_group=None,
        invocation_path=str(tmp_path / f"{stage_id}.md"),
    )


def test_check_capability_raises_for_gates_inline(tmp_path: Path) -> None:
    """check_capability('gates_inline') must raise OrchestrationUnsupportedError."""
    dispatcher = CodexAgentDispatcher()
    with pytest.raises(OrchestrationUnsupportedError) as exc_info:
        dispatcher.check_capability("gates_inline")
    assert "gates_inline" in str(exc_info.value).lower()


def test_check_capability_error_message_is_human_readable(tmp_path: Path) -> None:
    """OrchestrationUnsupportedError must carry a descriptive message, not just a code."""
    dispatcher = CodexAgentDispatcher()
    with pytest.raises(OrchestrationUnsupportedError) as exc_info:
        dispatcher.check_capability("gates_inline")
    message = str(exc_info.value)
    # Must explain why it fails, not just what failed
    assert len(message) > 20, "Error message must be descriptive"
    assert "codex" in message.lower()


def test_check_capability_raises_for_parallel(tmp_path: Path) -> None:
    """check_capability('parallel') must raise because Codex is reference-only."""
    dispatcher = CodexAgentDispatcher()
    with pytest.raises(OrchestrationUnsupportedError) as exc_info:
        dispatcher.check_capability("parallel")
    message = str(exc_info.value).lower()
    assert "reference-only" in message
    assert "parallel" in message


def test_check_capability_does_not_raise_for_sequential(tmp_path: Path) -> None:
    """check_capability('sequential') must NOT raise — Codex supports sequential dispatch."""
    dispatcher = CodexAgentDispatcher()
    dispatcher.check_capability("sequential")


def test_check_capability_raises_for_unknown_feature(tmp_path: Path) -> None:
    """check_capability with an unknown feature key must raise OrchestrationUnsupportedError."""
    dispatcher = CodexAgentDispatcher()
    with pytest.raises(OrchestrationUnsupportedError):
        dispatcher.check_capability("nonexistent_feature_xyz")


def test_unsupported_error_does_not_fail_silently(tmp_path: Path) -> None:
    """The capability check must raise, never return None silently for unsupported features."""
    dispatcher = CodexAgentDispatcher()
    raised = False
    try:
        dispatcher.check_capability("gates_inline")
    except OrchestrationUnsupportedError:
        raised = True
    assert raised, "OrchestrationUnsupportedError must be raised — cannot fail silently"


def test_supports_gates_inline_is_false() -> None:
    """capabilities() must declare supports_gates_inline=False."""
    cap = CodexAgentDispatcher().capabilities()
    assert cap.supports_gates_inline is False
