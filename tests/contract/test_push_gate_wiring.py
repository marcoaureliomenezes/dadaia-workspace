"""`ci push-gate-check` CLI wiring for the v0.9.0 range-scoped denylist scan.

Intent: CONTRACT — v0.9.0 A3.5, A6.3; 0.5.0 AC5.1, AC5.4 (T-050-14)

Pins two composition-root guarantees:

* A6.3 — ``push-gate-check`` ALWAYS builds and passes a real ``GitObjectReader`` into
  ``push_gate_decision`` — never omitted, never ``None`` (FR6 row 4/FR7 row A7.2).
* A3.5 — the stderr mode line distinguishes "operator denylist + baseline" (a
  ``DADAIA_PRIVACY_DENYLIST`` file present) from "baseline only" (absent).
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from typer.testing import CliRunner

from dadaia_workspace import container
from dadaia_workspace.cli.commands import ci
from dadaia_workspace.cli.main import app
from dadaia_workspace.core.cli_line import fix_line

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
    """A6.3: the scan runs over the real range — a tag push whose commit carries a
    denylisted term is refused (a tag has no branch policy to short-circuit it)."""
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
        fix_line(None, "specs", "init", "--context", "<ctx>", "--replace-foreign") in result.output
    )

    result = _runner.invoke(app, ["ci", "push-gate-check"], input=_stamped_specs(repo, 7))
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
    assert "baseline only (no operator denylist; private names go in" in baseline_only.output
    assert ".dadaia/states/privacy_denylist.json" in baseline_only.output

    monkeypatch.setattr(container, "load_denylist_terms", lambda: (("zz-synthetic-term", "test"),))
    with_operator = _runner.invoke(
        app,
        ["ci", "push-gate-check"],
        input=f"refs/tags/v2 {tip_sha} refs/tags/v2 {_ZERO}\n",
    )
    assert "operator denylist + baseline" in with_operator.output


def test_a_sibling_repo_name_that_is_an_english_word_does_not_block_the_push(
    monkeypatch, tmp_path: Path
) -> None:
    """Intent: CONTRACT — bug ``push-gate-foreign-slug-layer-blocks-onboarded-specs-push``.

    A context ``shop`` whose associated repo is ``docs``: the pushed blob uses the
    English word "docs". Names are private only through the operator denylist and the
    structural baseline (ADR 0032) — a sibling repo name is never a term source."""
    (tmp_path / ".dadaia").mkdir()
    (tmp_path / "repos" / "docs").mkdir(parents=True)
    repo = tmp_path / "repos" / "shop"
    _init_repo(repo)
    subprocess.run(["git", "checkout", "-q", "-b", "feature/0.1.0"], cwd=repo, check=True)
    (repo / "AGENTS.md").write_text("Read the docs before editing.\n", encoding="utf-8")
    subprocess.run(["git", "add", "AGENTS.md"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "scaffold"], cwd=repo, check=True)
    tip_sha = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True, check=True
    ).stdout.strip()

    monkeypatch.setattr(ci, "_repo_root", lambda: repo)
    monkeypatch.setattr(container, "load_denylist_terms", lambda: ())

    result = _runner.invoke(
        app,
        ["ci", "push-gate-check"],
        input=f"refs/heads/feature/0.1.0 {tip_sha} refs/heads/feature/0.1.0 {_ZERO}\n",
    )

    assert result.exit_code == 0, result.output


# ── 0.5.0 AC5.1/AC5.4 (T-050-14): the bootstrap birth through the REAL reader ──────────


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t.invalid", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _remote_objects(remote: Path) -> set[str]:
    listing = _git(remote, "cat-file", "--batch-all-objects", "--batch-check=%(objectname)")
    return set(listing.split())


def _gate(monkeypatch, tmp_path: Path, repo: Path, line: str) -> int:
    monkeypatch.setattr(ci, "_repo_root", lambda: repo)
    return _runner.invoke(app, ["ci", "push-gate-check"], input=line).exit_code


def test_births_publish_nothing_and_a_birth_with_content_is_refused(
    monkeypatch, tmp_path: Path
) -> None:
    remote = tmp_path / "origin.git"
    remote.mkdir()
    _git(remote, "init", "-q", "--bare")
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "remote", "add", "origin", str(remote))
    _git(repo, "commit", "-q", "--allow-empty", "-m", "root")
    root = _git(repo, "rev-parse", "HEAD")

    # An orphan empty root pushed as the principal branch: allowed, publishes only itself.
    assert (
        _gate(monkeypatch, tmp_path, repo, f"refs/heads/main {root} refs/heads/main {_ZERO}\n") == 0
    )
    _git(repo, "push", "-q", "--no-verify", "origin", "main")
    before = _remote_objects(remote)

    # `git branch develop main` pushed: allowed, and the remote gains no object.
    _git(repo, "branch", "develop", "main")
    line = f"refs/heads/develop {root} refs/heads/develop {_ZERO}\n"
    assert _gate(monkeypatch, tmp_path, repo, line) == 0
    _git(repo, "push", "-q", "--no-verify", "origin", "develop")
    assert _remote_objects(remote) == before

    # A birth carrying a new commit is refused.
    _git(repo, "checkout", "-q", "-b", "next", "main")
    (repo / "x.txt").write_text("x\n", encoding="utf-8")
    _git(repo, "add", "x.txt")
    _git(repo, "commit", "-q", "-m", "content")
    tip = _git(repo, "rev-parse", "HEAD")
    _git(repo, "update-ref", "-d", "refs/heads/develop")
    _git(repo, "branch", "develop", tip)
    line = f"refs/heads/develop {tip} refs/heads/develop {_ZERO}\n"
    assert _gate(monkeypatch, tmp_path, repo, line) != 0
