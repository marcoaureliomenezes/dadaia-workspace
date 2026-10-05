"""v0.4.4 A3.1; 0.5.0 AC6.4, AC6.5 (T-050-12): `ci push-gate-check`
driven as the pre-push hook drives it (git's ref lines on stdin, harness-free env, no
handoff on disk). A work-branch push, a branch deletion and a tag push pass; the branch
names come from the committed constitution's gitflow (custom, absent -> default + one
warning, inherited by an associated repo; its main repo absent -> default + one warning).
The integration-branch refusal and its fix are the refusal harness Case `birth_published`.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from dadaia_workspace.core.cli_line import shell_line
from dadaia_workspace.core.specs_version import CANONICAL_SPECS_VERSION
from tests.fixtures.harness_env import base_env

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
    (workspace / ".dadaia" / "states" / "spec_contexts.json").write_text(
        '{"contexts": []}', encoding="utf-8"
    )
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
        env=base_env(),  # harness-free, as the pre-push hook's child
        timeout=_EXIT_DEADLINE,
    )


@pytest.mark.parametrize(
    "line",
    [
        pytest.param("refs/heads/feature/0.0.1 {sha} refs/heads/feature/0.0.1 " + _ZERO, id="work-branch-push"),
        pytest.param("refs/heads/old " + _ZERO + " refs/heads/old {sha}", id="branch-deletion"),
        pytest.param("refs/tags/v1 {sha} refs/tags/v1 " + _ZERO, id="tag-push"),
    ],
)  # fmt: skip
def test_pass_matrix(tmp_path: Path, line: str) -> None:
    """Never review-gated: the verdict is a PR gate (A3.4), not on this path."""
    repo, sha = _init_repo(tmp_path, _SLUG)
    result = _run_push_gate(repo, tmp_path, line.format(sha=sha) + "\n")
    assert result.returncode == 0, result.stdout + result.stderr


_CUSTOM_BLOCK = "---\ngitflow: {principal: trunk, integration: next, work: work/}\n---\n# C\n"


def _push(branch: str, sha: str) -> str:
    return f"refs/heads/{branch} {sha} refs/heads/{branch} {_ZERO}\n"


def _write_constitution(repo: Path, text: str) -> None:
    """Committed: the gate reads HEAD's constitution, never the working tree (ADR 0048)."""
    (repo / "specs").mkdir(exist_ok=True)
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
    fix = shell_line("git", "-C", str(repo), "switch", "-c", "work/0.1.0", sha)
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
    # pre-push-gate-crashes-when-owner-main-repo-absent: an absent main repo carries no
    # committed text — ADR 0046's default plus one warning, never a traceback.
    shutil.rmtree(main)
    result = _run_push_gate(infra, tmp_path, _push("feature/0.0.1", sha))
    assert result.returncode == 0 and result.stderr.count("WARNING") == 1, result.stderr
    _write_constitution(infra, _CUSTOM_BLOCK)  # its own constitution is read first
    result = _run_push_gate(infra, tmp_path, _push("work/0.0.1", sha))
    assert result.returncode == 0 and "WARNING" not in result.stderr, result.stderr


@pytest.mark.parametrize(
    "stamp",
    [f"{CANONICAL_SPECS_VERSION}", f"{CANONICAL_SPECS_VERSION}\ngitflow: {{principal: main"],
)
def test_the_pushed_commits_tree_state_governs_the_canon_scan(tmp_path: Path, stamp: str) -> None:
    """sa-specs-tree-state-read-five-ways#B28-2: the pushed commit's stamp, not a checkout
    stamped 6; sa-specs-tree-state-read-five-ways#B28-3: a malformed one still scans."""
    repo, _ = _init_repo(tmp_path, _SLUG)
    (repo / "specs").mkdir()
    (repo / "specs" / "stray-notes.txt").write_text("x\n", encoding="utf-8")
    _write_constitution(repo, f"---\nspecs_pattern_version: {stamp}\n---\n# C\n")
    (repo / "specs" / "constitution.md").write_text("---\nspecs_pattern_version: 6\n---\n")
    sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True)
    result = _run_push_gate(repo, tmp_path, _push("feature/0.0.1", sha.stdout.strip()))
    assert result.returncode != 0 and "BLOCKED" in result.stderr, result.stderr
