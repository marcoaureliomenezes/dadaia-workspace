"""The repo-law write path (CWE-59/CWE-367):
``canon._write_absent`` behind ``scaffold_repo_law``. Size: SMALL (tmp filesystem only)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from dadaia_workspace.features.specs import canon

pytest.importorskip("fcntl")  # POSIX symlink + O_NOFOLLOW semantics

_BODIES = {"repo-AGENTS.md": "# repo law\n"}


@pytest.fixture
def public(tmp_path: Path) -> Path:
    templates = tmp_path / "public" / "templates"
    templates.mkdir(parents=True)
    for name, body in _BODIES.items():
        (templates / name).write_text(body, encoding="utf-8")
    return tmp_path / "public"


def test_installs_the_absent_repo_law(tmp_path: Path, public: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    written = canon.scaffold_repo_law(repo, project_name="p", public_dir=public)
    assert written == [repo / "AGENTS.md"]
    assert (repo / "AGENTS.md").read_text(encoding="utf-8") == "# repo law\n"


def test_present_law_is_never_overwritten(tmp_path: Path, public: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "AGENTS.md").write_text("mine\n", encoding="utf-8")
    assert canon.scaffold_repo_law(repo, project_name="p", public_dir=public) == []
    assert (repo / "AGENTS.md").read_text(encoding="utf-8") == "mine\n"


def test_symlinked_repo_root_is_never_written_through(tmp_path: Path, public: Path) -> None:
    outside = tmp_path / "outside-repo"
    outside.mkdir()
    repo = tmp_path / "repo"
    repo.symlink_to(outside, target_is_directory=True)
    assert canon.scaffold_repo_law(repo, project_name="p", public_dir=public) == []
    assert list(outside.iterdir()) == []


@pytest.mark.parametrize("dangling", [True, False])
def test_symlinked_destination_is_never_written_through(
    tmp_path: Path, public: Path, dangling: bool
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    target = tmp_path / "elsewhere.md"
    if not dangling:
        target.write_text("real\n", encoding="utf-8")
    (repo / "AGENTS.md").symlink_to(target)
    assert canon.scaffold_repo_law(repo, project_name="p", public_dir=public) == []
    assert (repo / "AGENTS.md").is_symlink()
    assert (target.read_text(encoding="utf-8") if target.exists() else None) == (
        None if dangling else "real\n"
    )


def test_scaffold_never_writes_through_a_symlinked_parent_dir(tmp_path: Path) -> None:
    outside = tmp_path / "outside-memory"
    outside.mkdir()
    specs = tmp_path / "specs"
    specs.mkdir()
    (specs / "memory").symlink_to(outside, target_is_directory=True)
    canon.scaffold(specs)
    assert list(outside.iterdir()) == []


def test_an_unwritable_directory_raises_instead_of_skipping(tmp_path: Path, public: Path) -> None:
    """Only an existing file or a symlinked target is skipped."""
    if os.geteuid() == 0:
        pytest.skip("root ignores directory permissions")
    repo = tmp_path / "repo"
    repo.mkdir()
    repo.chmod(0o555)
    try:
        with pytest.raises(PermissionError):
            canon.scaffold_repo_law(repo, project_name="p", public_dir=public)
    finally:
        repo.chmod(0o755)


def test_repo_law_heading_carries_the_project_name(tmp_path: Path, public: Path) -> None:
    """The template's
    ``<repo-name>`` is filled at scaffold time, never left for a doctor to flag."""
    (public / "templates" / "repo-AGENTS.md").write_text(
        "# <repo-name> — Repo Rules\n", encoding="utf-8"
    )
    repo = tmp_path / "repo"
    repo.mkdir()

    canon.scaffold_repo_law(repo, project_name="acme", public_dir=public)

    assert (repo / "AGENTS.md").read_text(encoding="utf-8") == "# acme — Repo Rules\n"
