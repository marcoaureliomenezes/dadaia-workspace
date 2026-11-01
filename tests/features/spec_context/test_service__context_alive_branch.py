"""``alive`` lands the main repo on the highest work branch origin holds, else on the integration
branch, over a real ``file://`` remote; a checkout git refuses is one refusal, never a WARNING."""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.container import scan_publish_candidates
from dadaia_workspace.core.exceptions import GitSyncError
from dadaia_workspace.core.models.spec_context import ContextState
from dadaia_workspace.features.spec_context.service import SpecContextService
from dadaia_workspace.infrastructure.git_subprocess import GitSubprocessClient
from tests.fakes import no_worktree_rows, register_dead
from tests.fixtures.real_git import git, seeded_remote
from tests.fixtures.stores import context_store


@pytest.fixture()
def workspace_root(tmp_path: Path) -> Path:
    root = tmp_path / "ws"
    (root / "repos").mkdir(parents=True)
    return root


@pytest.fixture()
def service(workspace_root: Path) -> SpecContextService:
    return SpecContextService(
        context_store=context_store(workspace_root / ".dadaia" / "states"),
        git_client=GitSubprocessClient(),
        workspace_root=workspace_root,
        install_hooks=lambda _repo: None,
        secret_scan=scan_publish_candidates,
        worktree_rows=no_worktree_rows,
    )


def _remote_with(workspace_root: Path, *branches: str) -> Path:
    remote = seeded_remote(workspace_root.parent, "foo")
    for branch in branches:
        git(
            workspace_root.parent / "seed-foo",
            "push",
            "-q",
            str(remote),
            f"HEAD:refs/heads/{branch}",
        )
    return remote


@pytest.mark.parametrize(
    ("origin", "lands_on"),
    [
        (("feature/0.6.0",), "feature/0.6.0"),
        (("feature/0.6.0", "feature/0.10.0", "feature/0.8.0"), "feature/0.10.0"),
        (("develop",), "develop"),
    ],
    ids=["one-work", "highest-of-three", "none-takes-integration"],
)
def test_alive_checks_out_the_highest_origin_work_branch_else_the_integration_branch(
    service: SpecContextService, workspace_root: Path, origin: tuple[str, ...], lands_on: str
) -> None:
    remote = _remote_with(workspace_root, *origin)
    register_dead(service, "foo", "foo", remote.as_uri())

    assert service.alive("foo").state == ContextState.ALIVE
    assert git(workspace_root / "repos" / "foo", "branch", "--show-current") == lands_on


def test_alive_refuses_with_one_fix_line_when_the_checkout_fails(
    service: SpecContextService, workspace_root: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    register_dead(service, "foo", "foo", _remote_with(workspace_root).as_uri())

    with pytest.raises(GitSyncError) as refused:
        service.alive("foo")

    assert refused.value.fix.startswith("Agent action: ")
    assert "\n" not in refused.value.fix
    assert capsys.readouterr().err == ""
    assert service.show("foo").state == ContextState.DEAD
