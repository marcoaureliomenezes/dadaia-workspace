"""``dadaia ci``: where the pre-push gate lands, and the ref gate judging ``old new ref`` lines."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.commands import ci
from dadaia_workspace.cli.main import app
from dadaia_workspace.core.cli_line import fix_line
from dadaia_workspace.core.platform import quote
from tests.helpers.oslib import read_text, run, write_text
from tests.helpers.oslib import run as os_run

_runner = CliRunner()


def test_install_hook_writes_and_refuses_overwrite_without_force(
    monkeypatch, tmp_path: Path
) -> None:
    """Under core.hooksPath the gate lands
    where git runs hooks; a hook already there is refused non-zero with a fix: line."""
    os_run(["git", "init", "-q", str(tmp_path)], check=True)
    os_run(["git", "-C", str(tmp_path), "config", "core.hooksPath", ".husky"], check=True)
    monkeypatch.setattr(ci, "_repo_root", lambda: tmp_path)

    result = _runner.invoke(app, ["ci", "install-hook"])
    assert result.exit_code == 0

    assert not (tmp_path / ".git" / "hooks" / "pre-push").exists()
    pre_push = tmp_path / ".husky" / "pre-push"
    assert pre_push.exists()
    pre_push_text = read_text(pre_push)
    assert "ci push-gate-check" in pre_push_text

    # second call without --force is refused (pre-push already present).
    refused = _runner.invoke(app, ["ci", "install-hook"])
    assert refused.exit_code == 1
    assert f"ci install-hook --force --repo {quote(str(tmp_path))}" in refused.output
    assert "fix: " in refused.output
    # --force overwrites both.
    assert _runner.invoke(app, ["ci", "install-hook", "--force"]).exit_code == 0


_WORK = "feature/0.6.0"
_WORK_REF = f"refs/heads/{_WORK}"


def _git(repo: Path, *argv: str) -> str:
    done = run(["git", "-C", str(repo), *argv], check=True)
    return done.stdout.strip()


def _commit(repo: Path, **files: str) -> str:
    for name, text in files.items():
        target = repo / name.replace("__", "/")
        target.parent.mkdir(parents=True, exist_ok=True)
        write_text(target, text)
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "c")
    return _git(repo, "rev-parse", "HEAD")


def _work_repo(tmp_path: Path) -> tuple[Path, str]:
    """A repo on the work branch whose origin holds the first commit; returns (repo, that sha)."""
    origin = tmp_path / "origin.git"
    os_run(["git", "init", "-q", "--bare", str(origin)], check=True)
    repo = tmp_path / "repo"
    repo.mkdir()
    os_run(["git", "init", "-q", "-b", _WORK, str(repo)], check=True)
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
    fix = result.output.rsplit("fix: ", 1)[1]
    assert fix.startswith("Agent action: ")
    assert fix_line(None, "worktree", "new", "repo") in fix
    assert _git(repo, "rev-parse", _WORK_REF) == tip


def test_ref_gate_passes_the_origin_sha_creation_and_a_non_work_ref(
    monkeypatch, tmp_path: Path
) -> None:
    repo, base = _work_repo(tmp_path)
    tip = _commit(repo, **{"src__a.py": "x = 1\n"})

    assert _ref_gate(monkeypatch, repo, f"{tip} {base} {_WORK_REF}").exit_code == 0
    assert _ref_gate(monkeypatch, repo, f"{base} {tip} refs/heads/wt/x").exit_code == 0
    assert _ref_gate(monkeypatch, repo).exit_code == 0


@pytest.mark.parametrize("zeros", [40, 64])
def test_ref_gate_refuses_a_zero_old_line_for_an_existing_work_ref_off_origin(
    monkeypatch, tmp_path: Path, zeros: int
) -> None:
    """``git branch -f`` and ``update-ref`` with no old sha hand git's zero old sha.

    The reference-transaction hook resolves a zero old sha for an existing ref to its current
    value before it calls the verb, so the old sha arrives resolved; this test feeds the verb the
    zero itself.
    """
    repo, _ = _work_repo(tmp_path)
    _commit(repo, **{"src__a.py": "x = 1\n"})
    other = _commit(repo, **{"src__b.py": "y = 2\n"})
    _git(repo, "update-ref", _WORK_REF, _git(repo, "rev-parse", "HEAD~1"))

    result = _ref_gate(monkeypatch, repo, f"{'0' * zeros} {other} {_WORK_REF}")

    assert result.exit_code == 1
    assert "[ref-gate] BLOCKED" in result.output


def test_ref_gate_passes_a_zero_old_line_creating_the_work_ref(monkeypatch, tmp_path: Path) -> None:
    repo, base = _work_repo(tmp_path)
    tip = _commit(repo, **{"src__a.py": "x = 1\n"})
    _git(repo, "update-ref", "-d", _WORK_REF)

    assert _ref_gate(monkeypatch, repo, f"{'0' * 40} {base} {_WORK_REF}").exit_code == 0
    assert _ref_gate(monkeypatch, repo, f"{'0' * 40} {tip} {_WORK_REF}").exit_code == 1


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


def test_ref_gate_refuses_when_the_move_check_faults(monkeypatch, tmp_path: Path) -> None:
    """A fault while reading the move's facts is a refusal the hook can read, never a fail-open."""
    from dadaia_workspace import container
    from dadaia_workspace.core.exceptions import GitSyncError

    repo, base = _work_repo(tmp_path)
    tip = _commit(repo, **{"specs__audits__2026-10-14.md": "finding\n"})
    real = container.build_git_client()

    class Faulting:
        def __getattr__(self, name: str):
            return getattr(real, name)

        def git(self, root: Path, *args: str) -> str:
            if args[0] == "rev-list":
                raise GitSyncError("git rev-list failed")
            return real.git(root, *args)

    monkeypatch.setattr(container, "build_git_client", Faulting)

    result = _ref_gate(monkeypatch, repo, f"{base} {tip} {_WORK_REF}")

    assert result.exit_code == 1
    assert "[ref-gate] BLOCKED" in result.output
    assert result.output.count("fix: ") == 1


def test_ref_gate_refuses_recreating_the_work_ref_off_origin_with_one_fix(
    monkeypatch, tmp_path: Path
) -> None:
    repo, _ = _work_repo(tmp_path)
    tip = _commit(repo, **{"src__a.py": "x = 1\n"})
    _git(repo, "update-ref", "-d", _WORK_REF)

    result = _ref_gate(monkeypatch, repo, f"{'0' * 40} {tip} {_WORK_REF}")

    assert result.exit_code == 1
    assert "[ref-gate] BLOCKED" in result.output
    assert result.output.count("fix: ") == 1
