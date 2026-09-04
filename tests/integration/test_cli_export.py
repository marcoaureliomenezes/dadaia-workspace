"""Intent: CONTRACT — AC11 (FR13, T-046-31): `dadaia export` -> `dadaia import` round trip.

Size: MEDIUM — two real initialized workspaces and the real `JsonContextStore`; the
CLI receives `--workspace` explicitly so the resolver never walks up from cwd.
"""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app
from dadaia_workspace.core.models.spec_context import ContextState, SpecContextProject
from dadaia_workspace.features.workspace.service import WorkspaceService
from dadaia_workspace.infrastructure.json_context_store import JsonContextStore
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
from dadaia_workspace.infrastructure.python_env import VenvPythonEnvironmentManager

_runner = CliRunner()

pytestmark = pytest.mark.slow


def _workspace(root: Path) -> JsonContextStore:
    WorkspaceService(
        public_assets=FileSystemPublicAssetManager(),
        python_env=VenvPythonEnvironmentManager(),
    ).init(root)
    return JsonContextStore(root / ".dadaia" / "states")


def _ctx(name: str, state: ContextState) -> SpecContextProject:
    return SpecContextProject(
        name=name,
        state=state,
        repo_slug=name,
        repo_url=f"https://example.com/{name}.git",
        created_at="2026-01-01T00:00:00+00:00",
        dead_since=None if state is ContextState.ALIVE else "2026-08-01T00:00:00+00:00",
        current_branch="develop",
    )


def test_export_then_import_restores_unknown_contexts_dead_and_skips_known(
    tmp_path: Path,
) -> None:
    source = _workspace(tmp_path / "source")
    source.save(_ctx("alpha", ContextState.ALIVE))
    source.save(_ctx("beta", ContextState.DEAD))

    exported = _runner.invoke(app, ["export", "--workspace", str(tmp_path / "source")])
    assert exported.exit_code == 0, exported.output
    dist = tmp_path / "source" / ".dadaia" / "dist"
    assert sorted(p.name for p in dist.iterdir()) == ["spec-contexts.json"]
    file = dist / "spec-contexts.json"
    assert str(file) in exported.output
    payload = json.loads(file.read_text("utf-8"))
    assert [c["name"] for c in payload["contexts"]] == ["alpha", "beta"]

    target = _workspace(tmp_path / "target")
    target.save(_ctx("alpha", ContextState.ALIVE))

    imported = _runner.invoke(app, ["import", str(file), "--workspace", str(tmp_path / "target")])
    assert imported.exit_code == 0, imported.output
    assert "skipped (exists)" in imported.output and "alpha" in imported.output
    assert "dadaia context alive beta" in imported.output

    beta = target.get("beta")
    assert beta is not None
    assert (beta.state, beta.repo_url, beta.current_branch) == (
        ContextState.DEAD,
        "https://example.com/beta.git",
        "develop",
    )
    assert beta.dead_since is not None
    assert target.get("alpha") == _ctx("alpha", ContextState.ALIVE)


def test_import_refuses_a_file_outside_the_contract(tmp_path: Path) -> None:
    _workspace(tmp_path / "target")
    bogus = tmp_path / "workspace-2026.tar.gz"
    bogus.write_bytes(b"not json")

    result = _runner.invoke(app, ["import", str(bogus), "--workspace", str(tmp_path / "target")])

    assert result.exit_code == 1
    assert "Error" in result.output
