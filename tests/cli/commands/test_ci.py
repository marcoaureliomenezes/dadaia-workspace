"""`ci push-gate-check` CLI wiring for the v0.9.0 range-scoped denylist scan.

Pins two composition-root guarantees:

* ``push-gate-check`` always builds and passes a real ``GitObjectReader`` into
  ``push_gate_decision``, never omitted and never ``None``.
* A3.5 — the stderr mode line distinguishes "operator denylist + baseline" (a
  ``DADAIA_PRIVACY_DENYLIST`` file present) from "baseline only" (absent).
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace import container
from dadaia_workspace.cli.commands import ci
from dadaia_workspace.cli.main import app
from dadaia_workspace.core.cli_line import fix_line
from dadaia_workspace.core.specs_version import CANONICAL_SPECS_VERSION

_runner = CliRunner()
_ZERO = "0" * 40


def _init_repo(path: Path) -> str:
    """A real, minimal git repo with one commit — returns the commit sha."""
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.email", "t@example.com"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "T"], cwd=path, check=True)
    (path / "seed.txt").write_text("seed\n", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=path, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "seed"], cwd=path, check=True)
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=path, capture_output=True, text=True, check=True
    ).stdout.strip()


def test_push_gate_check_always_wires_a_real_object_source(monkeypatch, tmp_path: Path) -> None:
    """A tag push whose commit carries a denylisted term is refused: the scan reads the real range."""
    repo = tmp_path / "repo"
    _init_repo(repo)
    (repo / "leak.md").write_text("zz-synthetic-term\n", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "leak"], cwd=repo, check=True)
    tip_sha = _git(repo, "rev-parse", "HEAD")

    monkeypatch.setattr(ci, "_repo_root", lambda: repo)
    monkeypatch.setattr(container, "load_denylist_terms", lambda: (("zz-synthetic-term", "t"),))

    result = _runner.invoke(
        app, ["ci", "push-gate-check"], input=f"refs/tags/v1 {tip_sha} refs/tags/v1 {_ZERO}\n"
    )

    assert result.exit_code == 1, result.output
    assert "leak.md:1" in result.output


def _stamped_specs(repo: Path, version: int) -> str:
    """Commit the stamp: the gate reads the pushed commit, never the checkout."""
    (repo / "specs" / "constitution.md").write_text(
        f"---\nspecs_pattern_version: {version}\n---\n# constitution\n", encoding="utf-8"
    )
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "stamp"], cwd=repo, check=True)
    return f"refs/heads/feature/0.0.1 {_git(repo, 'rev-parse', 'HEAD')} refs/heads/feature/0.0.1 {_ZERO}\n"


def test_canon_scan_does_not_apply_to_a_tree_stamped_below_the_canon(
    monkeypatch, tmp_path: Path
) -> None:
    """Bug pre-push-canon-scan-not-range-scoped: a pushed tree stamped 5 is foreign — the
    push proceeds printing state()'s fix; stamped canonical, the same path is refused."""
    repo = tmp_path / "repo"
    _init_repo(repo)
    (repo / "specs" / "backlog").mkdir(parents=True)
    (repo / "specs" / "backlog" / "candidates.md").write_text("x\n", encoding="utf-8")
    monkeypatch.setattr(ci, "_repo_root", lambda: repo)

    result = _runner.invoke(app, ["ci", "push-gate-check"], input=_stamped_specs(repo, 5))
    assert result.exit_code == 0, result.output
    # sa-fix-lines-not-built-by-cli-line#S1: the fix is named through the builder.
    assert (
        fix_line(None, "specs", "init", "--specs-dir", str(repo / "specs"), "--replace-foreign")
        in result.output
    )

    result = _runner.invoke(
        app, ["ci", "push-gate-check"], input=_stamped_specs(repo, CANONICAL_SPECS_VERSION)
    )
    assert result.exit_code == 1
    assert "specs/backlog/candidates.md" in result.output


def test_mode_line_distinguishes_operator_denylist_from_baseline_only(
    monkeypatch, tmp_path: Path
) -> None:
    """A3.5: the stderr mode line names which term sources actually ran.

    Patches the ``load_denylist_terms`` composition-root seam directly rather than
    relying on ``DADAIA_PRIVACY_DENYLIST``/filesystem discovery — this sandbox's own
    real workspace carries an operator denylist file, and
    ``infrastructure.privacy_check``'s workspace-root walk resolves from ``cwd``
    (the test's own tmp workspace is its cwd), so a
    file/env-based test would spuriously observe the ambient real denylist. The mode
    line's OWN branching logic — reacting to whatever term-loading returns — is what
    A3.5 actually pins.
    """
    repo = tmp_path / "repo"
    tip_sha = _init_repo(repo)

    monkeypatch.setattr(ci, "_repo_root", lambda: repo)

    monkeypatch.setattr(container, "load_denylist_terms", lambda: ())
    baseline_only = _runner.invoke(
        app,
        ["ci", "push-gate-check"],
        input=f"refs/tags/v1 {tip_sha} refs/tags/v1 {_ZERO}\n",
    )
    assert "baseline only" in baseline_only.output
    assert "operator denylist + baseline" not in baseline_only.output

    monkeypatch.setattr(container, "load_denylist_terms", lambda: (("zz-synthetic-term", "test"),))
    with_operator = _runner.invoke(
        app,
        ["ci", "push-gate-check"],
        input=f"refs/tags/v2 {tip_sha} refs/tags/v2 {_ZERO}\n",
    )
    assert "operator denylist + baseline" in with_operator.output


# ── 0.5.0 AC5.1/AC5.4 (T-050-14): the bootstrap birth through the REAL reader ──────────


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t.invalid", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def test_a_malformed_privacy_baseline_fails_the_gate_closed_with_one_fix_line(
    monkeypatch, capsys, tmp_path: Path
) -> None:
    from dadaia_workspace.cli import main
    from dadaia_workspace.core.skill_owner import load_owner
    from dadaia_workspace.infrastructure import privacy_check

    def unreadable():
        raise load_owner("dd-bug-resolution", "_refusal").Refusal(
            "privacy baseline is unreadable", "Operator action: reinstall the workspace"
        )

    monkeypatch.setattr(privacy_check, "load_baseline", unreadable)
    monkeypatch.setattr(container, "load_denylist_terms", lambda: ())
    monkeypatch.setattr(ci, "_repo_root", lambda: tmp_path)
    monkeypatch.setattr("sys.argv", ["dadaia", "ci", "push-gate-check"])

    with pytest.raises(SystemExit) as gone:
        main._safe_app()

    err = capsys.readouterr().err
    assert gone.value.code == 1
    assert "defect" not in err
    assert "privacy baseline is unreadable" in err
    assert [ln for ln in err.splitlines() if ln.startswith("fix:")] == [
        "fix: Operator action: reinstall the workspace"
    ]
