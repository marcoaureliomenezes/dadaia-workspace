"""Unit tests for T-PROP-01: install hash-compare overwrite.

Verifies that `dadaia public install` (via FileSystemPublicAssetManager.install /
_copy_file / _write_generated):

1. Overwrites a projected file when sha256(staged) != sha256(projected)
   (update propagates without --force).
2. Is a no-op when sha256(staged) == sha256(projected) (identical → skip).
3. --force clobbers regardless of hash match (existing semantics preserved).

All three tests operate on the internal _copy_file / _write_generated helpers
to keep them pure-unit (no CLI process boundary, no real staging step).
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


@pytest.fixture()
def manager() -> FileSystemPublicAssetManager:
    return FileSystemPublicAssetManager()


# ---------------------------------------------------------------------------
# _copy_file tests
# ---------------------------------------------------------------------------


class TestCopyFileHashCompare:
    """Tests for _copy_file — the binary-source write path."""

    def test_update_propagates_without_force(
        self, tmp_path: Path, manager: FileSystemPublicAssetManager
    ) -> None:
        """T-PROP-01 AC-1: staged content differs from projected → overwrite without --force."""
        src = tmp_path / "src" / "asset.md"
        dst = tmp_path / "dst" / "asset.md"

        _write(src, b"# Original content\n")
        _write(dst, b"# Old projected content\n")

        installed: list[str] = []
        manager._copy_file(src, dst, force=False, installed=installed)

        # File must have been updated
        assert dst.read_bytes() == src.read_bytes()
        # Report must contain [ok], not [skip]
        assert any("[ok]" in line for line in installed), f"Expected [ok] in {installed}"
        assert not any("[skip]" in line for line in installed), (
            f"Got unexpected [skip] in {installed}"
        )

    def test_noop_when_hashes_match(
        self, tmp_path: Path, manager: FileSystemPublicAssetManager
    ) -> None:
        """T-PROP-01 AC-2: staged == projected hash → no-op (skip), dst unchanged."""
        content = b"# Identical content\n"
        src = tmp_path / "src" / "asset.md"
        dst = tmp_path / "dst" / "asset.md"

        _write(src, content)
        _write(dst, content)

        # Record the mtime before to verify no write occurred
        mtime_before = dst.stat().st_mtime

        installed: list[str] = []
        manager._copy_file(src, dst, force=False, installed=installed)

        # File must not have been rewritten
        assert dst.read_bytes() == content
        assert dst.stat().st_mtime == mtime_before, "mtime changed — unexpected write"
        # Report must contain [skip]
        assert any("[skip]" in line for line in installed), f"Expected [skip] in {installed}"
        assert not any("[ok]" in line for line in installed), f"Got unexpected [ok] in {installed}"

    def test_force_still_clobbers_locally_modified(
        self, tmp_path: Path, manager: FileSystemPublicAssetManager
    ) -> None:
        """T-PROP-01 AC-3: --force clobbers even when projected content differs from staged."""
        src = tmp_path / "src" / "asset.md"
        dst = tmp_path / "dst" / "asset.md"

        _write(src, b"# Staged content\n")
        # dst has a locally-modified version that differs from src
        _write(dst, b"# Locally modified - should be overwritten by --force\n")

        installed: list[str] = []
        manager._copy_file(src, dst, force=True, installed=installed)

        assert dst.read_bytes() == src.read_bytes()
        assert any("[ok]" in line for line in installed), f"Expected [ok] in {installed}"

    def test_force_clobbers_even_when_identical(
        self, tmp_path: Path, manager: FileSystemPublicAssetManager
    ) -> None:
        """T-PROP-01 AC-3b: --force clobbers even identical content (no short-circuit)."""
        content = b"# Same content\n"
        src = tmp_path / "src" / "asset.md"
        dst = tmp_path / "dst" / "asset.md"

        _write(src, content)
        _write(dst, content)

        installed: list[str] = []
        manager._copy_file(src, dst, force=True, installed=installed)

        assert dst.read_bytes() == content
        assert any("[ok]" in line for line in installed), f"Expected [ok] in {installed}"


# ---------------------------------------------------------------------------
# _write_generated tests (generated-content write path)
# ---------------------------------------------------------------------------


class TestWriteGeneratedHashCompare:
    """Tests for _write_generated — the generated-content write path."""

    def test_update_propagates_without_force(
        self, tmp_path: Path, manager: FileSystemPublicAssetManager
    ) -> None:
        """T-PROP-01: generated content differs from projected → overwrite without --force."""
        dst = tmp_path / "dst" / "generated.json"
        _write(dst, b'{"old": true}\n')

        new_content = '{"new": true}\n'
        installed: list[str] = []
        manager._write_generated(dst, new_content, force=False, installed=installed)

        assert dst.read_text(encoding="utf-8") == new_content
        assert any("[ok]" in line for line in installed)
        assert not any("[skip]" in line for line in installed)

    def test_noop_when_content_matches(
        self, tmp_path: Path, manager: FileSystemPublicAssetManager
    ) -> None:
        """T-PROP-01: generated content matches projected → skip, dst unchanged."""
        content = '{"same": true}\n'
        dst = tmp_path / "dst" / "generated.json"
        _write(dst, content.encode())

        mtime_before = dst.stat().st_mtime
        installed: list[str] = []
        manager._write_generated(dst, content, force=False, installed=installed)

        assert dst.read_text(encoding="utf-8") == content
        assert dst.stat().st_mtime == mtime_before
        assert any("[skip]" in line for line in installed)
        assert not any("[ok]" in line for line in installed)

    def test_force_clobbers_locally_modified(
        self, tmp_path: Path, manager: FileSystemPublicAssetManager
    ) -> None:
        """T-PROP-01: --force clobbers even when generated and projected content differ."""
        dst = tmp_path / "dst" / "generated.json"
        _write(dst, b'{"local_mod": true}\n')

        new_content = '{"staged": true}\n'
        installed: list[str] = []
        manager._write_generated(dst, new_content, force=True, installed=installed)

        assert dst.read_text(encoding="utf-8") == new_content
        assert any("[ok]" in line for line in installed)


# ---------------------------------------------------------------------------
# guardrail pair helpers (AGENTS.md / CLAUDE.md paths)
# ---------------------------------------------------------------------------


class TestGuardrailPairHashCompare:
    """Tests for the guardrail pair write helpers (_install_workspace_guardrail_pair
    and _install_workspace_root_guardrail_pair).
    """

    def test_guardrail_agents_md_updates_without_force(self, tmp_path: Path) -> None:
        """AGENTS.md is overwritten when source SHA != projected SHA (no --force needed)."""
        from dadaia_workspace.infrastructure.public_assets import (
            _install_workspace_root_guardrail_pair,
        )

        workspace = tmp_path / "ws"
        workspace.mkdir()
        source = workspace / "source_AGENTS.md"
        source.write_bytes(b"# New AGENTS content\n")

        agents_dst = workspace / "AGENTS.md"
        agents_dst.write_bytes(b"# Old AGENTS content\n")

        installed: list[str] = []
        _install_workspace_root_guardrail_pair(
            source=source,
            workspace_root=workspace,
            force=False,
            installed=installed,
        )

        assert agents_dst.read_bytes() == source.read_bytes()
        assert any("[ok]" in line for line in installed)

    def test_guardrail_agents_md_noop_when_identical(self, tmp_path: Path) -> None:
        """AGENTS.md is a no-op when source SHA == projected SHA."""
        from dadaia_workspace.infrastructure.public_assets import (
            _install_workspace_root_guardrail_pair,
        )

        workspace = tmp_path / "ws"
        workspace.mkdir()
        content = b"# Same AGENTS content\n"
        source = workspace / "source_AGENTS.md"
        source.write_bytes(content)

        agents_dst = workspace / "AGENTS.md"
        agents_dst.write_bytes(content)

        mtime_before = agents_dst.stat().st_mtime
        installed: list[str] = []
        _install_workspace_root_guardrail_pair(
            source=source,
            workspace_root=workspace,
            force=False,
            installed=installed,
        )

        assert agents_dst.stat().st_mtime == mtime_before
        assert any("[skip]" in line for line in installed)
