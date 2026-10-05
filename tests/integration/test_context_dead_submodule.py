"""rc-9 AC3.6 row 24 (context-dead-submodule-refusal-prints-a-worktree-move-that-cannot-run):
a submodule is no linked worktree — dead holds the repo holding it, and the submodule's
relative gitdir still resolves after the move. Size: MEDIUM — real git in tmp_path."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

pytest.importorskip("fcntl")

from dadaia_workspace.core.models.spec_context import ContextState  # noqa: E402
from tests.integration.test_context_dead_holds import _alive, _git, _published  # noqa: E402

pytestmark = [pytest.mark.integration, pytest.mark.slow]


def test_dead_holds_a_repo_with_a_submodule_and_its_gitdir_resolves(tmp_path: Path) -> None:
    service, store, repo = _alive(tmp_path)
    sub = _published(tmp_path, tmp_path / "subsrc")
    _git("-c", "protocol.file.allow=always", "submodule", "add", str(sub), "sub", cwd=repo)
    _git("commit", "-m", "add sub", cwd=repo)
    _git("push", cwd=repo)

    service.dead("proj")

    [held] = (tmp_path / "ws" / ".dadaia" / "reaped").glob("*/repos/main/sub")
    resolved = subprocess.run(
        ["git", "rev-parse", "--is-inside-work-tree"], cwd=held, capture_output=True, text=True
    )
    assert resolved.stdout == "true\n", resolved.stderr
    assert store.get("proj").state is ContextState.DEAD  # type: ignore[union-attr]
