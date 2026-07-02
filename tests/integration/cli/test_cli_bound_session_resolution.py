"""Bound-session specs-dir resolution for resolver-driven CLIs (v0.1.50 FR4).

Root cause (pinned at definition review): `bugs.py` called the shared
`resolve_specs_dir` WITHOUT `ancestry_pids`, degrading bind-marker attribution to
single-`getppid()` equality — a bound harness session's CLI calls fell through to
`cwd/specs`, silently landing governance artifacts in a root-law-violating
workspace-root `specs/`. The fix centralizes ancestry-threading in ONE shared CLI
seam and adds a root-law guard to the cwd fallback.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace import container
from dadaia_workspace.cli.main import app

pytestmark = [pytest.mark.integration, pytest.mark.slow]

_runner = CliRunner()

_APPEND_ARGS = [
    "bugs",
    "append",
    "--bug-id",
    "fixture-bug",
    "--event",
    "reported",
    "--reported-by",
    "fixture-agent",
    "--title",
    "fixture title",
    "--severity",
    "LOW",
    "--surface",
    "fixture surface",
    "--component",
    "fixture component",
    "--context",
    "projx",
    "--tag",
    "fixture",
    "--symptom",
    "fixture symptom",
    "--repro",
    "fixture repro",
    "--expected",
    "fixture expected",
    "--notes",
    "fixture notes",
]


def _make_workspace(root: Path) -> None:
    states = root / ".dadaia" / "states"
    states.mkdir(parents=True)
    (states / "spec_contexts.json").write_text('{"contexts": []}', encoding="utf-8")


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in ("DADAIA_CONTEXT", "DADAIA_SESSION_ID"):
        monkeypatch.delenv(var, raising=False)


def test_bugs_append_resolves_bound_context_via_ancestry_chain(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A bind marker anchored at a DEEP ancestor (beyond getppid) must attribute:
    the CLI seam threads the full ancestry chain (degraded getppid-only misses it)."""
    ws = tmp_path / "ws"
    _make_workspace(ws)
    ctx_bugs = ws / "repos" / "projx" / "specs" / "bugs"
    ctx_bugs.mkdir(parents=True)

    chain = container.build_ancestry_pid_chain(os.getppid())
    if len(chain) < 2:
        pytest.skip("no grandparent pid available on this platform")
    deep_ancestor = chain[1]
    epoch = ws / ".dadaia" / "states" / "bind_epoch"
    epoch.mkdir(parents=True)
    (epoch / "projx").write_text(f"{deep_ancestor}\n", encoding="utf-8")

    monkeypatch.chdir(ws)
    result = _runner.invoke(app, _APPEND_ARGS)

    assert result.exit_code == 0, result.output
    assert list(ctx_bugs.glob("*.jsonl")), "event must land in the BOUND context's specs/bugs/"


def test_cwd_fallback_refuses_workspace_root_specs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The cwd fallback must refuse a root-law-violating workspace-root specs/."""
    ws = tmp_path / "ws"
    _make_workspace(ws)
    (ws / "specs" / "bugs").mkdir(parents=True)  # illegal top-level entry

    monkeypatch.chdir(ws)
    result = _runner.invoke(app, _APPEND_ARGS)

    assert result.exit_code != 0
    assert "specs" in result.output
    # Redaction-safe: no absolute operator-local path echoed.
    assert str(ws) not in result.output


def test_cwd_fallback_still_serves_plain_repo_dirs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Outside any workspace, cwd/specs stays a legitimate fallback (repo layout)."""
    repo = tmp_path / "repo"
    (repo / "specs" / "bugs").mkdir(parents=True)

    monkeypatch.chdir(repo)
    result = _runner.invoke(app, _APPEND_ARGS)

    assert result.exit_code == 0, result.output
    assert list((repo / "specs" / "bugs").glob("*.jsonl"))
