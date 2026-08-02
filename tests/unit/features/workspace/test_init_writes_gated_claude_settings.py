"""``init`` must never leave a Claude workspace with an ungated ``settings.json``.

Bug ``init-skip-assets-writes-gateless-claude-settings``: ``--skip-assets`` still wrote
``.claude/settings.json`` — but through a second, hand-rolled writer that only registered
the ctx-inject hook. The PreToolUse entrypoint carrying the root-whitelist policy, the
venv-guard and the SDD gate was absent, and init exited 0 saying nothing. A workspace that
looks scaffolded and enforces nothing is worse than one that is obviously empty.

The second half of the bug is that the two writers disagreed. The old code's comment
claimed "this is the same schema public_assets.py writes, so the two paths agree" — it was
not, and they did not. There is now exactly one writer, so agreement is structural rather
than asserted in a comment.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dadaia_workspace.features.workspace.service import WorkspaceService
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
from dadaia_workspace.infrastructure.python_env import VenvPythonEnvironmentManager


def _init(root: Path, *, skip_assets: bool) -> None:
    WorkspaceService(
        public_assets=FileSystemPublicAssetManager(),
        python_env=VenvPythonEnvironmentManager(),
    ).init(root, skip_assets=skip_assets, harnesses=("claude",))


@pytest.mark.parametrize("skip_assets", [False, True])
def test_init_wires_the_pretooluse_gate_regardless_of_skip_assets(
    tmp_path: Path, skip_assets: bool
) -> None:
    root = tmp_path / "ws"
    _init(root, skip_assets=skip_assets)

    settings = json.loads((root / ".claude" / "settings.json").read_text(encoding="utf-8"))
    hooks = settings["hooks"]

    assert "PreToolUse" in hooks, (
        "the PreToolUse entrypoint carries the root-whitelist policy, the venv-guard and "
        f"the SDD gate; skip_assets={skip_assets} must not silently drop it"
    )
    commands = [hook["command"] for entry in hooks["PreToolUse"] for hook in entry.get("hooks", [])]
    assert any("pre_gate" in command for command in commands), commands
    assert "UserPromptSubmit" in hooks, "context injection must still be wired"


def test_both_init_paths_write_byte_identical_settings(tmp_path: Path) -> None:
    """One file, one writer. Two writers that "agree" only in a comment is the bug."""
    with_assets, without_assets = tmp_path / "a", tmp_path / "b"
    _init(with_assets, skip_assets=False)
    _init(without_assets, skip_assets=True)

    a = (with_assets / ".claude" / "settings.json").read_text(encoding="utf-8")
    b = (without_assets / ".claude" / "settings.json").read_text(encoding="utf-8")
    assert a == b, "the two init paths must produce the same settings.json, byte for byte"
