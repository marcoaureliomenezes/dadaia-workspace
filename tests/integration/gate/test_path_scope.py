"""Integration tests for the v0.1.6 gate RULE D (write-allowlist via agents.index.json).

Black-box tests that invoke ``sdd-spec-gate.sh`` as a subprocess with controlled
stdin/env and assert on stdout (the block JSON) and exit code.

NEW contract (v0.1.6):
- RULE D runs ONLY on MUTATING paths (``specs/releases/**``, ``repos/<ctx>/**``).
  ADDITIVE paths (``.dadaia/reports``, ``.dadaia/handoff``, ``specs/backlog`` …) are
  never path-scope checked.
- RULE D reads ``.dadaia/agentic/agents.index.json`` ({agent: [globs]}), substitutes
  ``<ctx>`` with the bound context, and BLOCKs only when a persona is set, is present
  in the index, and none of its globs match. No persona / persona-absent-from-index /
  a matching glob → RULE D passes (fail-open on unknown writer).
- Precedence: MEMORY (RULE A) and FROZEN (RULE B) decide before RULE D.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.slow]

_GATE = (
    Path(__file__).parent.parent.parent.parent
    / "dadaia_workspace"
    / "public"
    / "scripts"
    / "sdd-spec-gate.sh"
)


def _build_workspace(
    tmp_path: Path,
    index: dict[str, list[str]] | None = None,
    active_phase: str = "TASKS",
    active_release: str = "test-release-v1",
    context_name: str = "dadaia-workspace",
) -> Path:
    """Minimal workspace: agents.index.json + spec_contexts.json + ACTIVE.md."""
    agentic = tmp_path / ".dadaia" / "agentic"
    agentic.mkdir(parents=True)
    (agentic / "agents.index.json").write_text(json.dumps(index or {}), encoding="utf-8")

    # Bound-context ACTIVE.md lives under repos/<ctx>/specs (gate reads it there).
    rel_dir = tmp_path / "repos" / context_name / "specs" / "releases" / active_release
    rel_dir.mkdir(parents=True)
    (tmp_path / "repos" / context_name / "specs" / "releases" / "ACTIVE.md").write_text(
        f"release: {active_release}\nphase: {active_phase}\n", encoding="utf-8"
    )

    state_dir = tmp_path / ".dadaia" / "states"
    state_dir.mkdir(parents=True)
    (state_dir / "spec_contexts.json").write_text(
        json.dumps(
            {
                "schema_version": "2",
                "contexts": [{"name": context_name, "state": "alive", "repo_slug": context_name}],
            }
        ),
        encoding="utf-8",
    )
    return tmp_path


def _run_gate(
    ws: Path,
    file_path: str,
    env_overrides: dict[str, str] | None = None,
    tool: str = "Write",
) -> tuple[str, int]:
    payload = {"tool_name": tool, "tool_input": {"file_path": file_path}}
    env = os.environ.copy()
    for key in (
        "DADAIA_AGENT_PERSONA",
        "CLAUDE_AGENT_PERSONA",
        "CODEX_AGENT_PERSONA",
        "OPENCODE_AGENT_PERSONA",
        "DADAIA_CONTEXT",
        "DADAIA_SESSION_ID",
    ):
        env.pop(key, None)
    env["WORKSPACE_ROOT"] = str(ws)
    env["SDD_GATE_LOG"] = str(ws / "gate.log")
    # Distinct lease session per test → no cross-test live-lease interference.
    env["CLAUDE_CODE_SESSION_ID"] = f"sess-{abs(hash(file_path)) % 10**8}"
    if env_overrides:
        env.update(env_overrides)
    proc = subprocess.run(
        ["bash", str(_GATE)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
    )
    return proc.stdout, proc.returncode


def _blocked(stdout: str) -> bool:
    return '"decision": "block"' in stdout or '"decision":"block"' in stdout


# --- RULE D only applies to MUTATING paths ---------------------------------


def test_additive_report_path_never_path_scoped(tmp_path: Path) -> None:
    """An agent writing to ANY .dadaia/reports path is ALLOWED (ADDITIVE, no RULE D)."""
    ws = _build_workspace(tmp_path, index={"code-reviewer": ["specs/**"]})
    out, _ = _run_gate(
        ws,
        ".dadaia/reports/other-agent/x.html",
        env_overrides={"DADAIA_AGENT_PERSONA": "code-reviewer"},
    )
    assert not _blocked(out)


def test_mutating_in_allowlist_allowed(tmp_path: Path) -> None:
    ws = _build_workspace(tmp_path, index={"product-engineer": ["specs/**"]})
    out, _ = _run_gate(
        ws,
        "specs/releases/test-release-v1/SPEC.md",
        env_overrides={"DADAIA_AGENT_PERSONA": "product-engineer"},
    )
    assert not _blocked(out)


def test_mutating_outside_allowlist_blocked(tmp_path: Path) -> None:
    ws = _build_workspace(
        tmp_path, index={"code-reviewer": [".dadaia/reports/<ctx>/code-reviewer/**"]}
    )
    out, _ = _run_gate(
        ws,
        "specs/releases/test-release-v1/SPEC.md",
        env_overrides={"DADAIA_AGENT_PERSONA": "code-reviewer"},
    )
    assert _blocked(out)
    assert "write_allowlist does not permit" in out


def test_mutating_no_persona_fail_open(tmp_path: Path) -> None:
    """No persona env → RULE D is skipped (fail-open), lease then allows."""
    ws = _build_workspace(tmp_path, index={"code-reviewer": ["nope/**"]})
    out, _ = _run_gate(ws, "specs/releases/test-release-v1/SPEC.md")
    assert not _blocked(out)


def test_mutating_persona_absent_from_index_fail_open(tmp_path: Path) -> None:
    ws = _build_workspace(tmp_path, index={"code-reviewer": ["nope/**"]})
    out, _ = _run_gate(
        ws,
        "specs/releases/test-release-v1/SPEC.md",
        env_overrides={"DADAIA_AGENT_PERSONA": "ghost-agent"},
    )
    assert not _blocked(out)


def test_double_star_glob_matches_nested(tmp_path: Path) -> None:
    ws = _build_workspace(tmp_path, index={"software-engineer": ["repos/<ctx>/**"]})
    out, _ = _run_gate(
        ws,
        "repos/dadaia-workspace/dadaia_workspace/features/x.py",
        env_overrides={"DADAIA_AGENT_PERSONA": "software-engineer"},
    )
    assert not _blocked(out)


def test_ctx_substitution_matches_bound_context(tmp_path: Path) -> None:
    ws = _build_workspace(
        tmp_path,
        index={"software-engineer": ["repos/<ctx>/tests/**"]},
        context_name="dadaia-workspace",
    )
    out, _ = _run_gate(
        ws,
        "repos/dadaia-workspace/tests/unit/x.py",
        env_overrides={"DADAIA_AGENT_PERSONA": "software-engineer"},
    )
    assert not _blocked(out)


# --- persona env resolution ------------------------------------------------


def test_harness_specific_persona_env_resolves(tmp_path: Path) -> None:
    ws = _build_workspace(tmp_path, index={"code-reviewer": ["nope/**"]})
    out, _ = _run_gate(
        ws,
        "specs/releases/test-release-v1/SPEC.md",
        env_overrides={"CLAUDE_AGENT_PERSONA": "code-reviewer"},
    )
    assert _blocked(out)


def test_dadaia_persona_takes_priority(tmp_path: Path) -> None:
    """DADAIA_AGENT_PERSONA (matching) wins over CLAUDE_AGENT_PERSONA (non-matching)."""
    ws = _build_workspace(
        tmp_path,
        index={"product-engineer": ["specs/**"], "code-reviewer": ["nope/**"]},
    )
    out, _ = _run_gate(
        ws,
        "specs/releases/test-release-v1/SPEC.md",
        env_overrides={
            "DADAIA_AGENT_PERSONA": "product-engineer",
            "CLAUDE_AGENT_PERSONA": "code-reviewer",
        },
    )
    assert not _blocked(out)


# --- precedence: MEMORY / FROZEN decide before RULE D ----------------------


def test_memory_atomicity_wins_over_path_scope(tmp_path: Path) -> None:
    ws = _build_workspace(tmp_path, index={"code-reviewer": ["specs/**"]}, active_phase="TASKS")
    out, _ = _run_gate(
        ws,
        "repos/dadaia-workspace/specs/memory/architecture.md",
        env_overrides={"DADAIA_AGENT_PERSONA": "code-reviewer"},
    )
    assert _blocked(out)
    assert "memory/ is atomic" in out


def test_archive_path_blocked_before_path_scope(tmp_path: Path) -> None:
    ws = _build_workspace(tmp_path, index={"software-engineer": ["specs/**"]})
    out, _ = _run_gate(
        ws,
        "repos/dadaia-workspace/specs/_archive/old.md",
        env_overrides={"DADAIA_AGENT_PERSONA": "software-engineer"},
    )
    assert _blocked(out)
    assert "_archive/ is read-only" in out
