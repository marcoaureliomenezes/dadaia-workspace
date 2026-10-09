"""Characterization of public stage/install/doctor at the public CLI."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace import container
from dadaia_workspace.cli.main import app
from dadaia_workspace.core.platform import PLATFORM
from dadaia_workspace.features.public.service import PublicAssetService
from dadaia_workspace.infrastructure.json_agent_model_policy_store import (
    JsonAgentModelPolicyStore,
)
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
from tests.helpers import public_asset_roster

_FIXTURE_SOURCE = b"# fixture root law\n\nRoot holds only: `<!-- root -->`.\n"
_FIXTURE_RENDERED = (
    b"# fixture root law\n\nRoot holds only: `.agents/ .claude/ .codex/ .cursor/ "
    b".dadaia/ .devin/ .github/ repos/ worktrees/ .dadaiaignore AGENTS.md prompt.md`.\n"
)


@pytest.mark.medium
@pytest.mark.slow(reason="runs three public CLI projection operations")
def test_public_projection_lifecycle(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ws = tmp_path / "ws"
    states = ws / ".dadaia" / "states"
    states.mkdir(parents=True)
    (states / "spec_contexts.json").write_bytes(b'{\n  "schema_version": "2",\n  "contexts": []\n}')
    (states / "harness_profile.json").write_bytes(
        b'{\n  "schema_version": "1",\n  "harnesses": [\n    "claude"\n  ]\n}'
    )

    # Match the suite's mirror-package fixture pattern: the filesystem adapter receives a
    # package-shaped public tree at its data-provider boundary, while its real stage,
    # install and doctor implementations remain intact. The characterized law input is
    # literal, so unrelated edits to the checkout's live law cannot move this oracle.
    package_dir = tmp_path / "package" / "dadaia_workspace"
    source_public = public_asset_roster.default_public_dir()
    public_dir = shutil.copytree(source_public, package_dir / "public")
    shutil.copytree(source_public.parent / "hooks", package_dir / "hooks")
    (package_dir / "core").mkdir()
    shutil.copy2(source_public.parent / "core" / "redaction.py", package_dir / "core")
    (package_dir / "infrastructure" / "data").mkdir(parents=True)
    shutil.copy2(
        source_public.parent / "infrastructure" / "data" / "privacy_baseline.json",
        package_dir / "infrastructure" / "data",
    )
    (public_dir / "data" / "AGENTS.md").write_bytes(_FIXTURE_SOURCE)
    manager = FileSystemPublicAssetManager()
    manager._public_dir = public_dir  # noqa: SLF001 — package asset-provider boundary
    service = PublicAssetService(
        manager, agent_policy_loader=lambda root: JsonAgentModelPolicyStore(root).load()
    )
    monkeypatch.setattr(container, "build_public_service", lambda: service)
    monkeypatch.chdir(ws)

    stage = CliRunner().invoke(app, ["public", "stage"])
    install = CliRunner().invoke(app, ["public", "install"])
    doctor = CliRunner().invoke(app, ["public", "doctor"])

    assert (stage.exit_code, install.exit_code, doctor.exit_code) == (0, 0, 0), doctor.output
    expected_stage = (
        "✓ 54 asset group(s) staged:" if PLATFORM.windows else "✓ 37 asset group(s) staged:"
    )
    expected_install = (
        "✓ 181 asset(s) processed:" if PLATFORM.windows else "✓ 164 asset(s) processed:"
    )
    assert stage.output.splitlines()[0] == expected_stage
    assert install.output.splitlines()[0] == expected_install
    assert "fix:" not in stage.output
    assert "fix:" not in install.output
    assert "fix:" not in doctor.output
    doctor_lines = doctor.output.splitlines()
    assert "[ok] stage:data/AGENTS.md" in doctor_lines
    assert "[ok] root:AGENTS.md" in doctor_lines
    assert doctor_lines[-3:] == [
        "[ok] public-privacy (baseline structural scan, no operator denylist)",
        "[ok] entities-derivation: 3 Personas ↔ 3 core sub-agents; 5 Deterministic Behaviors "
        "derived for every harness with a hook derivation (ENT-DERIVE-1)",
        "[ok] model-resolution",
    ]

    manifest = json.loads((ws / ".dadaia" / "agentic" / "manifest.json").read_bytes())
    assert next(asset for asset in manifest["assets"] if asset["path"] == "data/AGENTS.md") == {
        "path": "data/AGENTS.md",
        "sha256": "181abbc82681aabf0fa4cd8f35b4bb6815ec079d0cfc21da872e2e79524ff8f1",
        "type": "data",
    }
    assert (ws / ".dadaia" / "agentic" / "data" / "AGENTS.md").read_bytes() == _FIXTURE_RENDERED
    assert (ws / "AGENTS.md").read_bytes() == _FIXTURE_RENDERED
