"""Intent: CONTRACT — AC4.2-AC4.6 (T-050-15, T-050-40 R13 append-only model): `context
baseline` adopts what origin holds, publishes the local principal as it is on an empty
origin, never rewrites or deletes a branch, and every refusal leaves the repo and the
remote unchanged with the fix for its own cause.

Real git over ``file://`` bare remotes (MEDIUM): the contract is git's own branch/tag state.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from dadaia_workspace.container import scan_publish_candidates
from dadaia_workspace.core import workspace_layout
from dadaia_workspace.core.exceptions import ContextStateError, GitSyncError
from dadaia_workspace.core.models.spec_context import ContextState, SpecContextProject
from dadaia_workspace.features.spec_context.service import (
    DeadSecretFoundError,
    SpecContextService,
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
        store, GitSubprocessClient(), root, lambda _repo: None, scan_publish_candidates
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
    """*work* is checked out, level with origin, holds *base*, and adds exactly the
    onboarding paths to it (the anchor merged with origin's start)."""
    heads = _heads(bare)
    assert work in heads and "main" in heads and "develop" in heads
    assert _git(repo, "rev-parse", "HEAD") == _git(repo, "rev-parse", "@{u}") == heads[work]
    assert _ancestor(repo, heads[base], work)
    files = _git(repo, "diff", "--name-only", heads[base], work).splitlines()
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
    assert _ancestor(repo, theirs, "HEAD")


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
    """Review CRITICAL (round 4, N5) / design review C3, Q2: origin holds only another
    branch and the clone is unborn — nothing is guessed or pushed, no untracked operator
    file is overwritten, HEAD is on the work branch holding the anchor and the unborn
    name leaves no stray branch."""
    svc, repo, bare = env
    _seed(bare, tmp_path / "seed", "develop")
    _clone_onboarded(bare, repo)
    (repo / "README.md").write_text("OPERATOR\n", encoding="utf-8")
    before = _heads(bare)
    with pytest.raises(ContextStateError, match="'main'") as refused:
        svc.baseline("proj")
    assert _heads(bare) == before
    assert (repo / "README.md").read_text(encoding="utf-8") == "OPERATOR\n"
    assert _git(repo, "branch", "--show-current") == "feature/0.1.0"
    assert _git(repo, "for-each-ref", "--format=%(refname:short)", "refs/heads") == "feature/0.1.0"
    anchor = _git(repo, "rev-parse", "HEAD")
    assert anchor in str(refused.value) and "--principal '<principal>'" in str(refused.value)


def test_a_born_principal_absent_refusal_leaves_head_on_work_and_names_the_one_candidate(
    env, tmp_path: Path
) -> None:
    """Design review C3/C6: origin publishes `trunk` only — the one candidate is named in
    the fix; HEAD is on the work branch (never detached) and the local branch the operator
    was on is untouched."""
    svc, repo, bare = env
    _seed(bare, tmp_path / "seed", "trunk")
    _git(bare, "symbolic-ref", "HEAD", "refs/heads/trunk")
    _clone_onboarded(bare, repo)
    trunk = _git(repo, "rev-parse", "trunk")
    with pytest.raises(ContextStateError) as refused:
        svc.baseline("proj")
    assert str(refused.value).endswith("specs init --context proj --principal trunk")
    assert _git(repo, "branch", "--show-current") == "feature/0.1.0"
    assert _git(repo, "rev-parse", "trunk") == trunk and _heads(bare).keys() == {"trunk"}


def test_several_principal_candidates_are_listed_never_guessed(env, tmp_path: Path) -> None:
    """Design review C6: two candidate heads — both listed, a `<principal>` placeholder."""
    svc, repo, bare = env
    _seed(bare, tmp_path / "seed", "trunk", "master")
    _git(bare, "symbolic-ref", "HEAD", "refs/heads/trunk")
    _clone_onboarded(bare, repo)
    with pytest.raises(ContextStateError) as refused:
        svc.baseline("proj")
    message = str(refused.value)
    assert "master, trunk" in message and message.endswith("--principal '<principal>'")


def test_a_never_onboarded_repo_is_refused_with_the_specs_init_fix(env, tmp_path: Path) -> None:
    """sa-public-install-writes-the-root-map-into-product-repos#K3: Design review C1 / AC4.5: a constitution git would not commit (here: ignored) is
    refused before any write, so HEAD holds one after every anchor — never 'published'
    without specs (the old S20 false success)."""
    svc, repo, bare = env
    _seed(bare, tmp_path / "seed", "main", "develop")
    _git(repo.parent, "clone", "-q", bare.as_uri(), str(repo))
    _identity(repo)
    before, head = _heads(bare), _git(repo, "rev-parse", "HEAD")
    (repo / ".gitignore").write_text("specs/\n", encoding="utf-8")
    (repo / "specs").mkdir()
    (repo / "specs" / "constitution.md").write_text(_CONSTITUTION, encoding="utf-8")
    with pytest.raises(ContextStateError, match="no committable specs/constitution.md") as refused:
        svc.baseline("proj")
    assert str(refused.value).endswith("specs init --context proj")
    assert _heads(bare) == before and _git(repo, "rev-parse", "HEAD") == head
    assert _git(repo, "branch", "--show-current") == "main"


def test_a_stale_local_work_branch_takes_the_anchor_and_main_never_holds_it(
    env, tmp_path: Path
) -> None:
    """Design review C2 (D-E3) / review 6 N4: a local work branch from an earlier run, HEAD
    on the principal — the anchor is made detached, <work> is fast-forwarded onto it, and
    the local principal stays exactly where the operator left it."""
    svc, repo, bare = env
    _seed(bare, tmp_path / "seed", "main", "develop")
    _clone_onboarded(bare, repo)
    _git(repo, "branch", "feature/0.1.0", "origin/main")
    main = _git(repo, "rev-parse", "main")
    assert svc.baseline("proj") == "feature/0.1.0"
    assert _git(repo, "rev-parse", "main") == main
    _assert_published(repo, bare, "feature/0.1.0", "develop")


def test_a_work_branch_checked_out_in_another_worktree_is_refused_and_left_untouched(
    env, tmp_path: Path
) -> None:
    """Review 7 R8-1: <work> is checked out in a second worktree holding staged work — git
    refuses to move it (its text), the worktree's branch, index and files stay as they
    were, and nothing reaches origin."""
    svc, repo, bare = env
    _seed(bare, tmp_path / "seed", "main", "develop")
    _clone_onboarded(bare, repo)
    _git(repo, "branch", "feature/0.1.0", "origin/main")
    wt = tmp_path / "wt"
    _git(repo, "worktree", "add", "-q", str(wt), "feature/0.1.0")
    (wt / "new.py").write_text("operator staged work\n", encoding="utf-8")
    _git(wt, "add", "new.py")
    tip, before = _git(repo, "rev-parse", "feature/0.1.0"), _heads(bare)
    with pytest.raises(GitSyncError, match="refusing to fetch into branch") as refused:
        svc.baseline("proj")
    assert "context baseline proj" in str(refused.value)
    assert _git(repo, "rev-parse", "feature/0.1.0") == tip
    assert _git(wt, "status", "--porcelain") == "A  new.py"
    assert not (wt / "specs").exists()
    assert _heads(bare) == before


def test_a_stale_work_draft_conflict_names_the_anchor_and_never_publishes_the_old_draft(
    env, tmp_path: Path
) -> None:
    """Design review C2 (D-S13b): the stale <work> holds an older AGENTS.md — git's add/add
    conflict text names the anchor; nothing reaches origin; HEAD holds the new draft."""
    svc, repo, bare = env
    _seed(bare, tmp_path / "seed", "main", "develop")
    _clone_onboarded(bare, repo)
    _git(repo, "switch", "-q", "-c", "feature/0.1.0")
    (repo / "AGENTS.md").write_text("# old draft\n", encoding="utf-8")
    _git(repo, "add", "AGENTS.md")
    _git(repo, "commit", "-qm", "old draft")
    _git(repo, "switch", "-q", "main")
    (repo / "AGENTS.md").write_text("# new draft\n", encoding="utf-8")
    before = _heads(bare)
    with pytest.raises(GitSyncError, match="CONFLICT") as refused:
        svc.baseline("proj")
    anchor = _git(repo, "rev-parse", "HEAD")
    assert f"onboarding commit {anchor}" in str(refused.value)
    assert "context baseline proj" in str(refused.value)
    assert _git(repo, "show", f"{anchor}:AGENTS.md") == "# new draft"
    assert _heads(bare) == before


def test_an_unborn_clone_of_a_non_empty_origin_merges_onto_the_tool_root(
    env, tmp_path: Path
) -> None:
    """Q1 ruling (R10b): origin's HEAD dangles, so the clone is unborn — the root anchor the
    tool made merges origin's start with --allow-unrelated-histories; published() agrees."""
    svc, repo, bare = env
    _seed(bare, tmp_path / "seed", "main", "develop")
    _git(bare, "symbolic-ref", "HEAD", "refs/heads/nothing")
    _clone_onboarded(bare, repo)
    assert svc.baseline("proj") == "feature/0.1.0"
    assert GitSubprocessClient().published(repo)
    _assert_published(repo, bare, "feature/0.1.0", "develop")
    assert svc.baseline("proj") == ""


def test_unrelated_operator_history_keeps_gits_refusal(env, tmp_path: Path) -> None:
    """Q1 ruling: HEAD's root carries operator content — git's own refusal stands."""
    svc, repo, bare = env
    _seed(bare, tmp_path / "seed", "main", "develop")
    _git(repo.parent, "init", "-q", "-b", "main", str(repo))
    _identity(repo)
    _git(repo, "remote", "add", "origin", bare.as_uri())
    (repo / "app.py").write_text("x\n", encoding="utf-8")
    _git(repo, "add", "app.py")
    _git(repo, "commit", "-qm", "operator root")
    (repo / "specs").mkdir()
    (repo / "specs" / "constitution.md").write_text(_CONSTITUTION, encoding="utf-8")
    with pytest.raises(GitSyncError, match="unrelated histories"):
        svc.baseline("proj")


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
    """Review 5 H4: sa-principal-branch-defaults-to-main-and-cut-point-diverges#B42-4 — a
    master principal births no `main`; work is cut from the integration branch."""
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
    assert {flow[0], flow[1], work} == set(heads) and _ancestor(repo, heads[flow[1]], work)
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


def test_dirty_work_outside_the_paths_rides_along_uncommitted(env, tmp_path: Path) -> None:
    """Cut (h): no preflight refusal — the pathspec commit never takes foreign work; it
    stays modified in the tree and never reaches origin."""
    svc, repo, bare = env
    _seed(bare, tmp_path / "seed", "main")
    _clone_onboarded(bare, repo)
    (repo / "README.md").write_text("operator\n", encoding="utf-8")
    assert svc.baseline("proj") == "feature/0.1.0"
    _assert_published(repo, bare, "feature/0.1.0", "develop")
    assert (repo / "README.md").read_text(encoding="utf-8") == "operator\n"
    assert _git(repo, "status", "--porcelain") == "M README.md"


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


def test_the_tests_law_specs_init_writes_is_published(env) -> None:
    """sa-public-install-writes-the-root-map-into-product-repos#K3: the publishable paths
    are REPO_LAW's full relative paths, so ``tests/AGENTS.md`` is published too."""
    svc, repo, bare = env
    _clone_onboarded(bare, repo)
    (repo / "tests").mkdir()
    (repo / "tests" / "AGENTS.md").write_text("# tests law\n", encoding="utf-8")
    svc.baseline("proj")
    tree = _git(bare, "ls-tree", "-r", "--name-only", "main").splitlines()
    assert sorted(tree) == ["AGENTS.md", "specs/constitution.md", "tests/AGENTS.md"]
