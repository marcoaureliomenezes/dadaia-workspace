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
    """Write a BACKLOG.md ACTIVE subsection whose subject anchor resolves to no symbol
    (BL-SCHEMA ERROR) — SPEC v0.12.0 FR1/FR2, the single-source document, not a per-entry
    file.

    v0.1.55 FR5: the unresolved-subject error is status-gated (an `idea` is exempt), so the
    violation is planted at `candidate` for the check to fire.
    """
    bad = repo / "specs" / "backlog" / "BACKLOG.md"
    bad.write_text(
        "## ACTIVE\n\n"
        "### bad-item\n"
        "- **Title:** Bad\n"
        "- **Opened:** 2026-08-15\n"
        "- **Status:** candidate\n"
        "- **Description:** references a phantom symbol.\n"
        "- **Provenance:** operator request\n"
        "- **Intents:**\n```yaml\n"
        "- subject:\n    kind: code\n    ref: dadaia_workspace/m.py#Ghost\n  change: x\n"
        "```\n\n"
        "## LEDGER\n",
        encoding="utf-8",
    )
    return bad


def test_unrelated_commit_passes_despite_preexisting_debt_no_backlog_dir_noop_and_staged_violation_blocks(
    tmp_path: Path,
) -> None:
    """(a) staged non-backlog paths + broken backlog on disk ⇒ gate skips, does NOT block.
    Also folds in: a repo with no specs/backlog/ (not an SDD spec context) is a silent
    no-op (must not attempt the git-diff scoping at all). (b) a staged specs/backlog
    violation still blocks the commit (BL-SCHEMA ERROR), own repo."""
    repo = _init_repo(tmp_path)
    # Pre-existing backlog debt sits in the working tree but is NOT part of this commit.
    _plant_bl_schema_violation(repo)
    # Stage a source-only change (no backlog path staged).
    (repo / "dadaia_workspace" / "m.py").write_text(_SOURCE + "\n# edit\n", encoding="utf-8")
    _git(repo, "add", "dadaia_workspace/m.py")

    # Must NOT raise — the staged changeset does not intersect specs/backlog/**.
    _run_backlog_doctor_gate(repo)

    no_backlog_repo = tmp_path / "plain"
    (no_backlog_repo / "specs").mkdir(parents=True)
    _git(no_backlog_repo, "init", "-q")
    _git(no_backlog_repo, "config", "user.email", "t@e.st")
    _git(no_backlog_repo, "config", "user.name", "Test")
    _run_backlog_doctor_gate(no_backlog_repo)

    # (b) a staged specs/backlog violation still blocks the commit, own repo.
    blocking_repo = _init_repo(tmp_path.parent / (tmp_path.name + "-blocking"))
    _plant_bl_schema_violation(blocking_repo)
    _git(blocking_repo, "add", "specs/backlog/BACKLOG.md")

    with pytest.raises(typer.Exit) as exc:
        _run_backlog_doctor_gate(blocking_repo)
    assert exc.value.exit_code == 1
