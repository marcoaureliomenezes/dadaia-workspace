"""AC8.2: SpecContextService's dead() preflight reads the worktree rows it is handed — a
stub callable stands for the owner's reader."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from dadaia_workspace.container import scan_publish_candidates
from dadaia_workspace.features.spec_context.service import (
    DeadUnpushedCommitsError,
    SpecContextService,
)
from dadaia_workspace.infrastructure.git_subprocess import GitSubprocessClient
from tests.fakes import register_dead
from tests.fixtures.real_git import seeded_remote
from tests.fixtures.stores import context_store


def _alive(tmp_path: Path, rows: Any) -> SpecContextService:
    root = tmp_path / "ws"
    (root / "repos").mkdir(parents=True)
    kw: dict[str, Any] = {"worktree_rows": rows}
    service = SpecContextService(
        context_store=context_store(root / ".dadaia" / "states"),
        git_client=GitSubprocessClient(),
        workspace_root=root,
        install_hooks=lambda _repo: None,
        secret_scan=scan_publish_candidates,
        **kw,
    )
    remote = seeded_remote(tmp_path, "my-repo", branch="feature/0.1.0").as_uri()
    register_dead(service, "proj", "my-repo", remote)
    service.alive("proj")
    return service


def test_dead_refuses_with_the_exit_of_a_row_the_stub_holds(tmp_path: Path) -> None:
    seen: list[Path] = []

    def rows(root: Path) -> tuple[list[dict[str, Any]], str, str]:
        seen.append(root)
        return [{"repo": "my-repo", "exit": "Operator action: merge /w/a"}], "", ""

    service = _alive(tmp_path, rows)
    with pytest.raises(DeadUnpushedCommitsError) as refused:
        service.dead("proj")

    assert str(refused.value).endswith("fix: Operator action: merge /w/a")
    assert seen == [tmp_path / "ws"]


def test_dead_refuses_with_the_readers_fix_when_the_read_failed(tmp_path: Path) -> None:
    def rows(_root: Path) -> tuple[list[dict[str, Any]], str, str]:
        return [], "list failed: boom", "Operator action: rerun list"

    service = _alive(tmp_path, rows)
    with pytest.raises(DeadUnpushedCommitsError) as refused:
        service.dead("proj")

    assert "(list failed: boom)" in str(refused.value)
    assert str(refused.value).endswith("fix: Operator action: rerun list")
