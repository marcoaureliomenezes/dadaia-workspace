"""The repo-law write path (CWE-59/CWE-367):
``canon._write_absent`` behind ``scaffold_repo_law``. Size: SMALL (tmp filesystem only)."""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.features.specs import canon
from tests.helpers.oslib import link, read_text, write_text

_BODIES = {"repo-AGENTS.md": "# repo law\n"}


@pytest.fixture
def public(tmp_path: Path) -> Path:
    templates = tmp_path / "public" / "templates"
    templates.mkdir(parents=True)
    for name, body in _BODIES.items():
        write_text(templates / name, body)
    return tmp_path / "public"


def test_installs_the_absent_repo_law(tmp_path: Path, public: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    written = canon.scaffold_repo_law(repo, project_name="p", public_dir=public)
    assert written == [repo / "AGENTS.md"]
    assert read_text(repo / "AGENTS.md") == "# repo law\n"


def test_present_law_is_never_overwritten(tmp_path: Path, public: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    write_text(repo / "AGENTS.md", "mine\n")
    assert canon.scaffold_repo_law(repo, project_name="p", public_dir=public) == []
    assert read_text(repo / "AGENTS.md") == "mine\n"


def test_symlinked_repo_root_is_never_written_through(tmp_path: Path, public: Path) -> None:
    outside = tmp_path / "outside-repo"
    outside.mkdir()
    repo = tmp_path / "repo"
    assert link(str(outside), repo, is_dir=True)
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
        write_text(target, "real\n")
    assert link(str(target), repo / "AGENTS.md", is_dir=False)
    assert canon.scaffold_repo_law(repo, project_name="p", public_dir=public) == []
    assert (repo / "AGENTS.md").is_symlink()
    assert (read_text(target) if target.exists() else None) == (None if dangling else "real\n")


def test_scaffold_never_writes_through_a_symlinked_parent_dir(tmp_path: Path) -> None:
    outside = tmp_path / "outside-memory"
    outside.mkdir()
    specs = tmp_path / "specs"
    specs.mkdir()
    assert link(str(outside), specs / "memory", is_dir=True)
    canon.scaffold(specs)
    assert list(outside.iterdir()) == []


def test_a_refused_write_raises_instead_of_skipping(
    tmp_path: Path, public: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Only an existing file or a symlinked target is skipped; a write the host refuses (an
    unwritable directory: no mode bit makes one on Windows) propagates."""

    def refuse(*_args: object, **_kw: object) -> None:
        raise PermissionError("read-only directory")

    monkeypatch.setattr(canon, "atomic_write", refuse)
    repo = tmp_path / "repo"
    repo.mkdir()
    with pytest.raises(PermissionError):
        canon.scaffold_repo_law(repo, project_name="p", public_dir=public)
    assert list(repo.iterdir()) == []


def test_repo_law_heading_carries_the_project_name(tmp_path: Path, public: Path) -> None:
    """The template's
    ``<repo-name>`` is filled at scaffold time, never left for a doctor to flag."""
    write_text(public / "templates" / "repo-AGENTS.md", "# <repo-name> — Repo Rules\n")
    repo = tmp_path / "repo"
    repo.mkdir()

    canon.scaffold_repo_law(repo, project_name="acme", public_dir=public)

    assert read_text(repo / "AGENTS.md") == "# acme — Repo Rules\n"
