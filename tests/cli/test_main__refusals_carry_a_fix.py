"""Every CLI refusal prints `Error:` first and exactly one
`fix:` line, with no traceback; `create`'s conflict names its real recovery; an off-repo
directory is one refusal for `context alive` and `ci install-hook`.

Each case drives the console entry (`_safe_app`) on a temp workspace.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from dadaia_workspace import container
from dadaia_workspace.cli import main
from dadaia_workspace.core.exceptions import WorkspaceVenvBootstrapError
from dadaia_workspace.features.migrate.upgrade import _RETIRED_PART_HEADING
from tests.fakes import no_worktree_rows, seed_dead_context

pytest.importorskip("fcntl")  # POSIX-only: bare git remotes and file:// URLs; Windows skips

_GIT_ENV = {
    "GIT_AUTHOR_NAME": "t",
    "GIT_AUTHOR_EMAIL": "t@t.test",
    "GIT_COMMITTER_NAME": "t",
    "GIT_COMMITTER_EMAIL": "t@t.test",
}

Case = tuple[Path, list[str]]


def _git(*args: str, cwd: Path | None = None) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


def _workspace(tmp: Path, name: str = "ws") -> Path:
    root = tmp / name
    (root / ".dadaia/states").mkdir(parents=True)
    (root / ".dadaia/states/spec_contexts.json").write_text(
        json.dumps({"schema_version": 2, "contexts": []})
    )
    return root


def _foo(tmp: Path) -> Path:
    root = _workspace(tmp)
    seed_dead_context(root, "foo", "foo-repo", "https://x.test/foo-repo.git")
    return root


def _bare_remote(tmp: Path) -> Path:
    bare = tmp / "remote" / "foo.git"
    _git("init", "-q", "--bare", str(bare))
    seed = tmp / "seed"
    _git("init", "-q", "-b", "main", str(seed))
    (seed / "README.md").write_text("x")
    _git("add", "-A", cwd=seed)
    _git("commit", "-qm", "i", cwd=seed)
    _git("push", "-q", str(bare), "main", cwd=seed)
    return bare


def _alive_foo(tmp: Path, bare: Path) -> Path:
    root = _workspace(tmp)
    seed_dead_context(root, "foo", "foo", f"file://{bare}")
    os.chdir(root)
    _run(["context", "alive", "foo"])
    return root


def _run(argv: list[str]) -> int:
    sys.argv = ["dadaia", *argv]
    try:
        main._safe_app()
    except SystemExit as exc:
        return int(exc.code or 0)
    return 0


def _repo_add(tmp: Path, *args: str) -> Case:
    return _foo(tmp), ["context", "repo", "add", "foo", *args]


def _repo_add_other_url(tmp: Path) -> Case:
    root, _ = _repo_add(tmp, "assoc-a", "--url", "https://x.test/a.git")
    os.chdir(root)
    assert _run(["context", "repo", "add", "foo", "assoc-a", "--url", "https://x.test/a.git"]) == 0
    return root, ["context", "repo", "add", "foo", "assoc-a", "--url", "https://x.test/b.git"]


def _repo_add_foreign(tmp: Path) -> Case:
    root = _foo(tmp)
    seed_dead_context(root, "bar", "bar-repo", "https://x.test/bar-repo.git")
    return root, ["context", "repo", "add", "foo", "bar-repo", "--url", "https://x.test/b.git"]


def _create_conflict(tmp: Path) -> Case:
    return _foo(tmp), [
        "context", "create", "zz",
        "--main-repo", "https://x.test/a.git",
        "--associated-repo", "https://x.test/a.git",
    ]  # fmt: skip


def _alive_clone_fails(tmp: Path) -> Case:
    root = _workspace(tmp)
    seed_dead_context(root, "gone", "gone-repo", "file:///nonexistent/gone.git")
    return root, ["context", "alive", "gone"]


def _baseline_remote_gone(tmp: Path) -> Case:
    bare = _bare_remote(tmp)
    root = _alive_foo(tmp, bare)
    assert _run(["specs", "init", "--context", "foo"]) == 0
    shutil.move(str(bare), str(bare) + ".moved")
    return root, ["context", "baseline", "foo"]


def _dead_remote_gone(tmp: Path, monkeypatch: pytest.MonkeyPatch) -> Case:
    bare = _bare_remote(tmp)
    root = _alive_foo(tmp, bare)
    repo = root / "repos/foo"
    _git("checkout", "-q", "-b", "feature/0.1.0", cwd=repo)
    (repo / "n.txt").write_text("c")
    _git("add", "-A", cwd=repo)
    _git("commit", "-qm", "c", cwd=repo)
    shutil.move(str(bare), str(bare) + ".moved")
    real = container.build_spec_context_service
    monkeypatch.setattr(
        container,
        "build_spec_context_service",
        lambda r, **k: real(r, rows=no_worktree_rows),
    )
    return root, ["context", "dead", "foo"]


def _import_file(tmp: Path, text: str | None) -> Case:
    root = _workspace(tmp)
    f = root / "x.json"
    if text is not None:
        f.write_text(text)
    return root, ["import", str(f)]


def _init_venv_fails(tmp: Path, monkeypatch: pytest.MonkeyPatch) -> Case:
    class _Boom:
        def venv_change(self, *a: Any, **k: Any) -> None:
            raise WorkspaceVenvBootstrapError("could not create the workspace venv: pip failed")

    monkeypatch.setattr(container, "build_workspace_service", lambda root: _Boom())
    tmp.mkdir(exist_ok=True)
    return tmp, ["init", str(tmp / "w"), "--harness", "claude"]


def _two_tier_architecture(tmp: Path) -> Case:
    g = tmp / "g"
    _git("init", "-q", "-b", "main", str(g))
    os.chdir(g)
    assert _run(["specs", "init", "--specs-dir", str(g / "specs")]) == 0
    arch = g / "specs/memory/ARCHITECTURE.md"
    arch.write_text(arch.read_text() + "\n" + _RETIRED_PART_HEADING + "\n")
    return g, ["specs", "upgrade", "--specs-dir", str(g / "specs")]


def _malformed_constitution(tmp: Path) -> Case:
    (tmp / "specs").mkdir(parents=True)
    (tmp / "specs/constitution.md").write_text("---\n: [\n---\n")
    return tmp, ["specs", "init", "--specs-dir", str(tmp / "specs")]


# (id, builder(tmp, monkeypatch) -> (cwd, argv)) — the 17 measured sites.
SITES: list[tuple[str, Callable[[Path, pytest.MonkeyPatch], Case]]] = [
    ("repo-add-invalid-slug", lambda t, m: _repo_add(t, "not a slug", "--url", "https://x.test/a.git")),
    ("repo-add-different-url", lambda t, m: _repo_add_other_url(t)),
    ("repo-add-foreign-slug", lambda t, m: _repo_add_foreign(t)),
    ("repo-remove-unregistered", lambda t, m: (_foo(t), ["context", "repo", "remove", "foo", "never"])),
    ("create-associated-conflict", lambda t, m: _create_conflict(t)),
    ("alive-git-failure", lambda t, m: _alive_clone_fails(t)),
    ("baseline-git-failure", lambda t, m: _baseline_remote_gone(t)),
    ("dead-git-failure", _dead_remote_gone),
    ("import-missing-file", lambda t, m: _import_file(t, None)),
    ("import-not-json", lambda t, m: _import_file(t, "not json")),
    ("import-unknown-schema", lambda t, m: _import_file(t, json.dumps({"schema_version": 99, "contexts": []}))),
    ("reports-bare", lambda t, m: (_foo(t), ["reports", "validate"])),
    ("reports-missing-file", lambda t, m: (_foo(t), ["reports", "validate", "nope.handoff.json"])),
    ("init-venv-failure", _init_venv_fails),
    ("specs-upgrade-two-tier", lambda t, m: _two_tier_architecture(t)),
    ("specs-init-malformed-constitution", lambda t, m: _malformed_constitution(t)),
    ("specs-upgrade-unresolved-specs-dir", lambda t, m: (_workspace(t), ["specs", "upgrade"])),
]  # fmt: skip


# When no remedy clears it, git's own text stands alone.
_GIT_TEXT_ONLY = {"baseline-git-failure", "dead-git-failure"}


def _assert_one_fix(capsys: pytest.CaptureFixture[str], code: int, fixes: int = 1) -> list[str]:
    err = capsys.readouterr().err
    lines = err.splitlines()
    assert code == 1, err
    assert lines[0].startswith("Error:"), err
    assert "unexpected" not in err and "Traceback" not in err, err
    assert len([ln for ln in lines if ln.startswith("fix:")]) == fixes, err
    return lines


@pytest.fixture(autouse=True)
def _isolated(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr("dadaia_workspace.core.workspace_resolver.own_workspace_root", lambda: None)
    for var in ("DADAIA_SESSION_ID", "DADAIA_CONTEXT", "DADAIA_FENCED_ROOTS", "DADAIA_TRACEBACK"):
        monkeypatch.delenv(var, raising=False)
    for key, value in _GIT_ENV.items():
        monkeypatch.setenv(key, value)
    monkeypatch.chdir(tmp_path)


@pytest.mark.parametrize(("site", "build"), SITES, ids=[s for s, _ in SITES])
def test_refusal_prints_error_then_exactly_one_fix(
    site: str,
    build: Callable[[Path, pytest.MonkeyPatch], Case],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    cwd, argv = build(tmp_path / "case", monkeypatch)
    os.chdir(cwd)
    capsys.readouterr()
    code = _run(argv)
    lines = _assert_one_fix(capsys, code, 0 if site in _GIT_TEXT_ONLY else 1)
    if site == "create-associated-conflict":
        fix = next(ln for ln in lines if ln.startswith("fix:"))
        assert "context list" not in fix
        assert "--associated-repo" in fix


def test_context_alive_on_a_non_git_repo_dir_is_one_refusal(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = _workspace(tmp_path)
    seed_dead_context(root, "foo", "foo", "file:///nonexistent/foo.git")
    (root / "repos/foo").mkdir(parents=True)
    (root / "repos/foo/README.md").write_text("x")
    os.chdir(root)
    capsys.readouterr()
    _assert_one_fix(capsys, _run(["context", "alive", "foo"]))


def test_ci_install_hook_on_a_non_git_dir_is_one_refusal(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    plain = tmp_path / "plain"
    plain.mkdir()
    capsys.readouterr()
    _assert_one_fix(capsys, _run(["ci", "install-hook", "--repo", str(plain)]))
