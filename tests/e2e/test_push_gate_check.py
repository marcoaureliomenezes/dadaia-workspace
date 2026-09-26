"""v0.4.4 T-044-06 (FR3): the v2 branch contract across the REAL CLI boundary.

The pre-push hook forwards git's pre-push stdin ref lines (``<local-ref> <local-sha>
<remote-ref> <remote-sha>``) into ``dadaia ci push-gate-check``. Rather than stand up a
real remote and a real ``git push`` (slow, networked, nondeterministic), this drives the
SAME boundary the hook drives: it spawns ``ci push-gate-check`` through THIS interpreter
with the ref lines on stdin and no ``.dadaia/handoff/`` tree on disk at all — exactly the
contract ``pre-push-ci-gate.sh`` line 106 invokes.

Scenarios (v2):

* (a) a ``feature/{M.m.p}`` push flows — no security-reviewer handoff needed anywhere on
  disk (A3.4: the verdict is no longer checked on this path at all; it is a PR gate now,
  FR4).
* (b) a ``develop`` push is BLOCKED, naming the PR path (``feature/{M.m.p}`` → develop).
* (c) branch deletion (zero local sha) and a tag push both pass — never review-gated.
* (d) 0.5.0 AC6.4/AC6.5: the branch names come from the constitution gitflow — a custom
  one (``trunk``/``next``/``work/``), an absent block (default + warning, never a block),
  and an associated repo inheriting its context's main-repo gitflow.

Supersedes v0.6.0's verdict-keyed scenarios (a covering security-reviewer APPROVE
required for ``develop`` to flow, and the "keys on the stdin sha, never HEAD" regression,
which only had meaning while a verdict lookup existed on this path) — deleted per A3.4,
not disabled.

The CLI is invoked harness-free (no PreToolUse/PostToolUse payload), with only
``WORKSPACE_ROOT`` set, so this also covers the headless runtime the chokepoint protects.

Intent: CONTRACT — v0.4.4 A3.1; 0.5.0 AC6.4, AC6.5 (T-050-12)
Owner: dd-software-engineer
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from dadaia_workspace.core.cli_line import shell_line

pytestmark = pytest.mark.e2e

_SLUG = "demo-ctx"
_EXIT_DEADLINE = 30.0
_ZERO = "0" * 40


def _init_repo(workspace: Path, slug: str) -> tuple[Path, str]:
    """A real git repo at ``<workspace>/repos/<slug>`` with one real commit.

    Returns ``(repo, commit_sha)``. The v0.9.0 push-range denylist scan needs a
    resolvable git object for the pushed ``local_sha`` — a synthetic literal sha fails
    closed as a genuine git-read failure (FR6 row 2), so tests use a REAL commit sha.
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
    sha = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True, check=True
    ).stdout.strip()
    return repo, sha


def _hook_env(workspace: Path) -> dict[str, str]:
    """A harness-FREE env: only WORKSPACE_ROOT (mirrors the installed pre-push hook child)."""
    env = dict(os.environ)
    for bad in ("CLAUDE_CODE_SESSION_ID", "CODEX_SESSION_ID", "DADAIA_MODE"):
        env.pop(bad, None)
    env["WORKSPACE_ROOT"] = str(workspace)
    return env


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


def test_feature_branch_push_flows_with_no_verdict_anywhere(tmp_path: Path) -> None:
    workspace = tmp_path
    repo, sha = _init_repo(workspace, _SLUG)
    # No handoff on disk at all — the verdict is no longer checked on this path (A3.4).
    result = _run_push_gate(
        repo, workspace, f"refs/heads/feature/0.0.1 {sha} refs/heads/feature/0.0.1 {_ZERO}\n"
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_develop_push_is_blocked_naming_the_pr_path(tmp_path: Path) -> None:
    workspace = tmp_path
    repo, sha = _init_repo(workspace, _SLUG)
    result = _run_push_gate(
        repo, workspace, f"refs/heads/develop {sha} refs/heads/develop {_ZERO}\n"
    )
    out = result.stdout + result.stderr
    assert result.returncode != 0, out
    assert "BLOCKED" in out, out
    assert "PR" in out, out
    assert "feature/" in out, out


@pytest.mark.parametrize(
    "variant",
    ["branch-deletion", "tag-push"],
    ids=["branch-deletion-passes", "tag-push-passes"],
)
def test_pass_matrix(tmp_path: Path, variant: str) -> None:
    """Branch deletion (zero local sha) and a tag push both pass with NO verdict on
    disk — never review-gated, exactly as before A3.4 (the check simply does not exist
    anywhere on this path now)."""
    workspace = tmp_path
    repo, sha = _init_repo(workspace, _SLUG)

    if variant == "branch-deletion":
        result = _run_push_gate(repo, workspace, f"refs/heads/old {_ZERO} refs/heads/old {sha}\n")
    else:
        result = _run_push_gate(repo, workspace, f"refs/tags/v1 {sha} refs/tags/v1 {_ZERO}\n")
    assert result.returncode == 0, result.stdout + result.stderr


_CUSTOM_BLOCK = "---\ngitflow: {principal: trunk, integration: next, work: work/}\n---\n# C\n"


def _push(branch: str, sha: str) -> str:
    return f"refs/heads/{branch} {sha} refs/heads/{branch} {_ZERO}\n"


def _write_constitution(repo: Path, text: str) -> None:
    """Committed: the gate reads HEAD's constitution, never the working tree (ADR 0048)."""
    (repo / "specs").mkdir()
    (repo / "specs" / "constitution.md").write_text(text, encoding="utf-8")
    git = ["git", "-c", "user.name=t", "-c", "user.email=t@t.invalid"]
    subprocess.run([*git, "add", "specs"], cwd=repo, check=True, capture_output=True)
    subprocess.run([*git, "commit", "-qm", "c"], cwd=repo, check=True, capture_output=True)


def test_a_custom_gitflow_governs_the_push(tmp_path: Path) -> None:
    repo, sha = _init_repo(tmp_path, _SLUG)
    _write_constitution(repo, _CUSTOM_BLOCK)

    assert _run_push_gate(repo, tmp_path, _push("work/0.0.1", sha)).returncode == 0
    refused = _run_push_gate(repo, tmp_path, _push("feature/0.0.1", sha))
    assert refused.returncode != 0
    fix = shell_line("git", "-C", str(repo), "checkout", "-b", "work/<M.m.p>")
    assert f"fix: {fix}" in refused.stderr, refused.stderr


def test_an_absent_gitflow_block_warns_and_falls_back_to_the_default(tmp_path: Path) -> None:
    repo, sha = _init_repo(tmp_path, _SLUG)
    _write_constitution(repo, "---\nspecs_pattern_version: 7\n---\n# C\n")

    result = _run_push_gate(repo, tmp_path, _push("feature/0.0.1", sha))
    assert result.returncode == 0, result.stderr
    assert "WARNING" in result.stderr and "default gitflow" in result.stderr


def test_an_associated_repo_inherits_its_context_gitflow(tmp_path: Path) -> None:
    main, _ = _init_repo(tmp_path, _SLUG)
    _write_constitution(main, _CUSTOM_BLOCK)
    infra, sha = _init_repo(tmp_path, "demo-infra")
    (tmp_path / ".dadaia" / "states" / "spec_contexts.json").write_text(
        json.dumps(
            {
                "schema_version": "2",
                "contexts": [
                    {
                        "name": _SLUG,
                        "state": "alive",
                        "repo_slug": _SLUG,
                        "associated_repos": [{"slug": "demo-infra"}],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    result = _run_push_gate(infra, tmp_path, _push("work/0.0.1", sha))
    assert result.returncode == 0, result.stderr
    assert "WARNING" not in result.stderr
    assert _run_push_gate(infra, tmp_path, _push("feature/0.0.1", sha)).returncode != 0
