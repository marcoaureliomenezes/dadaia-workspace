"""Unit tests for T-PROP-01: install hash-compare overwrite.

Verifies that `dadaia public install` (via FileSystemPublicAssetManager._copy_file /
_write_generated, and the guardrail-pair root installer) applies the SAME 3-behavior
contract across every write class (binary-source assets, generated content, and the
AGENTS.md/CLAUDE.md guardrail pair):

1. Overwrites a projected file when sha256(staged) != sha256(projected)
   (update propagates without --force) — a real operator pain (persona updates
   needed --force before this fix) and the regression lock here.
2. Is a no-op when sha256(staged) == sha256(projected) (identical → skip).
3. --force clobbers regardless of hash match (existing semantics preserved).

Merged across the 3 write classes into one parametrized test per behavior, in place
of 3 near-identical unit-test classes.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import pytest

from dadaia_workspace.infrastructure.public_assets import (  # type: ignore[attr-defined]
    FileSystemPublicAssetManager,
    _install_workspace_root_guardrail_pair,
)


def _write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


@pytest.fixture()
def manager() -> FileSystemPublicAssetManager:
    return FileSystemPublicAssetManager()


_WriteClass = Literal["copy_file", "write_generated", "guardrail"]


def _run_install(
    write_class: _WriteClass,
    manager: FileSystemPublicAssetManager,
    tmp_path: Path,
    *,
    src_content: bytes,
    dst_content: bytes,
    force: bool,
) -> tuple[Path, list[str], float]:
    installed: list[str] = []
    if write_class == "copy_file":
        src = tmp_path / "src" / "asset.md"
        dst = tmp_path / "dst" / "asset.md"
        _write(src, src_content)
        _write(dst, dst_content)
        mtime_before = dst.stat().st_mtime
        manager._copy_file(src, dst, force=force, installed=installed)
        return dst, installed, mtime_before
    if write_class == "write_generated":
        dst = tmp_path / "dst" / "generated.json"
        _write(dst, dst_content)
        mtime_before = dst.stat().st_mtime
        manager._write_generated(dst, src_content.decode(), force=force, installed=installed)
        return dst, installed, mtime_before
    # guardrail
    workspace = tmp_path / "ws"
    workspace.mkdir(exist_ok=True)
    source = workspace / "source_AGENTS.md"
    source.write_bytes(src_content)
    agents_dst = workspace / "AGENTS.md"
    agents_dst.write_bytes(dst_content)
    mtime_before = agents_dst.stat().st_mtime
    _install_workspace_root_guardrail_pair(
        source=source, workspace_root=workspace, force=force, installed=installed
    )
    return agents_dst, installed, mtime_before


@pytest.mark.parametrize("write_class", ["copy_file", "write_generated", "guardrail"])
def test_propagate_without_force_on_hash_mismatch(
    write_class: _WriteClass, manager: FileSystemPublicAssetManager, tmp_path: Path
) -> None:
    """T-PROP-01 AC-1: staged content differs from projected → overwrite without --force."""
    src_content = b'{"new": true}\n' if write_class == "write_generated" else b"# New content\n"
    dst_content = b'{"old": true}\n' if write_class == "write_generated" else b"# Old content\n"

    dst, installed, _mtime_before = _run_install(
        write_class,
        manager,
        tmp_path,
        src_content=src_content,
        dst_content=dst_content,
        force=False,
    )
    if write_class == "write_generated":
        assert dst.read_text(encoding="utf-8") == src_content.decode()
    else:
        assert dst.read_bytes() == src_content
    assert any("[ok]" in line for line in installed), f"Expected [ok] in {installed}"
    assert not any("[skip]" in line for line in installed), f"Got unexpected [skip] in {installed}"


@pytest.mark.parametrize("write_class", ["copy_file", "write_generated", "guardrail"])
def test_noop_when_hash_matches(
    write_class: _WriteClass, manager: FileSystemPublicAssetManager, tmp_path: Path
) -> None:
    """T-PROP-01 AC-2: staged == projected hash → no-op (skip), dst unchanged."""
    content = b'{"same": true}\n' if write_class == "write_generated" else b"# Identical content\n"

    dst, installed, mtime_before = _run_install(
        write_class, manager, tmp_path, src_content=content, dst_content=content, force=False
    )
    if write_class == "write_generated":
        assert dst.read_text(encoding="utf-8") == content.decode()
    else:
        assert dst.read_bytes() == content
    assert dst.stat().st_mtime == mtime_before, "mtime changed — unexpected write on a no-op"
    # The guardrail pair also writes a sibling CLAUDE.md stub in the same call — only
    # inspect the report line for the destination file this test actually targets.
    relevant = (
        [ln for ln in installed if str(dst) in ln] if write_class == "guardrail" else installed
    )
    assert any("[skip]" in line for line in relevant), f"Expected [skip] in {relevant}"
    assert not any("[ok]" in line for line in relevant), f"Got unexpected [ok] in {relevant}"


@pytest.mark.parametrize("write_class", ["copy_file", "write_generated", "guardrail"])
@pytest.mark.parametrize("identical", [False, True], ids=["locally-modified", "identical"])
def test_force_clobbers_regardless_of_hash_match(
    write_class: _WriteClass,
    identical: bool,
    manager: FileSystemPublicAssetManager,
    tmp_path: Path,
) -> None:
    """T-PROP-01 AC-3/AC-3b: --force clobbers whether content differs or matches (no
    short-circuit on identical content)."""
    src_content = (
        b'{"staged": true}\n' if write_class == "write_generated" else b"# Staged content\n"
    )
    dst_content = (
        src_content
        if identical
        else (
            b'{"local_mod": true}\n'
            if write_class == "write_generated"
            else b"# Locally modified content\n"
        )
    )

    dst, installed, _mtime_before = _run_install(
        write_class, manager, tmp_path, src_content=src_content, dst_content=dst_content, force=True
    )
    if write_class == "write_generated":
        assert dst.read_text(encoding="utf-8") == src_content.decode()
    else:
        assert dst.read_bytes() == src_content
    assert any("[ok]" in line for line in installed), f"Expected [ok] in {installed}"
