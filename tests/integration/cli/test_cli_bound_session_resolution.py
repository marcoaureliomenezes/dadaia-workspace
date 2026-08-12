"""Bound-session specs-dir resolution for resolver-driven CLIs (v0.1.50 FR4).

Root cause (pinned at definition review): `bugs.py` called the shared
`resolve_specs_dir` in a way that silently degraded resolution for a bound harness
session, whose CLI calls fell through to `cwd/specs` — landing governance artifacts in
a root-law-violating workspace-root `specs/`. The fix centralizes resolution in ONE
shared CLI seam (`cli._specs_resolution`, T-50-04: now the single resolution authority).

T-50-05 (SPEC v0.5.0 FR1 deletion item 4): the `cwd/specs` fallback this module used to
pin as a legitimate "outside any workspace" escape hatch is deleted outright —
`DADAIA.md` §3 grants no rung for it. That case is re-pointed below to assert the new
terminal, actionable failure instead of a silent success into an ungoverned directory.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

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


def test_bound_session_resolution_context_flag_rootlaw_and_no_workspace_fails_clean(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """CRITICAL (minimal merge only, v0.1.76 rewrites; T-50-04 deletes the bind-epoch
    marker attribution this test used to exercise as part (1) — the harness-real,
    real-bind end-to-end coverage for the bound-session leg itself now lives in
    ``test_bind_resolution_seam_executed_path.py``): (1) ``bugs append``'s
    ``--context`` routing key (v0.1.82, bug ``bugs-append-ledger-ignores-context-flag``)
    lands the event in that context's ledger; (2) a specs/ AT the workspace root with no
    bound context now fails via the SAME generic terminal error every unresolved case
    raises (T-50-05 deletes the specific "Workspace Root Law" refusal patch along with
    the fallback it was bolted onto — the outcome, refusal, is unchanged); (3) T-50-05
    deletes the ``cwd/specs`` fallback outright — a bare directory outside any dadaia
    workspace no longer resolves via its own local specs/, even when one is right
    there on disk, because ``DADAIA.md`` §3 grants no rung for it."""
    # (1) --context routing key attribution.
    ws = tmp_path / "ws"
    _make_workspace(ws)
    ctx_bugs = ws / "repos" / "projx" / "specs" / "bugs"
    ctx_bugs.mkdir(parents=True)

    monkeypatch.chdir(ws)
    result = _runner.invoke(app, _APPEND_ARGS)

    assert result.exit_code == 0, result.output
    assert list(ctx_bugs.glob("*.jsonl")), "event must land in the routed context's specs/bugs/"

    # (2) a workspace-root specs/ with NO bound context fails via the generic terminal
    # error (not the old specific "Workspace Root Law" message — that patch is gone).
    rootlaw_ws = tmp_path / "rootlaw-ws"
    _make_workspace(rootlaw_ws)
    (rootlaw_ws / "specs" / "bugs").mkdir(parents=True)

    monkeypatch.chdir(rootlaw_ws)
    rootlaw_result = _runner.invoke(app, _APPEND_ARGS)

    assert rootlaw_result.exit_code != 0
    assert "specs" in rootlaw_result.output
    # Redaction-safe: no absolute operator-local path echoed.
    assert str(rootlaw_ws) not in rootlaw_result.output

    # (3) T-50-05: outside any dadaia workspace, the old cwd/specs fallback is deleted —
    # this now fails clean instead of silently writing into an ungoverned directory.
    repo = tmp_path / "repo"
    (repo / "specs" / "bugs").mkdir(parents=True)

    monkeypatch.chdir(repo)
    repo_result = _runner.invoke(app, _APPEND_ARGS)

    assert repo_result.exit_code != 0
    assert not list((repo / "specs" / "bugs").glob("*.jsonl"))
