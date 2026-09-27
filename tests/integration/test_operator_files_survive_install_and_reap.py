"""Operator files in harness dirs survive ``public install`` and ``doctor --fix``.

Intent: CONTRACT — sa-public-install-unlinks-operator-files-outside-its-ledger#D1..#D6,
sa-doctor-reaps-harness-owned-entries#H1..#H5 (AC1.2, ADR 0059). Size: MEDIUM
(integration: a real full-roster install into a tmp_path workspace, then the reaper).

Structural cause pinned: two authorities judged harness dirs besides the install
ledger — four named removers in ``install`` unlinked files the ledger never owned,
and the doctor's harness walk classified every non-ledger entry as slop and moved it.
The ledger is the one owner: it deletes only what it recorded; the rest is not ours.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.features.spec_context.doctor import DoctorService
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
from tests.fakes import FakeContextStore, FakeGitClient
from tests.helpers.harness_profile import register_all

pytestmark = pytest.mark.slow(reason="full public install into a tmp workspace")

_OPERATOR_FILES = {
    ".codex/agents/my-agent.toml": b'name = "my-agent"\n',
    ".claude/rules/release-governance.md": b"# my own rule\n",
    ".claude/workflows/deploy.workflow.md": b"# my deploy\n",
    ".claude/settings.local.json": b'{"permissions": {"allow": ["Bash(ls)"]}}\n',
    ".claude/skills/my-skill/SKILL.md": b"---\nname: my-skill\n---\n",
    ".agents/skills/my-shared/SKILL.md": b"---\nname: my-shared\n---\n",
}


def _workspace_with_operator_files(tmp_path: Path) -> tuple[Path, FileSystemPublicAssetManager]:
    ws = tmp_path / "ws"
    register_all(ws)
    manager = FileSystemPublicAssetManager()
    manager.install(ws)
    for rel, body in _OPERATOR_FILES.items():
        (ws / rel).parent.mkdir(parents=True, exist_ok=True)
        (ws / rel).write_bytes(body)
    return ws, manager


def _assert_intact(ws: Path) -> None:
    for rel, body in _OPERATOR_FILES.items():
        assert (ws / rel).read_bytes() == body, rel


def test_operator_files_in_harness_dirs_survive_public_install(tmp_path: Path) -> None:
    """sa-public-install-unlinks-operator-files-outside-its-ledger#D1..#D6."""
    ws, manager = _workspace_with_operator_files(tmp_path)
    manager.install(ws, force=True)
    _assert_intact(ws)
