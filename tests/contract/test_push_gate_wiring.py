"""`ci push-gate-check` CLI wiring for the v0.9.0 range-scoped denylist scan.

Intent: CONTRACT — v0.9.0 A3.5, A6.3

Pins two composition-root guarantees:

* A6.3 — ``push-gate-check`` ALWAYS builds and passes a real ``GitObjectReader`` into
  ``push_gate_decision`` — never omitted, never ``None`` (FR6 row 4/FR7 row A7.2).
* A3.5 — the stderr mode line distinguishes "operator denylist + baseline" (a
  ``DADAIA_PRIVACY_DENYLIST`` file present) from "baseline only" (absent).
"""

from __future__ import annotations

import subprocess
from collections.abc import Iterable
from pathlib import Path

from typer.testing import CliRunner

from dadaia_workspace import container
from dadaia_workspace.cli.commands import ci
from dadaia_workspace.cli.main import app
from dadaia_workspace.core.protocols.git_object_reader import ScannedObject

_runner = CliRunner()
_ZERO = "0" * 40


class _SpyObjectSource:
    """Wraps no real git — records every call so the test can assert it was reached."""

    def __init__(self) -> None:
        self.calls: list[tuple[Path, str, str]] = []

    def new_objects(self, repo: Path, local_sha: str, remote_sha: str) -> Iterable[ScannedObject]:
        self.calls.append((repo, local_sha, remote_sha))
        return ()


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
    """A6.3: the scan step is genuinely reached — the spy sees at least one call — for
    a tag push, which has no branch policy to short-circuit it."""
    repo = tmp_path / "repo"
    tip_sha = _init_repo(repo)

    monkeypatch.setattr(ci, "_repo_root", lambda: repo)
    monkeypatch.setenv("WORKSPACE_ROOT", str(tmp_path))

    spy = _SpyObjectSource()
    monkeypatch.setattr(container, "build_git_object_reader", lambda: spy)

    result = _runner.invoke(
        app,
        ["ci", "push-gate-check"],
        input=f"refs/tags/v1 {tip_sha} refs/tags/v1 {_ZERO}\n",
    )

    assert result.exit_code == 0, result.output
    assert spy.calls, "push-gate-check never reached the scan — object source unused"
    assert spy.calls[0] == (repo, tip_sha, _ZERO)


def test_mode_line_distinguishes_operator_denylist_from_baseline_only(
    monkeypatch, tmp_path: Path
) -> None:
    """A3.5: the stderr mode line names which term sources actually ran.

    Patches the ``load_denylist_terms`` composition-root seam directly rather than
    relying on ``DADAIA_PRIVACY_DENYLIST``/filesystem discovery — this sandbox's own
    real workspace carries an operator denylist file, and
    ``infrastructure.privacy_check``'s workspace-root walk resolves from ``cwd``
    (unaffected by the ``WORKSPACE_ROOT`` env override this test also sets), so a
    file/env-based test would spuriously observe the ambient real denylist. The mode
    line's OWN branching logic — reacting to whatever term-loading returns — is what
    A3.5 actually pins.
    """
    repo = tmp_path / "repo"
    tip_sha = _init_repo(repo)

    monkeypatch.setattr(ci, "_repo_root", lambda: repo)
    monkeypatch.setenv("WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.setattr(container, "build_git_object_reader", lambda: _SpyObjectSource())

    monkeypatch.setattr(container, "load_denylist_terms", lambda: ())
    baseline_only = _runner.invoke(
        app,
        ["ci", "push-gate-check"],
        input=f"refs/tags/v1 {tip_sha} refs/tags/v1 {_ZERO}\n",
    )
    assert "baseline only (no operator denylist)" in baseline_only.output

    monkeypatch.setattr(container, "load_denylist_terms", lambda: (("zz-synthetic-term", "test"),))
    with_operator = _runner.invoke(
        app,
        ["ci", "push-gate-check"],
        input=f"refs/tags/v2 {tip_sha} refs/tags/v2 {_ZERO}\n",
    )
    assert "operator denylist + baseline" in with_operator.output
