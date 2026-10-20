"""Unit tests for WorkspaceService."""

import json
from collections.abc import Callable
from pathlib import Path

import pytest

from dadaia_workspace.core.workspace_layout import provisioned_zones
from dadaia_workspace.features.workspace.service import WorkspaceService
from tests.fakes import FakePublicAssetManager, FakePythonEnvironmentManager
from tests.helpers.oslib import link, read_text, write_text


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
    service: WorkspaceService, workspace_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``init`` materialises exactly ``provisioned_zones()`` — the SAME view the doctor
    reports ``missing`` for, never a second list — so a retired zone (``academy``, ``reports``,
    ``scripts``, an eager ``tmp``) cannot reappear, and no ``academy.json`` is seeded.
    """
    service.init(workspace_root, harnesses=("claude", "codex"), skip_assets=True)

    dadaia = workspace_root / ".dadaia"
    assert {p.name for p in dadaia.iterdir()} == {z.name for z in provisioned_zones()}
    assert (dadaia / "states").is_dir()
    for retired in ("academy", "reports", "scripts", "tmp", "src"):
        assert not (dadaia / retired).exists(), retired
    assert (workspace_root / ".agents" / "skills").is_dir()
    # Harness directories belong to the projection (each record's `directory`), so a
    # `skip_assets` init creates none — init owns no harness-named branch.
    assert not (workspace_root / ".claude").exists()
    assert not (workspace_root / ".codex").exists()

    spec_contexts_path = dadaia / "states" / "spec_contexts.json"
    assert json.loads(read_text(spec_contexts_path)) == {"schema_version": "3", "contexts": []}
    assert spec_contexts_path.read_bytes() == b'{\n  "schema_version": "3",\n  "contexts": []\n}'

    registry_data = json.loads(read_text(dadaia / "states" / "server_registry.json"))
    assert registry_data["version"] == "1"
    assert registry_data["entries"] == []

    # Idempotent: modify the state file; second init must not overwrite it.
    occupied_registry = b'{\r\n  "version": "1",\r\n  "contexts": [{"name": "x"}]\r\n}\r\n'
    spec_contexts_path.write_bytes(occupied_registry)
    service.init(workspace_root, harnesses=("claude", "codex"), skip_assets=True)
    data = json.loads(read_text(spec_contexts_path))
    assert data["contexts"] == [{"name": "x"}]
    assert spec_contexts_path.read_bytes() == occupied_registry

    from dadaia_workspace.infrastructure.json_context_store import JsonContextStore

    seeded: list[Path] = []
    monkeypatch.setattr(
        JsonContextStore,
        "seed_if_absent",
        lambda store: seeded.append(store.states_dir),
        raising=False,
    )
    spec_contexts_path.unlink()
    service.init(workspace_root, harnesses=("claude",), skip_assets=True)
    assert (seeded, spec_contexts_path.exists()) == ([spec_contexts_path.parent], False)


def test_init_skip_assets_writes_no_settings_and_says_ungated(
    service: WorkspaceService, workspace_root: Path
) -> None:
    """init writes NO ``.claude/settings.json``: ``public install`` (runtime_config) is the
    one writer. Under ``--skip-assets`` the ungated state is loud instead of silently
    half-wired."""
    installed = service.init(workspace_root, harnesses=("claude", "codex"), skip_assets=True)
    assert not (workspace_root / ".claude" / "settings.json").exists()
    from dadaia_workspace.core.platform import PLATFORM

    cli = f".dadaia/.venv/{PLATFORM.venv_scripts_dir}/dadaia{PLATFORM.venv_exe_suffix}"
    assert any("ungated" in ln and f"{cli} public install" in ln for ln in installed), installed


def test_init_with_assets_never_writes_settings_itself(
    service: WorkspaceService, workspace_root: Path
) -> None:
    """On the normal path the full settings projection is ``public install``'s output —
    the service itself must not touch the file (one writer, one format)."""
    installed = service.init(workspace_root, harnesses=("claude", "codex"), skip_assets=False)
    assert not any("ungated" in line for line in installed)
    assert not (workspace_root / ".claude" / "settings.json").exists()


def test_a_refused_hold_leaves_the_list_form_denylist_in_place(workspace_root: Path) -> None:
    """A hold the sweep refuses is falsy, so the converted file never replaces the operator's."""
    from dadaia_workspace.features.spec_context.sweep import Skipped

    refused = WorkspaceService(
        public_assets=FakePublicAssetManager(),
        python_env=FakePythonEnvironmentManager(),
        hold=lambda *_: Skipped("skipped 'privacy_denylist.json' (errno 13: Permission denied)"),
    )
    denylist = workspace_root / ".dadaia" / "states" / "privacy_denylist.json"
    denylist.parent.mkdir(parents=True)
    write_text(denylist, '["zz-term-a"]')

    refused.init(workspace_root, harnesses=("claude",), skip_assets=True)

    assert read_text(denylist) == '["zz-term-a"]'


def test_a_symlinked_list_form_denylist_is_refused_and_left_untouched(workspace_root: Path) -> None:
    """The migration lands content on the denylist, so the one writer's symlink rule
    applies: the operator's link is neither moved aside nor replaced by a regular file."""
    from dadaia_workspace.features.spec_context.sweep import hold

    migrating = WorkspaceService(
        public_assets=FakePublicAssetManager(),
        python_env=FakePythonEnvironmentManager(),
        hold=hold,
    )
    states = workspace_root / ".dadaia" / "states"
    states.mkdir(parents=True)
    target = workspace_root / "elsewhere.json"
    write_text(target, '["zz-term-a"]')
    denylist = states / "privacy_denylist.json"
    assert link(str(target), denylist, is_dir=False)

    migrating.init(workspace_root, harnesses=("claude",), skip_assets=True)

    assert (denylist.is_symlink(), read_text(target)) == (True, '["zz-term-a"]')


def test_a_denylist_that_is_not_utf8_is_left_alone_and_init_goes_on(workspace_root: Path) -> None:
    """The legacy-form migration reads it to convert it; what it cannot read it leaves, as it
    leaves every other file it cannot convert."""
    denylist = workspace_root / ".dadaia" / "states" / "privacy_denylist.json"
    denylist.parent.mkdir(parents=True)
    denylist.write_bytes('["zz-term-é"]'.encode("cp1252"))

    WorkspaceService(
        public_assets=FakePublicAssetManager(), python_env=FakePythonEnvironmentManager()
    ).init(workspace_root, harnesses=("claude",), skip_assets=True)

    assert denylist.read_bytes() == '["zz-term-é"]'.encode("cp1252")


def test_the_ungated_warning_renders_the_cli_words_inline(
    tmp_path: Path, sentence: Callable[..., str]
) -> None:
    root = tmp_path / "a b"
    lines = WorkspaceService(
        public_assets=FakePublicAssetManager(), python_env=FakePythonEnvironmentManager()
    ).init(root, harnesses=("claude",), skip_assets=True)

    assert any(f"until '{sentence(root, 'public', 'install')}' runs" in ln for ln in lines), lines
