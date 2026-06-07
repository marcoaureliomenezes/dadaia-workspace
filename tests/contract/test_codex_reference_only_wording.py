"""Codex orchestration wording must distinguish agents from workflow docs."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS_DIR = REPO_ROOT / "dadaia_workspace" / "public" / "workflows"
AGENTS_DIR = REPO_ROOT / "dadaia_workspace" / "public" / "agents"
# agent-orchestration.md lives under specs/memory/product/agents/ (moved in v0.1.8 restructure)
AGENT_ORCHESTRATION = (
    REPO_ROOT / "specs" / "memory" / "product" / "agents" / "agent-orchestration.md"
)

FORBIDDEN_CODEX_PROMISES = (
    "deferred multi-agent tools when that capability is available",
    "fake literal `subagent` tool",
    "tool_search",
)


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_parallel_workflows_state_codex_workflow_docs_boundary() -> None:
    """Workflow docs must state that Codex does not auto-execute the file itself."""
    missing: list[str] = []

    for path in sorted(WORKFLOWS_DIR.glob("*.workflow.md")):
        content = _text(path)
        if "parallel_group:" not in content:
            continue
        lowered = content.lower()
        if not (
            "codex" in lowered and "workflow" in lowered and "does not auto-execute" in lowered
        ):
            missing.append(path.name)

    assert missing == []


def test_codex_facing_text_does_not_promise_fake_tools() -> None:
    """Codex-facing public text must not claim fake deferred tools."""
    paths = [
        AGENT_ORCHESTRATION,
        *sorted(AGENTS_DIR.glob("*.md")),
        *sorted(WORKFLOWS_DIR.glob("*.workflow.md")),
    ]
    failures: list[str] = []

    for path in paths:
        content = _text(path)
        for phrase in FORBIDDEN_CODEX_PROMISES:
            if phrase in content:
                failures.append(f"{path.relative_to(REPO_ROOT).as_posix()}: {phrase}")

    assert failures == []


def test_codex_dispatcher_memory_names_custom_agent_boundary() -> None:
    """Memory product truth must distinguish custom agents from workflow docs."""
    content = _text(AGENT_ORCHESTRATION).lower()
    assert "codex custom agents" in content
    assert "workflow markdown" in content
    assert "does not auto-execute" in content
