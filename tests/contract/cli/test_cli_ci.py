"""Public CLI contracts for `dadaia ci` (pre-push gate, T-GATE-01)."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from typer.testing import CliRunner

from dadaia_workspace.cli.commands import ci
from dadaia_workspace.cli.main import app

_runner = CliRunner()


def test_preflight_passes_when_all_checks_pass(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(ci, "_repo_root", lambda: tmp_path)
    monkeypatch.setattr(ci, "subprocess_runner", lambda root: lambda argv: (0, "ok"))

    result = _runner.invoke(app, ["ci", "preflight"])

    assert result.exit_code == 0
    assert "All preflight checks passed" in result.output


def test_preflight_blocks_when_a_check_fails(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(ci, "_repo_root", lambda: tmp_path)

    def factory(root: Path):
        def run(argv: Sequence[str]) -> tuple[int, str]:
            # argv may carry absolute tool paths (runner-derived resolution,
            # T-011-06) — match by substring, not exact element.
            if any("mypy" in part for part in argv):
                return (1, "type error on line 1")
            return (0, "ok")

        return run

    monkeypatch.setattr(ci, "subprocess_runner", factory)

    result = _runner.invoke(app, ["ci", "preflight", "--no-fail-fast"])

    assert result.exit_code == 1
    assert "Pre-push gate FAILED" in result.output
    assert "mypy --strict" in result.output


def test_install_hook_writes_both_executable_hooks(monkeypatch, tmp_path: Path) -> None:
    (tmp_path / ".git" / "hooks").mkdir(parents=True)
    monkeypatch.setattr(ci, "_repo_root", lambda: tmp_path)

    result = _runner.invoke(app, ["ci", "install-hook"])
    assert result.exit_code == 0

    pre_push = tmp_path / ".git" / "hooks" / "pre-push"
    pre_commit = tmp_path / ".git" / "hooks" / "pre-commit"
    assert pre_push.exists()
    assert pre_commit.exists()
    assert "ci preflight" in pre_push.read_text()
    assert "ci push-gate-check" in pre_push.read_text()
    assert "ci pre-commit-check" in pre_commit.read_text()


def test_install_hook_refuses_overwrite_without_force(monkeypatch, tmp_path: Path) -> None:
    (tmp_path / ".git" / "hooks").mkdir(parents=True)
    monkeypatch.setattr(ci, "_repo_root", lambda: tmp_path)

    assert _runner.invoke(app, ["ci", "install-hook"]).exit_code == 0
    # second call without --force is refused (pre-commit already present).
    assert _runner.invoke(app, ["ci", "install-hook"]).exit_code == 1
    # --force overwrites both.
    assert _runner.invoke(app, ["ci", "install-hook", "--force"]).exit_code == 0


def _init_workspace(tmp_path: Path, slug: str) -> Path:
    """Minimal workspace: sentinel state file + a repo dir under repos/<slug>."""
    (tmp_path / ".dadaia" / "states").mkdir(parents=True)
    (tmp_path / ".dadaia" / "states" / "spec_contexts.json").write_text("{}", encoding="utf-8")
    repo = tmp_path / "repos" / slug
    repo.mkdir(parents=True)
    return repo


def test_pre_commit_check_allows_when_no_lease(monkeypatch, tmp_path: Path) -> None:
    repo = _init_workspace(tmp_path, "demo")
    monkeypatch.setattr(ci, "_repo_root", lambda: repo)
    monkeypatch.setenv("WORKSPACE_ROOT", str(tmp_path))

    result = _runner.invoke(app, ["ci", "pre-commit-check"])
    assert result.exit_code == 0


def test_pre_commit_check_blocks_on_live_foreign_lease(monkeypatch, tmp_path: Path) -> None:
    import json
    from datetime import UTC, datetime

    import dadaia_workspace.container as container
    import dadaia_workspace.infrastructure.process_probe_adapter as ppa
    from dadaia_workspace.core.protocols.process_ancestry import Ancestry

    repo = _init_workspace(tmp_path, "demo")
    lock_dir = tmp_path / ".dadaia" / "states" / "ctx_locks"
    lock_dir.mkdir(parents=True)
    (lock_dir / "demo.lock.json").write_text(
        json.dumps(
            {
                "context": "demo",
                "session_id": "foreign-holder",
                "pid": 424242,  # a foreign holder pid, forced alive + non-ancestor below
                "heartbeat": datetime.now(tz=UTC).isoformat(),
                "ttl": 120,
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(ci, "_repo_root", lambda: repo)
    monkeypatch.setenv("WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.delenv("DADAIA_SESSION_ID", raising=False)

    # Force a deterministic NOT_ANCESTOR verdict (patch the container the CLI imports from).
    class _NotAncestor:
        def is_ancestor(self, _a: int, _d: int) -> Ancestry:
            return Ancestry.NOT_ANCESTOR

    monkeypatch.setattr(container, "build_process_ancestry", lambda: _NotAncestor())
    # Holder pid must read as alive (pid-veto keeps the lease live ⇒ block path).
    monkeypatch.setattr(ppa.OsProcessProbe, "is_pid_alive", lambda self, pid: True)

    result = _runner.invoke(app, ["ci", "pre-commit-check"])
    assert result.exit_code == 1
    assert "foreign-holder" in result.output


def test_push_gate_check_blocks_without_approve(monkeypatch, tmp_path: Path) -> None:
    repo = _init_workspace(tmp_path, "demo")
    monkeypatch.setattr(ci, "_repo_root", lambda: repo)
    monkeypatch.setenv("WORKSPACE_ROOT", str(tmp_path))

    sha = "a" * 40
    zero = "0" * 40
    result = _runner.invoke(
        app,
        ["ci", "push-gate-check"],
        input=f"refs/heads/main {sha} refs/heads/main {zero}\n",
    )
    assert result.exit_code == 1
    assert "BLOCKED" in result.output


def test_push_gate_check_passes_with_approve(monkeypatch, tmp_path: Path) -> None:
    import json

    repo = _init_workspace(tmp_path, "demo")
    monkeypatch.setattr(ci, "_repo_root", lambda: repo)
    monkeypatch.setenv("WORKSPACE_ROOT", str(tmp_path))

    sha = "a" * 40
    zero = "0" * 40
    handoff_dir = tmp_path / ".dadaia" / "handoff" / "demo"
    handoff_dir.mkdir(parents=True)
    (handoff_dir / "sec.handoff.json").write_text(
        json.dumps(
            {
                "schema_version": "handoff-v1.1",
                "agent": "security-reviewer",
                "verdict": "APPROVED",
                "metrics": {"commit_sha": sha},
                "artifact": {"type": "other"},
            }
        ),
        encoding="utf-8",
    )
    result = _runner.invoke(
        app,
        ["ci", "push-gate-check"],
        input=f"refs/heads/main {sha} refs/heads/main {zero}\n",
    )
    assert result.exit_code == 0
