"""T-13: SHA null-regression test.

AC C7 (ADR-CX-004): Adding a Codex-only adapter must leave .claude/**
byte-identical before and after the install call.

D-CX-6 doctor leak/drift/missing coverage lives in
``test_public_assets_doctor.py`` (``TestDcx6CodexRuntimeAdapters``) — this file's
sole survivor is the SHA null-regression proof, the only tree-hash isolation test
in the suite.
"""

from __future__ import annotations

import hashlib
import pathlib

from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager

_ADAPTER_CONTENT = "# Test adapter SKILL.md\n## Purpose\nCodex-only test adapter.\n"
_EXISTING_CLAUDE_SKILL_CONTENT = "# Existing shared skill\n## Purpose\nAlready installed.\n"


def _sha_tree(root: pathlib.Path) -> dict[str, str]:
    """Compute SHA-256 for every file under *root*, keyed by path relative to *root*."""
    result: dict[str, str] = {}
    if not root.exists():
        return result
    for f in sorted(root.rglob("*")):
        if f.is_file():
            result[str(f.relative_to(root))] = hashlib.sha256(f.read_bytes()).hexdigest()
    return result


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
    (existing_skill_dir / "SKILL.md").write_text(_EXISTING_CLAUDE_SKILL_CONTENT, encoding="utf-8")

    # Empty .codex/ dir
    (workspace_root / ".codex").mkdir(parents=True)

    return public_dir, workspace_root


def _make_manager(public_dir: pathlib.Path) -> FileSystemPublicAssetManager:
    """Instantiate a manager with *public_dir* patched as the asset source."""
    manager = FileSystemPublicAssetManager()
    manager._public_dir = public_dir
    return manager


def test_codex_null_regression_claude_unchanged_and_adapter_installed(
    tmp_path: pathlib.Path,
) -> None:
    """SHA tree of .claude/ is byte-identical before and after
    _install_codex_runtime_adapters, and the adapter itself lands under .codex/."""
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

    installed_path = workspace_root / ".codex" / "skills" / "test-adapter" / "SKILL.md"
    assert installed_path.exists(), (
        f".codex/skills/test-adapter/SKILL.md was not created. installed={installed!r}"
    )
    assert installed_path.read_text(encoding="utf-8") == _ADAPTER_CONTENT
