"""Characterization of public stage/install/doctor at the public CLI."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app


@pytest.mark.medium
@pytest.mark.slow(reason="runs three public CLI projection operations")
def test_public_projection_lifecycle(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ws = tmp_path / "ws"
    init = CliRunner().invoke(app, ["init", str(ws), "--harness", "claude"])
    assert init.exit_code == 0, init.output
    monkeypatch.chdir(ws)

    stage = CliRunner().invoke(app, ["public", "stage"])
    install = CliRunner().invoke(app, ["public", "install"])
    doctor = CliRunner().invoke(app, ["public", "doctor"])

    assert (stage.exit_code, install.exit_code, doctor.exit_code) == (0, 0, 0)
    assert stage.output.splitlines()[0] == "✓ 37 asset group(s) staged:"
    assert install.output.splitlines()[0] == "✓ 164 asset(s) processed:"
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
        "sha256": "3e64a916f6c3681cb2af2fa8bdb7f313e39f277fbc05f181110898267e0d22c6",
        "type": "data",
    }
    assert hashlib.sha256((ws / "AGENTS.md").read_bytes()).hexdigest() == (
        "3e64a916f6c3681cb2af2fa8bdb7f313e39f277fbc05f181110898267e0d22c6"
    )
