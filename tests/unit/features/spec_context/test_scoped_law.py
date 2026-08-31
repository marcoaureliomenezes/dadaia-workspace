"""F013 (20260830-design-bug-surface-audit): the scoped-law placement leaves the
lifecycle verb — ``scoped_law.install_scoped_law`` owns the two hardened writes the
974-line service.py used to inline, and the secret-scan engine's ONE home is the
privacy module. Intent: contract; size: unit."""

from __future__ import annotations

from pathlib import Path

from dadaia_workspace.features.spec_context import scoped_law


def _public_dir(tmp_path: Path) -> Path:
    templates = tmp_path / "public" / "templates"
    templates.mkdir(parents=True)
    (templates / "repo-AGENTS.md").write_text("# repo law\n", encoding="utf-8")
    (templates / "tests-AGENTS.md").write_text("# tests law\n", encoding="utf-8")
    return tmp_path / "public"


def test_installs_repo_law_when_absent(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    touched = scoped_law.install_scoped_law(repo, _public_dir(tmp_path))
    assert touched == ["AGENTS.md"]
    assert (repo / "AGENTS.md").read_text(encoding="utf-8") == "# repo law\n"


def test_never_overwrites_existing_law(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "AGENTS.md").write_text("mine\n", encoding="utf-8")
    touched = scoped_law.install_scoped_law(repo, _public_dir(tmp_path))
    assert touched == []
    assert (repo / "AGENTS.md").read_text(encoding="utf-8") == "mine\n"


def test_tests_law_lands_only_where_tests_exists(tmp_path: Path) -> None:
    public = _public_dir(tmp_path)
    repo_a = tmp_path / "a"
    repo_a.mkdir()
    assert "tests/AGENTS.md" not in scoped_law.install_scoped_law(repo_a, public)
    repo_b = tmp_path / "b"
    (repo_b / "tests").mkdir(parents=True)
    touched = scoped_law.install_scoped_law(repo_b, public)
    assert "tests/AGENTS.md" in touched
    assert (repo_b / "tests" / "AGENTS.md").read_text(encoding="utf-8") == "# tests law\n"


def test_refuses_symlinked_destinations(tmp_path: Path) -> None:
    public = _public_dir(tmp_path)
    repo = tmp_path / "repo"
    repo.mkdir()
    outside = tmp_path / "outside.md"
    outside.write_text("x", encoding="utf-8")
    (repo / "AGENTS.md").symlink_to(outside)
    (repo / "tests").mkdir()
    (repo / "tests" / "AGENTS.md").symlink_to(outside)
    touched = scoped_law.install_scoped_law(repo, public)
    assert touched == []
    assert outside.read_text(encoding="utf-8") == "x"


def test_secret_scan_engine_lives_in_the_privacy_module() -> None:
    from dadaia_workspace.features.spec_context import service
    from dadaia_workspace.infrastructure import privacy_check

    assert service._scan_file_for_secrets is privacy_check.scan_file_for_secrets
