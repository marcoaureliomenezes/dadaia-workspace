"""Seed-2 e2e: push-gate verdict chokepoint across the REAL CLI boundary (FR-W1-02).

The pre-push hook forwards git's pre-push stdin ref lines (``<local-ref> <local-sha>
<remote-ref> <remote-sha>``) into ``dadaia ci push-gate-check``. Rather than stand up a
real remote and a real ``git push`` (slow, networked, nondeterministic), this drives the
SAME boundary the hook drives: it spawns ``ci push-gate-check`` through THIS interpreter
with the ref lines on stdin and a synthetic ``.dadaia/handoff/`` tree on disk — exactly
the contract ``pre-push-ci-gate.sh`` line 106 invokes.

Scenarios (seed 2):

* (a) push-cycle commit WITHOUT a security-reviewer APPROVE → BLOCKED, actionable message.
* (b) WITH an APPROVE whose ``metrics.commit_sha`` == the pushed sha → flows.
* (c) branch deletion (zero sha) and tag push → pass with no verdict on disk.
* (d) predicate keys on the STDIN ref sha, never ``git rev-parse HEAD``: the repo HEAD is a
      DIFFERENT sha than the pushed ref sha, an APPROVE covers only the pushed sha, and the
      push still flows — proving HEAD is never consulted.

The CLI is invoked harness-free (no PreToolUse/PostToolUse payload), with only
``WORKSPACE_ROOT`` set, so this also covers the headless runtime the chokepoint protects.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.e2e

_SLUG = "demo-ctx"
_EXIT_DEADLINE = 30.0
_ZERO = "0" * 40


def _init_repo(workspace: Path, slug: str) -> tuple[Path, str]:
    """A real git repo at ``<workspace>/repos/<slug>`` with TWO real commits.

    Returns ``(repo, first_commit_sha)``. v0.9.0's push-range denylist scan needs a
    resolvable git object for the pushed ``local_sha`` — a synthetic literal sha (the
    pre-v0.9.0 fixture) now fails closed as a genuine git-read failure (FR6 row 2), so
    tests use a REAL commit sha instead. The repo's actual HEAD ends up at a SECOND,
    later commit so ``test_predicate_keys_on_stdin_sha_not_head`` still proves the
    predicate never consults ``git rev-parse HEAD``.
    """
    (workspace / ".dadaia" / "states").mkdir(parents=True, exist_ok=True)
    (workspace / ".dadaia" / "states" / "spec_contexts.json").write_text("{}", encoding="utf-8")
    repo = workspace / "repos" / slug
    repo.mkdir(parents=True)
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "t@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    (repo / "seed.txt").write_text("seed\n", encoding="utf-8")
    subprocess.run(["git", "add", "seed.txt"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "seed"], cwd=repo, check=True)
    first_sha = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True, check=True
    ).stdout.strip()
    (repo / "later.txt").write_text("later\n", encoding="utf-8")
    subprocess.run(["git", "add", "later.txt"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "later"], cwd=repo, check=True)
    return repo, first_sha


def _hook_env(workspace: Path) -> dict[str, str]:
    """A harness-FREE env: only WORKSPACE_ROOT (mirrors the installed pre-push hook child)."""
    env = dict(os.environ)
    for bad in ("CLAUDE_CODE_SESSION_ID", "CODEX_SESSION_ID", "DADAIA_MODE"):
        env.pop(bad, None)
    env["WORKSPACE_ROOT"] = str(workspace)
    return env


def _write_security_approve(workspace: Path, *, commit_sha: str, name: str = "sec") -> None:
    handoff_dir = workspace / ".dadaia" / "handoff" / _SLUG
    handoff_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "handoff-v1.1",
        "agent": "security-reviewer",
        "context": _SLUG,
        "produced_at": "2026-06-12T12:00:00Z",
        "scope": "push-gate e2e",
        "metrics": {"commit_sha": commit_sha},
        "artifact": {"type": "other"},
        "verdict": "APPROVED",
        "verdict_reason": "ok",
    }
    (handoff_dir / f"{name}.handoff.json").write_text(json.dumps(payload), encoding="utf-8")


def _run_push_gate(
    repo: Path, workspace: Path, stdin_text: str
) -> subprocess.CompletedProcess[str]:
    """Drive ``ci push-gate-check`` exactly as the pre-push hook does (ref lines on stdin)."""
    return subprocess.run(
        [sys.executable, "-m", "dadaia_workspace.cli.main", "ci", "push-gate-check"],
        cwd=repo,
        input=stdin_text,
        capture_output=True,
        text=True,
        env=_hook_env(workspace),
        timeout=_EXIT_DEADLINE,
    )


def test_push_without_security_approve_is_blocked(tmp_path: Path) -> None:
    workspace = tmp_path
    repo, pushed_sha = _init_repo(workspace, _SLUG)
    # No handoff on disk at all → no APPROVE → blocked with an actionable message.
    result = _run_push_gate(
        repo, workspace, f"refs/heads/develop {pushed_sha} refs/heads/develop {_ZERO}\n"
    )
    out = result.stdout + result.stderr
    assert result.returncode != 0, out
    assert "BLOCKED" in out, out
    assert "security-reviewer APPROVE" in out, out
    assert "origin/develop..develop" in out, out


@pytest.mark.parametrize(
    "variant",
    ["matching-approve", "branch-deletion", "tag-push"],
    ids=["approve-flows", "branch-deletion-passes", "tag-push-passes"],
)
def test_pass_matrix(tmp_path: Path, variant: str) -> None:
    """(b) a matching security-reviewer APPROVE flows; (c) branch deletion (zero
    local sha) and a tag push both pass with NO verdict on disk — never review-gated."""
    workspace = tmp_path
    repo, pushed_sha = _init_repo(workspace, _SLUG)

    if variant == "matching-approve":
        _write_security_approve(workspace, commit_sha=pushed_sha)
        result = _run_push_gate(
            repo, workspace, f"refs/heads/develop {pushed_sha} refs/heads/develop {_ZERO}\n"
        )
    elif variant == "branch-deletion":
        # Zero local sha = branch deletion; never review-gated, even with no handoff on disk.
        result = _run_push_gate(
            repo, workspace, f"refs/heads/old {_ZERO} refs/heads/old {pushed_sha}\n"
        )
    else:
        result = _run_push_gate(
            repo, workspace, f"refs/tags/v1 {pushed_sha} refs/tags/v1 {_ZERO}\n"
        )
    assert result.returncode == 0, result.stdout + result.stderr


def test_predicate_keys_on_stdin_sha_not_head(tmp_path: Path) -> None:
    """Regression: the gate keys on the STDIN ref sha, never ``git rev-parse HEAD``.

    The repo's real HEAD is a LATER commit; the pushed ref sha is the repo's FIRST
    commit (a real, resolvable object — required now that v0.9.0 scans it — but
    deliberately not HEAD). An APPROVE covers ONLY the first commit's sha. If the gate
    wrongly consulted HEAD it would block (no APPROVE for HEAD); keyed on the pushed
    sha it must flow.
    """
    workspace = tmp_path
    repo, pushed_sha = _init_repo(workspace, _SLUG)
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True, check=True
    ).stdout.strip()
    assert head != pushed_sha  # the pushed sha is deliberately not the repo HEAD.

    _write_security_approve(workspace, commit_sha=pushed_sha)
    result = _run_push_gate(
        repo, workspace, f"refs/heads/develop {pushed_sha} refs/heads/develop {_ZERO}\n"
    )
    assert result.returncode == 0, (
        "gate must key on the pushed sha, not HEAD: " + result.stdout + result.stderr
    )
