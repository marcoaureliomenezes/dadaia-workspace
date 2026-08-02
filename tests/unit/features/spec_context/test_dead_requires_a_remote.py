"""DEAD is a promise: commit, push, then remove from disk.

``dead()`` removes the repository directory. When the repo has a remote, the pushed
commits survive the removal and DEAD is a safe archival transition. When it has **no**
remote there is nowhere for the work to survive, so removing the directory destroys the
only copy — the auto-sync commit is deleted along with the ``.git`` that holds it.

The transition must therefore refuse rather than silently degrade the promise to
"commit and delete". Explicit consent (``no_remote_ok=True``) is the same escape hatch
``--commit`` already provides for the untracked-file review gate.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.core.models.spec_context import ContextState
from dadaia_workspace.features.spec_context.service import (
    DeadRemoteRequiredError,
    SpecContextService,
)
from tests.fakes import FakeContextStore, FakeGitClient


@pytest.fixture()
def workspace_root(tmp_path: Path) -> Path:
    root = tmp_path / "ws"
    (root / "repos").mkdir(parents=True)
    return root


@pytest.fixture()
def git() -> FakeGitClient:
    return FakeGitClient()


@pytest.fixture()
def service(workspace_root: Path, git: FakeGitClient) -> SpecContextService:
    return SpecContextService(
        context_store=FakeContextStore(),
        git_client=git,
        workspace_root=workspace_root,
    )


def _alive(service: SpecContextService, workspace_root: Path) -> Path:
    service.create("proj", "my-repo", "https://github.com/org/my-repo")
    service.alive("proj")
    return workspace_root / "repos" / "my-repo"


def test_dead_refuses_when_there_is_no_remote_to_push_to(
    service: SpecContextService, workspace_root: Path, git: FakeGitClient
) -> None:
    repo = _alive(service, workspace_root)
    git._dirty.add(repo)  # work exists, and no remote holds a copy of it

    with pytest.raises(DeadRemoteRequiredError) as excinfo:
        service.dead("proj")

    assert repo.exists(), "a refusal must leave the repository untouched on disk"
    assert repo not in git.pushed
    message = str(excinfo.value)
    assert "remote" in message.lower()
    assert "my-repo" in message or "proj" in message


def test_the_context_stays_alive_after_the_refusal(
    service: SpecContextService, workspace_root: Path, git: FakeGitClient
) -> None:
    """A refused transition may not half-apply: the record must still say ALIVE."""
    _alive(service, workspace_root)

    with pytest.raises(DeadRemoteRequiredError):
        service.dead("proj")

    assert service.show("proj").state == ContextState.ALIVE


def test_explicit_consent_accepts_the_loss_and_completes(
    service: SpecContextService, workspace_root: Path, git: FakeGitClient
) -> None:
    repo = _alive(service, workspace_root)
    git._dirty.add(repo)

    ctx = service.dead("proj", no_remote_ok=True)

    assert not repo.exists()
    assert ctx.state == ContextState.DEAD
    assert repo in git.committed, "consent still commits — it only waives the push"


def test_a_remote_needs_no_consent_flag(
    service: SpecContextService, workspace_root: Path, git: FakeGitClient
) -> None:
    """The guarantee is satisfiable here, so the normal path stays untouched."""
    repo = _alive(service, workspace_root)
    git._dirty.add(repo)
    git._has_remote.add(repo)

    ctx = service.dead("proj")

    assert not repo.exists()
    assert ctx.state == ContextState.DEAD
    assert repo in git.pushed


def test_a_repo_that_is_not_a_git_root_is_not_gated(
    workspace_root: Path, git: FakeGitClient
) -> None:
    """Nothing to push and nothing to lose to git — the gate must not fire."""
    git.is_git_root = lambda path: False  # type: ignore[method-assign]
    service = SpecContextService(
        context_store=FakeContextStore(), git_client=git, workspace_root=workspace_root
    )
    repo = _alive(service, workspace_root)

    ctx = service.dead("proj")

    assert not repo.exists()
    assert ctx.state == ContextState.DEAD
