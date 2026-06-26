"""Git-hook-level e2e for the backlog-consistency pre-commit chokepoint (T-25-06, §3.7.9).

Runs ``dadaia ci pre-commit-check`` through a REAL ``.git/hooks/pre-commit`` script in a
fixture git repo — NO harness hook environment. A planted divergent twin (and each planted
BL-SCHEMA/DUP/CONFLICT violation) BLOCKS the commit; a clean tree PASSES. A doctor exit-code
unit test alone does not satisfy this criterion (SPEC §3.7.9).

The repo is laid out as a Spec Context repo under ``<workspace>/repos/<slug>`` so the
pre-commit-check resolves the workspace + the repo's ``specs/`` exactly as in production. No
lease exists, so the lease gate allows (zero-false-block) and the backlog doctor decides.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.e2e

_SLUG = "demo-ctx"
_DEADLINE = 60.0

_SOURCE = "class Widget:\n    pass\n"

_CLEAN_INTENT = (
    "intents:\n  - subject: {{ kind: code, ref: dadaia_workspace/m.py#Widget }}\n"
    "    change: {change}\n"
)


def _init_repo(workspace: Path) -> Path:
    (workspace / ".dadaia" / "states").mkdir(parents=True, exist_ok=True)
    (workspace / ".dadaia" / "states" / "spec_contexts.json").write_text("{}", encoding="utf-8")
    repo = workspace / "repos" / _SLUG
    (repo / "specs" / "backlog").mkdir(parents=True)
    (repo / "specs" / "memory" / "product").mkdir(parents=True)
    (repo / "specs" / "memory" / "product" / "catalog.json").write_text(
        '{"features": []}', encoding="utf-8"
    )
    (repo / "dadaia_workspace").mkdir()
    (repo / "dadaia_workspace" / "m.py").write_text(_SOURCE, encoding="utf-8")

    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "t@e.st"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)

    hook = repo / ".git" / "hooks" / "pre-commit"
    hook.write_text(
        "#!/usr/bin/env bash\nset -e\n"
        f'exec "{sys.executable}" -m dadaia_workspace.cli.main ci pre-commit-check\n',
        encoding="utf-8",
    )
    hook.chmod(0o755)
    return repo


def _env(workspace: Path) -> dict[str, str]:
    env = dict(os.environ)
    for bad in ("CLAUDE_CODE_SESSION_ID", "CODEX_SESSION_ID", "DADAIA_MODE", "DADAIA_SESSION_ID"):
        env.pop(bad, None)
    env["WORKSPACE_ROOT"] = str(workspace)
    return env


def _item(repo: Path, slug: str, change: str) -> None:
    (repo / "specs" / "backlog" / f"{slug}.md").write_text(
        f"---\nstatus: idea\n{_CLEAN_INTENT.format(change=change)}---\n\n# {slug}\n",
        encoding="utf-8",
    )


def _commit(repo: Path, env: dict[str, str], message: str) -> subprocess.CompletedProcess[str]:
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True, env=env)
    return subprocess.run(
        ["git", "commit", "-m", message],
        cwd=repo,
        capture_output=True,
        text=True,
        env=env,
        timeout=_DEADLINE,
    )


def test_clean_backlog_commit_passes(tmp_path: Path) -> None:
    workspace = tmp_path
    repo = _init_repo(workspace)
    _item(repo, "clean-feature", "refactor Widget")
    result = _commit(repo, _env(workspace), "clean")
    assert result.returncode == 0, result.stdout + result.stderr


def test_divergent_twin_commit_blocks(tmp_path: Path) -> None:
    workspace = tmp_path
    repo = _init_repo(workspace)
    # C->D then C->E on the SAME code anchor (dadaia_workspace/m.py#Widget) → BL-CONFLICT.
    _item(repo, "twin-d", "change to D")
    _item(repo, "twin-e", "change to E")
    result = _commit(repo, _env(workspace), "divergent-twin")
    assert result.returncode != 0, result.stdout + result.stderr
    out = result.stdout + result.stderr
    assert "BL-CONFLICT" in out, out


def test_schema_violation_commit_blocks(tmp_path: Path) -> None:
    workspace = tmp_path
    repo = _init_repo(workspace)
    # An UNRESOLVED subject (no such symbol) → BL-SCHEMA.
    (repo / "specs" / "backlog" / "bad.md").write_text(
        "---\nstatus: idea\nintents:\n"
        "  - subject: { kind: code, ref: dadaia_workspace/m.py#Ghost }\n"
        "    change: x\n---\n\n# bad\n",
        encoding="utf-8",
    )
    result = _commit(repo, _env(workspace), "bad-schema")
    assert result.returncode != 0, result.stdout + result.stderr
    assert "BL-SCHEMA" in (result.stdout + result.stderr)
