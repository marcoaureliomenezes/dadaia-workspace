"""Codex orchestration wording must stay reference-only unless spawning exists."""

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
    "Codex best-effort parallel",
    "Codex supports best-effort parallel",
    "deferred multi-agent tools when that capability is available",
    "fake literal `subagent` tool",
    "parallel stages may be dispatched in parallel",
)


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_parallel_workflows_state_codex_reference_only_mode() -> None:
    """Any public workflow with parallel topology must include the Codex caveat."""
    missing: list[str] = []

    for path in sorted(WORKFLOWS_DIR.glob("*.workflow.md")):
        content = _text(path)
        if "parallel_group:" not in content:
            continue
        lowered = content.lower()
        if not (
            "codex receives manual/reference" in lowered and "does not spawn subagents" in lowered
        ):
            missing.append(path.name)

    assert missing == []


def test_codex_facing_text_does_not_promise_spawned_parallelism() -> None:
    """Codex-facing public text must not claim runtime spawning or fake tools."""
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


def test_codex_dispatcher_memory_names_manual_handoff_boundary() -> None:
    """Memory product truth must describe Codex orchestration as manual/reference."""
    content = _text(AGENT_ORCHESTRATION).lower()
    assert "reference-only" in content
    assert "manual handoff" in content
    assert "not a promise of runtime concurrency" in content
