"""Characterization of ``dadaia ci push-gate-check`` at the public CLI."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app
from tests.helpers.oslib import run, write_text
from tests.helpers.oslib import run as os_run


@pytest.mark.medium
@pytest.mark.slow(reason="runs the CLI over a real Git repository")
def test_tag_deletion_is_allowed_with_the_literal_scan_mode(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    states = tmp_path / ".dadaia" / "states"
    states.mkdir(parents=True)
    write_text(states / "spec_contexts.json", json.dumps({"schema_version": "2", "contexts": []}))
    repo = tmp_path / "repos" / "main"
    repo.mkdir(parents=True)
    os_run(["git", "init", "-q"], cwd=repo, check=True)
    (repo / "specs").mkdir()
    (repo / "specs" / "constitution.md").write_bytes(
        b'---\nspecs_pattern_version: 13\ngitflow: {"principal": "main", '
        b'"integration": "develop", "work": "feature/"}\n---\n'
    )
    (repo / "seed.txt").write_bytes(b"seed\n")
    os_run(["git", "add", "seed.txt", "specs/constitution.md"], cwd=repo, check=True)
    os_run(["git", "commit", "-q", "-m", "seed"], cwd=repo, check=True)
    head = run(["git", "rev-parse", "HEAD"], cwd=repo, check=True).stdout.strip()
    monkeypatch.chdir(repo)

    result = CliRunner().invoke(
        app,
        ["ci", "push-gate-check"],
        input=f"refs/tags/v1 {'0' * 40} refs/tags/v1 {head}\n",
    )

    assert result.exit_code == 0
    assert result.output == (
        "[pre-push] denylist scan mode: baseline only (no operator denylist; private names "
        "go in $DADAIA_PRIVACY_DENYLIST or .dadaia/states/privacy_denylist.json)\n"
    )
    assert run(["git", "status", "--porcelain=v1"], cwd=repo, check=True).stdout == ""
    assert (repo / "seed.txt").read_bytes() == b"seed\n"
    assert (repo / "specs" / "constitution.md").read_bytes() == (
        b'---\nspecs_pattern_version: 13\ngitflow: {"principal": "main", '
        b'"integration": "develop", "work": "feature/"}\n---\n'
    )
