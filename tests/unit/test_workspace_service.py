"""Unit tests for WorkspaceService."""

import json
from pathlib import Path

import pytest

from dadaia_workspace.core.workspace_layout import Creator, zones_created_by
from dadaia_workspace.features.workspace.service import WorkspaceService
from tests.fakes import FakePublicAssetManager, FakePythonEnvironmentManager


@pytest.fixture()
def workspace_root(tmp_path: Path) -> Path:
    return tmp_path / "ws"


@pytest.fixture()
def service() -> WorkspaceService:
    return WorkspaceService(
        public_assets=FakePublicAssetManager(),
        python_env=FakePythonEnvironmentManager(),
    )


def test_init_creates_only_registry_init_zones_and_canon_seeds(
    service: WorkspaceService, workspace_root: Path
) -> None:
    """Intent: CONTRACT — 0.4.6 AC10 (FR1/FR10).

    ``init`` materialises exactly the ``Creator.INIT`` rows of ``DADAIA_ZONES`` — the
    registry view, never a second list — so a retired zone (``academy``, ``reports``,
    ``scripts``, an eager ``tmp``) cannot reappear, and no ``academy.json`` is seeded.
    """
    service.init(workspace_root, skip_assets=True)

    dadaia = workspace_root / ".dadaia"
    assert {p.name for p in dadaia.iterdir()} == {z.name for z in zones_created_by(Creator.INIT)}
    assert (dadaia / "states").is_dir()
    for retired in ("academy", "reports", "scripts", "tmp", "src"):
        assert not (dadaia / retired).exists(), retired
    assert (workspace_root / ".agents" / "skills").is_dir()
    assert (workspace_root / ".claude").is_dir()
    assert (workspace_root / ".codex").is_dir()

    spec_contexts_path = dadaia / "states" / "spec_contexts.json"
    assert json.loads(spec_contexts_path.read_text()) == {"schema_version": "2", "contexts": []}

    registry_data = json.loads((dadaia / "states" / "server_registry.json").read_text())
    assert registry_data["version"] == "1"
    assert registry_data["entries"] == []

    never_inited = workspace_root.parent / "never"
    assert not service.is_initialized(never_inited)
    assert service.is_initialized(workspace_root)

    # Idempotent: modify the state file; second init must not overwrite it.
    spec_contexts_path.write_text(json.dumps({"version": "1", "contexts": [{"name": "x"}]}))
    service.init(workspace_root, skip_assets=True)
    data = json.loads(spec_contexts_path.read_text())
    assert data["contexts"] == [{"name": "x"}]


def test_init_skip_assets_writes_no_settings_and_says_ungated(
    service: WorkspaceService, workspace_root: Path
) -> None:
    """Bug init-skip-assets-writes-gateless-claude-settings: init carried a SECOND
    ``.claude/settings.json`` writer (``_configure_hook``) that emitted a gateless file
    (UserPromptSubmit only — no gate, no venv guard, no root whitelist), silently. The
    canonical writer is ``public install`` (runtime_config); init writes NO settings.
    Under ``--skip-assets`` the ungated state is loud instead of silently half-wired."""
    _, installed = service.init(workspace_root, skip_assets=True)
    assert not (workspace_root / ".claude" / "settings.json").exists()
    assert any("ungated" in line and "dadaia public install" in line for line in installed)


def test_init_with_assets_never_writes_settings_itself(
    service: WorkspaceService, workspace_root: Path
) -> None:
    """On the normal path the full settings projection is ``public install``'s output —
    the service itself must not touch the file (one writer, one format)."""
    _, installed = service.init(workspace_root, skip_assets=False)
    assert not any("ungated" in line for line in installed)
    assert not (workspace_root / ".claude" / "settings.json").exists()
