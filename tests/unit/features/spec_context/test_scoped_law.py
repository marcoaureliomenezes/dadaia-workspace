"""Intent: CONTRACT — 0.4.6 AC7 (scoped-law bridges); F013 (one home for the repo-tree writes).
Size: SMALL (unit)."""

from __future__ import annotations

from pathlib import Path

from dadaia_workspace.features.spec_context import scoped_law

_PUBLIC = Path(scoped_law.__file__).resolve().parents[2] / "public"

_TEMPLATES = {
    "repo-AGENTS.md": "# repo law\n",
    "repo-CLAUDE.md": "@AGENTS.md\n",
    "tests-AGENTS.md": "# tests law\n",
    "tests-CLAUDE.md": "@AGENTS.md\n",
}
_ROWS = {
    "AGENTS.md": "repo-AGENTS.md",
    "CLAUDE.md": "repo-CLAUDE.md",
    "tests/AGENTS.md": "tests-AGENTS.md",
    "tests/CLAUDE.md": "tests-CLAUDE.md",
}


def _public_dir(tmp_path: Path) -> Path:
    templates = tmp_path / "public" / "templates"
    templates.mkdir(parents=True)
    for name, body in _TEMPLATES.items():
        (templates / name).write_text(body, encoding="utf-8")
    return tmp_path / "public"


def test_installs_every_absent_row(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    (repo / "tests").mkdir(parents=True)
    touched = scoped_law.install_scoped_law(repo, _public_dir(tmp_path))
    assert touched == ["AGENTS.md", "CLAUDE.md", "tests/AGENTS.md", "tests/CLAUDE.md"]
    for dest, template in _ROWS.items():
        assert (repo / dest).read_text(encoding="utf-8") == _TEMPLATES[template]


def test_present_rows_are_left_untouched(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    (repo / "tests").mkdir(parents=True)
    (repo / "AGENTS.md").write_text("mine\n", encoding="utf-8")
    (repo / "tests" / "CLAUDE.md").write_text("mine\n", encoding="utf-8")
    touched = scoped_law.install_scoped_law(repo, _public_dir(tmp_path))
    assert touched == ["CLAUDE.md", "tests/AGENTS.md"]
    assert (repo / "AGENTS.md").read_text(encoding="utf-8") == "mine\n"
    assert (repo / "tests" / "CLAUDE.md").read_text(encoding="utf-8") == "mine\n"


def test_tests_rows_are_skipped_without_a_tests_dir(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    touched = scoped_law.install_scoped_law(repo, _public_dir(tmp_path))
    assert touched == ["AGENTS.md", "CLAUDE.md"]
    assert not (repo / "tests").exists()


def test_refuses_symlinked_destinations_and_directories(tmp_path: Path) -> None:
    public = _public_dir(tmp_path)
    outside = tmp_path / "outside.md"
    outside.write_text("x", encoding="utf-8")
    outside_tests = tmp_path / "outside-tests"
    outside_tests.mkdir()
    repo = tmp_path / "repo"
    repo.mkdir()
    for dest in ("AGENTS.md", "CLAUDE.md"):
        (repo / dest).symlink_to(outside)
    (repo / "tests").symlink_to(outside_tests, target_is_directory=True)
    assert scoped_law.install_scoped_law(repo, public) == []
    assert outside.read_text(encoding="utf-8") == "x"
    assert list(outside_tests.iterdir()) == []


def test_symlinked_repo_root_is_never_written_through(tmp_path: Path) -> None:
    outside = tmp_path / "outside-repo"
    (outside / "tests").mkdir(parents=True)
    repo = tmp_path / "repo"
    repo.symlink_to(outside, target_is_directory=True)
    assert scoped_law.install_scoped_law(repo, _public_dir(tmp_path)) == []
    assert sorted(p.name for p in outside.rglob("*")) == ["tests"]


def test_shipped_bridge_templates_are_one_import_line() -> None:
    for name in ("repo-CLAUDE.md", "tests-CLAUDE.md"):
        assert (_PUBLIC / "templates" / name).read_bytes() == b"@AGENTS.md\n"


def test_secret_scan_engine_lives_in_the_privacy_module() -> None:
    from dadaia_workspace.features.spec_context import service
    from dadaia_workspace.infrastructure import privacy_check

    assert service._scan_file_for_secrets is privacy_check.scan_file_for_secrets
