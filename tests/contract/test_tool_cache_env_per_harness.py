"""Every harness either carries the absolute tool-cache env or declares the gap.

Intent: CONTRACT — sa-tool-caches-land-outside-the-cache-zone#B40-2. Size: SMALL.
"""

from __future__ import annotations

import json
from pathlib import Path

from dadaia_workspace.core.harness_registry import L1_ENTRY_HARNESSES
from dadaia_workspace.infrastructure.runtime_config import codex_config, merge_claude_settings

_REGISTRY = Path(__file__).resolve().parents[2] / "dadaia_workspace/public/entities/registry.json"


def test_each_harness_carries_the_cache_env_or_declares_the_gap(tmp_path: Path) -> None:
    """sa-tool-caches-land-outside-the-cache-zone#B40-2: Claude and Codex export the same
    absolute env; kimi-code, cursor, devin and copilot declare a gap — never silence."""
    ws = Path("/ws")
    ruff, mypy = str(ws / ".dadaia/tmp/ruff-cache"), str(ws / ".dadaia/tmp/mypy-cache")
    assert merge_claude_settings(None, ws)["env"] == {
        "MYPY_CACHE_DIR": mypy,
        "RUFF_CACHE_DIR": ruff,
    }
    codex = codex_config(tmp_path / "agentic", ws)
    assert (
        f"[shell_environment_policy.set]\nMYPY_CACHE_DIR = '{mypy}'\nRUFF_CACHE_DIR = '{ruff}'\n"
        in codex
    )
    behaviors = json.loads(_REGISTRY.read_text(encoding="utf-8"))["behaviors"]
    (answer,) = [b["implementations"] for b in behaviors if b["id"] == "tool-cache-env"]
    assert sorted(answer) == sorted(L1_ENTRY_HARNESSES)
    gaps = sorted(h for h, text in answer.items() if text.startswith("gap:"))
    assert gaps == ["copilot", "cursor", "devin", "kimi-code"]
