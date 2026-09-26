"""Intent: CONTRACT — AC4.2-AC4.6 (T-050-15): `context baseline` publishes an onboarded
project on any remote state, commits only the onboarding paths, and every refusal leaves
the repo and the remote unchanged with one runnable fix line.

Real git over ``file://`` bare remotes (MEDIUM): the contract is git's own branch/tag state.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from dadaia_workspace.core import workspace_layout
from dadaia_workspace.core.exceptions import ContextStateError, GitSyncError
from dadaia_workspace.core.models.spec_context import ContextState, SpecContextProject
from dadaia_workspace.features.spec_context.service import DeadSecretFoundError, SpecContextService
from dadaia_workspace.infrastructure.git_subprocess import GitSubprocessClient
from tests.fakes import FakeContextStore
from tests.helpers.privacy_fixtures import aws_key_shape

_CONSTITUTION = (
    "---\nspecs_pattern_version: 6\n"
    "gitflow: {principal: main, integration: develop, work: feature/}\n---\n# c\n"
)


def _git(cwd: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, check=True
    ).stdout.strip()


def _identity(repo: Path) -> None:
    _git(repo, "config", "user.name", "T")
    _git(repo, "config", "user.email", "t@example.invalid")


@pytest.fixture(autouse=True)
def _no_global_git(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(tmp_path / "gitconfig"))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")


def _seed(bare: Path, work: Path, *branches: str, tag: str = "") -> None:
    """A remote whose *branches* carry one README commit (each later one a child)."""
    _git(work.parent, "init", "-q", "-b", branches[0], str(work))
    _identity(work)
    for n, branch in enumerate(branches):
        if n:
            _git(work, "checkout", "-q", "-b", branch)
        (work / "README.md").write_text(f"r{n}\n", encoding="utf-8")
        _git(work, "add", "README.md")
        _git(work, "commit", "-qm", f"c{n}")
    if tag:
        _git(work, "tag", tag, branches[0])
    _git(work, "push", "-q", "--tags", bare.as_uri(), *branches)


@pytest.fixture
def env(tmp_path: Path) -> tuple[SpecContextService, Path, Path]:
    root = tmp_path / "ws"
    (root / "repos").mkdir(parents=True)
    bare = tmp_path / "proj.git"
    _git(tmp_path, "init", "-q", "--bare", "-b", "main", str(bare))
    store = FakeContextStore()
    store.save(SpecContextProject("proj", ContextState.ALIVE, "proj", bare.as_uri(), "2026-01-01"))
    svc = SpecContextService(store, GitSubprocessClient(), root, lambda _repo: None)  # type: ignore[arg-type]
    return svc, root / "repos" / "proj", bare


def _clone_onboarded(bare: Path, repo: Path, identity: bool = True) -> None:
    _git(repo.parent, "clone", "-q", bare.as_uri(), str(repo))
    if identity:
        _identity(repo)
    (repo / "specs").mkdir()
    (repo / "specs" / "constitution.md").write_text(_CONSTITUTION, encoding="utf-8")
    (repo / "AGENTS.md").write_text("# law\n", encoding="utf-8")


def _heads(bare: Path) -> dict[str, str]:
    out = _git(bare, "for-each-ref", "--format=%(refname:lstrip=2) %(objectname)", "refs/heads")
    return dict(line.split() for line in out.splitlines())


def _assert_published(repo: Path, bare: Path, work: str, base: str) -> None:
    heads = _heads(bare)
    assert work in heads and "main" in heads and "develop" in heads
    assert _git(repo, "rev-parse", f"{work}^") == heads[base]
    assert _git(repo, "rev-parse", "HEAD") == _git(repo, "rev-parse", "@{u}") == heads[work]
    files = _git(repo, "show", "--name-only", "--format=", "HEAD").splitlines()
    assert sorted(files) == ["AGENTS.md", "specs/constitution.md"]


def test_unborn_remote_births_both_branches_from_one_empty_root(env) -> None:
    svc, repo, bare = env
    _clone_onboarded(bare, repo)
    assert svc.baseline("proj") == "feature/0.1.0"
    heads = _heads(bare)
    assert heads["main"] == heads["develop"]
    assert _git(bare, "rev-list", "--parents", "-n1", "main") == heads["main"]  # parentless
    assert _git(bare, "ls-tree", "main") == ""
    _assert_published(repo, bare, "feature/0.1.0", "develop")


@pytest.mark.skipif(sys.platform == "win32", reason="the shipped pre-push hook is bash")
@pytest.mark.parametrize("seeded", [(), ("main",)], ids=["unborn", "principal-only"])
def test_every_birth_passes_the_shipped_pre_push_gate(
    env, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, seeded
) -> None:
    """Review H4: births are pushed by `<sha>:refs/heads/<b>` refspec — the real shipped
    pre-push gate (this interpreter's CLI) admits them without a same-named local head."""
    svc, repo, bare = env
    if seeded:
        _seed(bare, tmp_path / "seed", *seeded)
    _clone_onboarded(bare, repo)
    runner = tmp_path / "dadaia"
    runner.write_text(f'#!/bin/sh\nexec "{sys.executable}" -m dadaia_workspace "$@"\n')
    runner.chmod(0o755)
    monkeypatch.setenv("DADAIA_BIN", str(runner))
    monkeypatch.setenv("WORKSPACE_ROOT", str(repo.parent.parent))
    hook = repo / ".git" / "hooks" / "pre-push"
    shutil.copyfile(workspace_layout.public_scripts_dir() / "pre-push-ci-gate.sh", hook)
    hook.chmod(0o755)
    assert svc.baseline("proj") == "feature/0.1.0"
    _assert_published(repo, bare, "feature/0.1.0", "develop")


def test_principal_only_births_integration_at_its_tip(env, tmp_path: Path) -> None:
    svc, repo, bare = env
    _seed(bare, tmp_path / "seed", "main")
    _clone_onboarded(bare, repo)
    assert svc.baseline("proj") == "feature/0.1.0"
    heads = _heads(bare)
    assert heads["develop"] == _git(tmp_path / "seed", "rev-parse", "main")
    _assert_published(repo, bare, "feature/0.1.0", "develop")


def test_both_present_are_reused_and_work_is_cut_from_integration(env, tmp_path: Path) -> None:
    svc, repo, bare = env
    _seed(bare, tmp_path / "seed", "main", "develop")
    before = _heads(bare)
    _clone_onboarded(bare, repo)
    svc.baseline("proj")
    assert {b: _heads(bare)[b] for b in ("main", "develop")} == {
        b: before[b] for b in ("main", "develop")
    }
    _assert_published(repo, bare, "feature/0.1.0", "develop")


def test_a_tag_makes_the_work_branch_its_next_patch(env, tmp_path: Path) -> None:
    svc, repo, bare = env
    _seed(bare, tmp_path / "seed", "main", tag="v0.3.1")
    _clone_onboarded(bare, repo)
    assert svc.baseline("proj") == "feature/0.3.2"
    _assert_published(repo, bare, "feature/0.3.2", "develop")


def test_second_run_is_a_no_op(env) -> None:
    svc, repo, bare = env
    _clone_onboarded(bare, repo)
    svc.baseline("proj")
    before, head = _heads(bare), _git(repo, "rev-parse", "HEAD")
    assert svc.baseline("proj") == ""
    assert _heads(bare) == before and _git(repo, "rev-parse", "HEAD") == head


def test_dirty_outside_the_paths_refuses_and_its_fix_lets_the_rerun_proceed(
    env, tmp_path: Path
) -> None:
    svc, repo, bare = env
    _seed(bare, tmp_path / "seed", "main")
    _clone_onboarded(bare, repo)
    (repo / "notes.md").write_text("operator\n", encoding="utf-8")
    before, branch = _heads(bare), _git(repo, "branch", "--show-current")
    with pytest.raises(ContextStateError) as refused:
        svc.baseline("proj")
    assert _heads(bare) == before and _git(repo, "branch", "--show-current") == branch
    fix = str(refused.value).rsplit("fix: ", 1)[1]
    ran = subprocess.run(fix, shell=True, capture_output=True, text=True)  # noqa: S602
    assert ran.returncode == 0, ran.stderr + ran.stdout
    svc.baseline("proj")
    _assert_published(repo, bare, "feature/0.1.0", "develop")


def test_an_unborn_dirty_clone_publishes_and_leaves_foreign_files_untouched(env) -> None:
    """T-050-15 stall: `git stash` cannot run unborn; an unborn clone's foreign files are
    untracked, never committed and never overwritten (the born branches are empty), so
    baseline proceeds instead of printing a fix that cannot run."""
    svc, repo, bare = env
    _clone_onboarded(bare, repo)
    (repo / "notes.md").write_text("operator\n", encoding="utf-8")
    assert svc.baseline("proj") == "feature/0.1.0"
    _assert_published(repo, bare, "feature/0.1.0", "develop")
    assert (repo / "notes.md").read_text(encoding="utf-8") == "operator\n"
    assert "notes.md" not in _git(bare, "ls-tree", "-r", "--name-only", "feature/0.1.0")


def test_missing_identity_refuses_before_any_write(env, tmp_path: Path, monkeypatch) -> None:
    svc, repo, bare = env
    # No guessing: a host whose name yields an email would otherwise hand git an identity.
    (tmp_path / "gitconfig").write_text("[user]\n\tuseConfigOnly = true\n", encoding="utf-8")
    for var in ("NAME", "EMAIL"):
        monkeypatch.delenv(f"GIT_AUTHOR_{var}", raising=False)
        monkeypatch.delenv(f"GIT_COMMITTER_{var}", raising=False)
    _clone_onboarded(bare, repo, identity=False)
    with pytest.raises(ContextStateError, match="identity unknown") as refused:
        svc.baseline("proj")
    assert "fix: git -C" in str(refused.value)
    assert _heads(bare) == {}


def test_an_env_identity_publishes_without_git_config(env, monkeypatch) -> None:
    """Bug baseline-identity-precheck-ignores-git-env-identity: git's identity is
    whatever git resolves — GIT_AUTHOR_*/GIT_COMMITTER_* included — never config alone."""
    svc, repo, bare = env
    for role in ("AUTHOR", "COMMITTER"):
        monkeypatch.setenv(f"GIT_{role}_NAME", "T")
        monkeypatch.setenv(f"GIT_{role}_EMAIL", "t@example.invalid")
    _clone_onboarded(bare, repo, identity=False)
    assert svc.baseline("proj") == "feature/0.1.0"
    _assert_published(repo, bare, "feature/0.1.0", "develop")


def test_offline_refuses_with_the_same_baseline_line(env, tmp_path: Path) -> None:
    svc, repo, bare = env
    _clone_onboarded(bare, repo)
    _git(repo, "remote", "set-url", "origin", (tmp_path / "gone.git").as_uri())
    with pytest.raises(GitSyncError) as refused:
        svc.baseline("proj")
    assert str(refused.value).splitlines()[-1].endswith("context baseline proj")
    assert _heads(bare) == {}


def test_a_non_ascii_foreign_file_refuses_with_a_fix_that_clears(env, tmp_path: Path) -> None:
    """Review C1: core.quotePath quoted `memória.md`; the printed stash named a path that
    does not exist, so the rerun refused forever."""
    svc, repo, bare = env
    _seed(bare, tmp_path / "seed", "main")
    _clone_onboarded(bare, repo)
    (repo / "memória.md").write_text("operator\n", encoding="utf-8")
    with pytest.raises(ContextStateError) as refused:
        svc.baseline("proj")
    fix = str(refused.value).rsplit("fix: ", 1)[1]
    ran = subprocess.run(fix, shell=True, capture_output=True, text=True)  # noqa: S602
    assert ran.returncode == 0, ran.stderr + ran.stdout
    svc.baseline("proj")
    _assert_published(repo, bare, "feature/0.1.0", "develop")


@pytest.mark.parametrize("seeded", [(), ("main",)], ids=["unborn", "born"])
def test_a_secret_under_a_non_ascii_name_refuses_before_any_write(
    env, tmp_path: Path, seeded
) -> None:
    """Review C1/M5: the secret scan reads the same real paths git commits, and refuses
    before any birth or checkout, with a fix line."""
    svc, repo, bare = env
    if seeded:
        _seed(bare, tmp_path / "seed", *seeded)
    _clone_onboarded(bare, repo)
    (repo / "specs" / "memória.md").write_text(f"k={aws_key_shape()}\n", encoding="utf-8")
    before, branch = _heads(bare), _git(repo, "branch", "--show-current")
    with pytest.raises(DeadSecretFoundError) as refused:
        svc.baseline("proj")
    assert "specs/memória.md" in str(refused.value) and "\nfix: " in str(refused.value)
    assert _heads(bare) == before and _git(repo, "branch", "--show-current") == branch


@pytest.mark.parametrize("checked_out", [True, False], ids=["checked-out", "not-checked-out"])
def test_a_local_principal_with_commits_is_never_reset(env, checked_out: bool) -> None:
    """Review H4: births go by `<sha>:refs/heads/<b>` refspec; local heads stay as they are."""
    svc, repo, bare = env
    _clone_onboarded(bare, repo)
    _git(repo, "checkout", "-q", "-b", "main")
    (repo / "README.md").write_text("local\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-qm", "local work")
    tip = _git(repo, "rev-parse", "main")
    if not checked_out:
        _git(repo, "checkout", "-q", "-b", "side")
    assert svc.baseline("proj") == "feature/0.1.0"
    assert _git(repo, "rev-parse", "main") == tip
    assert _git(bare, "ls-tree", "main") == ""


def test_a_second_foreign_backup_is_published_inside_specs_bkp(env, tmp_path: Path) -> None:
    """Review H1: `specs init --replace-foreign` over an existing specs-bkp/ moves the tree to
    specs-bkp/<UTC>/ — inside the paths baseline publishes, so the pushed tree carries it."""
    svc, repo, bare = env
    seed = tmp_path / "seed"
    _git(tmp_path, "init", "-q", "-b", "main", str(seed))
    _identity(seed)
    for rel in ("specs/features/login.md", "specs-bkp/old.md"):
        (seed / rel).parent.mkdir(parents=True, exist_ok=True)
        (seed / rel).write_text(f"{rel}\n", encoding="utf-8")
    _git(seed, "add", ".")
    _git(seed, "commit", "-qm", "foreign")
    _git(seed, "push", "-q", bare.as_uri(), "main")
    _git(repo.parent, "clone", "-q", bare.as_uri(), str(repo))
    _identity(repo)
    GitSubprocessClient().move(repo, "specs", "specs-bkp/20260101T000000Z")
    (repo / "specs").mkdir()
    (repo / "specs" / "constitution.md").write_text(_CONSTITUTION, encoding="utf-8")
    (repo / "AGENTS.md").write_text("# law\n", encoding="utf-8")
    assert svc.baseline("proj") == "feature/0.1.0"
    pushed = _git(bare, "ls-tree", "-r", "--name-only", "feature/0.1.0").splitlines()
    assert "specs-bkp/20260101T000000Z/features/login.md" in pushed
    assert "specs/features/login.md" not in pushed and "specs-bkp/old.md" in pushed
