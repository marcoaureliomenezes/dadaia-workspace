"""Integration tests for the W1-4 pre-commit backlog-gate scoping.

The pre-commit backlog doctor gate (``_run_backlog_doctor_gate``) must run the blocking
BL-* sweep ONLY when the staged changeset intersects ``specs/backlog/**``. A commit that
stages no backlog file must never be blocked by pre-existing backlog debt (bugs
``precommit-backlog-doctor-blocks-unrelated-commits`` +
``backlog-doctor-blocks-consumed-item-refactor-commit``); a staged backlog violation must
still block.

These exercise the REAL ``git diff --cached`` seam against a fixture git repo — no mocking
of the staged-path resolution — and call the gate function directly (the CLI's git-hook
path is proven separately in ``tests/e2e/features/test_backlog_precommit.py``).
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
import typer

from dadaia_workspace.cli.commands.ci import _run_backlog_doctor_gate

_SOURCE = "class Widget:\n    pass\n"


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True)


def _init_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    (repo / "specs" / "backlog").mkdir(parents=True)
    (repo / "specs" / "memory" / "product").mkdir(parents=True)
    (repo / "specs" / "memory" / "product" / "catalog.json").write_text(
        '{"features": []}', encoding="utf-8"
    )
    (repo / "dadaia_workspace").mkdir()
    (repo / "dadaia_workspace" / "m.py").write_text(_SOURCE, encoding="utf-8")

    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "t@e.st")
    _git(repo, "config", "user.name", "Test")
    return repo


def _plant_bl_schema_violation(repo: Path) -> Path:
    """Write a backlog item whose subject anchor resolves to no symbol (BL-SCHEMA ERROR).

    v0.1.55 FR5: the unresolved-subject error is status-gated (an `idea` is exempt), so the
    violation is planted at `candidate` for the check to fire.
    """
    bad = repo / "specs" / "backlog" / "bad.md"
    bad.write_text(
        "---\nstatus: candidate\nintents:\n"
        "  - subject: { kind: code, ref: dadaia_workspace/m.py#Ghost }\n"
        "    change: x\n---\n\n# bad\n",
        encoding="utf-8",
    )
    return bad


def test_unrelated_commit_passes_despite_preexisting_backlog_debt(tmp_path: Path) -> None:
    """(a) staged non-backlog paths + broken backlog on disk ⇒ gate skips, does NOT block."""
    repo = _init_repo(tmp_path)
    # Pre-existing backlog debt sits in the working tree but is NOT part of this commit.
    _plant_bl_schema_violation(repo)
    # Stage a source-only change (no backlog path staged).
    (repo / "dadaia_workspace" / "m.py").write_text(_SOURCE + "\n# edit\n", encoding="utf-8")
    _git(repo, "add", "dadaia_workspace/m.py")

    # Must NOT raise — the staged changeset does not intersect specs/backlog/**.
    _run_backlog_doctor_gate(repo)


def test_staged_backlog_violation_still_blocks(tmp_path: Path) -> None:
    """(b) a staged specs/backlog violation still blocks the commit (BL-SCHEMA ERROR)."""
    repo = _init_repo(tmp_path)
    _plant_bl_schema_violation(repo)
    _git(repo, "add", "specs/backlog/bad.md")

    with pytest.raises(typer.Exit) as exc:
        _run_backlog_doctor_gate(repo)
    assert exc.value.exit_code == 1


def test_no_backlog_dir_is_noop(tmp_path: Path) -> None:
    """A repo with no specs/backlog/ (not an SDD spec context) is a silent no-op."""
    repo = tmp_path / "plain"
    (repo / "specs").mkdir(parents=True)
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "t@e.st")
    _git(repo, "config", "user.name", "Test")
    # Must NOT raise (and must not attempt the git-diff scoping — no backlog dir at all).
    _run_backlog_doctor_gate(repo)
