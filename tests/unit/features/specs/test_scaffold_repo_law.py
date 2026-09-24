"""Intent: CONTRACT — T-048-05 review finding 3 (CWE-59/CWE-367); ports v0.4.3 A17.1/A17.2,
v0.7.0 FR3 and 0.4.6 AC7 from the deleted ``scoped_law`` tests onto the one write path
``canon._write_absent`` behind ``scaffold_repo_law``. Size: SMALL (tmp filesystem only)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from dadaia_workspace.features.specs import canon

pytest.importorskip("fcntl")  # POSIX symlink + O_NOFOLLOW semantics

_BODIES = {"repo-AGENTS.md": "# repo law\n", "tests-AGENTS.md": "# tests law\n"}


@pytest.fixture
def public(tmp_path: Path) -> Path:
    templates = tmp_path / "public" / "templates"
    templates.mkdir(parents=True)
    for name, body in _BODIES.items():
        (templates / name).write_text(body, encoding="utf-8")
    return tmp_path / "public"


def test_installs_every_absent_row_beside_an_existing_tests_tree(
    tmp_path: Path, public: Path
) -> None:
    repo = tmp_path / "repo"
    (repo / "tests").mkdir(parents=True)
    written = canon.scaffold_repo_law(repo, public_dir=public)
    assert written == [repo / "AGENTS.md", repo / "tests" / "AGENTS.md"]
    assert (repo / "AGENTS.md").read_text(encoding="utf-8") == "# repo law\n"
    assert (repo / "tests" / "AGENTS.md").read_text(encoding="utf-8") == "# tests law\n"


def test_present_rows_are_never_overwritten_and_no_tests_dir_is_invented(
    tmp_path: Path, public: Path
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "AGENTS.md").write_text("mine\n", encoding="utf-8")
    assert canon.scaffold_repo_law(repo, public_dir=public) == []
    assert (repo / "AGENTS.md").read_text(encoding="utf-8") == "mine\n"
    assert not (repo / "tests").exists()


def test_symlinked_tests_dir_is_never_written_through(tmp_path: Path, public: Path) -> None:
    outside = tmp_path / "outside-tests"
    outside.mkdir()
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "tests").symlink_to(outside, target_is_directory=True)
    assert canon.scaffold_repo_law(repo, public_dir=public) == [repo / "AGENTS.md"]
    assert list(outside.iterdir()) == []


def test_symlinked_repo_root_is_never_written_through(tmp_path: Path, public: Path) -> None:
    outside = tmp_path / "outside-repo"
    (outside / "tests").mkdir(parents=True)
    repo = tmp_path / "repo"
    repo.symlink_to(outside, target_is_directory=True)
    assert canon.scaffold_repo_law(repo, public_dir=public) == []
    assert sorted(p.name for p in outside.rglob("*")) == ["tests"]


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
    assert canon.scaffold_repo_law(repo, public_dir=public) == []
    assert (repo / "AGENTS.md").is_symlink()
    assert (target.read_text(encoding="utf-8") if target.exists() else None) == (
        None if dangling else "real\n"
    )


def test_the_write_is_one_atomic_exclusive_nofollow_open(
    tmp_path: Path, public: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """CWE-367: no probe-then-write window — the create itself refuses an existing or
    symlinked destination."""
    repo = tmp_path / "repo"
    repo.mkdir()
    dst = str(repo / "AGENTS.md")
    seen: list[int] = []
    real_open = os.open

    def spy(path: object, flags: int, *args: object, **kwargs: object) -> int:
        if str(path) == dst:
            seen.append(flags)
        return real_open(path, flags, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(os, "open", spy)
    canon.scaffold_repo_law(repo, public_dir=public)
    assert seen, "the scoped-law write must go through os.open"
    assert seen[0] & os.O_CREAT and seen[0] & os.O_EXCL and seen[0] & os.O_NOFOLLOW


def test_scaffold_never_writes_through_a_symlinked_parent_dir(tmp_path: Path) -> None:
    outside = tmp_path / "outside-memory"
    outside.mkdir()
    specs = tmp_path / "specs"
    specs.mkdir()
    (specs / "memory").symlink_to(outside, target_is_directory=True)
    canon.scaffold(specs)
    assert list(outside.iterdir()) == []


def test_an_unwritable_directory_raises_instead_of_skipping(tmp_path: Path, public: Path) -> None:
    """Review N2: only an existing file or a symlinked target is skipped."""
    if os.geteuid() == 0:
        pytest.skip("root ignores directory permissions")
    repo = tmp_path / "repo"
    repo.mkdir()
    repo.chmod(0o555)
    try:
        with pytest.raises(PermissionError):
            canon.scaffold_repo_law(repo, public_dir=public)
    finally:
        repo.chmod(0o755)
