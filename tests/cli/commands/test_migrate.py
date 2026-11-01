"""``dadaia migrate`` reports the schema stamp the registry carries after it, not a literal of its own."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app
from tests.helpers.oslib import read_text, write_text

_runner = CliRunner()
_ATIVO = {"name": "d", "state": "ativo", "repo_slug": "d", "repo_url": "", "created_at": "t"}


def test_migrate_prints_the_stamp_the_registry_carries_after_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / ".dadaia" / "states" / "spec_contexts.json"
    path.parent.mkdir(parents=True)
    write_text(path, json.dumps({"schema_version": "1", "contexts": [_ATIVO]}))
    monkeypatch.chdir(tmp_path)

    preview = _runner.invoke(app, ["migrate", "--dry-run"])
    done = _runner.invoke(app, ["migrate", "--yes"])

    stamp = json.loads(read_text(path))["schema_version"]
    assert f"→ '{stamp}'" in preview.output, preview.output
    assert f"is now at schema_version {stamp}." in done.output, done.output
