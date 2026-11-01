"""Size: MEDIUM — two real initialized workspaces and the real `JsonContextStore`; the
CLI receives `--workspace` explicitly so the resolver never walks up from cwd.
"""

import json
import tarfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app
from dadaia_workspace.core.harness_registry import L1_ENTRY_HARNESSES
from dadaia_workspace.core.models.spec_context import ContextState, SpecContextProject
from dadaia_workspace.features.workspace.service import WorkspaceService
from dadaia_workspace.infrastructure.json_context_store import JsonContextStore
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
from dadaia_workspace.infrastructure.python_env import VenvPythonEnvironmentManager
from tests.fixtures.stores import fake_venv
from tests.helpers.oslib import read_text

_runner = CliRunner()

pytestmark = pytest.mark.slow


def _workspace(root: Path) -> JsonContextStore:
    WorkspaceService(
        public_assets=FileSystemPublicAssetManager(),
        python_env=VenvPythonEnvironmentManager(),
    ).init(root, harnesses=L1_ENTRY_HARNESSES)
    return JsonContextStore(root / ".dadaia" / "states")


def _ctx(name: str, state: ContextState) -> SpecContextProject:
    return SpecContextProject(
        name=name,
        state=state,
        repo_slug=name,
        repo_url=f"https://example.com/{name}.git",
        created_at="2026-01-01T00:00:00+00:00",
        dead_since=None if state is ContextState.ALIVE else "2026-08-01T00:00:00+00:00",
    )


def test_export_writes_the_artifact_and_leaves_the_registry_alone(tmp_path: Path) -> None:
    source = _workspace(tmp_path / "source")
    source.save(_ctx("alpha", ContextState.ALIVE))
    source.save(_ctx("beta", ContextState.DEAD))
    registry = tmp_path / "source" / ".dadaia" / "states" / "spec_contexts.json"
    before = registry.read_bytes()

    exported = _runner.invoke(app, ["export", "--workspace", str(tmp_path / "source")])

    assert exported.exit_code == 0, exported.output
    dist = tmp_path / "source" / ".dadaia" / "dist"
    assert sorted(p.name for p in dist.iterdir()) == ["spec-contexts.json"]
    file = dist / "spec-contexts.json"
    assert str(file) in exported.output
    payload = json.loads(read_text(file))
    assert payload["schema_version"] == "export-v1"
    assert [(c["name"], c["state"]) for c in payload["contexts"]] == [
        ("alpha", "alive"),
        ("beta", "dead"),
    ]
    assert registry.read_bytes() == before


@pytest.mark.medium
def test_export_hard_writes_one_archive(tmp_path: Path) -> None:
    source = _workspace(tmp_path / "source")
    fake_venv(tmp_path / "source", cli="#!python\nprint('[]')\n")  # `worktree list` reads no trees
    source.save(_ctx("alpha", ContextState.DEAD))

    exported = _runner.invoke(app, ["export", "--hard", "--workspace", str(tmp_path / "source")])

    assert exported.exit_code == 0, exported.output
    archive = tmp_path / "source" / ".dadaia" / "dist" / "workspace-export.tar.gz"
    assert str(archive) in exported.output
    with tarfile.open(archive) as tar:
        assert tar.getnames() == ["spec-contexts.json"]


def test_export_help_does_not_name_import() -> None:
    helped = _runner.invoke(app, ["export", "--help"])

    assert helped.exit_code == 0, helped.output
    assert "import" not in helped.output.lower()


def test_explicit_workspace_pointing_at_an_uninitialized_dir_is_refused(tmp_path: Path) -> None:
    """An explicit --workspace is authoritative; a path without its own `.dadaia/` is refused
    instead of silently resolving to the enclosing live workspace.

    Size: MEDIUM — a real filesystem workspace sentinel driven through the CLI."""
    live = tmp_path / "live"
    _workspace(live)
    registry = live / ".dadaia" / "states" / "spec_contexts.json"
    before = read_text(registry)
    nested = live / ".dadaia" / "tmp" / "x"
    nested.mkdir(parents=True)

    result = _runner.invoke(app, ["export", "--workspace", str(nested)])

    assert (result.exit_code, result.exception.__class__) == (1, SystemExit), result.output
    assert "fix: " in result.output
    assert read_text(registry) == before
    assert not (live / ".dadaia" / "dist").exists()
