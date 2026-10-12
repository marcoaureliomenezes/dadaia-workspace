"""AC8.2: DoctorService renders the worktree rows it is handed — a stub callable stands for
the owner's reader, so no process runs."""

from __future__ import annotations

import shlex
import subprocess
from collections.abc import Collection
from pathlib import Path
from typing import Any

from dadaia_workspace.core.models.spec_context import ContextState, SpecContextProject
from dadaia_workspace.features.spec_context.doctor import DoctorService
from dadaia_workspace.hooks import ctx_inject
from tests.helpers import worktree_ws


class _Store:
    def list_all(self) -> list[SpecContextProject]:
        return [
            SpecContextProject(
                name="c",
                repo_slug="demo",
                repo_url="git@example.invalid:demo.git",
                state=ContextState.ALIVE,
                created_at="2026-09-13T00:00:00Z",
            )
        ]


_ROWS = [
    {
        "repo": "demo",
        "path": "/w/a",
        "state": "ready",
        "warn": True,
        "fix": "Operator action: merge /w/a",
        "age_hours": 3,
    },  # fmt: skip
    {"repo": "other", "path": "/w/b", "state": "empty", "warn": False, "fix": ""},
]


def _doctor(tmp_path: Path, rows: Any) -> DoctorService:
    (tmp_path / "repos" / "demo").mkdir(parents=True)
    return DoctorService(_Store(), None, tmp_path, worktree_rows=rows)  # type: ignore[arg-type]


def test_the_rows_handed_in_are_rendered_for_the_contexts_repos_only(tmp_path: Path) -> None:
    seen: list[Path] = []

    def rows(root: Path, repos: Collection[str]) -> tuple[list[dict[str, Any]], str, str]:
        seen.append(root)
        return [r for r in _ROWS if r["repo"] in repos], "", ""

    [finding] = _doctor(tmp_path, rows).check_worktrees("c")

    assert (finding.verdict, finding.message, finding.fix) == (
        "warning",
        "ready /w/a  age_hours=3",
        "Operator action: merge /w/a",
    )
    assert seen == [tmp_path]


def test_a_failed_read_is_one_warning_with_the_readers_fix(tmp_path: Path) -> None:
    def rows(_root: Path, _repos: Collection[str]) -> tuple[list[dict[str, Any]], str, str]:
        return [], "list failed: boom", "Operator action: rerun list"

    [finding] = _doctor(tmp_path, rows).check_worktrees("c")

    assert (finding.verdict, finding.message, finding.fix) == (
        "warning",
        "list failed: boom",
        "Operator action: rerun list",
    )


def test_a_worktree_of_a_repo_in_no_context_is_a_finding_with_one_fix_and_a_bind_block_line(
    tmp_path: Path,
) -> None:
    """AC15.2: the owner reports a tree of a repo that left its context; doctor and the
    `ctx_inject` bind block render it, and the registered repo's row is as before."""
    root = worktree_ws.make_workspace(tmp_path)
    worktree_ws.git(root / "repos/r", "checkout", "-q", "feature/0.5.0")
    assert worktree_ws.run(root, "new", "r", "0.5.0-rc1/j1").returncode == 0
    gone = root / "repos/gone"
    gone.mkdir()
    worktree_ws.git(gone, "init", "-q")
    worktree_ws.git(gone, "commit", "-q", "--allow-empty", "-m", "init")
    tree = root / "worktrees/gone/0.5.0-rc1/j1"
    worktree_ws.git(gone, "worktree", "add", "-q", "-b", "wt/0.5.0-rc1/j1", str(tree))
    doctor = worktree_ws.registered_doctor(root)

    found = {f.message.split(" ", 1)[1].split("  ")[0]: f for f in doctor.check_worktrees("c")}
    block = "\n".join(ctx_inject._worktrees(root, "c"))

    assert str(root / "worktrees/r/0.5.0-rc1/j1") in found  # the registered repo's row stays
    assert found[str(tree)].message.startswith("unregistered")
    assert found[str(tree)].fix and "\n" not in found[str(tree)].fix
    assert f"unregistered {tree}" in block


def test_the_fix_line_of_an_unregistered_tree_that_was_never_locked_removes_it(
    tmp_path: Path,
) -> None:
    """AC15.2: the one fix act drops a tree made without `--lock`; `worktree unlock` exits 128 there."""
    root = worktree_ws.make_workspace(tmp_path)
    gone = root / "repos/gone"
    gone.mkdir()
    worktree_ws.git(gone, "init", "-q")
    worktree_ws.git(gone, "commit", "-q", "--allow-empty", "-m", "init")
    tree = root / "worktrees/gone/0.5.0-rc1/j1"
    worktree_ws.git(gone, "worktree", "add", "-q", "-b", "wt/0.5.0-rc1/j1", str(tree))
    doctor = worktree_ws.registered_doctor(root)
    [finding] = [f for f in doctor.check_worktrees("c") if f.message.startswith("unregistered")]

    command = finding.fix.split("`")[1]
    assert command == f"git -C {gone} worktree remove --force --force {tree}"
    subprocess.run(shlex.split(command), check=True, capture_output=True)

    assert not [f for f in doctor.check_worktrees("c") if f.message.startswith("unregistered")]
    assert not tree.exists()
