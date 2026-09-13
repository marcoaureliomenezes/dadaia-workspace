"""Intent: CONTRACT — 0.4.7 FR6: the reaper never touches a repo-local virtualenv.

``.venv``, ``.git`` and ``node_modules`` end the repo-tree walk. They are pruned
BEFORE anything is classified, so the unattended reaper can never move a virtualenv
(absolute interpreter paths die with the move). A cache directory beside it is still
reported and still moved.

size: SMALL.
"""

from __future__ import annotations

from pathlib import Path

from dadaia_workspace.core.models.spec_context import ContextState, SpecContextProject
from dadaia_workspace.features.spec_context.doctor import DoctorService
from tests.fakes import FakeGitClient


class _Store:
    def __init__(self, contexts: list[SpecContextProject]) -> None:
        self._contexts = contexts

    def list_all(self) -> list[SpecContextProject]:
        return self._contexts

    def get(self, name: str) -> SpecContextProject | None:
        return next((c for c in self._contexts if c.name == name), None)


def _workspace(tmp_path: Path) -> Path:
    ws = tmp_path / "ws"
    (ws / ".dadaia" / "states").mkdir(parents=True)
    repo = ws / "repos" / "demo"
    (repo / ".venv" / "bin").mkdir(parents=True)
    (repo / ".venv" / "bin" / "python").write_text("#!/bin/sh\n", encoding="utf-8")
    (repo / ".venv" / ".pytest_cache").mkdir()
    (repo / ".pytest_cache").mkdir()
    (repo / "src").mkdir()
    return ws


def _doctor(ws: Path) -> DoctorService:
    ctx = SpecContextProject(
        name="demo",
        repo_slug="demo",
        repo_url="git@example.invalid:demo.git",
        state=ContextState.ALIVE,
        created_at="2026-09-13T00:00:00Z",
    )
    return DoctorService(
        context_store=_Store([ctx]),
        git_client=FakeGitClient(),
        workspace_root=ws,
    )


def test_a_repo_local_venv_is_never_a_finding_and_is_never_moved(tmp_path: Path) -> None:
    ws = _workspace(tmp_path)
    doctor = _doctor(ws)

    paths = {finding.path for finding in doctor.scan()}
    assert not any(".venv" in path for path in paths), paths
    assert "repos/demo/.pytest_cache" in paths, paths

    doctor.fix()

    assert (ws / "repos" / "demo" / ".venv" / "bin" / "python").exists()
    assert not (ws / "repos" / "demo" / ".pytest_cache").exists()
