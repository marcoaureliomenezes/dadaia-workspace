"""Git-hook-level e2e for the backlog-consistency pre-commit chokepoint (T-25-06, §3.7.9).

Runs ``dadaia ci pre-commit-check`` through a REAL ``.git/hooks/pre-commit`` script in a
fixture git repo — NO harness hook environment. A planted violation for EACH of the four
backlog codes (BL-SCHEMA/BL-DUP/BL-CONFLICT/BL-STALE) BLOCKS the commit at the git-hook
layer; a clean tree PASSES. A doctor exit-code unit/integration test alone does not satisfy
this criterion (SPEC §3.7.9) — every code must be proven at the commit boundary.

The repo is laid out as a Spec Context repo under ``<workspace>/repos/<slug>`` so the
pre-commit-check resolves the workspace + the repo's ``specs/`` exactly as in production. No
lease exists, so the lease gate allows (zero-false-block) and the backlog doctor decides.

The four violations are exercised by a **single parameterized** test (one planter matrix) —
NOT four copy-pasted functions (SPEC §3.8 #8 — no copy-paste fan-out).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from collections.abc import Callable
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


# ── one parameterized matrix over the four BL-* codes at the git-hook layer ───────


def _plant_schema(repo: Path) -> None:
    # An UNRESOLVED subject (no such symbol) → BL-SCHEMA.
    (repo / "specs" / "backlog" / "bad.md").write_text(
        "---\nstatus: idea\nintents:\n"
        "  - subject: { kind: code, ref: dadaia_workspace/m.py#Ghost }\n"
        "    change: x\n---\n\n# bad\n",
        encoding="utf-8",
    )


def _plant_dup(repo: Path) -> None:
    # Same anchor-set + SAME change on two items → BL-DUP.
    _item(repo, "dup-a", "refactor Widget")
    _item(repo, "dup-b", "refactor Widget")


def _plant_conflict(repo: Path) -> None:
    # C->D then C->E on the SAME code anchor → BL-CONFLICT (the divergent twin).
    _item(repo, "twin-d", "change to D")
    _item(repo, "twin-e", "change to E")


def _plant_stale(repo: Path) -> None:
    # A slug listed in an archived release's consumed_backlog ledger that still exists in
    # specs/backlog/ → BL-STALE.
    _item(repo, "shipped-feature", "refactor Widget")
    archive = repo / "specs" / "_archive" / "v0.1.20"
    archive.mkdir(parents=True)
    (archive / "consumed_backlog.json").write_text(
        json.dumps(
            {"release": "v0.1.20", "consumed": [{"slug": "shipped-feature", "shipped_anchors": []}]}
        ),
        encoding="utf-8",
    )


@pytest.mark.parametrize(
    ("planter", "expected_code"),
    [
        (_plant_schema, "BL-SCHEMA"),
        (_plant_dup, "BL-DUP"),
        (_plant_conflict, "BL-CONFLICT"),
        (_plant_stale, "BL-STALE"),
    ],
)
def test_each_violation_blocks_commit(
    tmp_path: Path,
    planter: Callable[[Path], None],
    expected_code: str,
) -> None:
    workspace = tmp_path
    repo = _init_repo(workspace)
    planter(repo)
    result = _commit(repo, _env(workspace), f"plant-{expected_code}")
    out = result.stdout + result.stderr
    assert result.returncode != 0, out
    assert expected_code in out, out
