"""AC8.2: DoctorService renders the worktree rows it is handed — a stub callable stands for
the owner's reader, so no process runs."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from dadaia_workspace.core.models.spec_context import ContextState, SpecContextProject
from dadaia_workspace.features.spec_context.doctor import DoctorService


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

    def rows(root: Path) -> tuple[list[dict[str, Any]], str, str]:
        seen.append(root)
        return _ROWS, "", ""

    [finding] = _doctor(tmp_path, rows).check_worktrees("c")

    assert (finding.verdict, finding.message, finding.fix) == (
        "warning",
        "ready /w/a  age_hours=3",
        "Operator action: merge /w/a",
    )
    assert seen == [tmp_path]


def test_a_failed_read_is_one_warning_with_the_readers_fix(tmp_path: Path) -> None:
    def rows(_root: Path) -> tuple[list[dict[str, Any]], str, str]:
        return [], "list failed: boom", "Operator action: rerun list"

    [finding] = _doctor(tmp_path, rows).check_worktrees("c")

    assert (finding.verdict, finding.message, finding.fix) == (
        "warning",
        "list failed: boom",
        "Operator action: rerun list",
    )
