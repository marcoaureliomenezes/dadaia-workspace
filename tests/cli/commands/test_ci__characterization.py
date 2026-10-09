"""Characterization of ``dadaia ci push-gate-check`` at the public CLI."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app


@pytest.mark.medium
@pytest.mark.slow(reason="runs the CLI over a real Git repository")
def test_tag_deletion_is_allowed_with_the_literal_scan_mode(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    states = tmp_path / ".dadaia" / "states"
    states.mkdir(parents=True)
    (states / "spec_contexts.json").write_text(
        json.dumps({"schema_version": "2", "contexts": []}), encoding="utf-8"
    )
    repo = tmp_path / "repos" / "main"
    repo.mkdir(parents=True)
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    (repo / "specs").mkdir()
    (repo / "specs" / "constitution.md").write_bytes(
        b'---\nspecs_pattern_version: 12\ngitflow: {"principal": "main", '
        b'"integration": "develop", "work": "feature/"}\n---\n'
    )
    (repo / "seed.txt").write_bytes(b"seed\n")
    subprocess.run(["git", "add", "seed.txt", "specs/constitution.md"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "seed"], cwd=repo, check=True)
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, check=True, capture_output=True, text=True
    ).stdout.strip()
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
    assert (
        subprocess.run(
            ["git", "status", "--porcelain=v1"],
            cwd=repo,
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        == ""
    )
    assert (repo / "seed.txt").read_bytes() == b"seed\n"
    assert (repo / "specs" / "constitution.md").read_bytes() == (
        b'---\nspecs_pattern_version: 12\ngitflow: {"principal": "main", '
        b'"integration": "develop", "work": "feature/"}\n---\n'
    )
