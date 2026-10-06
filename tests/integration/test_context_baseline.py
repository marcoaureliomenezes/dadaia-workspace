"""AC4.2-AC4.6 (T-050-15, T-050-40 R13 append-only model): `context
baseline` adopts what origin holds, publishes the local principal as it is on an empty
origin, never rewrites or deletes a branch, and every refusal leaves the repo and the
remote unchanged with the fix for its own cause.

Real git over ``file://`` bare remotes (MEDIUM): the contract is git's own branch/tag state.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from collections.abc import Callable
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
from tests.conftest import GIT_QUIET_INCLUDE
from tests.fixtures.stores import context_store
from tests.helpers.privacy_fixtures import aws_key_shape

_WORK = "feature/0.1.0"
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
    (tmp_path / "gitconfig").write_text(GIT_QUIET_INCLUDE, encoding="utf-8")
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
    store = context_store(root / ".dadaia" / "states")
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


def _published(repo: Path, bare: Path, work: str = _WORK, base: str = "develop") -> bool:
    """*work* is checked out, level with origin, holds *base*, and adds exactly the
    onboarding paths to it (the anchor merged with origin's start)."""
    heads = _heads(bare)
    files = _git(repo, "diff", "--name-only", heads[base], work).splitlines()
    return (
        {work, "main", "develop"} <= set(heads)
        and _git(repo, "rev-parse", "HEAD") == _git(repo, "rev-parse", "@{u}") == heads[work]
        and _ancestor(repo, heads[base], work)
        and sorted(files) == ["AGENTS.md", "specs/constitution.md"]
    )


def _ancestor(repo: Path, old: str, new: str) -> bool:
    done = subprocess.run(["git", "merge-base", "--is-ancestor", old, new], cwd=repo)
    return done.returncode == 0


def _commit_file(repo: Path, rel: str, text: str = "x\n") -> None:
    (repo / rel).parent.mkdir(parents=True, exist_ok=True)
    (repo / rel).write_text(text, encoding="utf-8")
    _git(repo, "add", rel)
    _git(repo, "commit", "-qm", rel)


def _draft(
    principal: str, integration: str = "develop", work: str = "feature/"
) -> Callable[[Path], object]:
    text = _CONSTITUTION.replace(
        "{principal: main, integration: develop, work: feature/}",
        f"{{principal: {principal}, integration: {integration}, work: {work}}}",
    )
    return lambda repo: (repo / "specs" / "constitution.md").write_text(text, encoding="utf-8")


def _tree(bare: Path, ref: str) -> list[str]:
    return sorted(_git(bare, "ls-tree", "-r", "--name-only", ref).splitlines())


_ONBOARDING = ["AGENTS.md", "specs/constitution.md"]
#: (seeded origin branches, origin HEAD, tag, prepare(repo), work returned,
#:  then(repo, bare, seed_heads) -> bool)
_ADOPTIONS = [
    pytest.param((), "", "", lambda r: None, _WORK,
        lambda r, b, s: len(set(_heads(b).values())) == 1 and _tree(b, "main") == _ONBOARDING
        and _git(r, "rev-parse", "HEAD") == _git(r, "rev-parse", "@{u}"),
        id="R13-2-empty-origin-gets-the-onboarding-commit-as-the-principal"),
    pytest.param((), "", "", lambda r: _commit_file(r, "app.py"), _WORK,
        lambda r, b, s: "app.py" in _tree(b, "main") and _ancestor(r, _heads(b)["main"], _heads(b)["develop"]),
        id="C2-operator-code-on-local-main-published-as-it-is"),
    pytest.param(("main",), "", "", lambda r: None, _WORK,
        lambda r, b, s: _heads(b)["develop"] == _heads(b)["main"] == s["main"] and _published(r, b),
        id="principal-only-births-integration-at-its-tip"),
    pytest.param(("main", "develop"), "", "", lambda r: None, _WORK,
        lambda r, b, s: all(_heads(b)[x] == s[x] for x in ("main", "develop")) and _published(r, b),
        id="both-present-are-reused-work-cut-from-integration"),
    pytest.param(("main", "develop", _WORK), "", "", lambda r: None, _WORK,
        lambda r, b, s: _heads(b)[_WORK] == _git(r, "rev-parse", "HEAD") and _ancestor(r, s[_WORK], "HEAD"),
        id="R13-1-origin-work-branch-adopted-never-deleted"),
    pytest.param(("main",), "", "v0.4.7", lambda r: _commit_file(r, "specs/releases/0.5.0/_RELEASE.json", "{}"), "feature/0.5.0",
        lambda r, b, s: "feature/0.5.0" in _heads(b),
        id="sa-live-work-branch-named-three-ways#B41-1-live-release-never-a-tag"),
    pytest.param(("main", "develop"), "", "", lambda r: _git(r, "branch", _WORK, "origin/main"), _WORK,
        lambda r, b, s: _git(r, "rev-parse", "main") == s["main"] and _published(r, b),
        id="D-E3-stale-local-work-takes-the-anchor-main-never-holds-it"),
    pytest.param(("main", "develop"), "nothing", "", lambda r: None, _WORK,
        lambda r, b, s: GitSubprocessClient().published(r) and _published(r, b),
        id="R10b-unborn-clone-of-non-empty-origin-merges-onto-the-tool-root"),
    pytest.param(("master", "develop"), "master", "", _draft("master"), _WORK,
        lambda r, b, s: set(_heads(b)) == {"master", "develop", _WORK} and "specs/constitution.md" in _tree(b, _WORK),
        id="sa-principal-branch-defaults-to-main-and-cut-point-diverges#B42-4-master-principal"),
    pytest.param(("main", "develop"), "main", "", _draft("main", "develop", "release/"), "release/0.1.0",
        lambda r, b, s: set(_heads(b)) == {"main", "develop", "release/0.1.0"}
        and _ancestor(r, _heads(b)["develop"], "release/0.1.0"),
        id="H4-release-prefix-from-the-committed-draft"),
    pytest.param(("master",), "master", "", lambda r: (_draft("master")(r), _commit_file(r, "specs/constitution.md", (r / "specs/constitution.md").read_text())), _WORK,
        lambda r, b, s: "specs/constitution.md" in _tree(b, _WORK) and (r / "specs/constitution.md").is_file(),
        id="P7c-specs-committed-on-the-principal-are-published"),
    pytest.param(("main", "develop"), "", "", lambda r: _commit_file(r, "app.py"), _WORK,
        lambda r, b, s: "app.py" in _tree(b, _WORK),
        id="P8-local-principal-commits-carried-onto-work"),
    pytest.param(("main",), "", "", lambda r: (r / "README.md").write_text("operator\n"), _WORK,
        lambda r, b, s: _published(r, b) and _git(r, "status", "--porcelain") == "M README.md",
        id="h-dirty-work-outside-the-paths-rides-along-uncommitted"),
    pytest.param((), "", "", lambda r: (r / "notes.md").write_text("operator\n"), _WORK,
        lambda r, b, s: (r / "notes.md").read_text() == "operator\n" and "notes.md" not in _tree(b, _WORK),
        id="unborn-clone-keeps-its-untracked-foreign-files"),
]  # fmt: skip


@pytest.mark.parametrize(("seeded", "head", "tag", "prepare", "work", "then"), _ADOPTIONS)
def test_baseline_adopts_origin_and_publishes_the_draft(
    env: tuple[SpecContextService, Path, Path],
    tmp_path: Path,
    seeded: tuple[str, ...],
    head: str,
    tag: str,
    prepare: Callable[[Path], object],
    work: str,
    then: Callable[[Path, Path, dict[str, str]], bool],
) -> None:
    """AC4.2-AC4.4: baseline returns the work branch it published and the Then holds —
    origin's branches adopted, never rewritten; the draft published on top."""
    svc, repo, bare = env
    if seeded:
        _seed(bare, tmp_path / "seed", *seeded, tag=tag)
    if head:
        _git(bare, "symbolic-ref", "HEAD", f"refs/heads/{head}")
    seed_heads = _heads(bare)
    _clone_onboarded(bare, repo)
    prepare(repo)
    assert svc.baseline("proj") == work
    assert then(repo, bare, seed_heads), _heads(bare)


@pytest.mark.skipif(sys.platform == "win32", reason="the shipped pre-push hook is bash")
@pytest.mark.parametrize("seeded", [(), ("main",)], ids=["empty", "principal-only"])
def test_every_publish_passes_the_shipped_pre_push_gate(env, tmp_path: Path, seeded) -> None:
    """The real shipped pre-push gate (this interpreter's CLI) admits the first publish and
    the integration birth at the published principal."""
    svc, repo, bare = env
    if seeded:
        _seed(bare, tmp_path / "seed", *seeded)
    _clone_onboarded(bare, repo)
    runner = tmp_path / ".dadaia" / ".venv" / "bin" / "dadaia"
    runner.parent.mkdir(parents=True)
    runner.write_text(f'#!/bin/sh\nexec "{sys.executable}" -m dadaia_workspace "$@"\n')
    runner.chmod(0o755)
    hook = repo / ".git" / "hooks" / "pre-push"
    shutil.copyfile(workspace_layout.public_scripts_dir() / "pre-push-ci-gate.sh", hook)
    hook.chmod(0o755)
    assert svc.baseline("proj") == "feature/0.1.0"
    assert {"main", "develop", "feature/0.1.0"} <= set(_heads(bare))


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
    assert anchor in str(refused.value) and "Operator action: choose the principal" in str(
        refused.value
    )


def test_several_principal_candidates_are_listed_never_guessed(env, tmp_path: Path) -> None:
    """Design review C6: two candidate heads — both listed, the choice the operator's."""
    svc, repo, bare = env
    _seed(bare, tmp_path / "seed", "trunk", "master")
    _git(bare, "symbolic-ref", "HEAD", "refs/heads/trunk")
    _clone_onboarded(bare, repo)
    with pytest.raises(ContextStateError) as refused:
        svc.baseline("proj")
    message = str(refused.value)
    assert "master, trunk" in message and message.endswith("--principal` with it")


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


def test_a_tool_commit_never_falls_back_to_a_tool_identity(tmp_path: Path, monkeypatch) -> None:
    """SA-H3-2: one identity rule (git's own) — no hard-coded fallback author."""
    (tmp_path / "gitconfig").write_text(
        f"{GIT_QUIET_INCLUDE}[user]\n\tuseConfigOnly = true\n", encoding="utf-8"
    )
    for var in ("NAME", "EMAIL"):
        monkeypatch.delenv(f"GIT_AUTHOR_{var}", raising=False)
        monkeypatch.delenv(f"GIT_COMMITTER_{var}", raising=False)
    repo = tmp_path / "r"
    _git(tmp_path, "init", "-q", str(repo))
    (repo / "a.md").write_text("a\n", encoding="utf-8")
    client = GitSubprocessClient()
    assert (
        client.identity_fix(repo) == f"Operator action: set git user.name in the config of {repo}"
    )
    with pytest.raises(GitSyncError):
        client.commit_paths(repo, "c", ["a.md"])


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
