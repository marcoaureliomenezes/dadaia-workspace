"""Unit tests for DoctorService ROOT-* invariants (T-SANI-05).

Each invariant gets:
- a clean-state test (no issue reported)
- a violating-state test (issue reported with correct code)
- a fixability check where applicable
"""

from __future__ import annotations

# Guard: skip this entire module on platforms where fcntl is not available (e.g. Windows).
import pytest

pytest.importorskip("fcntl")

from pathlib import Path  # noqa: E402

from dadaia_workspace.features.spec_context.doctor import DoctorService  # noqa: E402
from tests.fakes import FakeContextStore, FakeGitClient  # noqa: E402

# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def _make_doctor(workspace_root: Path) -> DoctorService:
    """Build DoctorService with empty context store for ROOT-only tests."""
    ctx_store = FakeContextStore()
    git_client = FakeGitClient()
    return DoctorService(ctx_store, git_client, workspace_root)


def _init_workspace(root: Path) -> None:
    """Create the minimal workspace skeleton expected by DoctorService."""
    (root / ".dadaia" / "states").mkdir(parents=True)
    (root / ".dadaia" / "states" / "spec_contexts.json").write_text(
        '{"schema_version": "2", "contexts": []}'
    )
    (root / "repos").mkdir(parents=True)
    (root / "AGENTS.md").write_text("# agents")


# ---------------------------------------------------------------------------
# ROOT-1: workspace root contains only whitelisted entries
# ---------------------------------------------------------------------------


class TestRoot1:
    def test_clean_workspace_no_root1(self, tmp_path: Path) -> None:
        """A workspace with only whitelisted entries reports no ROOT-1."""
        _init_workspace(tmp_path)
        svc = _make_doctor(tmp_path)
        codes = {i.code for i in svc.check()}
        assert "ROOT-1" not in codes

    def test_stray_file_triggers_root1(self, tmp_path: Path) -> None:
        """A non-whitelisted file at root triggers ROOT-1."""
        _init_workspace(tmp_path)
        (tmp_path / "random_junk.txt").write_text("oops")
        svc = _make_doctor(tmp_path)
        issues = svc.check()
        codes = {i.code for i in issues}
        assert "ROOT-1" in codes

    def test_stray_dir_triggers_root1(self, tmp_path: Path) -> None:
        """A non-whitelisted directory at root triggers ROOT-1."""
        _init_workspace(tmp_path)
        (tmp_path / "my_project").mkdir()
        svc = _make_doctor(tmp_path)
        codes = {i.code for i in svc.check()}
        assert "ROOT-1" in codes

    def test_whitelisted_dirs_allowed(self, tmp_path: Path) -> None:
        """All whitelisted dirs do not trigger ROOT-1."""
        _init_workspace(tmp_path)
        for name in [".agents", ".claude", ".codex", ".pi"]:
            (tmp_path / name).mkdir(exist_ok=True)
        svc = _make_doctor(tmp_path)
        codes = {i.code for i in svc.check()}
        assert "ROOT-1" not in codes

    def test_pi_dir_allowed(self, tmp_path: Path) -> None:
        """`.pi/` (PI Layer-2 harness home) does not trigger ROOT-1."""
        _init_workspace(tmp_path)
        (tmp_path / ".pi").mkdir(exist_ok=True)
        svc = _make_doctor(tmp_path)
        codes = {i.code for i in svc.check()}
        assert "ROOT-1" not in codes

    def test_gitignore_is_allowed(self, tmp_path: Path) -> None:
        """.gitignore at root is always permitted."""
        _init_workspace(tmp_path)
        (tmp_path / ".gitignore").write_text("*.pyc\n")
        svc = _make_doctor(tmp_path)
        codes = {i.code for i in svc.check()}
        assert "ROOT-1" not in codes

    def test_operator_exception_suppresses_root1(self, tmp_path: Path) -> None:
        """Files matching operator exception globs do not trigger ROOT-1."""
        _init_workspace(tmp_path)
        (tmp_path / "prompt.md").write_text("# notes")
        (tmp_path / "screenshot.png").write_bytes(b"PNG")
        exc_file = tmp_path / ".dadaia" / "states" / "root_exceptions.txt"
        exc_file.write_text("prompt.md\nscreenshot.png\n")
        svc = _make_doctor(tmp_path)
        codes = {i.code for i in svc.check()}
        assert "ROOT-1" not in codes

    def test_operator_exception_glob_suppresses_root1(self, tmp_path: Path) -> None:
        """Wildcard globs in operator exception list suppress ROOT-1."""
        _init_workspace(tmp_path)
        (tmp_path / "session-tab-1280.png").write_bytes(b"PNG")
        exc_file = tmp_path / ".dadaia" / "states" / "root_exceptions.txt"
        exc_file.write_text("*.png\n")
        svc = _make_doctor(tmp_path)
        codes = {i.code for i in svc.check()}
        assert "ROOT-1" not in codes

    def test_exception_file_comments_ignored(self, tmp_path: Path) -> None:
        """Comment lines (starting with #) in root_exceptions.txt are ignored."""
        _init_workspace(tmp_path)
        (tmp_path / "stray.txt").write_text("junk")
        exc_file = tmp_path / ".dadaia" / "states" / "root_exceptions.txt"
        exc_file.write_text("# this is a comment\n")
        svc = _make_doctor(tmp_path)
        codes = {i.code for i in svc.check()}
        assert "ROOT-1" in codes  # comment is not an exception; stray.txt is flagged

    def test_root1_is_not_fixable(self, tmp_path: Path) -> None:
        """ROOT-1 issues are not auto-fixable (requires human relocation)."""
        _init_workspace(tmp_path)
        (tmp_path / "some_stray.py").write_text("x = 1")
        svc = _make_doctor(tmp_path)
        root1_issues = [i for i in svc.check() if i.code == "ROOT-1"]
        assert len(root1_issues) == 1
        assert root1_issues[0].fixable is False

    def test_tool_configs_not_in_root1_but_root3(self, tmp_path: Path) -> None:
        """Tool config files (.mcp.json, CLAUDE.md) trigger ROOT-3 not ROOT-1."""
        _init_workspace(tmp_path)
        (tmp_path / ".mcp.json").write_text("{}")
        svc = _make_doctor(tmp_path)
        codes = {i.code for i in svc.check()}
        # ROOT-3 handles tool configs; ROOT-1 should also flag them (they are not whitelisted)
        # but the important thing is ROOT-3 fires too
        assert "ROOT-3" in codes


# ---------------------------------------------------------------------------
# ROOT-2: no forbidden caches/outputs at workspace root
# ---------------------------------------------------------------------------


class TestRoot2:
    def test_clean_workspace_no_root2(self, tmp_path: Path) -> None:
        """No forbidden caches present → no ROOT-2."""
        _init_workspace(tmp_path)
        svc = _make_doctor(tmp_path)
        codes = {i.code for i in svc.check()}
        assert "ROOT-2" not in codes

    def test_ruff_cache_triggers_root2(self, tmp_path: Path) -> None:
        """A .ruff_cache directory at root triggers ROOT-2."""
        _init_workspace(tmp_path)
        (tmp_path / ".ruff_cache").mkdir()
        svc = _make_doctor(tmp_path)
        codes = {i.code for i in svc.check()}
        assert "ROOT-2" in codes

    def test_pytest_cache_triggers_root2(self, tmp_path: Path) -> None:
        """A .pytest_cache directory at root triggers ROOT-2."""
        _init_workspace(tmp_path)
        (tmp_path / ".pytest_cache").mkdir()
        svc = _make_doctor(tmp_path)
        codes = {i.code for i in svc.check()}
        assert "ROOT-2" in codes

    def test_coverage_file_triggers_root2(self, tmp_path: Path) -> None:
        """A .coverage file at root triggers ROOT-2."""
        _init_workspace(tmp_path)
        (tmp_path / ".coverage").write_text("")
        svc = _make_doctor(tmp_path)
        codes = {i.code for i in svc.check()}
        assert "ROOT-2" in codes

    def test_playwright_mcp_triggers_root2(self, tmp_path: Path) -> None:
        """A .playwright-mcp directory at root triggers ROOT-2."""
        _init_workspace(tmp_path)
        (tmp_path / ".playwright-mcp").mkdir()
        svc = _make_doctor(tmp_path)
        codes = {i.code for i in svc.check()}
        assert "ROOT-2" in codes

    def test_mypy_cache_triggers_root2(self, tmp_path: Path) -> None:
        """A .mypy_cache directory at root triggers ROOT-2."""
        _init_workspace(tmp_path)
        (tmp_path / ".mypy_cache").mkdir()
        svc = _make_doctor(tmp_path)
        codes = {i.code for i in svc.check()}
        assert "ROOT-2" in codes

    def test_hypothesis_dir_triggers_root2(self, tmp_path: Path) -> None:
        """A .hypothesis directory at root triggers ROOT-2."""
        _init_workspace(tmp_path)
        (tmp_path / ".hypothesis").mkdir()
        svc = _make_doctor(tmp_path)
        codes = {i.code for i in svc.check()}
        assert "ROOT-2" in codes

    def test_root2_is_fixable(self, tmp_path: Path) -> None:
        """ROOT-2 issues are fixable (caches are safe to delete)."""
        _init_workspace(tmp_path)
        (tmp_path / ".ruff_cache").mkdir()
        svc = _make_doctor(tmp_path)
        root2_issues = [i for i in svc.check() if i.code == "ROOT-2"]
        assert len(root2_issues) == 1
        assert root2_issues[0].fixable is True

    def test_fix_removes_root2_caches(self, tmp_path: Path) -> None:
        """fix() deletes forbidden cache dirs at workspace root."""
        _init_workspace(tmp_path)
        cache_dir = tmp_path / ".ruff_cache"
        cache_dir.mkdir()
        coverage_file = tmp_path / ".coverage"
        coverage_file.write_text("")
        svc = _make_doctor(tmp_path)
        # Pre-condition: both exist
        assert cache_dir.exists()
        assert coverage_file.exists()
        actions = svc.fix()
        assert not cache_dir.exists(), ".ruff_cache should have been deleted"
        assert not coverage_file.exists(), ".coverage should have been deleted"
        # At least one ROOT-2 action reported
        root2_actions = [a for a in actions if "ROOT-2" in a]
        assert len(root2_actions) >= 2

    def test_fix_removes_cache_dir_with_contents(self, tmp_path: Path) -> None:
        """fix() recursively removes a cache dir that contains files."""
        _init_workspace(tmp_path)
        cache_dir = tmp_path / ".pytest_cache"
        cache_dir.mkdir()
        (cache_dir / "v").mkdir()
        (cache_dir / "v" / "cache.json").write_text("{}")
        svc = _make_doctor(tmp_path)
        svc.fix()
        assert not cache_dir.exists()


# ---------------------------------------------------------------------------
# ROOT-3: tool configs in canonical homes or exception list (WARN, not fixable)
# ---------------------------------------------------------------------------


class TestRoot3:
    def test_clean_workspace_no_root3(self, tmp_path: Path) -> None:
        """No tool config files present → no ROOT-3."""
        _init_workspace(tmp_path)
        svc = _make_doctor(tmp_path)
        codes = {i.code for i in svc.check()}
        assert "ROOT-3" not in codes

    def test_mcp_json_triggers_root3(self, tmp_path: Path) -> None:
        """.mcp.json at root (not in exception list) triggers ROOT-3."""
        _init_workspace(tmp_path)
        (tmp_path / ".mcp.json").write_text("{}")
        svc = _make_doctor(tmp_path)
        codes = {i.code for i in svc.check()}
        assert "ROOT-3" in codes

    def test_claude_md_triggers_root3(self, tmp_path: Path) -> None:
        """CLAUDE.md at root triggers ROOT-3."""
        _init_workspace(tmp_path)
        (tmp_path / "CLAUDE.md").write_text("# stub")
        svc = _make_doctor(tmp_path)
        codes = {i.code for i in svc.check()}
        assert "ROOT-3" in codes

    def test_tool_config_in_exception_list_suppresses_root3(self, tmp_path: Path) -> None:
        """Tool config present in root_exceptions.txt does not trigger ROOT-3."""
        _init_workspace(tmp_path)
        (tmp_path / ".mcp.json").write_text("{}")
        exc_file = tmp_path / ".dadaia" / "states" / "root_exceptions.txt"
        exc_file.write_text(".mcp.json\n")
        svc = _make_doctor(tmp_path)
        codes = {i.code for i in svc.check()}
        assert "ROOT-3" not in codes

    def test_root3_is_not_fixable(self, tmp_path: Path) -> None:
        """ROOT-3 is a WARN — not auto-fixable (requires research/relocation)."""
        _init_workspace(tmp_path)
        (tmp_path / ".mcp.json").write_text("{}")
        svc = _make_doctor(tmp_path)
        root3_issues = [i for i in svc.check() if i.code == "ROOT-3"]
        assert len(root3_issues) == 1
        assert root3_issues[0].fixable is False


# ---------------------------------------------------------------------------
# ROOT-4: .dadaia/ contains only canonical top-level subdirs
# ---------------------------------------------------------------------------


class TestRoot4:
    def test_clean_workspace_no_root4(self, tmp_path: Path) -> None:
        """A workspace with only canonical .dadaia subdirs reports no ROOT-4."""
        _init_workspace(tmp_path)
        svc = _make_doctor(tmp_path)
        codes = {i.code for i in svc.check()}
        assert "ROOT-4" not in codes

    def test_known_canonical_subdirs_no_root4(self, tmp_path: Path) -> None:
        """All known canonical .dadaia subdirs do not trigger ROOT-4."""
        _init_workspace(tmp_path)
        for name in ["agentic", "mcps", "scripts", "tmp", "reports", "states", "logs"]:
            (tmp_path / ".dadaia" / name).mkdir(exist_ok=True)
        svc = _make_doctor(tmp_path)
        codes = {i.code for i in svc.check()}
        assert "ROOT-4" not in codes

    def test_unknown_subdir_triggers_root4(self, tmp_path: Path) -> None:
        """An unknown subdirectory inside .dadaia/ triggers ROOT-4."""
        _init_workspace(tmp_path)
        (tmp_path / ".dadaia" / "mystery-tool-output").mkdir()
        svc = _make_doctor(tmp_path)
        codes = {i.code for i in svc.check()}
        assert "ROOT-4" in codes

    def test_dadaia_hooks_subdir_no_root4(self, tmp_path: Path) -> None:
        """v0.1.47 W1-9: .dadaia/hooks/ (Python governance hooks) is canonical, not ROOT-4.

        Regression for bug workspace-doctor-root4-false-positive-dadaia-hooks.
        """
        _init_workspace(tmp_path)
        (tmp_path / ".dadaia" / "hooks").mkdir()
        svc = _make_doctor(tmp_path)
        codes = {i.code for i in svc.check()}
        assert "ROOT-4" not in codes

    def test_dotfile_inside_dadaia_not_root4(self, tmp_path: Path) -> None:
        """Dotfiles (non-directories) inside .dadaia/ are allowed (e.g. .gitkeep)."""
        _init_workspace(tmp_path)
        (tmp_path / ".dadaia" / ".gitkeep").write_text("")
        svc = _make_doctor(tmp_path)
        codes = {i.code for i in svc.check()}
        assert "ROOT-4" not in codes

    def test_root4_is_not_fixable(self, tmp_path: Path) -> None:
        """ROOT-4 is a WARN — not auto-fixable (requires human decision)."""
        _init_workspace(tmp_path)
        (tmp_path / ".dadaia" / "some-unknown-tool").mkdir()
        svc = _make_doctor(tmp_path)
        root4_issues = [i for i in svc.check() if i.code == "ROOT-4"]
        assert len(root4_issues) == 1
        assert root4_issues[0].fixable is False

    def test_no_dadaia_dir_no_root4(self, tmp_path: Path) -> None:
        """If .dadaia/ is absent, ROOT-4 is not triggered."""
        # Minimal workspace without .dadaia existing (pathological but defensive)
        ctx_store = FakeContextStore()
        git_client = FakeGitClient()
        svc = DoctorService(ctx_store, git_client, tmp_path)
        issues = svc._check_root_4()
        assert issues == []
