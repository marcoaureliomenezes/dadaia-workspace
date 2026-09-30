"""The unit tier spawns no process (tests/AGENTS.md): `dead()` and the doctor read no
`worktree.py` rows here (bug unit-tests-spawn-the-worktree-script-through-a-cli-stub)."""

import pytest

from dadaia_workspace.features.spec_context import doctor, service


@pytest.fixture(autouse=True)
def _no_open_worktree(monkeypatch: pytest.MonkeyPatch) -> None:
    for owner in (service, doctor):
        monkeypatch.setattr(owner, "worktree_rows", lambda _root: ([], "", ""))
