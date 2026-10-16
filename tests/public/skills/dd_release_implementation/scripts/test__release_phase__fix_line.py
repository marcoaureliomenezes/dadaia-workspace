"""The release phase fixes are spelled over their words: a blank in the path stays one word, and
no fix holds a shell substitution; the sha is read from HEAD, or the act that supplies it is named."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from dadaia_workspace.core.skill_owner import load_owner
from tests.helpers.oslib import command, run

_PHASE = load_owner("dd-release-implementation", "_release_phase")


def test_the_worktree_list_fix_quotes_a_root_with_a_blank(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        _PHASE, "run", lambda argv, **_: subprocess.CompletedProcess(argv, 1, "", "")
    )
    root = tmp_path / "a b"
    root.mkdir()
    with pytest.raises(_PHASE.Refusal) as refused:
        _PHASE._worktree_rows(root)
    owner = Path(_PHASE.__file__).resolve().parents[2] / "dd-gitflow-default/scripts/worktree.py"
    assert refused.value.fix == command(sys.executable, str(owner), "list")


def _refusal_fix(specs: Path) -> str:
    with pytest.raises(_PHASE.Refusal) as refused:
        _PHASE.set_phase(specs, "IMPLEMENTATION", "nope")
    return str(refused.value.fix)


def test_a_bad_sha_fix_names_the_real_head_sha(tmp_path: Path) -> None:
    repo = tmp_path / "a b"
    (repo / "specs").mkdir(parents=True)
    run(["git", "init", "-q", str(repo)], check=True)
    run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@t.invalid",
         "commit", "-q", "--allow-empty", "-m", "base"], check=True)  # fmt: skip
    sha = run(["git", "-C", str(repo), "rev-parse", "--short", "HEAD"], check=True).stdout.strip()
    assert _refusal_fix(repo / "specs") == command(
        *_PHASE.SCRIPT, "phase", "IMPLEMENTATION", "--sha", sha
    )


def test_a_bad_sha_fix_without_git_is_an_act_never_a_shell_substitution(tmp_path: Path) -> None:
    (tmp_path / "specs").mkdir()
    fix = _refusal_fix(tmp_path / "specs")
    assert "$(" not in fix and fix.startswith("Agent action: run `")
    assert fix.count("Agent action:") == 1
