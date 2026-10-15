"""``dadaia ci``: where the pre-push gate lands, and the ref gate judging ``old new ref`` lines."""

from __future__ import annotations

import shlex
import subprocess
from pathlib import Path

from typer.testing import CliRunner

from dadaia_workspace.cli.commands import ci
from dadaia_workspace.cli.main import app

_runner = CliRunner()


def test_install_hook_writes_and_refuses_overwrite_without_force(
    monkeypatch, tmp_path: Path
) -> None:
    """Under core.hooksPath the gate lands
    where git runs hooks; a hook already there is refused non-zero with a fix: line."""
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "core.hooksPath", ".husky"], check=True)
    monkeypatch.setattr(ci, "_repo_root", lambda: tmp_path)

    result = _runner.invoke(app, ["ci", "install-hook"])
    assert result.exit_code == 0

    assert not (tmp_path / ".git" / "hooks" / "pre-push").exists()
    pre_push = tmp_path / ".husky" / "pre-push"
    assert pre_push.exists()
    pre_push_text = pre_push.read_text()
    assert "ci push-gate-check" in pre_push_text

    # second call without --force is refused (pre-push already present).
    refused = _runner.invoke(app, ["ci", "install-hook"])
    assert refused.exit_code == 1
    assert f"ci install-hook --force --repo {tmp_path.as_posix()}" in refused.output
    assert "fix: " in refused.output
    # --force overwrites both.
    assert _runner.invoke(app, ["ci", "install-hook", "--force"]).exit_code == 0


_WORK = "feature/0.6.0"
_WORK_REF = f"refs/heads/{_WORK}"


def _git(repo: Path, *argv: str) -> str:
    done = subprocess.run(
        ["git", "-C", str(repo), *argv], capture_output=True, text=True, check=True
    )
    return done.stdout.strip()


def _commit(repo: Path, **files: str) -> str:
    for name, text in files.items():
        target = repo / name.replace("__", "/")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "c")
    return _git(repo, "rev-parse", "HEAD")


def _work_repo(tmp_path: Path) -> tuple[Path, str]:
    """A repo on the work branch whose origin holds the first commit; returns (repo, that sha)."""
    origin = tmp_path / "origin.git"
    subprocess.run(["git", "init", "-q", "--bare", str(origin)], check=True)
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "-b", _WORK, str(repo)], check=True)
    _git(repo, "config", "user.email", "t@example.com")
    _git(repo, "config", "user.name", "T")
    base = _commit(repo, **{"seed.txt": "seed\n"})
    _git(repo, "remote", "add", "origin", str(origin))
    _git(repo, "push", "-q", "origin", _WORK)
    _git(repo, "fetch", "-q", "origin")
    return repo, base


def _ref_gate(monkeypatch, repo: Path, *lines: str):
    monkeypatch.setattr(ci, "_repo_root", lambda: repo)
    return _runner.invoke(app, ["ci", "ref-gate-check"], input="".join(f"{x}\n" for x in lines))


def test_ref_gate_refuses_a_work_update_off_origin_with_the_worktree_route(
    monkeypatch, tmp_path: Path
) -> None:
    """The one fix opens a tree through the worktree tool; no ref moves."""
    repo, base = _work_repo(tmp_path)
    tip = _commit(repo, **{"src__a.py": "x = 1\n"})

    result = _ref_gate(monkeypatch, repo, f"{base} {tip} {_WORK_REF}")

    assert result.exit_code == 1
    assert "[ref-gate] BLOCKED" in result.output
    assert result.output.count("fix: ") == 1
    fix = shlex.split(result.output.rsplit("fix: ", 1)[1])
    assert fix[0].endswith("dadaia")
    assert fix[1:] == ["worktree", "new", "repo", "change"]
    assert _git(repo, "rev-parse", _WORK_REF) == tip


def test_ref_gate_passes_the_origin_sha_creation_and_a_non_work_ref(
    monkeypatch, tmp_path: Path
) -> None:
    repo, base = _work_repo(tmp_path)
    tip = _commit(repo, **{"src__a.py": "x = 1\n"})
    zero = "0" * 40

    assert _ref_gate(monkeypatch, repo, f"{tip} {base} {_WORK_REF}").exit_code == 0
    assert _ref_gate(monkeypatch, repo, f"{zero} {tip} {_WORK_REF}").exit_code == 0
    assert _ref_gate(monkeypatch, repo, f"{base} {tip} refs/heads/wt/x").exit_code == 0
    assert _ref_gate(monkeypatch, repo).exit_code == 0


def test_ref_gate_passes_a_work_branch_with_no_origin(monkeypatch, tmp_path: Path) -> None:
    repo, base = _work_repo(tmp_path)
    tip = _commit(repo, **{"src__a.py": "x = 1\n"})
    _git(repo, "update-ref", "-d", f"refs/remotes/origin/{_WORK}")

    assert _ref_gate(monkeypatch, repo, f"{base} {tip} {_WORK_REF}").exit_code == 0


def test_ref_gate_passes_a_work_update_touching_only_audits(monkeypatch, tmp_path: Path) -> None:
    repo, base = _work_repo(tmp_path)
    tip = _commit(repo, **{"specs__audits__2026-10-14.md": "finding\n"})

    result = _ref_gate(monkeypatch, repo, f"{base} {tip} {_WORK_REF}")

    assert result.exit_code == 0, result.output


def test_ref_gate_refuses_an_audit_update_that_touches_any_other_path(
    monkeypatch, tmp_path: Path
) -> None:
    repo, base = _work_repo(tmp_path)
    tip = _commit(repo, **{"specs__audits__a.md": "finding\n", "src__a.py": "x = 1\n"})

    result = _ref_gate(monkeypatch, repo, f"{base} {tip} {_WORK_REF}")

    assert result.exit_code == 1
    assert "[ref-gate] BLOCKED" in result.output
    assert result.output.count("fix: ") == 1
