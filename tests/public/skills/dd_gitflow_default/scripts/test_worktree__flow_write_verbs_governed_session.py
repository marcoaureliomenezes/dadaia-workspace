"""Every write verb of `backlog.py`, `release.py` and `worktree.py` asks the one governed-session
decider (`context session-check`, stood in for by the workspace stub CLI) before it writes: on a
harness that names its subagent, a session with no live record is refused with the decider's fix
line and nothing is written; a live record, or a caller with no id, passes. Read-only verbs are not asked."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

from tests.fixtures.harness_env import suite_env
from tests.helpers.oslib import run as run_text
from tests.helpers.oslib import write_text
from tests.helpers.worktree_ws import RELAUNCH, fixes, make_workspace, record_session

_SKILLS = Path(__file__).resolve().parents[5] / "dadaia_workspace/public/skills"
_SCRIPT = {
    "backlog": _SKILLS / "dd-backlog-definition/scripts/backlog.py",
    "release": _SKILLS / "dd-release-implementation/scripts/release.py",
    "worktree": _SKILLS / "dd-gitflow-default/scripts/worktree.py",
}
#: A judged harness: its session-id env var (each registry row that names a subagent key).
_HARNESS = {"claude": "CLAUDE_CODE_SESSION_ID", "codex": "CODEX_THREAD_ID"}
_SPECS = "repos/r/specs"
_WRITES = [
    pytest.param("backlog", ["new", "s", "--title", "t", "--specs", _SPECS], id="backlog-new"),
    pytest.param(
        "backlog", ["exit", "s", "--disposition", "dropped", "--specs", _SPECS], id="backlog-exit"
    ),
    pytest.param("release", ["new", "0.6.0", "--specs", _SPECS], id="release-new"),
    pytest.param("release", ["phase", "CLOSURE", "--specs", _SPECS], id="release-phase"),
    pytest.param("release", ["memory", "--specs", _SPECS], id="release-memory"),
    pytest.param("release", ["ship", "--specs", _SPECS], id="release-ship"),
    pytest.param("worktree", ["new", "r", "0.5.0/wt-backlog-x"], id="worktree-new"),
    pytest.param("worktree", ["merge", "worktrees/r/0.5.0/wt-backlog-x"], id="worktree-merge"),
    pytest.param("worktree", ["clean", "worktrees/r/0.5.0/wt-backlog-x"], id="worktree-clean"),
    pytest.param("worktree", ["sync", "worktrees/r/0.5.0/wt-backlog-x"], id="worktree-sync"),
    pytest.param("worktree", ["pause", "worktrees/r/0.5.0/wt-backlog-x"], id="worktree-pause"),
    pytest.param("worktree", ["resume", "worktrees/r/0.5.0/wt-backlog-x"], id="worktree-resume"),
]
_READS = [
    pytest.param("backlog", ["check", "--specs", _SPECS], id="backlog-check"),
    pytest.param("release", ["check", "--specs", _SPECS], id="release-check"),
    pytest.param("release", ["drift", "--specs", _SPECS], id="release-drift"),
    pytest.param("worktree", ["list"], id="worktree-list"),
]
_HARNESSES = pytest.mark.parametrize("var", _HARNESS.values(), ids=_HARNESS)


@pytest.fixture
def root(tmp_path: Path) -> Path:
    make_workspace(tmp_path)
    (tmp_path / _SPECS / "backlog").mkdir()
    write_text(
        tmp_path / _SPECS / "backlog/BACKLOG.json",
        json.dumps({"schema": "backlog-v1", "active": []}),
    )
    return tmp_path


def _run(root: Path, script: str, argv: list[str], var: str | None, sid: str = "sess-1"):
    env = suite_env(
        os.environ,
        Path.home(),
        overrides={
            "HOME": str(root),
            "PATH": os.environ["PATH"],
            "GIT_CONFIG_NOSYSTEM": "1",
            **({var: sid} if var else {}),
        },
    )
    return run_text([sys.executable, str(_SCRIPT[script]), *argv], cwd=root, env=env)


def _snapshot(root: Path) -> dict[str, bytes]:
    return {
        str(p.relative_to(root)): p.read_bytes()
        for top in ("repos", "worktrees")
        for p in sorted((root / top).rglob("*"))
        if p.is_file() and ".git/" not in p.as_posix() + "/"
    } | {str(p.relative_to(root)): b"" for p in (root / "worktrees").rglob("*") if p.is_dir()}


@_HARNESSES
@pytest.mark.parametrize(("script", "argv"), _WRITES)
def test_a_judged_session_with_no_record_is_refused_and_nothing_is_written(
    root: Path, script: str, argv: list[str], var: str
) -> None:
    before = _snapshot(root)

    refused = _run(root, script, argv, var)

    assert refused.returncode == 1 and fixes(refused) == [RELAUNCH], refused.stderr
    assert _snapshot(root) == before


@_HARNESSES
@pytest.mark.parametrize(
    ("script", "argv"),
    [_WRITES[0], _WRITES[3], _WRITES[6]],
    ids=["backlog-new", "release-phase", "worktree-new"],
)
def test_a_judged_session_with_a_live_record_is_not_refused(
    root: Path, script: str, argv: list[str], var: str
) -> None:
    record_session(root, "sess-1")

    done = _run(root, script, argv, var)

    assert RELAUNCH not in fixes(done), done.stderr


@pytest.mark.parametrize(
    ("script", "argv"),
    [_WRITES[0], _WRITES[3], _WRITES[6]],
    ids=["backlog-new", "release-phase", "worktree-new"],
)
def test_a_caller_with_no_session_id_is_not_judged(
    root: Path, script: str, argv: list[str]
) -> None:
    done = _run(root, script, argv, None)

    assert RELAUNCH not in fixes(done), done.stderr


@_HARNESSES
@pytest.mark.parametrize(("script", "argv"), _READS)
def test_a_read_only_verb_is_not_asked(root: Path, script: str, argv: list[str], var: str) -> None:
    done = _run(root, script, argv, var)

    assert RELAUNCH not in fixes(done), done.stderr
