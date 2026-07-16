"""`specs init` must not scaffold the forbidden workspace-root specs/ (validation-027 F-04/F-10).

Coherence law: a gate never demands what its tooling refuses. `specs doctor` refuses
the workspace-root specs/ fallback (Root Law), so `specs init` must refuse to CREATE
it there — same guidance, same law. An explicit --specs-dir always wins.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app

_runner = CliRunner()


@pytest.fixture
def workspace_root(tmp_path: Path, monkeypatch) -> Path:
    (tmp_path / ".dadaia" / "states").mkdir(parents=True)
    (tmp_path / "repos").mkdir()
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_specs_init_refuses_workspace_root_default(workspace_root: Path) -> None:
    result = _runner.invoke(app, ["specs", "init"])
    assert result.exit_code != 0
    assert not (workspace_root / "specs").exists(), "must not scaffold root specs/"
    out = result.output
    assert "Root Law" in out or "specs-dir" in out or "bind" in out.lower()


def test_specs_init_explicit_specs_dir_still_works(workspace_root: Path) -> None:
    target = workspace_root / "repos" / "proj" / "specs"
    result = _runner.invoke(app, ["specs", "init", "--specs-dir", str(target)])
    assert result.exit_code == 0, result.output
    assert (target / "constitution.md").exists()


def test_specs_init_outside_workspace_root_keeps_default(tmp_path: Path, monkeypatch) -> None:
    proj = tmp_path / "some-project"
    proj.mkdir()
    monkeypatch.chdir(proj)
    result = _runner.invoke(app, ["specs", "init"])
    assert result.exit_code == 0, result.output
    assert (proj / "specs" / "constitution.md").exists()
