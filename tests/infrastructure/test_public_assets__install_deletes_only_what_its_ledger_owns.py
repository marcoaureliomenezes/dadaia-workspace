"""``public install`` deletes only what its install ledger recorded.

sa-public-install-unlinks-operator-files-outside-its-ledger#D1,
sa-public-install-unlinks-operator-files-outside-its-ledger#D2,
sa-public-install-unlinks-operator-files-outside-its-ledger#D6.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
from tests.helpers.harness_profile import register_all

pytestmark = pytest.mark.slow(reason="full public install into a tmp workspace")

_OPERATOR_FILES = {
    ".codex/agents/my-agent.toml": b'name = "my-agent"\n',
    ".claude/rules/release-governance.md": b"# my own rule\n",
    ".claude/workflows/deploy.workflow.md": b"# my deploy\n",
    ".codex/workflows/hotfix-release.workflow.md": b"# my hotfix\n",
}
_INFRA = Path(__file__).resolve().parents[2] / "dadaia_workspace" / "infrastructure"
_DELETERS = frozenset({"unlink", "rmtree", "remove", "rmdir"})
_ALLOWED = frozenset(
    {
        "public_assets.py:_reconcile_install_ledger",
        "public_assets.py:_prune_empty_dirs",
        "public_assets.py:stage",
    }
)


def test_operator_files_outside_the_ledger_survive_public_install(tmp_path: Path) -> None:
    """#D1, #D2 — operator files are byte-identical and unnamed after a re-install; Codex gets
    only its native `.rules` and a config with no `[skills]` or `approved_commands`."""
    ws = tmp_path / "ws"
    register_all(ws)
    manager = FileSystemPublicAssetManager()
    manager.install(ws)
    for rel, body in _OPERATOR_FILES.items():
        (ws / rel).parent.mkdir(parents=True, exist_ok=True)
        (ws / rel).write_bytes(body)

    output = manager.install(ws, force=True)

    for rel, body in _OPERATOR_FILES.items():
        assert (ws / rel).read_bytes() == body, rel
        assert not [line for line in output if rel in line], rel
    rules = sorted(p.name for p in (ws / ".codex" / "rules").iterdir())
    assert rules == ["dadaia-command-policy.rules"]
    config = (ws / ".codex" / "config.toml").read_text(encoding="utf-8")
    assert "[skills]" not in config and "approved_commands" not in config


def test_the_install_modules_delete_only_through_the_ledger_prune() -> None:
    """#D6 — only the ledger prune, its empty-dir tidy-up and `stage` call a deleter."""
    found: set[str] = set()
    for name in ("projection_rules.py", "install_helpers.py", "public_assets.py"):
        tree = ast.parse((_INFRA / name).read_text(encoding="utf-8"))
        for fn in ast.walk(tree):
            if not isinstance(fn, ast.FunctionDef | ast.AsyncFunctionDef):
                continue
            for node in ast.walk(fn):
                if (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr in _DELETERS
                ):
                    found.add(f"{name}:{fn.name}")
    assert found <= _ALLOWED, sorted(found - _ALLOWED)
