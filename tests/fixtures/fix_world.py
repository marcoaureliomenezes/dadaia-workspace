"""The refusal worlds both fix-line homes drive: one workspace and context over ``file://`` remotes
(`World`), the cases that plant a refusal (`Case`, `_REFUSALS`), the stand-in pre-push gate, and the
helpers that spell a host path or a workspace-CLI line for the shell a case runs in.

size: MEDIUM — real git and real CLI child processes, no network.
"""

from __future__ import annotations

import contextlib
import inspect
import os
import re
import shutil
import subprocess
import sys
import sysconfig
from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path, PurePosixPath

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app
from dadaia_workspace.core.cli_line import fix_line, git_line
from dadaia_workspace.core.gitflow import DEFAULT, work_branch
from dadaia_workspace.core.models.spec_context import (
    AssociatedRepo,
    ContextState,
    SpecContextProject,
)
from dadaia_workspace.core.platform import workspace_cli_path
from dadaia_workspace.core.specs_version import CANONICAL_SPECS_VERSION
from dadaia_workspace.features.spec_context.service import git_hooks_dir, install_git_hooks
from dadaia_workspace.infrastructure.json_context_store import JsonContextStore
from tests.conftest import GIT_QUIET_INCLUDE
from tests.helpers.oslib import (
    Caps,
    cli_path,
    command,
    detect,
    link,
    make_writable,
    python_in,
    read_text,
    stub_cli,
    write_text,
)
from tests.helpers.oslib import run as os_run
from tests.helpers.privacy_fixtures import aws_key_shape

_TERM = "zorblaxquux"


def _host_path(shell_path: str, caps: Caps | None = None) -> str:
    """A path a POSIX shell printed (Git Bash: ``/c/Users/Shared``) as the host's own, which ``chdir``
    takes."""
    return (
        re.sub(r"^/([a-zA-Z])/", r"\1:/", shell_path) if (caps or detect()).windows else shell_path
    )


def _repo_cli(*argv: str, caps: Caps | None = None) -> str:
    """The workspace CLI run from a clone two levels under its workspace, as a finished line; the
    path is built POSIX-style so it spells alike whatever host builds it."""
    return command(str(cli_path(PurePosixPath("../.."), caps)), *argv, caps=caps)


def _rmtree(path: Path) -> None:
    """Remove *path*, git's read-only pack files included."""
    shutil.rmtree(path, onexc=lambda fn, name, _: (make_writable(Path(name)), fn(name)))


def _single_fix(done: subprocess.CompletedProcess[str]) -> str:
    output = done.stdout + done.stderr
    lines = [line[len("fix: ") :] for line in output.splitlines() if line.startswith("fix: ")]
    assert len(lines) == 1, f"exactly one fix line expected, got {len(lines)}:\n{output}"
    assert "&&" not in lines[0], f"one command per fix line (PowerShell 5.1): {lines[0]}"
    return lines[0]


def _constitution(
    principal: str = "main", integration: str = "develop", work: str = "feature/"
) -> str:
    return (
        f"---\nspecs_pattern_version: {CANONICAL_SPECS_VERSION}\n"
        f"gitflow: {{principal: {principal}, integration: {integration}, work: {work}}}\n---\n# c\n"
    )


#: The caller's environment keys a world never inherits.
_UNSET = (
    "COLUMNS",
    "LINES",
    "DADAIA_CONTEXT",
    "DADAIA_SESSION_ID",
    "GIT_AUTHOR_NAME",
    "GIT_AUTHOR_EMAIL",
    "GIT_COMMITTER_NAME",
    "GIT_COMMITTER_EMAIL",
    "DADAIA_PRIVACY_DENYLIST",
)


class Templates:
    """One world per seed prefix: a prefix's git steps run once under *root*, and every case
    starts from its own copy — never one mutable world shared, fix chains mutate the remote."""

    def __init__(self, root: Path) -> None:
        self.root = root

    def get(self, prefix: Callable[[World], None]) -> Path:
        tmp = self.root / prefix.__name__.strip("_")
        if not tmp.exists():
            prefix(World(tmp))
        return tmp


def _template(prefix: Callable[[World], None]) -> Callable[[World], None]:
    """*prefix*, run through :meth:`World.adopt`."""

    def adopt(world: World) -> None:
        world.adopt(prefix)

    return adopt


class World:
    """One workspace (registry + the CLI at the path ``fix_line`` spells), one context
    ``proj`` whose main repo ``repos/proj`` is a clone of the bare ``proj.git``."""

    @classmethod
    def of(cls, tmp: Path) -> World:
        """A world under *tmp* whose seed templates are shared by every world of the session."""
        return cls(tmp, Templates(tmp.parent / "fixline-templates"))

    def __init__(self, tmp: Path, templates: Templates | None = None) -> None:
        self.tmp = tmp
        self.templates = templates
        self.ws = tmp / "ws"
        self.repo = self.ws / "repos" / "proj"
        self.bare = tmp / "proj.git"
        self.elsewhere = tmp / "elsewhere"
        self.elsewhere.mkdir(parents=True)
        (self.ws / "repos").mkdir(parents=True)
        (self.ws / ".dadaia" / "states").mkdir(parents=True)
        write_text(self.ws / ".dadaia" / "states" / "spec_contexts.json", '{"contexts": []}')
        self.env = {k: v for k, v in os.environ.items() if k not in _UNSET}
        self.env.update(
            GIT_CONFIG_GLOBAL=str(tmp / "gitconfig"),
            GIT_CONFIG_NOSYSTEM="1",
            TERM="dumb",
        )
        write_text(
            tmp / "gitconfig",
            f"{GIT_QUIET_INCLUDE}[user]\n\tname = T\n\temail = t@example.invalid\n\tuseConfigOnly = true\n"
            "[init]\n\tdefaultBranch = main\n",
        )
        # The workspace CLI, as `fix_line` spells it: a venv layout (pyvenv.cfg + the base
        # interpreter, no pip, nothing installed) so the CLI owns THIS workspace from any
        # cwd, importing this checkout and the running venv's dependencies.
        cli = workspace_cli_path(self.ws)
        venv = cli.parent.parent
        cli.parent.mkdir(parents=True)
        base = Path(sys._base_executable)
        write_text(venv / "pyvenv.cfg", f"home = {base.parent}\n")
        interpreter = python_in(venv)
        if not link(str(base), interpreter, is_dir=False):
            pytest.skip("this host refuses symlinks")
        main = "#!python\nimport runpy\nrunpy.run_module('dadaia_workspace', run_name='__main__')\n"
        stub_cli(cli.parent, "dadaia", main, python=interpreter)
        self.env["PYTHONPATH"] = os.pathsep.join(
            [self.env.get("PYTHONPATH", ""), sysconfig.get_paths()["purelib"]]
        )
        self.git(tmp, "init", "-q", "--bare", "-b", "main", str(self.bare))
        JsonContextStore(self.ws / ".dadaia" / "states").save(
            SpecContextProject(
                "proj", ContextState.ALIVE, "proj", self.bare.as_uri(), "2026-01-01T00:00:00+00:00"
            )
        )

    def adopt(self, prefix: Callable[[World], None]) -> None:
        """Run *prefix* on this fresh world — as a copy of the module's template world when
        there is one. A prefix writes the bare remote and the clone only; the clone's
        ``origin`` and hook are the absolute paths relocated."""
        if self.templates is None:
            prefix(self)
            return
        template = self.templates.get(prefix)
        shutil.rmtree(self.bare)
        shutil.copytree(template / self.bare.name, self.bare, symlinks=True)
        if (template / self.repo.relative_to(self.tmp)).is_dir():
            shutil.copytree(template / self.repo.relative_to(self.tmp), self.repo, symlinks=True)
            self.git(self.repo, "remote", "set-url", "origin", self.bare.as_uri())
            install_git_hooks(self.repo, force=True)

    def run(
        self, argv: list[str] | str, cwd: Path, stdin: str = "", setup: bool = False
    ) -> subprocess.CompletedProcess[str]:
        shell = isinstance(argv, str)
        env = self.env | {"DADAIA_WT": "1"} if setup else self.env
        return os_run(["sh", "-c", argv] if shell else argv, cwd=cwd, env=env, input=stdin, timeout=50)  # fmt: skip

    def git(self, cwd: Path, *args: str) -> str:
        done = self.run(["git", *args], cwd, setup=True)
        assert done.returncode == 0, f"git {args}: {done.stderr}"
        return done.stdout.strip()

    def cli(self, *argv: str) -> subprocess.CompletedProcess[str]:
        return self.run([str(workspace_cli_path(self.ws)), *argv], self.elsewhere)

    def seed(self, constitution: str | None = None, *branches: str, live: str = "") -> None:
        """The bare remote carries *branches* (default ``main`` then ``develop``), each at
        one commit holding a README and, when given, ``specs/constitution.md`` and the
        *live* release's ``_RELEASE.json``."""
        src = self.tmp / "seed"
        self.git(self.tmp, "init", "-q", str(src))
        write_text(src / "README.md", "r\n")
        if constitution is not None:
            (src / "specs").mkdir()
            write_text(src / "specs" / "constitution.md", constitution)
        if live:
            (src / "specs" / "releases" / live).mkdir(parents=True)
            write_text(src / "specs" / "releases" / live / "_RELEASE.json", "{}\n")
        self.git(src, "add", "-A")
        self.git(src, "commit", "-qm", "seed")
        for branch in branches or ("main", "develop"):
            self.git(src, "push", "-q", self.bare.as_uri(), f"HEAD:refs/heads/{branch}")

    def clone(self, hook: bool = True) -> None:
        self.git(self.tmp, "clone", "-q", self.bare.as_uri(), str(self.repo))
        if hook:
            install_git_hooks(self.repo)

    def commit(self, rel: str, text: str, branch: str | None = None) -> None:
        if branch is not None:
            self.git(self.repo, "checkout", "-q", "-b", branch)
        path = self.repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        write_text(path, text)
        self.git(self.repo, "add", rel)
        self.git(self.repo, "commit", "-qm", f"add {rel}")

    def onboard(self, constitution: str | None = None) -> None:
        (self.repo / "specs").mkdir(exist_ok=True)
        write_text(self.repo / "specs" / "constitution.md", constitution or _constitution())
        write_text(self.repo / "AGENTS.md", "# law\n")

    def remote_heads(self) -> dict[str, str]:
        out = self.git(self.bare, "for-each-ref", "--format=%(refname:lstrip=2) %(objectname)")
        return dict(line.split() for line in out.splitlines())

    def deny(self) -> None:
        denylist = self.ws / ".dadaia" / "states" / "privacy_denylist.json"
        write_text(denylist, f'{{"{_TERM}": "t"}}')
        self.env["DADAIA_PRIVACY_DENYLIST"] = str(denylist)  # the fix runs from any cwd


@dataclass(frozen=True)
class Case:
    """*build* plants the refusal and returns the command that hits it (argv, or a shell
    line run in the repo); *before* is the documented step the refusal text asks
    for before its fix (an edit), or the act an action fix names (an act declaring a second
    parameter is handed the printed fix line); *then* replaces the re-run when the fix renames what the
    refused command named; *done* asserts the published end state."""

    build: Callable[[World], list[str] | str]
    done: Callable[[World], None]
    before: Callable[..., None] | None = None
    then: list[str] | str | None = None
    replaces: bool = False

    def play(self, world: World, fix: str) -> None:
        """Runs *before* on *world*; a two-parameter act is handed the printed *fix* line."""
        if self.before is None:
            return
        if len(inspect.signature(self.before).parameters) == 2:
            self.before(world, fix)
        else:
            self.before(world)


@dataclass(frozen=True)
class Skip:
    """A site this harness cannot drive, with the reason."""

    reason: str


def _hit(world: World, command: list[str] | str) -> subprocess.CompletedProcess[str]:
    if isinstance(command, str):
        return world.run(command, world.repo)
    return world.cli(*command) if command[0] != "git" else world.run(command, world.repo)


def _push_gate(world: World, push: str) -> subprocess.CompletedProcess[str]:
    """The first refusal of *push*: the ref lines git hands its pre-push hook, captured by a
    stand-in hook, fed to an in-process ``ci push-gate-check`` (80 columns, no TTY) from the
    hook's cwd. The hook's own forwarding stays proven by the real pushes below and by
    ``test_the_gate_is_read_only…``; one line without a TTY by the sentinel."""
    refs, cwd = world.tmp / "pre-push.refs", world.tmp / "pre-push.cwd"
    hooks = git_hooks_dir(world.repo)
    assert hooks is not None
    shipped = (hooks / "pre-push").read_bytes()
    write_text(hooks / "pre-push", f'#!/bin/sh\npwd > "{cwd}"\ncat > "{refs}"\nexit 1\n')
    try:
        world.run(push, world.repo)
    finally:
        (hooks / "pre-push").write_bytes(shipped)
    env: dict[str, str | None] = {**world.env, **dict.fromkeys(_UNSET), "COLUMNS": "80"}
    with contextlib.chdir(_host_path(read_text(cwd).strip())):
        ran = CliRunner().invoke(app, ["ci", "push-gate-check"], input=read_text(refs), env=env)
    return subprocess.CompletedProcess(push, ran.exit_code, ran.output, "")


# ── push-gate cases ──────────────────────────────────────────────────────────────────


@_template
def _published(world: World) -> None:
    world.seed(_constitution())
    world.clone()


@_template
def _released(world: World) -> None:
    """Published, with a live release: the work branch is the rule's, never its fallback."""
    world.seed(_constitution(), live="1.0.0")
    world.clone()


@_template
def _seeded(world: World) -> None:
    world.seed(_constitution())


def _outside(world: World, published: bool = True) -> str:
    """The refused ref is not the checked-out one."""
    if published:
        _published(world)
    world.commit("notes.md", "n\n", branch="topic")
    world.git(world.repo, "checkout", "-q", "main")
    return "git push -q origin topic"


def _outside_with_work(world: World) -> str:
    """The live work branch has diverged from the refused ref: only switch + merge carries it."""
    _published(world)
    world.commit("w.md", "w\n", branch="feature/0.1.0")
    world.git(world.repo, "checkout", "-q", "main")
    return _outside(world, published=False)


def _outside_detached(world: World) -> str:
    _published(world)
    world.commit("notes.md", "n\n", branch="topic")
    world.git(world.repo, "checkout", "-q", "--detach")
    world.git(world.repo, "branch", "-q", "-D", "topic")
    return "git push -q origin HEAD:refs/heads/topic"


#: The refusal's documented steps after its switch: merge the refused commit, push the work.
_MERGE_TOPIC = "git merge -q --no-edit topic && git push -q origin feature/0.1.0"


def _work_carries_topic(world: World) -> None:
    tip = world.remote_heads()["feature/0.1.0"]
    assert "notes.md" in world.git(world.repo, "ls-tree", "--name-only", tip).splitlines()


def _mismatch(world: World) -> str:
    _published(world)
    world.commit("notes.md", "n\n", branch="topic")
    return "git push -q origin topic:feature/1.0.0"


def _birth_published(world: World) -> str:
    world.seed(_constitution(), "main")
    world.clone()
    world.commit("notes.md", "n\n", branch="develop")
    return "git push -q origin develop"


def _develop_at_main(world: World) -> None:
    heads = world.remote_heads()
    assert heads["develop"] == heads["main"]


def _baseline_done(
    world: World, work: str = "feature/0.1.0", gitflow: tuple[str, ...] = ("main", "develop")
) -> None:
    heads = world.remote_heads()
    assert {*gitflow, work} <= set(heads), heads
    shown = world.git(world.repo, "show", "--name-only", "--format=", heads[work])
    assert "specs/constitution.md" in shown.splitlines()


def _malformed(world: World) -> str:
    _released(world)
    world.commit("notes.md", "n\n", branch=_work(world))
    return f"printf 'not a ref line\\n' | {fix_line(world.ws, 'ci', 'push-gate-check')}"


def _work(world: World) -> str:
    """The live work branch by the one rule."""
    return work_branch(world.repo, DEFAULT, world.repo.name)


def _work_pushed(world: World, work: str = "feature/1.0.0") -> None:
    assert world.remote_heads().get(work) == world.git(world.repo, "rev-parse", work)


def _denylisted(world: World) -> str:
    _published(world)
    world.deny()
    world.commit("notes.md", f"a {_TERM} b\n", branch="feature/1.0.0")
    world.commit("more.md", "m\n")
    return "git push -q origin feature/1.0.0"


def _drop_term(world: World) -> None:
    write_text(world.repo / "notes.md", "a b\n")


#: The refusal's documented step after its fix, the rewrite verb: push it again.
_COMMIT_PUSH = "git push -q origin feature/1.0.0"


def _clean_publish(world: World) -> None:
    """The operator's work is published, without the term."""
    tip = world.remote_heads()["feature/1.0.0"]
    assert _TERM not in world.git(world.repo, "log", "-p", tip, "--not", "origin/develop")
    assert {"notes.md", "more.md"} <= set(
        world.git(world.bare, "ls-tree", "--name-only", tip).split()
    )
    assert not world.git(world.repo, "status", "--porcelain")


def _denylisted_not_checked_out(world: World) -> str:
    """HEAD is `main`; the refused branch must be switched to first."""
    command = _denylisted(world)
    world.git(world.repo, "checkout", "-q", "main")
    return command


#: The operator's edit happens on the refused branch, after the switch.
_CLEAN_COMMIT_PUSH = f"printf 'a b\\n' > notes.md && {_COMMIT_PUSH}"


def _denylisted_advanced_integration(world: World) -> str:
    """Origin's integration moved on after this work was cut."""
    _published(world)
    world.deny()
    world.commit("mine.md", "m\n", branch="feature/1.0.0")
    world.git(world.repo, "push", "-q", "-u", "origin", "feature/1.0.0")
    other = world.tmp / "other"
    world.git(world.tmp, "clone", "-q", "-b", "develop", world.bare.as_uri(), str(other))
    write_text(other / "dep.txt", "dependabot\n")
    world.git(other, "add", "dep.txt")
    world.git(other, "commit", "-qm", "dep")
    world.git(other, "push", "-q", "--no-verify", "origin", "develop")
    world.git(world.repo, "fetch", "-q", "origin")
    world.commit("notes.md", f"a {_TERM} b\n", branch="feature/1.0.1")
    world.commit("more.md", "m\n")
    return "git push -q origin feature/1.0.1"


def _nothing_reverted(world: World) -> None:
    tip = world.remote_heads()["feature/1.0.1"]
    assert world.git(world.repo, "rev-parse", f"{tip}^") == world.remote_heads()["feature/1.0.0"]
    deleted = world.git(world.repo, "log", "--format=", "--name-only", "--diff-filter=D", tip)
    assert "dep.txt" not in deleted.split()
    assert _TERM not in world.git(world.repo, "log", "-p", tip, "--not", "origin/feature/1.0.0")


def _non_canon(world: World) -> str:
    _published(world)
    world.commit("specs/junk.md", "j\n", branch="feature/1.0.0")
    world.commit("notes.md", "n\n")  # real work rides the range: the rewrite keeps it
    return "git push -q origin feature/1.0.0"


def _rm_junk(world: World) -> None:
    world.git(world.repo, "rm", "-q", "specs/junk.md")


def _no_junk(world: World) -> None:
    tip = world.remote_heads()["feature/1.0.0"]
    assert "specs/junk.md" not in world.git(world.repo, "ls-tree", "-r", "--name-only", tip)


def _denylisted_in_a_worktree(world: World) -> str:
    """The pushing repo is a worktree under repos/<slug>/."""
    _published(world)
    world.deny()
    wt = world.repo / ".claude" / "worktrees" / "agent-x"
    world.git(world.repo, "worktree", "add", "-q", "-b", "feature/1.0.0", str(wt), "origin/develop")
    write_text(wt / "notes.md", f"a {_TERM} b\n")
    world.git(wt, "add", "notes.md")
    world.git(wt, "commit", "-qm", "n")
    return git_line(wt, "push", "-q", "origin", "feature/1.0.0")


def _drop_worktree_term(world: World) -> None:
    write_text(world.repo / ".claude" / "worktrees" / "agent-x" / "notes.md", "a b\n")


def _worktree_clean(world: World) -> None:
    tip = world.remote_heads()["feature/1.0.0"]
    assert _TERM not in world.git(world.repo, "log", "-p", tip, "--not", "origin/develop")
    assert "notes.md" in world.git(world.repo, "ls-tree", "--name-only", tip).splitlines()


def _denylisted_no_context(world: World) -> str:
    """No context owns the pushing repo: the fix adopts it, never a `<context>` placeholder."""
    command = _denylisted(world)
    JsonContextStore(world.ws / ".dadaia" / "states").delete("proj")
    return command


# ── baseline cases ───────────────────────────────────────────────────────────────────


def _no_identity(world: World) -> list[str]:
    world.clone()
    world.onboard()
    write_text(world.tmp / "gitconfig", f"{GIT_QUIET_INCLUDE}[user]\n\tuseConfigOnly = true\n")
    return ["context", "baseline", "proj"]


def _secret_draft(world: World) -> list[str]:
    world.clone()
    world.onboard()
    write_text(world.repo / "AGENTS.md", f"key {aws_key_shape()}\n")
    return ["context", "baseline", "proj"]


def _drop_secret(world: World) -> None:
    write_text(world.repo / "AGENTS.md", "key\n")


def _remote_back(world: World) -> None:
    (world.tmp / "away.git").rename(world.bare)


def _baseline_denylisted(world: World) -> list[str]:
    world.clone()
    world.onboard()
    world.deny()
    write_text(world.repo / "AGENTS.md", f"a {_TERM}\n")
    # Committed before the publish, so only the gate sees it: the in-process preflight
    # preflight refuses an untracked onboarding file first.
    world.git(world.repo, "add", "AGENTS.md")
    world.git(world.repo, "commit", "-qm", "draft")
    return ["context", "baseline", "proj"]


def _drop_draft_term(world: World) -> None:
    write_text(world.repo / "AGENTS.md", "a\n")


#: The refusal's documented step after its fix, the rewrite verb: the publish again.
_BASELINE_AGAIN = _repo_cli("context", "baseline", "proj")


def _no_url_no_checkout(world: World) -> list[str]:
    _seeded(world)
    store = JsonContextStore(world.ws / ".dadaia" / "states")
    store.update(
        SpecContextProject("proj", ContextState.DEAD, "proj", "", "2026-01-01T00:00:00+00:00")
    )
    return ["context", "alive", "proj"]


def _identity(world: World) -> None:
    for key, value in (("user.name", "T"), ("user.email", "t@example.invalid")):
        world.git(world.repo, "config", key, value)


def _origin(world: World) -> None:
    world.git(world.repo, "remote", "add", "origin", world.bare.as_uri())


def _clone(world: World) -> None:
    world.git(world.tmp, "clone", "-q", world.bare.as_uri(), str(world.repo))


def _create(world: World) -> None:
    assert (
        world.cli("context", "create", "proj", "--main-repo", world.bare.as_uri()).returncode == 0
    )


def _cloned(world: World) -> None:
    assert (world.repo / "README.md").is_file()


def _advance_origin_work(world: World) -> None:
    other = world.tmp / "other"
    world.git(world.tmp, "clone", "-q", "-b", "feature/1.0.0", world.bare.as_uri(), str(other))
    write_text(other / "x.md", "x\n")
    world.git(other, "add", "x.md")
    world.git(other, "commit", "-qm", "x")
    world.git(other, "push", "-q", "origin", "feature/1.0.0")


def _no_checkout(world: World) -> list[str]:
    _seeded(world)
    return ["context", "baseline", "proj"]


def _draft_principal_absent(world: World) -> list[str]:
    """Origin publishes `main` under a malformed block;
    the draft names `trunk` — the one origin candidate is the fix's principal."""
    world.seed("---\nspecs_pattern_version: 7\ngitflow: {principal: main\n---\n# c\n", "main")
    world.clone()
    world.onboard(_constitution("trunk", "stage", "rel/"))
    return ["context", "baseline", "proj"]


def _never_onboarded(world: World) -> list[str]:
    """No constitution on disk — the fix is onboarding's specs step."""
    world.seed(None)
    world.clone()
    return ["context", "baseline", "proj"]


def _unknown_context(world: World) -> list[str]:
    _seeded(world)
    JsonContextStore(world.ws / ".dadaia" / "states").delete("proj")
    return ["context", "baseline", "proj"]


def _alive_remote_gone(world: World) -> list[str]:
    _seeded(world)
    store = JsonContextStore(world.ws / ".dadaia" / "states")
    store.update(
        SpecContextProject(
            "proj", ContextState.DEAD, "proj", world.bare.as_uri(), "2026-01-01T00:00:00+00:00"
        )
    )
    world.bare.rename(world.tmp / "away.git")
    return ["context", "alive", "proj"]


def _alive_no_integration(world: World) -> list[str]:
    """Origin holds `main` only: neither a work branch nor the declared integration branch."""
    world.seed(_constitution(), "main")
    store = JsonContextStore(world.ws / ".dadaia" / "states")
    store.update(
        SpecContextProject(
            "proj", ContextState.DEAD, "proj", world.bare.as_uri(), "2026-01-01T00:00:00+00:00"
        )
    )
    return ["context", "alive", "proj"]


def _origin_gains_develop(world: World) -> None:
    world.git(world.tmp / "seed", "push", "-q", world.bare.as_uri(), "HEAD:refs/heads/develop")
    world.git(world.repo, "fetch", "-q", "origin")


# ── dead cases ───────────────────────────────────────────────────────────────────────


def _dead_done(world: World) -> None:
    assert not world.repo.exists()


def _on_work(world: World) -> None:
    _published(world)
    world.git(world.repo, "checkout", "-q", "-b", "feature/1.0.0", "origin/develop")
    world.git(world.repo, "push", "-q", "-u", "origin", "feature/1.0.0")


def _untracked(world: World) -> list[str]:
    _on_work(world)
    write_text(world.repo / "notes.md", "n\n")
    return ["context", "dead", "proj"]


def _discard_notes(world: World) -> None:
    (world.repo / "notes.md").unlink()


def _two_untracked(world: World) -> list[str]:
    _untracked(world)
    write_text(world.repo / "b.md", "b\n")
    return ["context", "dead", "proj"]


def _discard_what_the_fix_names(world: World) -> None:
    """The operator discards exactly the paths the printed fix names — no more."""
    fix = _single_fix(_hit(world, ["context", "dead", "proj"]))
    for name in ("notes.md", "b.md"):
        if name in fix:
            (world.repo / name).unlink()
    assert not world.git(world.repo, "status", "--porcelain"), "the one fix left a path dirty"


def _no_origin(world: World) -> list[str]:
    _on_work(world)
    world.git(world.repo, "remote", "remove", "origin")
    store = JsonContextStore(world.ws / ".dadaia" / "states")
    ctx = store.get("proj")
    assert ctx is not None
    store.update(SpecContextProject(ctx.name, ctx.state, ctx.repo_slug, "", ctx.created_at))
    return ["context", "dead", "proj"]


def _unborn_dirty(world: World) -> list[str]:
    world.clone()
    write_text(world.repo / "notes.txt", "n\n")
    return ["context", "dead", "proj"]


def _commits_no_remote(world: World) -> list[str]:
    world.git(world.tmp, "init", "-q", str(world.repo))
    install_git_hooks(world.repo)
    world.commit("README.md", "r\n")
    return ["context", "dead", "proj"]


def _dirty_on_integration(world: World) -> list[str]:
    _released(world)
    world.git(world.repo, "checkout", "-q", "develop")
    world.commit("README.md", "edited\n")  # unpushed, on the integration branch
    return ["context", "dead", "proj"]


def _dead_via_work(world: World) -> None:
    heads = world.remote_heads()
    assert heads["develop"] == world.git(world.bare, "rev-parse", "main")
    assert "feature/1.0.0" in heads  # the planted live release's work branch
    assert not world.repo.exists()


def _associated_on_integration(world: World) -> list[str]:
    """An associated repo has no specs/ — its work branch is the main repo's."""
    _released(world)
    world.git(world.repo, "checkout", "-q", "-b", "feature/1.0.0", "origin/develop")
    world.git(world.repo, "push", "-q", "-u", "origin", "feature/1.0.0")
    lib, lib_bare = world.ws / "repos" / "lib", world.tmp / "lib.git"
    world.git(world.tmp, "init", "-q", "--bare", "-b", "main", str(lib_bare))
    world.git(world.tmp, "clone", "-q", lib_bare.as_uri(), str(lib))
    write_text(lib / "README.md", "r\n")  # no specs/ of its own
    world.git(lib, "add", "README.md")
    world.git(lib, "commit", "-qm", "r")
    world.git(lib, "push", "-q", "origin", "HEAD:main", "HEAD:develop")
    world.git(lib, "checkout", "-q", "-b", "develop", "--track", "origin/develop")
    install_git_hooks(lib)
    write_text(lib / "README.md", "edited\n")
    world.git(lib, "commit", "-qam", "edited")
    store = JsonContextStore(world.ws / ".dadaia" / "states")
    ctx = store.get("proj")
    assert ctx is not None
    store.update(replace(ctx, associated_repos=(AssociatedRepo("lib", lib_bare.as_uri()),)))
    return ["context", "dead", "proj"]


def _associated_dead(world: World) -> None:
    """Every repo is pushed before any is held."""
    assert "feature/1.0.0" in world.git(world.tmp / "lib.git", "branch")
    assert not world.repo.exists() and not (world.ws / "repos" / "lib").exists()


def _dead_denylisted(world: World) -> list[str]:
    _on_work(world)
    world.deny()
    world.commit("README.md", f"a {_TERM}\n")
    return ["context", "dead", "proj"]


def _dead_denylisted_two_commits(world: World) -> list[str]:
    """The term sits in the newest of two unpublished commits: the remedy's reset moves the branch."""
    _on_work(world)
    world.deny()
    world.commit("notes.md", "n\n")
    world.commit("README.md", f"a {_TERM}\n")
    return ["context", "dead", "proj"]


def _unpushed_side_branch(world: World) -> list[str]:
    """A local branch other than HEAD's carries a commit origin lacks: a non-work branch the
    gate refuses to push, already archived once, then advanced."""
    _published(world)
    world.git(world.repo, "checkout", "-q", "-b", "wt/0.5.0a", "origin/develop")
    world.commit("notes.md", "n\n")
    archived = world.git(world.repo, "rev-parse", "HEAD")[:7]
    world.git(world.repo, "push", "-q", "origin", f"HEAD:refs/tags/archive/wt/0.5.0a/{archived}")
    world.commit("notes.md", "m\n")
    world.git(world.repo, "checkout", "-q", "--detach", "origin/main")
    return ["context", "dead", "proj"]


def _stashed(world: World) -> list[str]:
    """A stash entry dies with the clone."""
    _on_work(world)
    write_text(world.repo / "README.md", "edited\n")
    world.git(world.repo, "stash", "push", "-q", "-m", "wip")
    return ["context", "dead", "proj"]


def _play_stash_act(world: World) -> None:
    """The operator drops the stash entry, the second act the refusal names (a pop would
    leave a dirty checkout, which dead refuses)."""
    world.git(world.repo, "stash", "drop", "-q")


def _dead_twice(world: World) -> list[str]:
    """Dead on a dead context."""
    _seeded(world)
    store = JsonContextStore(world.ws / ".dadaia" / "states")
    store.update(
        SpecContextProject(
            "proj", ContextState.DEAD, "proj", world.bare.as_uri(), "2026-01-01T00:00:00+00:00"
        )
    )
    return ["context", "dead", "proj"]


def _dead_clean_detached(world: World) -> list[str]:
    """A clean published detached HEAD has nothing to push."""
    _published(world)
    world.git(world.repo, "checkout", "-q", "--detach", "origin/main")
    return ["context", "dead", "proj"]


def _drop_readme_term(world: World) -> None:
    write_text(world.repo / "README.md", "a\n")


def _work_ahead_of_origin(world: World) -> str:
    """The work branch is ahead of its published self; the command is the hook's ref line
    for that update, fed to the real ``ci ref-gate-check``."""
    _published(world)
    world.commit("w.md", "w\n", branch="feature/0.1.0")
    world.git(world.repo, "push", "-q", "-u", "origin", "feature/0.1.0")
    world.commit("more.md", "m\n")
    return (
        "printf '%s %s refs/heads/feature/0.1.0\\n' $(git rev-parse HEAD~1) $(git rev-parse HEAD)"
        f" | {fix_line(world.ws, 'ci', 'ref-gate-check')}"
    )


def _work_forced(world: World) -> list[str]:
    """The work branch, published, forced to a commit origin does not hold: the real hook refuses."""
    _published(world)
    world.git(world.repo, "branch", "feature/0.1.0", "origin/develop")
    world.git(world.repo, "push", "-q", "origin", "feature/0.1.0")
    world.git(world.repo, "fetch", "-q", "origin")
    world.commit("a.txt", "a", branch="other")
    return ["git", "branch", "-f", "feature/0.1.0", "other"]


def _open_a_tree(world: World, fix: str) -> None:
    """The act the refusal names: the printed runner and repo slug open a tree, which the merge lands."""
    named = re.search(r"with (.+) and the name of", fix)
    assert named, f"no runner command in the fix: {fix}"
    done = world.run(f"{named[1]} 0.1.0/wt-backlog-foo", world.repo)
    assert done.returncode == 0, done.stderr


def _tree_opened(world: World) -> None:
    assert "wt/0.1.0/wt-backlog-foo" in world.git(world.repo, "branch", "--list", "wt/*")


def _land_the_work_branch(world: World) -> None:
    """What a tree's merge and push leave: origin holds the work branch's tip."""
    world.git(world.repo, "push", "-q", "origin", "feature/0.1.0")


def _work_pushed_0_1_0(world: World) -> None:
    assert world.remote_heads()["feature/0.1.0"] == world.git(world.repo, "rev-parse", "HEAD")


# ── the census ───────────────────────────────────────────────────────────────────────

_REFUSALS: dict[str, tuple[Case | tuple[Case, ...] | Skip, ...]] = {
    "branch_policy._refuse_branch": (
        Case(_birth_published, _develop_at_main, replaces=True),
        (
            Case(_outside, _work_carries_topic, then=_MERGE_TOPIC),
            Case(_outside_with_work, _work_carries_topic, then=_MERGE_TOPIC),
            Case(_outside_detached, _work_carries_topic, then="git push -q origin feature/0.1.0"),
        ),
        Skip("an Agent action on the git host: the PR is no command to run"),
    ),
    "branch_policy.check_branch_policy": (
        Case(_mismatch, _work_pushed, then="git push -q origin feature/1.0.0"),
    ),
    "branch_policy.check_ref_policy": (
        (
            Case(_work_ahead_of_origin, _work_pushed_0_1_0, before=_land_the_work_branch),
            Case(_work_forced, _tree_opened, before=_open_a_tree, replaces=True),
        ),
    ),
    "push_gate._rewrite_fix": (
        (
            Case(_denylisted_not_checked_out, _clean_publish, then=_CLEAN_COMMIT_PUSH),
            Case(_denylisted, _clean_publish, before=_drop_term, then=_COMMIT_PUSH),
            Case(
                _denylisted_in_a_worktree,
                _worktree_clean,
                before=_drop_worktree_term,
                then="git -C .claude/worktrees/agent-x push -q origin feature/1.0.0",
            ),
            Case(_denylisted_no_context, _clean_publish, before=_drop_term, then=_COMMIT_PUSH),
            Case(
                _denylisted_advanced_integration,
                _nothing_reverted,
                before=_drop_term,
                then="git push -q origin feature/1.0.1",
            ),
            Case(_non_canon, _no_junk, before=_rm_junk, then=_COMMIT_PUSH),
        ),
    ),
    "push_gate._read_failure": (Skip("needs a corrupted object store; `git fsck` names it"),),
    "push_gate.push_gate_decision": (
        Case(_malformed, lambda w: _work_pushed(w, _work(w)), replaces=True),
    ),
    "ci._gate_inputs": (
        Skip(
            "it prints the work-branch rule's own fix; test_ci__push_gate_gitflow_resolution pins it"
        ),
    ),
    "ci._repo_root": (Skip("the pre-push hook always runs inside the repo it pushes"),),
    "ci.push_gate_check": (Skip("the gate's refusal: its fix is a branch_policy/push_gate site"),),
    "ci._fold": (
        Skip(
            "a group left with no message: test__worktree_end.py pins its one fix and the unchanged branch"
        ),
    ),
    "ci._rewrite_unpublished": (
        Skip("refuses a commit origin holds: test_reference_transaction__work_branch.py"),
    ),
    "service.SpecContextService.show": (Case(_unknown_context, _cloned, before=_create),),
    "service.SpecContextService.alive": (
        Case(_no_url_no_checkout, _cloned, before=_clone),
        Case(_alive_remote_gone, _cloned, before=_remote_back),
        Case(_alive_no_integration, _cloned, before=_origin_gains_develop),
    ),
    "service.SpecContextService.baseline": (
        Case(_no_checkout, _cloned),
        Case(_no_identity, _baseline_done, before=_identity),
        Case(_never_onboarded, _baseline_done),
        Case(_baseline_denylisted, _baseline_done, before=_drop_draft_term, then=_BASELINE_AGAIN),
    ),
    "service.SpecContextService._refuse_principal_absent": (
        Case(_draft_principal_absent, lambda w: _baseline_done(w, "rel/0.1.0", ("main", "stage"))),
    ),
    "service.SpecContextService._require_publishable": (
        Case(_secret_draft, _baseline_done, before=_drop_secret),
    ),
    "service.SpecContextService._dead_preflight": (
        (
            Case(_untracked, _dead_done, before=_discard_notes),
            Case(_two_untracked, _dead_done, before=_discard_what_the_fix_names),
        ),
        Case(_no_origin, _dead_done, before=_origin),
        (
            Case(_unpushed_side_branch, _dead_done),
            Case(_commits_no_remote, _dead_done, before=_origin),
            Case(_stashed, _dead_done, before=_play_stash_act),
        ),
        (
            Case(_dirty_on_integration, _dead_via_work),
            Case(_associated_on_integration, _associated_dead),
        ),
    ),
    "service.SpecContextService.dead": (
        Case(_dead_twice, _dead_done),
        (
            Case(
                _dead_denylisted,
                _dead_done,
                before=_drop_readme_term,
            ),
            Case(
                _dead_denylisted_two_commits,
                _dead_done,
                before=_drop_readme_term,
            ),
        ),
        Skip("a refused hold (`repos/` outside the workspace): test_context_dead_holds.py"),
    ),
}
