"""dadaia init CLI: creates .dadaia+states and the level-1 root files from the argv DIR; the
rerun overwrites no operator file and migrates a list-form privacy denylist once."""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app
from dadaia_workspace.core.workspace_layout import occupied

_runner = CliRunner()


@pytest.mark.parametrize(
    "links",
    [(), ("prompt.md", ".dadaia/states/server_registry.json")],
    ids=["fresh", "dangling-links-never-written-through"],
)
def test_init_creates_states_and_the_three_root_files_and_is_idempotent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, links: tuple[str, ...]
) -> None:
    """AC2.2 (ADR 0095): init and its re-run create `prompt.md`,
    `AGENTS.md` and `.dadaiaignore` when absent and never overwrite the operator's; a dangling
    link (CWE-59) is present, never written through."""
    ws, outside = tmp_path / "ws", tmp_path / "outside"
    outside.mkdir()
    for rel in links:
        (ws / rel).parent.mkdir(parents=True, exist_ok=True)
        (ws / rel).symlink_to(outside / Path(rel).name)
    ws.mkdir(exist_ok=True)
    monkeypatch.chdir(ws)

    result = _runner.invoke(app, ["init", str(ws), "--harness", "claude"])
    assert result.exit_code == 0, result.output
    assert occupied(ws / ".dadaia" / "states" / "spec_contexts.json")
    assert all(occupied(ws / name) for name in ("prompt.md", "AGENTS.md", ".dadaiaignore"))
    assert list(outside.iterdir()) == []
    (ws / ".dadaiaignore").write_text("# mine\n", encoding="utf-8")

    rerun = _runner.invoke(app, ["init", str(ws), "--harness", "claude"])
    assert rerun.exit_code == 0, rerun.output
    assert (ws / ".dadaiaignore").read_text(encoding="utf-8") == "# mine\n"
    assert list(outside.iterdir()) == []


def test_init_converts_a_list_form_denylist_once_and_holds_the_original(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC3.10 / list-form-privacy-denylist-errors-without-migration
    (ADR 0157): the upgrade rewrites a 0.4.7 list form as the object form once, the original
    held under `.dadaia/reaped/`; the pre-push loader then reads it."""
    from dadaia_workspace.container import load_denylist_terms

    ws = tmp_path / "ws"
    ws.mkdir()
    monkeypatch.chdir(ws)
    monkeypatch.delenv("DADAIA_PRIVACY_DENYLIST", raising=False)
    assert _runner.invoke(app, ["init", str(ws), "--harness", "claude"]).exit_code == 0
    denylist = ws / ".dadaia" / "states" / "privacy_denylist.json"
    original = '["zz-term-a", ["zz-term-b", "why"]]'
    denylist.write_text(original, encoding="utf-8")

    for _ in range(2):
        result = _runner.invoke(app, ["init", str(ws), "--harness", "claude"])
        assert result.exit_code == 0, result.output
    assert json.loads(denylist.read_text(encoding="utf-8")) == {"zz-term-a": "", "zz-term-b": "why"}
    held = list((ws / ".dadaia" / "reaped").rglob("privacy_denylist.json"))
    assert [h.read_text(encoding="utf-8") for h in held] == [original]
    assert load_denylist_terms() == (("zz-term-a", ""), ("zz-term-b", "why"))


def test_a_failed_denylist_conversion_leaves_the_operator_terms_in_place(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC3.10, review L1 (CWE-636): when the converted file cannot be
    written, the original stays where the loader reads it and nothing is held; a list holding
    anything but strings or string pairs is never converted."""
    ws = tmp_path / "ws"
    ws.mkdir()
    monkeypatch.chdir(ws)
    assert _runner.invoke(app, ["init", str(ws), "--harness", "claude"]).exit_code == 0
    denylist = ws / ".dadaia" / "states" / "privacy_denylist.json"
    for original, blocker in (('["zz-term-a"]', True), ('[{"zz-term-a": "x"}]', False)):
        denylist.write_text(original, encoding="utf-8")
        if blocker:
            (denylist.parent / "privacy_denylist.json.migrating").mkdir()
        assert _runner.invoke(app, ["init", str(ws), "--harness", "claude"]).exit_code == 0
        assert denylist.read_text(encoding="utf-8") == original
        assert not list((ws / ".dadaia" / "reaped").rglob("privacy_denylist.json"))


@pytest.mark.xfail(strict=True, reason="J2.S3.T5: AC2.5")
def test_an_upgrade_leaves_no_reconcile_scratch_and_rewrites_only_a_differing_hook(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import hashlib
    import subprocess

    from dadaia_workspace.core import workspace_layout
    from dadaia_workspace.core.cli_line import cli_path
    from dadaia_workspace.core.platform import PLATFORM
    from dadaia_workspace.infrastructure.python_env import (
        VenvPythonEnvironmentManager,
        build_digest,
    )
    from tests.fixtures.provider_dist import install_fake_dist

    def upgrade(venv: str, running: str) -> None:
        venv_bin = ws / ".dadaia" / ".venv" / PLATFORM.venv_scripts_dir
        cli_path(ws).parent.mkdir(parents=True, exist_ok=True)
        cli_path(ws).write_text(f"#!{venv_bin / ('python' + PLATFORM.venv_exe_suffix)}")
        cli_path(ws).chmod(0o755)
        built = f"{venv} {build_digest(None)}"
        monkeypatch.setattr(VenvPythonEnvironmentManager, "installed_build", lambda s, w: built)
        install_fake_dist(monkeypatch, running)
        result = _runner.invoke(app, ["init", str(ws)])
        assert result.exit_code == 0, result.output
        assert f"upgraded {venv} -> {running}" in result.output

    install_fake_dist(monkeypatch, "0.4.8")
    ws = tmp_path / "ws"
    assert _runner.invoke(app, ["init", str(ws), "--harness", "claude"]).exit_code == 0
    monkeypatch.chdir(ws)
    subprocess.run(["git", "init", "-q", str(ws / "repos" / "app")], check=True)
    (ws / ".dadaia" / "states" / "spec_contexts.json").write_text(
        json.dumps(
            {
                "schema_version": "2",
                "contexts": [
                    {
                        "name": "app",
                        "state": "alive",
                        "repo_slug": "app",
                        "repo_url": "https://example.invalid/app.git",
                        "created_at": "2026-01-01T00:00:00Z",
                        "alive_since": "2026-01-01T00:00:00Z",
                        "dead_since": None,
                        "current_branch": None,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    shipped = (workspace_layout.public_scripts_dir() / "pre-push-ci-gate.sh").read_bytes()
    hook = ws / "repos" / "app" / ".git" / "hooks" / "pre-push"
    hook.write_bytes(shipped)
    stamp = hook.stat().st_mtime_ns

    upgrade("0.4.7", "0.4.8")
    assert not (ws / ".dadaia" / "tmp" / "reconcile").exists()
    assert (hook.read_bytes(), hook.stat().st_mtime_ns) == (shipped, stamp)

    old = b"#!/bin/sh\n# an older shipped gate\n"
    hook.write_bytes(old)
    monkeypatch.setattr(
        "dadaia_workspace.core.template_history.load_shipped_hashes",
        lambda _d: {"scripts/pre-push-ci-gate.sh": {hashlib.sha256(old).hexdigest()}},
    )
    upgrade("0.4.8", "0.4.9")
    assert hook.read_bytes() == shipped
