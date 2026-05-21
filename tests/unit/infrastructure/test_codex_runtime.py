"""T-13: SHA null-regression and doctor leak detection tests.

AC C7 (ADR-CX-004): Adding a Codex-only adapter must leave .claude/** and
.opencode/** byte-identical before and after the install call.

AC C8 (D-CX-6): Doctor must detect missing, drift, and accidental leak of
Codex-only adapters into .claude/skills/ or .opencode/skills/.
"""

from __future__ import annotations

import hashlib
import pathlib

from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager

# ---------------------------------------------------------------------------
# SHA tree helper
# ---------------------------------------------------------------------------


def _sha_tree(root: pathlib.Path) -> dict[str, str]:
    """Compute SHA-256 for every file under *root*, keyed by path relative to *root*."""
    result: dict[str, str] = {}
    if not root.exists():
        return result
    for f in sorted(root.rglob("*")):
        if f.is_file():
            result[str(f.relative_to(root))] = hashlib.sha256(f.read_bytes()).hexdigest()
    return result


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_ADAPTER_CONTENT = "# Test adapter SKILL.md\n## Purpose\nCodex-only test adapter.\n"
_EXISTING_CLAUDE_SKILL_CONTENT = "# Existing shared skill\n## Purpose\nAlready installed.\n"


def _make_workspace(tmp_path: pathlib.Path) -> tuple[pathlib.Path, pathlib.Path]:
    """Create a minimal workspace and public dir under *tmp_path*.

    Returns (public_dir, workspace_root).

    Layout:
        tmp_path/
          public/
            runtime/
              codex/
                test-adapter/
                  SKILL.md   ← source adapter
          workspace/
            .claude/
              skills/
                existing-skill/
                  SKILL.md   ← must not be touched by codex install
            .opencode/       ← must not gain files
            .codex/          ← install target
    """
    public_dir = tmp_path / "public"
    codex_src = public_dir / "runtime" / "codex" / "test-adapter"
    codex_src.mkdir(parents=True)
    (codex_src / "SKILL.md").write_text(_ADAPTER_CONTENT, encoding="utf-8")

    workspace_root = tmp_path / "workspace"

    # Pre-existing .claude/skills/existing-skill/SKILL.md
    existing_skill_dir = workspace_root / ".claude" / "skills" / "existing-skill"
    existing_skill_dir.mkdir(parents=True)
    (existing_skill_dir / "SKILL.md").write_text(
        _EXISTING_CLAUDE_SKILL_CONTENT, encoding="utf-8"
    )

    # Empty .opencode/ dir
    (workspace_root / ".opencode").mkdir(parents=True)

    # Empty .codex/ dir
    (workspace_root / ".codex").mkdir(parents=True)

    return public_dir, workspace_root


def _make_manager(public_dir: pathlib.Path) -> FileSystemPublicAssetManager:
    """Instantiate a manager with *public_dir* patched as the asset source."""
    manager = FileSystemPublicAssetManager()
    manager._public_dir = public_dir
    return manager


# ---------------------------------------------------------------------------
# Group 1: SHA null-regression (AC C7, ADR-CX-004)
# ---------------------------------------------------------------------------


class TestShaNull:
    """SHA snapshot tests: codex install must not touch .claude/** or .opencode/**."""

    def test_codex_null_regression_claude_unchanged(self, tmp_path: pathlib.Path) -> None:
        """SHA tree of .claude/ is byte-identical before and after _install_codex_runtime_adapters."""
        public_dir, workspace_root = _make_workspace(tmp_path)
        manager = _make_manager(public_dir)

        sha_before = _sha_tree(workspace_root / ".claude")
        installed: list[str] = []
        manager._install_codex_runtime_adapters(workspace_root, force=False, installed=installed)
        sha_after = _sha_tree(workspace_root / ".claude")

        assert sha_before == sha_after, (
            ".claude/ was modified by _install_codex_runtime_adapters. "
            f"Before: {sha_before!r}  After: {sha_after!r}"
        )

    def test_codex_null_regression_opencode_unchanged(self, tmp_path: pathlib.Path) -> None:
        """SHA tree of .opencode/ is byte-identical before and after _install_codex_runtime_adapters."""
        public_dir, workspace_root = _make_workspace(tmp_path)
        manager = _make_manager(public_dir)

        sha_before = _sha_tree(workspace_root / ".opencode")
        installed: list[str] = []
        manager._install_codex_runtime_adapters(workspace_root, force=False, installed=installed)
        sha_after = _sha_tree(workspace_root / ".opencode")

        assert sha_before == sha_after, (
            ".opencode/ was modified by _install_codex_runtime_adapters. "
            f"Before: {sha_before!r}  After: {sha_after!r}"
        )

    def test_codex_runtime_adapter_installed(self, tmp_path: pathlib.Path) -> None:
        """After install, .codex/skills/test-adapter/SKILL.md exists with source content."""
        public_dir, workspace_root = _make_workspace(tmp_path)
        manager = _make_manager(public_dir)

        installed: list[str] = []
        manager._install_codex_runtime_adapters(workspace_root, force=False, installed=installed)

        installed_path = workspace_root / ".codex" / "skills" / "test-adapter" / "SKILL.md"
        assert installed_path.exists(), (
            f".codex/skills/test-adapter/SKILL.md was not created. installed={installed!r}"
        )
        assert installed_path.read_text(encoding="utf-8") == _ADAPTER_CONTENT


# ---------------------------------------------------------------------------
# Group 2: Doctor leak detection (AC C8, D-CX-6)
# ---------------------------------------------------------------------------


class TestDcx6DoctorLeakDetection:
    """Doctor must detect missing, drift, and accidental leaks for runtime/codex adapters."""

    def _make_single_adapter_workspace(
        self, tmp_path: pathlib.Path, slug: str = "my-adapter"
    ) -> tuple[pathlib.Path, pathlib.Path]:
        """Create workspace with a single adapter slug (different from _make_workspace's 'test-adapter')."""
        public_dir = tmp_path / "public"
        codex_src = public_dir / "runtime" / "codex" / slug
        codex_src.mkdir(parents=True)
        (codex_src / "SKILL.md").write_text(_ADAPTER_CONTENT, encoding="utf-8")

        workspace_root = tmp_path / "workspace"
        (workspace_root / ".codex").mkdir(parents=True)
        (workspace_root / ".claude").mkdir(parents=True)
        (workspace_root / ".opencode").mkdir(parents=True)

        return public_dir, workspace_root

    def test_dcx6_missing_reports_missing(self, tmp_path: pathlib.Path) -> None:
        """If adapter is not installed, doctor reports [missing] codex:skills/my-adapter/SKILL.md."""
        public_dir, workspace_root = self._make_single_adapter_workspace(tmp_path)
        manager = _make_manager(public_dir)

        # Adapter is NOT installed — .codex/skills/my-adapter/SKILL.md is absent.
        result = manager._dcx6_codex_runtime_adapters(workspace_root)

        missing_lines = [r for r in result if "[missing]" in r and "my-adapter" in r]
        assert missing_lines, (
            f"Expected a [missing] entry for my-adapter but got: {result!r}"
        )
        assert any("codex:skills/my-adapter/SKILL.md" in line for line in missing_lines), (
            f"[missing] line does not reference 'codex:skills/my-adapter/SKILL.md': {missing_lines!r}"
        )

    def test_dcx6_drift_reports_drift(self, tmp_path: pathlib.Path) -> None:
        """If installed adapter content differs from source, doctor reports [drift]."""
        public_dir, workspace_root = self._make_single_adapter_workspace(tmp_path)
        manager = _make_manager(public_dir)

        # Install the adapter correctly first.
        installed: list[str] = []
        manager._install_codex_runtime_adapters(workspace_root, force=True, installed=installed)

        # Corrupt the installed copy.
        installed_path = workspace_root / ".codex" / "skills" / "my-adapter" / "SKILL.md"
        installed_path.write_text("# MODIFIED — drift introduced\n", encoding="utf-8")

        result = manager._dcx6_codex_runtime_adapters(workspace_root)

        drift_lines = [r for r in result if "[drift]" in r and "my-adapter" in r]
        assert drift_lines, (
            f"Expected a [drift] entry for my-adapter but got: {result!r}"
        )
        assert any("codex:skills/my-adapter/SKILL.md" in line for line in drift_lines), (
            f"[drift] line does not reference 'codex:skills/my-adapter/SKILL.md': {drift_lines!r}"
        )

    def test_dcx6_ok_when_in_sync(self, tmp_path: pathlib.Path) -> None:
        """If adapter is installed correctly, doctor emits no [missing] or [drift] for it."""
        public_dir, workspace_root = self._make_single_adapter_workspace(tmp_path)
        manager = _make_manager(public_dir)

        # Install the adapter correctly.
        installed: list[str] = []
        manager._install_codex_runtime_adapters(workspace_root, force=True, installed=installed)

        result = manager._dcx6_codex_runtime_adapters(workspace_root)

        adapter_problems = [
            r
            for r in result
            if ("my-adapter" in r) and ("[missing]" in r or "[drift]" in r)
        ]
        assert not adapter_problems, (
            f"Expected no [missing]/[drift] for my-adapter but got: {adapter_problems!r}"
        )

    def test_dcx6_leak_to_claude_detected(self, tmp_path: pathlib.Path) -> None:
        """If adapter is also present in .claude/skills/, doctor reports [leak] claude:skills/."""
        public_dir, workspace_root = self._make_single_adapter_workspace(tmp_path)
        manager = _make_manager(public_dir)

        # Install adapter to .codex/skills/ (correct).
        installed: list[str] = []
        manager._install_codex_runtime_adapters(workspace_root, force=True, installed=installed)

        # Also copy it to .claude/skills/ (incorrect — leak).
        leak_dir = workspace_root / ".claude" / "skills" / "my-adapter"
        leak_dir.mkdir(parents=True)
        (leak_dir / "SKILL.md").write_text(_ADAPTER_CONTENT, encoding="utf-8")

        result = manager._dcx6_codex_runtime_adapters(workspace_root)

        leak_lines = [r for r in result if "[leak]" in r and "claude" in r and "my-adapter" in r]
        assert leak_lines, (
            f"Expected a [leak] entry for claude:skills/my-adapter but got: {result!r}"
        )
        assert any("claude:skills/my-adapter/SKILL.md" in line for line in leak_lines), (
            f"[leak] line does not reference 'claude:skills/my-adapter/SKILL.md': {leak_lines!r}"
        )

    def test_dcx6_leak_to_opencode_detected(self, tmp_path: pathlib.Path) -> None:
        """If adapter is also present in .opencode/skills/, doctor reports [leak] opencode:skills/."""
        public_dir, workspace_root = self._make_single_adapter_workspace(tmp_path)
        manager = _make_manager(public_dir)

        # Install adapter to .codex/skills/ (correct).
        installed: list[str] = []
        manager._install_codex_runtime_adapters(workspace_root, force=True, installed=installed)

        # Also copy it to .opencode/skills/ (incorrect — leak).
        leak_dir = workspace_root / ".opencode" / "skills" / "my-adapter"
        leak_dir.mkdir(parents=True)
        (leak_dir / "SKILL.md").write_text(_ADAPTER_CONTENT, encoding="utf-8")

        result = manager._dcx6_codex_runtime_adapters(workspace_root)

        leak_lines = [
            r for r in result if "[leak]" in r and "opencode" in r and "my-adapter" in r
        ]
        assert leak_lines, (
            f"Expected a [leak] entry for opencode:skills/my-adapter but got: {result!r}"
        )
        assert any("opencode:skills/my-adapter/SKILL.md" in line for line in leak_lines), (
            f"[leak] line does not reference 'opencode:skills/my-adapter/SKILL.md': {leak_lines!r}"
        )
