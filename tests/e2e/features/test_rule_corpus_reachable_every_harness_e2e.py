"""The by-name rule corpus must exist for EVERY harness, not only Claude.

Bug ``r11-codex-only-reconcile-rule-corpus-missing`` (consumer-side validator, R11/F-02).
A ``--harness codex`` workspace gets no ``.claude/rules/`` at all, yet the ``AGENTS.md``
the Codex agent reads cites five rules by name and tells it to open
``.claude/rules/<name>.md``. Every one of those citations is dead: the agent is pointed at
law it cannot reach, and gets no error either.

The root ``AGENTS.md`` states the contract itself — "This corpus is reachable from EVERY
harness — Claude Code loads it natively, and Codex (and any other harness) can read it
directly with a file read." The corpus is therefore harness-independent, exactly like the
git-chokepoint scripts that every Layer-1 target already installs.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from dadaia_workspace.features.workspace.service import WorkspaceService
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
from dadaia_workspace.infrastructure.python_env import VenvPythonEnvironmentManager

pytestmark = pytest.mark.e2e

_CITATION = re.compile(r"`([a-z][a-z0-9-]+)`\s+rule\b")


def _init(root: Path, harness: str) -> None:
    WorkspaceService(
        public_assets=FileSystemPublicAssetManager(),
        python_env=VenvPythonEnvironmentManager(),
    ).init(root, harnesses=(harness,))


@pytest.mark.parametrize("harness", ["claude", "codex", "pi", "kimi-code"])
def test_every_rule_cited_by_agents_md_is_on_disk(tmp_path: Path, harness: str) -> None:
    root = tmp_path / harness
    _init(root, harness)

    agents_md = root / "AGENTS.md"
    assert agents_md.is_file(), f"{harness}: no root AGENTS.md was projected"
    cited = sorted(set(_CITATION.findall(agents_md.read_text(encoding="utf-8"))))
    assert cited, f"{harness}: AGENTS.md cites no rules — the fixture would prove nothing"

    rules_dir = root / ".claude" / "rules"
    available = {p.stem for p in rules_dir.glob("*.md")} if rules_dir.is_dir() else set()
    missing = [name for name in cited if name not in available]
    assert not missing, (
        f"{harness}: AGENTS.md sends the agent to .claude/rules/<name>.md for {missing}, "
        "and those files do not exist. The agent follows the citation, finds nothing, and "
        "is told nothing."
    )
