"""``public install`` deletes only what its install ledger recorded.

Intent: CONTRACT — sa-public-install-unlinks-operator-files-outside-its-ledger#D1,
sa-public-install-unlinks-operator-files-outside-its-ledger#D2,
#D6. Size: MEDIUM (integration: a real full-roster install into a tmp_path workspace).
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
#: The only functions of the install modules allowed to delete: the ledger prune (and
#: its empty-dir tidy-up) and the stage rebuild of .dadaia/agentic.
_ALLOWED = frozenset(
    {
        "public_assets.py:_reconcile_install_ledger",
        "public_assets.py:_prune_empty_dirs",
        "public_assets.py:stage",
    }
)


def test_operator_files_outside_the_ledger_survive_public_install(tmp_path: Path) -> None:
    """sa-public-install-unlinks-operator-files-outside-its-ledger#D1, #D2: each operator
    file is byte-identical after a second install and no output line names it."""
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


def test_codex_install_projects_only_the_native_rules_and_a_skills_free_config(
    tmp_path: Path,
) -> None:
    """Re-homed from the deleted legacy-cleanup test: Codex gets its native ``.rules``
    policy only, and its config carries neither a ``[skills]`` table nor
    ``approved_commands``."""
    ws = tmp_path / "ws"
    register_all(ws)
    FileSystemPublicAssetManager().install(ws)

    assert sorted(p.name for p in (ws / ".codex" / "rules").iterdir()) == [
        "dadaia-command-policy.rules"
    ]
    config = (ws / ".codex" / "config.toml").read_text(encoding="utf-8")
    assert "[skills]" not in config
    assert "approved_commands" not in config


def test_the_install_modules_delete_only_through_the_ledger_prune() -> None:
    """sa-public-install-unlinks-operator-files-outside-its-ledger#D6."""
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
