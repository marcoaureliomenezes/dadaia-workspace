"""Intent: CONTRACT — memory-catalog-context-is-the-checkout-folder-name#upgrade: the
upgrade repair regenerates a drifted catalog pair through its ONE generator
(`memory.py catalog generate`), so the doctor's memory ledger ends clean.

size: MEDIUM — the real CLI verb and the real skill script as a child process.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app
from dadaia_workspace.features.specs.canon import default_public_dir, scaffold

pytestmark = pytest.mark.integration

_MEMORY = default_public_dir() / "skills" / "dd-spec-navigator" / "scripts" / "memory.py"


def _check(specs: Path) -> subprocess.CompletedProcess[str]:
    argv = [sys.executable, str(_MEMORY), "check", "--specs", str(specs)]
    return subprocess.run(argv, capture_output=True, text=True, check=False)


def test_specs_upgrade_regenerates_a_catalog_an_older_generator_wrote(tmp_path: Path) -> None:
    specs = tmp_path / "proj" / "specs"
    scaffold(specs, project_name="proj")
    catalog = specs / "memory" / "product" / "catalog.json"
    older = {"generated_at": "2026-01-01T00:00:00Z", "context": "proj", "features": []}
    catalog.write_text(json.dumps(older, indent=2) + "\n", encoding="utf-8")
    assert _check(specs).returncode == 1

    run = CliRunner().invoke(app, ["specs", "upgrade", "--specs-dir", str(specs)])

    assert run.exit_code == 0, run.output
    assert _check(specs).returncode == 0, _check(specs).stdout
    assert "context" not in json.loads(catalog.read_text(encoding="utf-8"))
