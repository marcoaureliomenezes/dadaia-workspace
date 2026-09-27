"""Every public install is whole: no scope flag exists, and the staged set is the
public walk's set.

Intent: CONTRACT — sa-scoped-public-install-prunes-the-gate-wiring (WP-08)

L1: `public install --only <family>` is refused by the CLI (exit 2, unknown option).
L2: `stage` never copies a file the one public walk ignores (`__pycache__`).
"""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from dadaia_workspace.cli.main import app
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager


def test_public_install_has_no_only_option() -> None:
    """L1."""
    result = CliRunner().invoke(app, ["public", "install", "--only", "skills"])
    assert result.exit_code == 2


def test_stage_copies_no_bytecode_cache(tmp_path: Path) -> None:
    """L2."""
    public_dir = tmp_path / "public"
    cache = public_dir / "skills" / "s" / "__pycache__"
    cache.mkdir(parents=True)
    (public_dir / "skills" / "s" / "SKILL.md").write_text("# s\n", encoding="utf-8")
    (cache / "m.cpython-312.pyc").write_bytes(b"\x00")
    manager = FileSystemPublicAssetManager()
    manager._public_dir = public_dir  # noqa: SLF001
    workspace = tmp_path / "ws"
    workspace.mkdir()

    manager.stage(workspace)

    agentic = workspace / ".dadaia" / "agentic"
    assert (agentic / "skills" / "s" / "SKILL.md").is_file()
    assert not (agentic / "skills" / "s" / "__pycache__").exists()
