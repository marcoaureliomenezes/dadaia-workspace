"""Intent: CONTRACT — pre-push-gate-never-runs-under-core-hookspath: the real `ci
install-hook` + a real `git push` to a local bare remote. The planted-term refuse ->
amend -> push journey is the refusal harness Case `denylisted`
(test_refusal_fix_lines_clear_their_refusal.py); the refusal message shape (A5.1-A5.3,
masking) is tests/unit/features/chokepoints/test_push_denylist_scan.py.
`DADAIA_BIN` is stubbed to skip only `ci preflight`, which refuses outside the source repo.
Size: LARGE — real git hooks.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.e2e

_SLUG = "denylist-journey"
_BRANCH = "feature/0.0.1"
_EXIT_DEADLINE = 30.0
_PLANTED_TERM = "zz-fake-context-name"  # synthetic — never a real term (TASKS standing rule)


def _git(args: list[str], cwd: Path, env: dict[str, str] | None = None) -> None:
    subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True, env=env)


def _init_repo_and_remote(workspace: Path, slug: str) -> tuple[Path, Path]:
    """A throwaway working repo on the v2 pushable branch plus a local bare remote (no
    network)."""
    bare = workspace / "remote.git"
    bare.mkdir(parents=True)
    _git(["init", "--bare", "-q"], bare)

    repo = workspace / "repos" / slug
    repo.mkdir(parents=True)
    _git(["init", "-q", "-b", _BRANCH], repo)
    _git(["config", "user.email", "t@example.com"], repo)
    _git(["config", "user.name", "Test"], repo)
    _git(["remote", "add", "origin", str(bare)], repo)
    return repo, bare


def _write_dadaia_stub(workspace: Path, python_exe: str) -> Path:
    """``DADAIA_BIN`` override for the installed hook (resolution rank 1, see
    ``pre-push-ci-gate.sh``): skip ONLY the ``ci preflight`` stage — that stage targets
    the dadaia-workspace source repo and refuses honestly outside it
    (``ci-preflight-unusable-outside-the-source-repo``); A9.2 proves it green for THIS
    release's own repo separately. Every other verb — in particular
    ``ci push-gate-check``, which is what this journey proves — forwards to the REAL
    CLI through this interpreter, stdin included (``exec`` preserves file descriptors).
    """
    stub = workspace / "dadaia-stub.sh"
    stub.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        'if [ "${1:-}" = "ci" ] && [ "${2:-}" = "preflight" ]; then\n'
        '    echo "[stub] ci preflight skipped for this throwaway repo '
        '(A9.2 covers the real repo)" >&2\n'
        "    exit 0\n"
        "fi\n"
        f'exec "{python_exe}" -m dadaia_workspace.cli.main "$@"\n',
        encoding="utf-8",
    )
    stub.chmod(0o755)
    return stub


def _hook_env(workspace: Path, *, stub: Path, denylist_file: Path) -> dict[str, str]:
    """A harness-FREE env mirroring the installed pre-push hook's real child env."""
    env = dict(os.environ)
    for bad in ("CLAUDE_CODE_SESSION_ID", "CODEX_SESSION_ID", "CODEX_THREAD_ID", "DADAIA_MODE"):
        env.pop(bad, None)
    env["DADAIA_BIN"] = str(stub)
    env["DADAIA_PRIVACY_DENYLIST"] = str(denylist_file)
    return env


def _write_denylist_file(workspace: Path) -> Path:
    path = workspace / "privacy_denylist.json"
    path.write_text(json.dumps({_PLANTED_TERM: "planted e2e term (synthetic)"}), encoding="utf-8")
    return path


def _push(repo: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "push", "origin", f"{_BRANCH}:{_BRANCH}"],
        cwd=repo,
        capture_output=True,
        text=True,
        env=env,
        timeout=_EXIT_DEADLINE,
    )


def _remote_branch_sha(bare: Path) -> str | None:
    result = subprocess.run(
        ["git", "rev-parse", "--verify", f"refs/heads/{_BRANCH}"],
        cwd=bare,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def test_the_gate_runs_where_core_hookspath_points(tmp_path: Path) -> None:
    """pre-push-gate-never-runs-under-core-hookspath#B1, pre-push-gate-never-runs-under-core-hookspath#B3 (AC1.3): with ``core.hooksPath``
    set, ``ci install-hook`` puts the gate where git runs hooks, and a push carrying an
    AKIA-shaped key is refused. Composed at runtime — never a tracked secret literal."""
    repo, bare = _init_repo_and_remote(tmp_path, _SLUG)
    _git(["config", "core.hooksPath", ".husky"], repo)
    (repo / "creds.txt").write_text("key " + "AKIA" + "Q" * 16 + "\n", encoding="utf-8")
    _git(["add", "creds.txt"], repo)
    _git(["commit", "-q", "-m", "seed"], repo)
    result = subprocess.run(
        [sys.executable, "-m", "dadaia_workspace.cli.main", "ci", "install-hook"],
        cwd=repo,
        capture_output=True,
        text=True,
        timeout=_EXIT_DEADLINE,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert (repo / ".husky" / "pre-push").is_file()

    stub = _write_dadaia_stub(tmp_path, sys.executable)
    env = _hook_env(tmp_path, stub=stub, denylist_file=_write_denylist_file(tmp_path))
    refused = _push(repo, env)

    assert refused.returncode != 0, refused.stdout + refused.stderr
    assert _remote_branch_sha(bare) is None
