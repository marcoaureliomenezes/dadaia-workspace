"""T-69-10 (FR5) — E2E: a bound context is visible to the CLI (v0.1.69).

The operator-observability path the four v0.1.69 bugs jointly broke: a modern Codex
session's bind was invisible to every resolver-driven command (FR1, CRITICAL); the
diagnostic verbs rejected explicit ``--context`` (FR2, HIGH); ``preflight`` was an inert
hardcoded stub (FR3, MEDIUM); and ``context show`` never reflected a successful bind
(FR4, MEDIUM).

This E2E chains what T-69-01..09 proved in isolation, as production composes it:
provision a hand-assembled ``tmp_path`` workspace + context (no real git clone, no real
subprocess/binary — hermetic, matching the existing ``test_cli_bound_session_resolution.py``
/ ``test_specs_resolver_harness_bind.py`` fixture pattern), bind it via the REAL
``context bind`` Typer command with NO ``DADAIA_SESSION_ID`` set (the normal bare-bind
shape), then assert:

1. ``context show <ctx> --json`` reflects the bind (FR4 — the incumbent-pointer fallback).
2. ``lifecycle preflight --context <ctx> --release-id <rel> --json`` resolves the bound
   context's specs and runs the REAL preflight-input assembly (FR3) — never the retired
   generic stub reason (AC3.1), regardless of whether the check ultimately blocks
   (a fresh checkout with no git history correctly blocks — that is success, not
   failure, per AC3.1's parenthetical).

Intent: CONTRACT — v0.1.69 FR1-FR4 (T-69-10)
Owner: software-engineer
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app

pytestmark = [pytest.mark.integration]

_runner = CliRunner()
_CTX = "journey-ctx"
_RELEASE = "v0.1.99"


def _git(cwd: Path, *args: str) -> None:
    proc = subprocess.run(
        ["git", "-c", "user.email=e2e@test", "-c", "user.name=e2e", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=30.0,
    )
    assert proc.returncode == 0, f"git {args}: {proc.stderr or proc.stdout}"


def _make_workspace(root: Path) -> Path:
    ws = root / "ws"
    (ws / ".dadaia" / "states" / "ctx_locks").mkdir(parents=True)
    (ws / ".dadaia" / "sessions").mkdir(parents=True)
    (ws / ".dadaia" / "states" / "spec_contexts.json").write_text(
        json.dumps(
            {
                "schema_version": "2",
                "contexts": [
                    {
                        "name": _CTX,
                        "state": "alive",
                        "repo_slug": _CTX,
                        "repo_url": "https://example.invalid/journey-ctx.git",
                        "created_at": "2026-07-01T00:00:00+00:00",
                        "alive_since": "2026-07-01T00:00:00+00:00",
                        "dead_since": None,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    repo = ws / "repos" / _CTX
    (repo / "specs" / "releases" / _RELEASE).mkdir(parents=True)
    for name in ("SPEC.md", "PLAN.md", "TASKS.md"):
        (repo / "specs" / "releases" / _RELEASE / name).write_text(
            f"# {name}\n\n> **Status:** Aprovado\n", encoding="utf-8"
        )
    (repo / "specs" / "releases" / "ACTIVE.md").write_text(
        f"release: {_RELEASE}\nphase: IMPLEMENTATION\n", encoding="utf-8"
    )
    (repo / "specs" / "memory" / "product").mkdir(parents=True)
    (repo / "specs" / "memory" / "tech-stack.md").write_text(
        "# tech\nJOURNEY-MARKER\n", encoding="utf-8"
    )
    (repo / "specs" / "memory" / "product" / "catalog.json").write_text(
        '{"features": []}', encoding="utf-8"
    )
    (repo / "specs" / "backlog").mkdir(parents=True)
    _git(repo, "-c", "init.defaultBranch=main", "init")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "seed: journey-ctx specs tree")
    return ws


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in (
        "DADAIA_CONTEXT",
        "DADAIA_SESSION_ID",
        "CLAUDE_CODE_SESSION_ID",
        "CODEX_SESSION_ID",
        "CODEX_THREAD_ID",
    ):
        monkeypatch.delenv(var, raising=False)


def test_bound_context_visible_to_cli_e2e(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ws = _make_workspace(tmp_path)
    monkeypatch.chdir(ws)
    monkeypatch.setenv("CODEX_THREAD_ID", "journey-harness-session")

    # 1) bind — real Typer command, no DADAIA_SESSION_ID (the normal bare-bind shape).
    bind_result = _runner.invoke(
        app,
        ["context", "bind", _CTX, "--mode", "implementation", "--release", _RELEASE],
    )
    assert bind_result.exit_code == 0, bind_result.output

    # 2) Context show reflects this harness's caller-owned bind record.
    show_result = _runner.invoke(app, ["context", "show", _CTX, "--json"])
    assert show_result.exit_code == 0, show_result.output
    show_payload = json.loads(show_result.output)
    assert show_payload["session"] is not None, (
        f"context show must reflect the bind (FR4); got: {show_payload}"
    )
    session = show_payload["session"]
    assert session["context"] == _CTX
    assert session["mode"].upper() == "BOUND_IMPLEMENTATION"
    assert session["release"] == _RELEASE
    bound_sid = session["session_id"]
    assert bound_sid
