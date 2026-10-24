"""The deploy gate `evals/scripts/gate.py HEAD_SHA`, run as a subprocess in a throwaway git
repository with a fake `gh` first on PATH. It passes (exit 0, prints the evaluated sha and the run
URL) only when the tree diff from the evaluated sha to the head lists the release-bookkeeping set;
otherwise it exits 1 with one `fix: Agent action:` line and no traceback.

Owner: dd-sw-engineer-sr
"""

from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path

import pytest

from tests.helpers.oslib import run, write_text

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(shutil.which("sh") is None, reason="the fake `gh` is a POSIX sh script"),
]

_GATE = Path(__file__).resolve().parents[2] / "evals" / "scripts" / "gate.py"
_URL = "https://github.com/o/r/actions/runs"
_FIX = "fix: Agent action: "
_DISPATCH = "gh workflow run eval.yml --ref feature/0.5.0"
_PYPROJECT = 'name = "x"\nversion = "0.5.0"\n'


def _git(repo: Path, *argv: str) -> str:
    cmd = ["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false", *argv]
    done = run(cmd, cwd=repo, timeout=60)
    assert done.returncode == 0, done.stderr
    return done.stdout.strip()


def _commit(repo: Path, files: dict[str, str]) -> str:
    for name, text in files.items():
        (repo / name).parent.mkdir(parents=True, exist_ok=True)
        write_text(repo / name, text)
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "c")
    return _git(repo, "rev-parse", "HEAD")


def _fixture(tmp_path: Path) -> tuple[Path, str]:
    """A repo whose commit E holds the bookkeeping files and one source file; returns it and E."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "--initial-branch=main")
    e = _commit(
        repo,
        {
            "specs/releases/0.5.0/_RELEASE.json": "{}\n",
            "CHANGELOG.md": "# log\n",
            ".release-please-manifest.json": '{".": "0.5.0"}\n',
            "pyproject.toml": _PYPROJECT,
            "src/mod.py": "A = 1\n",
        },
    )
    return repo, e


def _run(sha: str, *, event: str = "workflow_dispatch", conclusion: str = "success") -> dict:
    return {"head_sha": sha, "event": event, "conclusion": conclusion, "html_url": f"{_URL}/{sha}"}


def _gate(tmp_path: Path, repo: Path, runs: list[dict], head: str) -> tuple[int, str]:
    """Run the gate with a fake `gh` that lists *runs*, newest first."""
    body = {"workflow_runs": runs}
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    write_text(tmp_path / "runs.json", json.dumps(body))
    gh = bin_dir / "gh"
    write_text(gh, f"#!/bin/sh\ncat '{(tmp_path / 'runs.json').as_posix()}'\n")
    gh.chmod(0o755)
    env = os.environ | {
        "GITHUB_REPOSITORY": "o/r",
        "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
    }
    done = run([sys.executable, str(_GATE), head], cwd=repo, env=env, timeout=60)
    return done.returncode, done.stdout + done.stderr


def _assert_failed_with_fix_line(code: int, out: str) -> None:
    assert code == 1
    assert "Traceback" not in out
    fixes = [ln for ln in out.splitlines() if ln.startswith(_FIX)]
    assert len(fixes) == 1
    assert _DISPATCH in fixes[0]


def test_bookkeeping_only_diff_passes_and_prints_the_sha_and_url(tmp_path: Path) -> None:
    repo, e = _fixture(tmp_path)
    head = _commit(
        repo,
        {
            "specs/releases/0.5.0/_RELEASE.json": '{"phase": "CLOSURE"}\n',
            "CHANGELOG.md": "# log\n\n## 0.5.0\n",
            ".release-please-manifest.json": '{".": "0.5.1"}\n',
            "pyproject.toml": 'name = "x"\nversion = "0.5.1"\n',
        },
    )
    code, out = _gate(tmp_path, repo, [_run(e)], head)
    assert code == 0, out
    assert e in out
    assert f"{_URL}/{e}" in out


def test_source_file_changed_after_e_fails(tmp_path: Path) -> None:
    repo, e = _fixture(tmp_path)
    head = _commit(repo, {"src/mod.py": "A = 2\n"})
    _assert_failed_with_fix_line(*_gate(tmp_path, repo, [_run(e)], head))


def test_pyproject_line_other_than_version_changed_fails(tmp_path: Path) -> None:
    repo, e = _fixture(tmp_path)
    head = _commit(repo, {"pyproject.toml": 'name = "y"\nversion = "0.5.0"\n'})
    _assert_failed_with_fix_line(*_gate(tmp_path, repo, [_run(e)], head))


def test_good_run_sha_absent_from_the_repo_fails_without_traceback(tmp_path: Path) -> None:
    repo, _ = _fixture(tmp_path)
    head = _commit(repo, {"CHANGELOG.md": "# log\n\nmore\n"})
    _assert_failed_with_fix_line(*_gate(tmp_path, repo, [_run("0" * 39 + "1")], head))


def _allowed_head(repo: Path) -> str:
    return _commit(repo, {"CHANGELOG.md": "# log\n\nmore\n"})


def test_failed_run_fails(tmp_path: Path) -> None:
    repo, e = _fixture(tmp_path)
    head = _allowed_head(repo)
    _assert_failed_with_fix_line(*_gate(tmp_path, repo, [_run(e, conclusion="failure")], head))


def test_no_run_fails(tmp_path: Path) -> None:
    repo, _ = _fixture(tmp_path)
    head = _allowed_head(repo)
    _assert_failed_with_fix_line(*_gate(tmp_path, repo, [], head))


def test_push_event_run_fails(tmp_path: Path) -> None:
    repo, e = _fixture(tmp_path)
    head = _allowed_head(repo)
    _assert_failed_with_fix_line(*_gate(tmp_path, repo, [_run(e, event="push")], head))


def test_older_good_run_passes_behind_a_newer_failed_run(tmp_path: Path) -> None:
    repo, e = _fixture(tmp_path)
    later = _commit(repo, {"src/mod.py": "A = 2\n"})
    head = _allowed_head(repo)
    runs = [_run(later, conclusion="failure"), _run(e)]
    code, out = _gate(tmp_path, repo, runs, head)
    assert code == 0, out
    assert e in out
    assert f"{_URL}/{e}" in out
