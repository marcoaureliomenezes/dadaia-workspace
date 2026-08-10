"""Bug context-baseline-rejects-official-scaffold-followup (Consumer R1-D1).

The official fresh-context sequence is ``context create`` → ``context alive`` (which
commits its own scaffold) → optionally ``specs init`` (which adds more scaffold files) →
``context baseline``. Baseline refused that follow-up state as "uncommitted changes on
top of existing history", making the documented sequence self-inconsistent. Contract:
a dirty tree whose every path is scaffold-shaped (``specs/**`` or ``AGENTS.md``)
converges into the baseline commit; anything operator-shaped still refuses.
"""

from __future__ import annotations

import pytest

pytest.importorskip("fcntl")

from pathlib import Path  # noqa: E402

from dadaia_workspace.core.exceptions import ContextStateError  # noqa: E402
from dadaia_workspace.features.spec_context.service import SpecContextService  # noqa: E402
from tests.fakes import FakeContextStore, FakeGitClient  # noqa: E402

_CTX = "ctx-fresh"


def _service(tmp_path: Path) -> tuple[SpecContextService, FakeGitClient, Path]:
    root = tmp_path / "ws"
    (root / "repos").mkdir(parents=True)
    git = FakeGitClient()
    service = SpecContextService(
        context_store=FakeContextStore(),
        git_client=git,
        workspace_root=root,
    )
    service.create(_CTX, repo_slug=_CTX, repo_url="")
    service.alive(_CTX)
    repo = root / "repos" / _CTX
    repo.mkdir(parents=True, exist_ok=True)
    return service, git, repo


def test_baseline_accepts_scaffold_shaped_followup_on_top_of_history(tmp_path: Path) -> None:
    service, git, repo = _service(tmp_path)
    # Post-alive canonical state: history exists; a `specs init` follow-up left
    # tool-authored scaffold files dirty.
    git._has_commits.add(repo)
    git._dirty.add(repo)
    git._diff_names[repo] = ("specs/releases/ACTIVE.md", "specs/backlog/README.md", "AGENTS.md")
    git._untracked[repo] = ["specs/backlog/README.md"]

    ctx = service.baseline(_CTX)

    assert ctx.name == _CTX
    assert git.committed, "the scaffold follow-up must be folded into the baseline commit"


def test_baseline_still_refuses_operator_content_on_top_of_history(tmp_path: Path) -> None:
    service, git, repo = _service(tmp_path)
    git._has_commits.add(repo)
    git._dirty.add(repo)
    git._diff_names[repo] = ("specs/releases/ACTIVE.md", "notes-from-operator.txt")

    with pytest.raises(ContextStateError, match="never sweeps operator content"):
        service.baseline(_CTX)
    assert git.committed == []
