"""dadaia init CLI — one fn: creates .dadaia+states, idempotent rerun, cwd default.

Merged per plan-integration.md (5 -> 1). Deleted the skip-message + assets-output
wording greps.
"""

from pathlib import Path

from typer.testing import CliRunner

from dadaia_workspace.cli.main import app

_runner = CliRunner()


def test_init_creates_states_idempotent_and_cwd_default(tmp_path: Path, monkeypatch) -> None:
    ws = tmp_path / "ws"
    ws.mkdir()
    monkeypatch.chdir(ws)

    result = _runner.invoke(app, ["init", "--workspace", str(ws), "--skip-assets"])
    assert result.exit_code == 0, result.output
    assert (ws / ".dadaia").exists()
    assert (ws / ".dadaia" / "states" / "spec_contexts.json").exists()

    rerun = _runner.invoke(app, ["init", "--workspace", str(ws), "--skip-assets"])
    assert rerun.exit_code == 0, rerun.output

    # cwd-default case: a sibling (not nested) root so upward .dadaia resolution from
    # the first workspace never interferes.
    cwd_ws = tmp_path / "cwd-case"
    cwd_ws.mkdir()
    monkeypatch.chdir(cwd_ws)
    cwd_result = _runner.invoke(app, ["init", "--skip-assets"])
    assert cwd_result.exit_code == 0, cwd_result.output
    assert (cwd_ws / ".dadaia").exists()


def test_bare_init_nested_inside_ancestor_dotdadaia_targets_cwd(
    tmp_path: Path, monkeypatch
) -> None:
    """Bug ancestor-walk-workspace-root-silent-mistarget (T-043-47/A30.5): a bare
    `dadaia init` (no --workspace) invoked from inside an ANCESTOR workspace's own
    .dadaia/tmp/ tree — the R7-sanctioned throwaway-workspace pattern — must create the
    new workspace AT cwd, never silently re-project the ancestor's assets instead."""
    ancestor = tmp_path / "ancestor-ws"
    ancestor.mkdir()
    setup = _runner.invoke(app, ["init", "--workspace", str(ancestor), "--skip-assets"])
    assert setup.exit_code == 0, setup.output
    ancestor_sentinel = ancestor / ".dadaia" / "states" / "spec_contexts.json"
    assert ancestor_sentinel.exists()
    ancestor_sentinel_mtime = ancestor_sentinel.stat().st_mtime_ns

    nested = ancestor / ".dadaia" / "tmp" / "qa-engineer" / "20260818" / "throwaway-ws"
    nested.mkdir(parents=True)
    monkeypatch.chdir(nested)

    result = _runner.invoke(app, ["init", "--skip-assets"])
    assert result.exit_code == 0, result.output

    # The NEW workspace was created at the nested cwd, not the ancestor.
    assert (nested / ".dadaia" / "states" / "spec_contexts.json").exists()
    # The ancestor's own sentinel was never touched by the nested invocation.
    assert ancestor_sentinel.stat().st_mtime_ns == ancestor_sentinel_mtime
    # The path may wrap across lines in the terminal; compare without newlines.
    assert str(nested.resolve()) in result.output.replace("\n", "")
