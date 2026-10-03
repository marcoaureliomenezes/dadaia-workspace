"""Intent: CONTRACT — T-048-05 review finding 3 (CWE-59/CWE-367); ports v0.4.3 A17.1/A17.2,
v0.7.0 FR3 and 0.4.6 AC7 from the deleted ``scoped_law`` tests onto the one write path
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
    """sa-public-install-writes-the-root-map-into-product-repos#K5."""
    repo = tmp_path / "repo"
    repo.mkdir()
    written = canon.scaffold_repo_law(repo, project_name="p", public_dir=public)
    assert written == [repo / "AGENTS.md"]
    assert (repo / "AGENTS.md").read_text(encoding="utf-8") == "# repo law\n"


def test_present_law_is_never_overwritten(tmp_path: Path, public: Path) -> None:
    """sa-public-install-writes-the-root-map-into-product-repos#K5."""
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "AGENTS.md").write_text("mine\n", encoding="utf-8")
    assert canon.scaffold_repo_law(repo, project_name="p", public_dir=public) == []
    assert (repo / "AGENTS.md").read_text(encoding="utf-8") == "mine\n"


def test_symlinked_repo_root_is_never_written_through(tmp_path: Path, public: Path) -> None:
    """sa-public-install-writes-the-root-map-into-product-repos#K5."""
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
    """sa-public-install-writes-the-root-map-into-product-repos#K5."""
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
    """sa-public-install-writes-the-root-map-into-product-repos#K5."""
    outside = tmp_path / "outside-memory"
    outside.mkdir()
    specs = tmp_path / "specs"
    specs.mkdir()
    (specs / "memory").symlink_to(outside, target_is_directory=True)
    canon.scaffold(specs)
    assert list(outside.iterdir()) == []


def test_an_unwritable_directory_raises_instead_of_skipping(tmp_path: Path, public: Path) -> None:
    """sa-public-install-writes-the-root-map-into-product-repos#K5: Review N2: only an existing file or a symlinked target is skipped."""
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
    """sa-public-install-writes-the-root-map-into-product-repos#K1: Bug scaffold-repo-agents-keeps-repo-name-placeholder: the template's
    ``<repo-name>`` is filled at scaffold time, never left for a doctor to flag."""
    (public / "templates" / "repo-AGENTS.md").write_text(
        "# <repo-name> — Repo Rules\n", encoding="utf-8"
    )
    repo = tmp_path / "repo"
    repo.mkdir()

    canon.scaffold_repo_law(repo, project_name="acme", public_dir=public)

    assert (repo / "AGENTS.md").read_text(encoding="utf-8") == "# acme — Repo Rules\n"
