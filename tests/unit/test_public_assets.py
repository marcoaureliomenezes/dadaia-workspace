"""Pure unit tests for public asset privacy checks."""

from __future__ import annotations

from pathlib import Path

from dadaia_workspace.infrastructure.public_assets import (
    _PUBLIC_PRIVACY_DENYLIST,
    FileSystemPublicAssetManager,
)


def test_public_privacy_gate_flags_text_denylist(tmp_path: Path) -> None:
    public_dir = tmp_path / "public"
    data_dir = public_dir / "data"
    data_dir.mkdir(parents=True)
    first_term, _ = _PUBLIC_PRIVACY_DENYLIST[0]
    (data_dir / "AGENTS.md").write_text(f"Private endpoint: {first_term}\n", encoding="utf-8")

    manager = FileSystemPublicAssetManager()
    manager._public_dir = public_dir  # noqa: SLF001

    report = manager._check_public_privacy()  # noqa: SLF001

    assert any(line.startswith("[error] public-privacy:") for line in report)
    assert any(first_term in line.lower() for line in report)


def test_public_privacy_gate_ignores_bytecode_cache(tmp_path: Path) -> None:
    public_dir = tmp_path / "public"
    cache_dir = public_dir / "skills" / "sample" / "__pycache__"
    cache_dir.mkdir(parents=True)
    first_term, _ = _PUBLIC_PRIVACY_DENYLIST[0]
    (cache_dir / "leak.pyc").write_bytes(first_term.encode())
    (public_dir / "data").mkdir()
    (public_dir / "data" / "AGENTS.md").write_text("# clean\n", encoding="utf-8")

    manager = FileSystemPublicAssetManager()
    manager._public_dir = public_dir  # noqa: SLF001

    assert manager._check_public_privacy() == ["[ok] public-privacy"]  # noqa: SLF001
