"""`dadaia ci verdict-check` — the security-verdict PR gate's CLI backend (v0.4.4 FR4;
v0.5.1 K7, built over ``features.chokepoints.verdict.covering_verdict``).

Real, disposable git repos (a few kilobytes on ``tmp_path``, per dadaia-test-
stewardship's "no real venvs" rule — this is plain git, not a venv) drive the
first-parent resolution ``_first_parent_sha`` shells out for; the pure covering_verdict
matching itself is covered more cheaply in
``tests/unit/features/chokepoints/test_verdict.py``. This file's job is proving the
CLI verb wires that pure rule to a real repo correctly: exit codes, messages, and the
``--release-id`` narrowing/validation surface ``.github/scripts/pr-verdict-check.sh``
now delegates to entirely.

Intent: CONTRACT — v0.4.4 A4.3, A4.5; v0.5.1 K7
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from typer.testing import CliRunner

from dadaia_workspace.cli.commands import ci
from dadaia_workspace.cli.main import app

_runner = CliRunner()


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=True)


def _init_repo(repo: Path) -> None:
    repo.mkdir(parents=True, exist_ok=True)
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "test@example.invalid")
    _git(repo, "config", "user.name", "Test")


def _commit(repo: Path, name: str) -> str:
    (repo / name).write_text("x", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", f"chore: {name}")
    return _git(repo, "rev-parse", "HEAD").stdout.strip()


def _write_verdict(
    repo: Path, sha: str, *, release_id: str = "0.5.1", archived: bool = False
) -> None:
    root = repo / "specs" / "releases"
    root = (
        (root / "_archive" / release_id / "verdicts")
        if archived
        else (root / release_id / "verdicts")
    )
    root.mkdir(parents=True, exist_ok=True)
    payload = {
        "agent": "security-reviewer",
        "verdict": "APPROVED",
        "metrics": {"commit_sha": sha},
    }
    (root / f"{sha}.handoff.json").write_text(json.dumps(payload), encoding="utf-8")


def test_head_match_passes(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(ci, "_repo_root", lambda: tmp_path)
    _init_repo(tmp_path)
    reviewed = _commit(tmp_path, "a.txt")
    _write_verdict(tmp_path, reviewed)

    result = _runner.invoke(app, ["ci", "verdict-check", "--head", reviewed])
    assert result.exit_code == 0, result.output
    assert "PASS" in result.output


def test_first_parent_match_passes(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(ci, "_repo_root", lambda: tmp_path)
    _init_repo(tmp_path)
    reviewed = _commit(tmp_path, "a.txt")
    _write_verdict(tmp_path, reviewed)
    evidence_head = _commit(tmp_path, "verdict-file")  # the verdict's OWN commit

    result = _runner.invoke(app, ["ci", "verdict-check", "--head", evidence_head])
    assert result.exit_code == 0, result.output


def test_archived_evidence_passes(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(ci, "_repo_root", lambda: tmp_path)
    _init_repo(tmp_path)
    reviewed = _commit(tmp_path, "a.txt")
    _write_verdict(tmp_path, reviewed, archived=True)

    result = _runner.invoke(app, ["ci", "verdict-check", "--head", reviewed])
    assert result.exit_code == 0, result.output


def test_no_evidence_anywhere_fails_naming_the_shape(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(ci, "_repo_root", lambda: tmp_path)
    _init_repo(tmp_path)
    reviewed = _commit(tmp_path, "a.txt")

    result = _runner.invoke(app, ["ci", "verdict-check", "--head", reviewed])
    assert result.exit_code == 1
    assert "verdicts" in result.output


def test_unreviewed_trailing_commit_fails(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(ci, "_repo_root", lambda: tmp_path)
    _init_repo(tmp_path)
    reviewed = _commit(tmp_path, "a.txt")
    _write_verdict(tmp_path, reviewed)
    _commit(tmp_path, "verdict-file")
    drifted = _commit(tmp_path, "unreviewed.txt")

    result = _runner.invoke(app, ["ci", "verdict-check", "--head", drifted])
    assert result.exit_code == 1


def test_rejected_verdict_never_qualifies(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(ci, "_repo_root", lambda: tmp_path)
    _init_repo(tmp_path)
    reviewed = _commit(tmp_path, "a.txt")
    root = tmp_path / "specs" / "releases" / "0.5.1" / "verdicts"
    root.mkdir(parents=True)
    payload = {
        "agent": "security-reviewer",
        "verdict": "REJECTED",
        "metrics": {"commit_sha": reviewed},
    }
    (root / f"{reviewed}.handoff.json").write_text(json.dumps(payload), encoding="utf-8")

    result = _runner.invoke(app, ["ci", "verdict-check", "--head", reviewed])
    assert result.exit_code == 1


def test_non_sha_head_is_refused_before_any_git_call(tmp_path: Path) -> None:
    result = _runner.invoke(app, ["ci", "verdict-check", "--head", "not-a-sha"])
    assert result.exit_code == 1
    assert "40-hex" in result.output


def test_malformed_release_id_is_refused(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(ci, "_repo_root", lambda: tmp_path)
    _init_repo(tmp_path)
    reviewed = _commit(tmp_path, "a.txt")

    result = _runner.invoke(
        app, ["ci", "verdict-check", "--head", reviewed, "--release-id", "../../etc"]
    )
    assert result.exit_code == 1


def test_release_id_narrows_the_search(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(ci, "_repo_root", lambda: tmp_path)
    _init_repo(tmp_path)
    reviewed = _commit(tmp_path, "a.txt")
    _write_verdict(tmp_path, reviewed, release_id="0.5.1")

    matching = _runner.invoke(
        app, ["ci", "verdict-check", "--head", reviewed, "--release-id", "0.5.1"]
    )
    assert matching.exit_code == 0, matching.output

    excluding = _runner.invoke(
        app, ["ci", "verdict-check", "--head", reviewed, "--release-id", "0.6.0"]
    )
    assert excluding.exit_code == 1
