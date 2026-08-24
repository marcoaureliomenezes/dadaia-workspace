"""End-to-end push-denylist journey — real git hooks, planted-term refusal, clean push
after amend (SPEC v0.9.0 FR9/A9.1; SPEC v0.4.4 FR3 — the v2 pushable branch).

Intent: CONTRACT — v0.9.0 A9.1, A5.1, A5.2, A5.3; v0.4.4 A3.1, A3.3

Drives the REAL push-gate chain across a real git-hook boundary in a throwaway
repository: ``dadaia ci install-hook`` installs the shipped ``pre-push-ci-gate.sh``
into ``.git/hooks/pre-push``, and a real ``git push`` (to a local bare remote, no
network) triggers it exactly as an operator's push would. ``DADAIA_BIN`` is stubbed to
skip the ``ci preflight`` stage only — that stage refuses honestly outside the
dadaia-workspace SOURCE repo (``ci-preflight-unusable-outside-the-source-repo``) and
A9.2 already proves it green for THIS release's own repo elsewhere; every other stage
of the installed hook runs for real, including the v0.9.0 range-scoped denylist scan
(FR1/FR2) over real git objects read by the real ``GitSubprocessObjectReader``, and the
v0.4.4 v2 branch policy (FR3) — ``feature/{M.m.p}`` is the pushable branch; the security
verdict no longer lives on this path at all (A3.4), so a clean push after amend needs no
APPROVE handoff anywhere.

Journey (one continuous, stateful flow — the second half depends on the first's repo
state, exactly as PLAN.md Phase 4 describes it):

1. A single commit plants a synthetic term (``zz-fake-context-name`` — never a real
   term, per the TASKS standing rule) in a tracked file, alongside an unrelated
   harmless file, on ``feature/0.0.1`` (the v2 pushable branch).
2. ``git push origin feature/0.0.1:feature/0.0.1`` is REFUSED by the installed
   ``pre-push`` hook (A3.3: the range-scoped denylist scan still runs on the feature
   push — under v2 that push is the first publication to origin). The FR5 message shape
   is asserted on the real combined stdout+stderr: the masked term, ``path:line``, the
   law it enforces, the edit+rewrite-before-push remediation (never a rewrite of
   published history), and — critically — the unmasked term and the raw offending line
   content appear NOWHERE in the output (A5.2, CWE-532). The bare remote is proven
   untouched by the refused push.
3. The term is removed and the commit amended — the SAME ``git push`` now flows clean,
   with NO security-reviewer handoff written anywhere (A3.4) — the remote's
   ``feature/0.0.1`` ref lands on the amended sha.

Owner: software-engineer (LARGE-tier e2e; tests/AGENTS.md "every file names an owner").
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
_LEAK_LINE = f"see {_PLANTED_TERM} here\n"
_MASKED_TERM = f"{_PLANTED_TERM[0]}…{_PLANTED_TERM[-1]}"  # "z…e" — Hit._mask's shape


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


def _plant_and_commit(repo: Path) -> None:
    (repo / "readme.txt").write_text("hello\n", encoding="utf-8")
    (repo / "leak.txt").write_text(_LEAK_LINE, encoding="utf-8")
    _git(["add", "readme.txt", "leak.txt"], repo)
    _git(["commit", "-q", "-m", "seed"], repo)


def _install_hooks(repo: Path) -> Path:
    """Run the REAL ``dadaia ci install-hook`` verb (this is what "install the hooks"
    means for this journey) and return the installed ``pre-push`` script path."""
    result = subprocess.run(
        [sys.executable, "-m", "dadaia_workspace.cli.main", "ci", "install-hook"],
        cwd=repo,
        capture_output=True,
        text=True,
        timeout=_EXIT_DEADLINE,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    pre_push = repo / ".git" / "hooks" / "pre-push"
    assert pre_push.exists() and os.access(pre_push, os.X_OK), result.stdout + result.stderr
    return pre_push


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
    env["WORKSPACE_ROOT"] = str(workspace)
    env["DADAIA_BIN"] = str(stub)
    env["DADAIA_PRIVACY_DENYLIST"] = str(denylist_file)
    return env


def _write_denylist_file(workspace: Path) -> Path:
    path = workspace / "privacy_denylist.json"
    path.write_text(json.dumps([[_PLANTED_TERM, "planted e2e term (synthetic)"]]), encoding="utf-8")
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


def test_planted_term_refused_then_clean_push_after_amend(tmp_path: Path) -> None:
    workspace = tmp_path
    repo, bare = _init_repo_and_remote(workspace, _SLUG)
    _plant_and_commit(repo)
    _install_hooks(repo)

    stub = _write_dadaia_stub(workspace, sys.executable)
    denylist_file = _write_denylist_file(workspace)
    env = _hook_env(workspace, stub=stub, denylist_file=denylist_file)

    # --- (2) refused: the planted term is in the pushed range -----------------------
    refused = _push(repo, env)
    out1 = refused.stdout + refused.stderr
    assert refused.returncode != 0, out1
    assert "BLOCKED" in out1, out1

    # A5.1 — ref, path:line, short blob sha, masked term + source layer.
    assert _BRANCH in out1, out1
    assert "leak.txt:1" in out1, out1
    assert "(blob " in out1, out1
    assert f"'{_MASKED_TERM}'" in out1, out1
    assert "operator denylist" in out1, out1
    assert "DADAIA.md §7" in out1, out1  # "DADAIA.md §7"

    # A5.2 — the unmasked term and the raw offending line never appear anywhere.
    assert _PLANTED_TERM not in out1, out1
    assert _LEAK_LINE.strip() not in out1, out1
    assert "fake-context-name" not in out1, out1

    # A5.3 — remediation names edit + rewrite-before-push, never published-history rewrite.
    assert "edit the file" in out1, out1
    assert "already-published history" in out1 and "never needs a rewrite" in out1, out1
    assert "--no-verify" in out1, out1

    # The refused push never reached the remote.
    assert _remote_branch_sha(bare) is None, "refused push must not land on the remote"

    # --- (3) remove the term, amend, push clean — NO verdict handoff needed (A3.4) ---
    # `commit --amend` also fires the installed pre-commit hook, which resolves its
    # runner the same way (DADAIA_BIN rank 1) — pass the same env.
    (repo / "leak.txt").write_text("see REDACTED here\n", encoding="utf-8")
    _git(["add", "leak.txt"], repo, env=env)
    _git(["commit", "-q", "--amend", "--no-edit"], repo, env=env)
    amended_sha = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True, check=True
    ).stdout.strip()

    clean = _push(repo, env)
    out2 = clean.stdout + clean.stderr
    assert clean.returncode == 0, out2
    assert _PLANTED_TERM not in out2, out2

    assert _remote_branch_sha(bare) == amended_sha, out2
