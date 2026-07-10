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


def test_codex_orchestration_wording_forbidden_and_required_phrases() -> None:
    """Workflow docs state the Codex-does-not-auto-execute boundary, no Codex-facing
    text promises fake deferred tools, and memory product truth distinguishes custom
    agents from workflow docs."""
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

    content = _text(AGENT_ORCHESTRATION).lower()
    assert "codex custom agents" in content
    assert "workflow markdown" in content
    # The v0.1.48 W2 ownership-consolidation rewrote the atom's phrasing from
    # "does not auto-execute" to "never auto-execute(s)" — the boundary claim is
    # the invariant, not its exact wording; accept either canonical form.
    assert "does not auto-execute" in content or "never auto-execute" in content
