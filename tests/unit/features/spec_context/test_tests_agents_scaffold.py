"""T-070-07 (v0.7.0 FR3): consumer repos receive tests/AGENTS.md at the alive() seam.

Intent: CONTRACT — v0.7.0 FR3 (consumer test-doctrine distribution).

The stewardship doctrine reaches consumer workspaces as a scoped test law:
``public/templates/tests-AGENTS.md`` is copied to ``<repo>/tests/AGENTS.md`` at the
same seam that installs ``repo-AGENTS.md`` — ONLY when ``<repo>/tests/`` already
exists and carries no ``AGENTS.md`` of its own (GRILL P2). ``alive()`` must never
invent a ``tests/`` directory: a repo without one is not a repo this doctrine can
scaffold into, and a stray folder would land in every non-Python consumer.
"""

from __future__ import annotations

import pytest

pytest.importorskip("fcntl")

from pathlib import Path  # noqa: E402

from dadaia_workspace.features.spec_context.service import (  # noqa: E402
    _PUBLIC_DIR,
    SpecContextService,
)
from tests.fakes import FakeContextStore, FakeGitClient  # noqa: E402

_TEMPLATE = _PUBLIC_DIR / "templates" / "tests-AGENTS.md"


@pytest.fixture()
def workspace_root(tmp_path: Path) -> Path:
    root = tmp_path / "ws"
    root.mkdir()
    (root / "repos").mkdir()
    return root


@pytest.fixture()
def service(workspace_root: Path) -> SpecContextService:
    return SpecContextService(
        context_store=FakeContextStore(),
        git_client=FakeGitClient(),
        workspace_root=workspace_root,
    )


def _repo_with_tests_dir(service: SpecContextService, workspace_root: Path) -> Path:
    service.create("proj", "my-repo", "https://github.com/org/my-repo")
    repo = workspace_root / "repos" / "my-repo"
    (repo / "tests").mkdir(parents=True, exist_ok=True)
    return repo


def test_tests_dir_without_agents_receives_the_template_byte_identical(
    service: SpecContextService, workspace_root: Path
) -> None:
    repo = _repo_with_tests_dir(service, workspace_root)
    service.alive("proj")
    installed = repo / "tests" / "AGENTS.md"
    assert installed.exists(), "tests/ exists and has no AGENTS.md — the template must land"
    assert installed.read_bytes() == _TEMPLATE.read_bytes(), (
        "the copy is byte-identical — no rendering step exists at this seam"
    )


def test_existing_tests_agents_is_never_overwritten(
    service: SpecContextService, workspace_root: Path
) -> None:
    repo = _repo_with_tests_dir(service, workspace_root)
    own_law = "# my own scoped test law\n"
    (repo / "tests" / "AGENTS.md").write_text(own_law, encoding="utf-8")
    service.alive("proj")
    assert (repo / "tests" / "AGENTS.md").read_text(encoding="utf-8") == own_law


def test_repo_without_tests_dir_gets_no_directory_and_no_file(
    service: SpecContextService, workspace_root: Path
) -> None:
    service.create("proj", "my-repo", "https://github.com/org/my-repo")
    repo = workspace_root / "repos" / "my-repo"
    assert not (repo / "tests").exists()
    service.alive("proj")
    assert not (repo / "tests").exists(), (
        "alive() must never invent tests/ — the naive mkdir(parents=True) failure mode"
    )
