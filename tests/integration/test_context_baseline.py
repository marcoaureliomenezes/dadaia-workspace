"""Intent: CONTRACT — AC4.2-AC4.6 (T-050-15, T-050-40 R13 append-only model): `context
baseline` adopts what origin holds, publishes the local principal as it is on an empty
origin, never rewrites or deletes a branch, and every refusal leaves the repo and the
remote unchanged with the fix for its own cause.

Real git over ``file://`` bare remotes (MEDIUM): the contract is git's own branch/tag state.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from dadaia_workspace.core import workspace_layout
from dadaia_workspace.core.exceptions import ContextStateError, GitSyncError
from dadaia_workspace.core.invocation import repo_owner
from dadaia_workspace.core.models.spec_context import ContextState, SpecContextProject
from dadaia_workspace.features.spec_context.service import (
    DeadSecretFoundError,
    SpecContextService,
    _sync_failure,
)
from dadaia_workspace.infrastructure.git_subprocess import GitSubprocessClient
from dadaia_workspace.infrastructure.json_context_store import JsonContextStore
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
    (root / ".dadaia" / "states").mkdir(parents=True)
    bare = tmp_path / "proj.git"
    _git(tmp_path, "init", "-q", "--bare", "-b", "main", str(bare))
    store = JsonContextStore(root / ".dadaia" / "states")
    store.save(SpecContextProject("proj", ContextState.ALIVE, "proj", bare.as_uri(), "2026-01-01"))
    svc = SpecContextService(
        store, GitSubprocessClient(), root, lambda _repo: None, repo_owner=repo_owner
    )  # type: ignore[arg-type]
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
    """*work* is checked out, level with origin, and is *base* (its first parent) plus the
    onboarding commit — a fast-forward, or a merge of that commit into *base*."""
    heads = _heads(bare)
    assert work in heads and "main" in heads and "develop" in heads
    assert _git(repo, "rev-parse", "HEAD") == _git(repo, "rev-parse", "@{u}") == heads[work]
    assert _git(repo, "rev-parse", f"{work}^") == heads[base]
    files = _git(repo, "diff", "--name-only", f"{work}^", work).splitlines()
    assert sorted(files) == ["AGENTS.md", "specs/constitution.md"]


def _ancestor(repo: Path, old: str, new: str) -> bool:
    done = subprocess.run(["git", "merge-base", "--is-ancestor", old, new], cwd=repo)
    return done.returncode == 0


def test_an_empty_origin_receives_the_local_principal_and_both_branches_cut_from_it(env) -> None:
    """R13 rule 2: nothing contentless is born — the onboarding commit IS the principal."""
    svc, repo, bare = env
    _clone_onboarded(bare, repo)
    assert svc.baseline("proj") == "feature/0.1.0"
    heads = _heads(bare)
    assert heads["main"] == heads["develop"] == heads["feature/0.1.0"]
    assert _git(repo, "rev-parse", "HEAD") == _git(repo, "rev-parse", "@{u}") == heads["main"]
    tree = _git(bare, "ls-tree", "-r", "--name-only", "main").splitlines()
    assert sorted(tree) == ["AGENTS.md", "specs/constitution.md"]


def test_operator_code_on_local_main_is_published_as_it_is(env) -> None:
    """Review C2 (round 4): code committed before the first publish reaches origin on the
    principal — never left on an unrelated root, never rewritten."""
    svc, repo, bare = env
    _clone_onboarded(bare, repo)
    (repo / "app.py").write_text("x\n", encoding="utf-8")
    _git(repo, "add", "app.py")
    _git(repo, "commit", "-qm", "operator code")
    tip = _git(repo, "rev-parse", "HEAD")
    assert svc.baseline("proj") == "feature/0.1.0"
    heads = _heads(bare)
    assert _ancestor(repo, tip, heads["main"]) and _ancestor(repo, heads["main"], heads["develop"])
    assert "app.py" in _git(bare, "ls-tree", "--name-only", "feature/0.1.0").splitlines()


@pytest.mark.skipif(sys.platform == "win32", reason="the shipped pre-push hook is bash")
@pytest.mark.parametrize("seeded", [(), ("main",)], ids=["empty", "principal-only"])
def test_every_publish_passes_the_shipped_pre_push_gate(
    env, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, seeded
) -> None:
    """The real shipped pre-push gate (this interpreter's CLI) admits the first publish and
    the integration birth at the published principal."""
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
    assert {"main", "develop", "feature/0.1.0"} <= set(_heads(bare))


def test_principal_only_births_integration_at_its_tip(env, tmp_path: Path) -> None:
    svc, repo, bare = env
    _seed(bare, tmp_path / "seed", "main")
    _clone_onboarded(bare, repo)
    assert svc.baseline("proj") == "feature/0.1.0"
    heads = _heads(bare)
    assert heads["develop"] == heads["main"] == _git(tmp_path / "seed", "rev-parse", "main")
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


def test_an_origin_work_branch_is_adopted_never_deleted(env, tmp_path: Path) -> None:
    """R13 rule 1 / review H (round 4): the origin work branch is the live one — the publish
    appends on it; its commits stay."""
    svc, repo, bare = env
    _seed(bare, tmp_path / "seed", "main", "develop", "feature/0.1.0")
    theirs = _heads(bare)["feature/0.1.0"]
    _clone_onboarded(bare, repo)
    assert svc.baseline("proj") == "feature/0.1.0"
    assert _heads(bare)["feature/0.1.0"] == _git(repo, "rev-parse", "HEAD")
    assert _git(repo, "rev-parse", "HEAD^") == theirs


def test_a_tag_makes_the_work_branch_its_next_patch(env, tmp_path: Path) -> None:
    svc, repo, bare = env
    _seed(bare, tmp_path / "seed", "main", tag="v0.3.1")
    _clone_onboarded(bare, repo)
    assert svc.baseline("proj") == "feature/0.3.2"
    _assert_published(repo, bare, "feature/0.3.2", "develop")


@pytest.mark.parametrize("seeded", [(), ("main", "develop")], ids=["empty", "adopted"])
def test_second_run_is_a_no_op(env, tmp_path: Path, seeded) -> None:
    svc, repo, bare = env
    if seeded:
        _seed(bare, tmp_path / "seed", *seeded)
    _clone_onboarded(bare, repo)
    svc.baseline("proj")
    before, head = _heads(bare), _git(repo, "rev-parse", "HEAD")
    assert svc.baseline("proj") == ""
    assert _heads(bare) == before and _git(repo, "rev-parse", "HEAD") == head


def test_an_origin_without_the_principal_refuses_and_publishes_nothing(env, tmp_path: Path) -> None:
    """Review CRITICAL (round 4, N5): origin holds only another branch and the clone is
    unborn — nothing is guessed or pushed, no untracked operator file is overwritten."""
    svc, repo, bare = env
    _seed(bare, tmp_path / "seed", "develop")
    _clone_onboarded(bare, repo)
    (repo / "README.md").write_text("OPERATOR\n", encoding="utf-8")
    before = _heads(bare)
    with pytest.raises(ContextStateError, match="'main'"):
        svc.baseline("proj")
    assert _heads(bare) == before
    assert (repo / "README.md").read_text(encoding="utf-8") == "OPERATOR\n"


@pytest.mark.parametrize(
    ("flow", "work"),
    [
        (("master", "develop", "feature/"), "feature/0.1.0"),
        (("main", "develop", "release/"), "release/0.1.0"),
    ],
    ids=["master-principal", "release-prefix"],
)
def test_a_non_default_gitflow_is_adopted_from_the_committed_draft(
    env, tmp_path: Path, flow: tuple[str, str, str], work: str
) -> None:
    """Review 5 H4 (P7/P7b): one baseline path — the onboarding is committed first and the
    gitflow read once, from that commit; a non-default gitflow publishes under its names."""
    svc, repo, bare = env
    _seed(bare, tmp_path / "seed", *dict.fromkeys((flow[0], "develop")))
    _git(bare, "symbolic-ref", "HEAD", f"refs/heads/{flow[0]}")
    _clone_onboarded(bare, repo)
    draft = _CONSTITUTION.replace(
        "{principal: main, integration: develop, work: feature/}",
        f"{{principal: {flow[0]}, integration: {flow[1]}, work: {flow[2]}}}",
    )
    (repo / "specs" / "constitution.md").write_text(draft, encoding="utf-8")
    assert svc.baseline("proj") == work
    heads = _heads(bare)
    assert {flow[0], flow[1], work} <= set(heads)
    assert "specs/constitution.md" in _git(bare, "ls-tree", "-r", "--name-only", work).split()


def test_specs_the_operator_committed_on_the_principal_are_published(env, tmp_path: Path) -> None:
    """Review 5 H4 (P7c): the committed onboarding reaches origin — never a false success
    that leaves origin with the README alone and the specs gone from disk."""
    svc, repo, bare = env
    _seed(bare, tmp_path / "seed", "master")
    _git(bare, "symbolic-ref", "HEAD", "refs/heads/master")
    _clone_onboarded(bare, repo)
    draft = _CONSTITUTION.replace("principal: main", "principal: master")
    (repo / "specs" / "constitution.md").write_text(draft, encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "specs")
    assert svc.baseline("proj") == "feature/0.1.0"
    pushed = _git(bare, "ls-tree", "-r", "--name-only", "feature/0.1.0").split()
    assert "specs/constitution.md" in pushed and (repo / "specs" / "constitution.md").is_file()


def test_local_principal_commits_are_carried_onto_the_work_branch(env, tmp_path: Path) -> None:
    """Review 5 M3 (P8): operator commits on the local principal are never stranded — the
    published work branch carries them."""
    svc, repo, bare = env
    _seed(bare, tmp_path / "seed", "main", "develop")
    _clone_onboarded(bare, repo)
    (repo / "app.py").write_text("operator code\n", encoding="utf-8")
    _git(repo, "add", "app.py")
    _git(repo, "commit", "-qm", "operator code")
    assert svc.baseline("proj") == "feature/0.1.0"
    assert "app.py" in _git(bare, "ls-tree", "--name-only", "feature/0.1.0").split()


def test_a_draft_origin_tracks_is_never_stashed_away(env, tmp_path: Path) -> None:
    """Review 5 H5 (P9): origin's integration already tracks AGENTS.md — git's own text
    stands alone; the drafts are never stashed into a false 'already published'."""
    svc, repo, bare = env
    seed = tmp_path / "seed"
    _seed(bare, seed, "main")
    _git(seed, "checkout", "-q", "-b", "develop")
    (seed / "AGENTS.md").write_text("upstream agents\n", encoding="utf-8")
    _git(seed, "add", "AGENTS.md")
    _git(seed, "commit", "-qm", "a")
    _git(seed, "push", "-q", bare.as_uri(), "develop")
    _clone_onboarded(bare, repo)
    with pytest.raises(GitSyncError) as refused:
        svc.baseline("proj")
    assert "stash" not in str(refused.value)
    assert _git(repo, "stash", "list") == ""
    assert (repo / "specs" / "constitution.md").is_file()


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


def test_an_unborn_clone_keeps_its_untracked_foreign_files(env) -> None:
    """Review CRITICAL (round 4): no forced checkout — an unborn clone's foreign files stay
    untracked and byte-identical."""
    svc, repo, bare = env
    _clone_onboarded(bare, repo)
    (repo / "notes.md").write_text("operator\n", encoding="utf-8")
    assert svc.baseline("proj") == "feature/0.1.0"
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


def test_a_tool_commit_never_falls_back_to_a_tool_identity(tmp_path: Path, monkeypatch) -> None:
    """SA-H3-2: one identity rule (git's own) — no hard-coded fallback author."""
    (tmp_path / "gitconfig").write_text("[user]\n\tuseConfigOnly = true\n", encoding="utf-8")
    for var in ("NAME", "EMAIL"):
        monkeypatch.delenv(f"GIT_AUTHOR_{var}", raising=False)
        monkeypatch.delenv(f"GIT_COMMITTER_{var}", raising=False)
    repo = tmp_path / "r"
    _git(tmp_path, "init", "-q", str(repo))
    (repo / "a.md").write_text("a\n", encoding="utf-8")
    client = GitSubprocessClient()
    assert client.identity_fix(repo).startswith("git -C")
    with pytest.raises(GitSyncError):
        client.commit_all(repo, "c")


def test_an_env_identity_publishes_without_git_config(env, monkeypatch) -> None:
    """Bug baseline-identity-precheck-ignores-git-env-identity: git's identity is
    whatever git resolves — GIT_AUTHOR_*/GIT_COMMITTER_* included — never config alone."""
    svc, repo, bare = env
    for role in ("AUTHOR", "COMMITTER"):
        monkeypatch.setenv(f"GIT_{role}_NAME", "T")
        monkeypatch.setenv(f"GIT_{role}_EMAIL", "t@example.invalid")
    _clone_onboarded(bare, repo, identity=False)
    assert svc.baseline("proj") == "feature/0.1.0"


def test_a_wrong_origin_url_gets_the_set_url_fix(env, tmp_path: Path) -> None:
    """Review HIGH (round 4): no "rerun the verb" class — a wrong URL gets set-url."""
    svc, repo, bare = env
    _clone_onboarded(bare, repo)
    _git(repo, "remote", "set-url", "origin", (tmp_path / "gone.git").as_uri())
    with pytest.raises(GitSyncError) as refused:
        svc.baseline("proj")
    fix = str(refused.value).splitlines()[-1]
    assert fix.startswith("fix: git -C") and "remote set-url origin" in fix
    assert _heads(bare) == {}


@pytest.mark.parametrize(
    ("stderr", "fix"),
    [
        ("fatal: 'x' does not appear to be a git repository", "remote set-url origin"),
        ("ERROR: Repository not found.", "remote set-url origin"),
        # Review 5 H5/H6/M1: git's own text stands alone — a pull fix led dead into a
        # conflicted merge, `ls-remote` cannot clear an auth failure, a stash hid drafts.
        ("! [rejected] feature/1.0.0 -> feature/1.0.0 (fetch first)", None),
        ("! [rejected] x -> x (non-fast-forward)", None),
        ("git@h: Permission denied (publickey).\nfatal: Could not read from remote", None),
        ("fatal: Authentication failed for 'https://h/x'", None),
        ("error: Your local changes to the following files would be overwritten by checkout", None),
        ("[pre-push] BLOCKED: x\nfix: git -C r branch -m a b", None),
        ("fatal: something new", None),
    ],
)
def test_every_sync_failure_gets_the_fix_for_its_own_cause(tmp_path: Path, stderr, fix) -> None:
    """R13 rule 4: one fix per cause; the gate's own fix passes through; an unknown cause
    carries git's text and no invented fix — never a rebase, a delete, a force or a rerun."""
    text = str(_sync_failure(GitSyncError(stderr), tmp_path))
    fixes = [line for line in text.splitlines() if line.startswith("fix: ")]
    if fix is None:
        assert len(fixes) == (1 if "fix:" in stderr else 0)
    else:
        assert len(fixes) == 1 and fix in fixes[0]
    assert not re.search(r"(?<!no-)rebase |--delete|--force|reset|context baseline", "".join(fixes))


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
    before any write, with a fix line."""
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


def test_the_publish_code_never_rewrites_forces_or_deletes() -> None:
    """R13 rule 3: no forced checkout, reset, rebase, force-push, remote delete or squash
    in the publish, the gate or the sync-failure fixes."""
    pkg = Path(__file__).resolve().parents[2] / "dadaia_workspace"
    for rel in (
        "features/spec_context/service.py",
        "features/chokepoints/branch_policy.py",
    ):
        text = (pkg / rel).read_text(encoding="utf-8")
        for verb in ('"-f"', '"reset"', '"rebase"', '"--force"', '"--delete"', "--republish"):
            assert verb not in text, f"{rel} carries {verb}"
