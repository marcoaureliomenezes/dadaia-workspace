"""Wiring test for .github/scripts/pr-verdict-check.sh (v0.4.4 FR4, T-044-07).

The security verdict that used to gate every push (pre-push hook, per-pushed-sha) is
deleted from that path (A3.4, T-044-06) and relocates to a CI PR gate keyed on the PR
head sha (FR4). A GitHub Actions checkout never sees ``.dadaia/handoff/`` — it is a
workspace-local, gitignored directory (``features/chokepoints/service.py``'s module
docstring; ``dadaia ci gc-push-verdicts`` only ever reads it from a local clone) — so
the evidence this gate reads is a COMMITTED copy of the security-reviewer's APPROVED
handoff, placed on the branch at
``specs/releases/<release-id>/verdicts/<reviewed-sha>.handoff.json`` (the same
"review artifact committed on the branch" cadence DADAIA.md §5 already uses for a
qa-engineer segment close).

Because the verdict evidence file cannot be part of the very commit whose sha it
names (committing the file changes the tree, hence the sha — a real chicken-and-egg
git property, not a script quirk), "covers the PR head sha" (A4.3) is defined as: the
verdict's ``metrics.commit_sha`` is the PR head itself, OR an ancestor of it where
every path that differs between the two is itself under
``specs/releases/*/verdicts/*`` — i.e. nothing but more verdict evidence landed after
the reviewed commit. Each test below proves one branch of that rule against a real,
disposable git repository (dadaia-test-stewardship: "No real venvs built in tests" —
this is a plain git repo, not a venv, and costs a few kilobytes on tmp_path).

Intent: CONTRACT — v0.4.4 A4.3, A4.5 (T-044-07)
Owner: software-engineer
"""

from __future__ import annotations

import json
import os
import stat
import subprocess
from pathlib import Path

import pytest

pytestmark = [pytest.mark.integration]

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SCRIPT = _REPO_ROOT / ".github" / "scripts" / "pr-verdict-check.sh"
_RELEASE_ID = "v9.9.9"
_TEST_PATH = "/usr/bin:/bin"


def _git(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True, check=True)


def _head(repo: Path) -> str:
    return _git("rev-parse", "HEAD", cwd=repo).stdout.strip()


def _init_repo(tmp_path: Path) -> Path:
    """A throwaway git repo with an ACTIVE.md pointing at ``_RELEASE_ID``."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _git("init", "-q", "-b", "main", cwd=repo)
    _git("config", "user.email", "test@example.invalid", cwd=repo)
    _git("config", "user.name", "Test", cwd=repo)
    releases_dir = repo / "specs" / "releases"
    releases_dir.mkdir(parents=True)
    (releases_dir / "ACTIVE.md").write_text(
        f"release: {_RELEASE_ID}\nphase: IMPLEMENTATION\n", encoding="utf-8"
    )
    (repo / "app.py").write_text("print('v1')\n", encoding="utf-8")
    _git("add", "-A", cwd=repo)
    _git("commit", "-q", "-m", "chore: bootstrap", cwd=repo)
    return repo


def _commit_code_change(repo: Path, content: str) -> str:
    (repo / "app.py").write_text(content, encoding="utf-8")
    _git("add", "-A", cwd=repo)
    _git("commit", "-q", "-m", "feat: change app.py", cwd=repo)
    return _head(repo)


def _commit_verdict(
    repo: Path,
    *,
    covers_sha: str,
    verdict: str = "APPROVED",
    agent: str = "security-reviewer",
    release_id: str = _RELEASE_ID,
) -> str:
    payload = {
        "schema_version": "handoff-v1.2",
        "agent": agent,
        "context": "dadaia-workspace",
        "release_id": release_id,
        "verdict": verdict,
        "metrics": {"commit_sha": covers_sha},
    }
    verdicts_dir = repo / "specs" / "releases" / release_id / "verdicts"
    verdicts_dir.mkdir(parents=True, exist_ok=True)
    (verdicts_dir / f"{covers_sha}.handoff.json").write_text(json.dumps(payload), encoding="utf-8")
    _git("add", "-A", cwd=repo)
    _git("commit", "-q", "-m", "chore: attach security verdict", cwd=repo)
    return _head(repo)


def _run_script(
    repo: Path, head_sha: str, extra_env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    env = {"PATH": _TEST_PATH, "PR_HEAD_SHA": head_sha, **(extra_env or {})}
    return subprocess.run(
        ["bash", str(_SCRIPT)], cwd=str(repo), capture_output=True, text=True, env=env
    )


def test_script_exists_and_is_executable() -> None:
    assert _SCRIPT.is_file(), f"expected script at {_SCRIPT}"
    if os.name != "nt":
        mode = _SCRIPT.stat().st_mode
        assert mode & stat.S_IXUSR, "script must be executable (chmod +x)"


def test_script_has_valid_bash_syntax() -> None:
    result = subprocess.run(["bash", "-n", str(_SCRIPT)], capture_output=True, text=True)
    assert result.returncode == 0, f"bash -n failed: {result.stderr}"


def test_no_verdicts_directory_fails_naming_the_expected_path(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    head = _head(repo)
    result = _run_script(repo, head)
    assert result.returncode != 0, result.stdout + result.stderr
    assert _RELEASE_ID in result.stdout + result.stderr
    assert "verdicts" in result.stdout + result.stderr


def test_exact_sha_match_passes(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    reviewed = _commit_code_change(repo, "print('v2')\n")
    _commit_verdict(repo, covers_sha=reviewed)
    # The PR head IS the reviewed sha itself (no trailing commit needed in this case).
    result = _run_script(repo, reviewed)
    assert result.returncode == 0, result.stdout + result.stderr


def test_ancestor_with_pure_evidence_trailing_commit_passes(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    reviewed = _commit_code_change(repo, "print('v2')\n")
    evidence_head = _commit_verdict(repo, covers_sha=reviewed)
    assert evidence_head != reviewed
    result = _run_script(repo, evidence_head)
    assert result.returncode == 0, result.stdout + result.stderr


def test_unreviewed_code_change_after_the_review_fails(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    reviewed = _commit_code_change(repo, "print('v2')\n")
    _commit_verdict(repo, covers_sha=reviewed)
    drifted_head = _commit_code_change(repo, "print('v3 - unreviewed')\n")
    result = _run_script(repo, drifted_head)
    assert result.returncode != 0, result.stdout + result.stderr
    assert "app.py" in result.stdout + result.stderr


def test_rejected_verdict_does_not_qualify(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    reviewed = _commit_code_change(repo, "print('v2')\n")
    evidence_head = _commit_verdict(repo, covers_sha=reviewed, verdict="REJECTED")
    result = _run_script(repo, evidence_head)
    assert result.returncode != 0, result.stdout + result.stderr


def test_wrong_agent_does_not_qualify(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    reviewed = _commit_code_change(repo, "print('v2')\n")
    evidence_head = _commit_verdict(repo, covers_sha=reviewed, agent="qa-engineer")
    result = _run_script(repo, evidence_head)
    assert result.returncode != 0, result.stdout + result.stderr


def test_sha_not_ancestor_of_head_fails(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    reviewed = _commit_code_change(repo, "print('v2')\n")
    _commit_verdict(repo, covers_sha=reviewed)
    # A divergent branch's tip is never an ancestor of the reviewed line's history.
    _git("checkout", "-q", "-b", "unrelated", "main", cwd=repo)
    unrelated_head = _commit_code_change(repo, "print('unrelated branch')\n")
    result = _run_script(repo, unrelated_head)
    assert result.returncode != 0, result.stdout + result.stderr


def test_release_id_env_override_is_honored(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    reviewed = _commit_code_change(repo, "print('v2')\n")
    evidence_head = _commit_verdict(repo, covers_sha=reviewed, release_id="v8.8.8")
    # ACTIVE.md still names v9.9.9 — without the override the v8.8.8 verdict is invisible.
    no_override = _run_script(repo, evidence_head)
    assert no_override.returncode != 0, no_override.stdout + no_override.stderr

    overridden = _run_script(repo, evidence_head, {"RELEASE_ID": "v8.8.8"})
    assert overridden.returncode == 0, overridden.stdout + overridden.stderr


def test_missing_active_md_and_no_override_fails_with_clear_message(tmp_path: Path) -> None:
    repo = tmp_path / "bare-repo"
    repo.mkdir()
    _git("init", "-q", "-b", "main", cwd=repo)
    _git("config", "user.email", "test@example.invalid", cwd=repo)
    _git("config", "user.name", "Test", cwd=repo)
    (repo / "app.py").write_text("print('v1')\n", encoding="utf-8")
    _git("add", "-A", cwd=repo)
    _git("commit", "-q", "-m", "chore: bootstrap", cwd=repo)
    head = _head(repo)

    result = _run_script(repo, head)
    assert result.returncode != 0
    assert "ACTIVE.md" in result.stdout + result.stderr
