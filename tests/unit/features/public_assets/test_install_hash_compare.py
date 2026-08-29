"""Unit tests for T-PROP-01: install hash-compare overwrite — the guardrail pair's
OWN bespoke path.

K3 (v0.5.1): ``FileSystemPublicAssetManager._copy_file``/``_write_generated`` are
retired — every projected file except the consumer-repo guardrail fan-out now flows
through the ``ProjectionRule``/``install_rules`` seam
(``tests/unit/infrastructure/test_projection.py`` covers ITS T-PROP-01-equivalent
skip/overwrite/force contract for the ``bytes`` compare semantic). The guardrail pair
stays a bespoke, N-target, provenance-gated writer (``public_assets.py``'s own
docstring), so its identical 3-behavior hash-compare contract is pinned here,
standalone.

1. Overwrites a projected file when sha256(staged) != sha256(projected)
   (update propagates without --force).
2. Is a no-op when sha256(staged) == sha256(projected) (identical → skip).
3. --force clobbers regardless of hash match (existing semantics preserved).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.infrastructure.workspace_guardrail import (
    _install_workspace_root_guardrail_pair,
)


def _run_install(
    tmp_path: Path,
    *,
    src_content: bytes,
    dst_content: bytes,
    force: bool,
) -> tuple[Path, list[str], float]:
    installed: list[str] = []
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


def test_propagate_without_force_on_hash_mismatch(tmp_path: Path) -> None:
    """T-PROP-01 AC-1: staged content differs from projected → overwrite without --force."""
    dst, installed, _mtime_before = _run_install(
        tmp_path,
        src_content=b"# New content\n",
        dst_content=b"# Old content\n",
        force=False,
    )
    assert dst.read_bytes() == b"# New content\n"
    assert any("[ok]" in line for line in installed), f"Expected [ok] in {installed}"
    assert not any("[skip]" in line for line in installed), f"Got unexpected [skip] in {installed}"


def test_noop_when_hash_matches(tmp_path: Path) -> None:
    """T-PROP-01 AC-2: staged == projected hash → no-op (skip), dst unchanged."""
    content = b"# Identical content\n"
    dst, installed, mtime_before = _run_install(
        tmp_path, src_content=content, dst_content=content, force=False
    )
    assert dst.read_bytes() == content
    assert dst.stat().st_mtime == mtime_before, "mtime changed — unexpected write on a no-op"
    # The guardrail pair also writes a sibling CLAUDE.md stub in the same call — only
    # inspect the report line for the destination file this test actually targets.
    relevant = [ln for ln in installed if str(dst) in ln]
    assert any("[skip]" in line for line in relevant), f"Expected [skip] in {relevant}"
    assert not any("[ok]" in line for line in relevant), f"Got unexpected [ok] in {relevant}"


@pytest.mark.parametrize("identical", [False, True], ids=["locally-modified", "identical"])
def test_force_clobbers_regardless_of_hash_match(identical: bool, tmp_path: Path) -> None:
    """T-PROP-01 AC-3/AC-3b: --force clobbers whether content differs or matches (no
    short-circuit on identical content)."""
    src_content = b"# Staged content\n"
    dst_content = src_content if identical else b"# Locally modified content\n"

    dst, installed, _mtime_before = _run_install(
        tmp_path, src_content=src_content, dst_content=dst_content, force=True
    )
    assert dst.read_bytes() == src_content
    assert any("[ok]" in line for line in installed), f"Expected [ok] in {installed}"
