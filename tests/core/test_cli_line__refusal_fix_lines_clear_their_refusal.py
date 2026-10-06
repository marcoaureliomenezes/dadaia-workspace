"""0.5.0 c3 re-review (C1, H1-H4, M1): every refusal of the pre-push
gate (`ci push-gate-check`), `context baseline` and `context dead` prints ONE fix line
that, executed verbatim, clears the refusal.

The doctor has this harness (``test_doctor_fix_lines_clear_their_finding.py``); these
three verbs did not, and their fix lines failed review round after round, one site at a
time. Each case below builds the triggering state over ``file://`` remotes and hits the
refusal: a push-gate case feeds the ref lines git hands its hook to an in-process
``ci push-gate-check`` (80 columns, no TTY); a baseline/alive/dead case runs the real
command as a child process. It takes the single ``fix:`` line and runs it with ``sh -c`` —
an ``Operator action:`` line is played by the case's *operator* instead (ADR 0158) — and
runs the real command (the real push through the shipped hook) again. One line without a TTY — every family prints through
``cli/_fail.fail`` — is proven on a real child by
:func:`test_every_fix_line_prints_on_one_line_without_a_tty`. Progress rule:
the command then succeeds, or refuses with a DIFFERENT fix line (the next step), which is
followed the same way — at most four steps, never a repeated line. A fix that is itself
the publish (``git push …``, ``context baseline``) replaces the refused command: its
success is the clearance.

The census counts every ``fix:`` producer in the four modules per enclosing function: a new
refusal without a case (or a ``Skip`` reason) fails :func:`test_every_fix_site_has_a_case`.

size: MEDIUM — real git and real CLI child processes, no network.
"""

from __future__ import annotations

import ast
import contextlib
import os
import re
import shutil
import subprocess
import sys
import sysconfig
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app
from dadaia_workspace.core.cli_line import cli_path, fix_line, shell_line
from dadaia_workspace.core.gitflow import DEFAULT, work_branch
from dadaia_workspace.core.models.spec_context import (
    AssociatedRepo,
    ContextState,
    SpecContextProject,
)
from dadaia_workspace.core.specs_version import CANONICAL_SPECS_VERSION
from dadaia_workspace.features.spec_context.service import git_hooks_dir, install_git_hooks
from dadaia_workspace.infrastructure.json_context_store import JsonContextStore
from tests.conftest import GIT_QUIET_INCLUDE
from tests.helpers.privacy_fixtures import aws_key_shape

pytestmark = [
    pytest.mark.slow(reason="real git remotes and CLI child processes per case"),
    pytest.mark.skipif(sys.platform == "win32", reason="the shipped pre-push hook is bash"),
]

_PKG = Path(__file__).resolve().parents[2] / "dadaia_workspace"
_TERM = "zorblaxquux"


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
    """One world per seed prefix per module: a prefix's git steps run once, and every case
    starts from its own copy — never one mutable world shared, fix chains mutate the remote."""

    def __init__(self, factory: pytest.TempPathFactory) -> None:
        self.factory = factory
        self.dirs: dict[Callable[[World], None], Path] = {}

    def get(self, prefix: Callable[[World], None]) -> Path:
        if prefix not in self.dirs:
            world = World(self.factory.mktemp(prefix.__name__.strip("_")))
            prefix(world)
            self.dirs[prefix] = world.tmp
        return self.dirs[prefix]


def _template(prefix: Callable[[World], None]) -> Callable[[World], None]:
    """*prefix*, run through :meth:`World.adopt`."""

    def adopt(world: World) -> None:
        world.adopt(prefix)

    return adopt


@pytest.fixture(scope="module")
def templates(tmp_path_factory: pytest.TempPathFactory) -> Templates:
    return Templates(tmp_path_factory)


@pytest.fixture
def world(tmp_path: Path, templates: Templates) -> World:
    return World(tmp_path, templates)


class World:
    """One workspace (registry + the CLI at the path ``fix_line`` spells), one context
    ``proj`` whose main repo ``repos/proj`` is a clone of the bare ``proj.git``."""

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
        (self.ws / ".dadaia" / "states" / "spec_contexts.json").write_text('{"contexts": []}')
        self.env = {k: v for k, v in os.environ.items() if k not in _UNSET}
        self.env.update(
            GIT_CONFIG_GLOBAL=str(tmp / "gitconfig"),
            GIT_CONFIG_NOSYSTEM="1",
            TERM="dumb",
        )
        (tmp / "gitconfig").write_text(
            f"{GIT_QUIET_INCLUDE}[user]\n\tname = T\n\temail = t@example.invalid\n\tuseConfigOnly = true\n"
            "[init]\n\tdefaultBranch = main\n",
            encoding="utf-8",
        )
        # The workspace CLI, as `fix_line` spells it: a venv layout (pyvenv.cfg + the base
        # interpreter, no pip, nothing installed) so the CLI owns THIS workspace from any
        # cwd, importing this checkout and the running venv's dependencies.
        cli = cli_path(self.ws)
        venv = cli.parent.parent
        cli.parent.mkdir(parents=True)
        base = Path(sys._base_executable)
        (venv / "pyvenv.cfg").write_text(f"home = {base.parent}\n", encoding="utf-8")
        (cli.parent / "python").symlink_to(base)
        cli.write_text(f'#!/bin/sh\nexec "{cli.parent / "python"}" -m dadaia_workspace "$@"\n')
        cli.chmod(0o755)
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
        self, argv: list[str] | str, cwd: Path, stdin: str = ""
    ) -> subprocess.CompletedProcess[str]:
        shell = isinstance(argv, str)
        return subprocess.run(  # noqa: S603
            ["sh", "-c", argv] if shell else argv,
            cwd=cwd, env=self.env, input=stdin, capture_output=True, text=True, timeout=50,
        )  # fmt: skip

    def git(self, cwd: Path, *args: str) -> str:
        done = self.run(["git", *args], cwd)
        assert done.returncode == 0, f"git {args}: {done.stderr}"
        return done.stdout.strip()

    def cli(self, *argv: str) -> subprocess.CompletedProcess[str]:
        return self.run([str(cli_path(self.ws)), *argv], self.elsewhere)

    def seed(self, constitution: str | None = None, *branches: str, live: str = "") -> None:
        """The bare remote carries *branches* (default ``main`` then ``develop``), each at
        one commit holding a README and, when given, ``specs/constitution.md`` and the
        *live* release's ``_RELEASE.json``."""
        src = self.tmp / "seed"
        self.git(self.tmp, "init", "-q", str(src))
        (src / "README.md").write_text("r\n", encoding="utf-8")
        if constitution is not None:
            (src / "specs").mkdir()
            (src / "specs" / "constitution.md").write_text(constitution, encoding="utf-8")
        if live:
            (src / "specs" / "releases" / live).mkdir(parents=True)
            (src / "specs" / "releases" / live / "_RELEASE.json").write_text("{}\n")
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
        path.write_text(text, encoding="utf-8")
        self.git(self.repo, "add", rel)
        self.git(self.repo, "commit", "-qm", f"add {rel}")

    def onboard(self, constitution: str | None = None) -> None:
        (self.repo / "specs").mkdir(exist_ok=True)
        (self.repo / "specs" / "constitution.md").write_text(
            constitution or _constitution(), encoding="utf-8"
        )
        (self.repo / "AGENTS.md").write_text("# law\n", encoding="utf-8")

    def remote_heads(self) -> dict[str, str]:
        out = self.git(self.bare, "for-each-ref", "--format=%(refname:lstrip=2) %(objectname)")
        return dict(line.split() for line in out.splitlines())

    def deny(self) -> None:
        (self.ws / ".dadaia" / "states" / "privacy_denylist.json").write_text(
            f'{{"{_TERM}": "t"}}', encoding="utf-8"
        )


def _single_fix(done: subprocess.CompletedProcess[str]) -> str:
    output = done.stdout + done.stderr
    lines = [line[len("fix: ") :] for line in output.splitlines() if line.startswith("fix: ")]
    assert len(lines) == 1, f"exactly one fix line expected, got {len(lines)}:\n{output}"
    assert "&&" not in lines[0], f"one command per fix line (PowerShell 5.1): {lines[0]}"
    return lines[0]


@dataclass(frozen=True)
class Case:
    """*build* plants the refusal and returns the command that hits it (argv, or a shell
    line run in the repo); *operator* is the documented human step the refusal text asks
    for before its fix (an edit), or the act an ``Operator action:`` fix names; *then* replaces the re-run when the fix renames what the
    refused command named; *done* asserts the published end state."""

    build: Callable[[World], list[str] | str]
    done: Callable[[World], None]
    operator: Callable[[World], None] | None = None
    then: list[str] | str | None = None
    replaces: bool = False


@dataclass(frozen=True)
class Skip:
    """A site this harness cannot drive, with the reason."""

    reason: str


def _hit(world: World, command: list[str] | str) -> subprocess.CompletedProcess[str]:
    if isinstance(command, str):
        return world.run(command, world.repo)
    return world.cli(*command) if command[0] != "git" else world.run(command, world.repo)


def _gate(world: World, push: str) -> subprocess.CompletedProcess[str]:
    """The first refusal of *push*: the ref lines git hands its pre-push hook, captured by a
    stand-in hook, fed to an in-process ``ci push-gate-check`` (80 columns, no TTY) from the
    hook's cwd. The hook's own forwarding stays proven by the real pushes below and by
    ``test_the_gate_is_read_only…``; one line without a TTY by the sentinel."""
    refs, cwd = world.tmp / "pre-push.refs", world.tmp / "pre-push.cwd"
    hooks = git_hooks_dir(world.repo)
    assert hooks is not None
    shipped = (hooks / "pre-push").read_bytes()
    (hooks / "pre-push").write_text(f'#!/bin/sh\npwd > "{cwd}"\ncat > "{refs}"\nexit 1\n')
    try:
        world.run(push, world.repo)
    finally:
        (hooks / "pre-push").write_bytes(shipped)
    env: dict[str, str | None] = {**world.env, **dict.fromkeys(_UNSET), "COLUMNS": "80"}
    with contextlib.chdir(cwd.read_text().strip()):
        ran = CliRunner().invoke(app, ["ci", "push-gate-check"], input=refs.read_text(), env=env)
    return subprocess.CompletedProcess(push, ran.exit_code, ran.output, "")


def _drive(world: World, case: Case) -> None:
    command = case.build(world)
    if isinstance(command, str) and " push " in command:
        done = _gate(world, command)
    else:
        done = _hit(world, command)
    assert done.returncode != 0, f"the case planted no refusal:\n{done.stdout}{done.stderr}"
    seen: list[str] = []
    for step in range(4):
        fix = _single_fix(done)
        assert fix not in seen, f"no progress — the same fix line again:\n{fix}"
        seen.append(fix)
        act = fix.startswith("Operator action: ")
        if case.operator is not None and (act or step == 0):
            case.operator(world)
        assert "<" not in fix.replace("<<", ""), f"a placeholder: {fix}"
        ran = None if act else world.run(fix, world.elsewhere)  # a fix line runs from any cwd
        assert ran is None or ran.returncode == 0, f"the fix does not run:\n{fix}\n{ran}"
        if case.replaces and step == 0:
            case.done(world)
            return
        done = _hit(world, case.then if case.then is not None else command)
        if done.returncode == 0:
            case.done(world)
            return
    pytest.fail("the refusal chain did not clear within four fix lines:\n" + "\n".join(seen))


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
    """Review H-C (P4): the refused ref is not the checked-out one."""
    if published:
        _published(world)
    world.commit("notes.md", "n\n", branch="topic")
    world.git(world.repo, "checkout", "-q", "main")
    return "git push -q origin topic"


def _outside_with_work(world: World) -> str:
    """Review 5 M2: the live work branch exists and has DIVERGED from the refused ref — a
    fast-forward cannot carry it; the switch + merge does."""
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
    """The live work branch by the ONE rule (sa-live-work-branch-named-three-ways)."""
    return work_branch(world.repo / "specs", DEFAULT)


def _work_pushed(world: World, work: str = "feature/1.0.0") -> None:
    assert world.remote_heads().get(work) == world.git(world.repo, "rev-parse", work)


def _denylisted(world: World) -> str:
    _published(world)
    world.deny()
    world.commit("notes.md", f"a {_TERM} b\n", branch="feature/1.0.0")
    world.commit("more.md", "m\n")
    return "git push -q origin feature/1.0.0"


def _drop_term(world: World) -> None:
    (world.repo / "notes.md").write_text("a b\n", encoding="utf-8")


#: The refusal's documented steps after its fix: commit the edited work, push it again.
_COMMIT_PUSH = "git commit -qa --amend --no-edit && git push -q origin feature/1.0.0"


def _clean_publish(world: World) -> None:
    """L3: the operator's work is PUBLISHED (not merely left on disk), without the term."""
    tip = world.remote_heads()["feature/1.0.0"]
    assert _TERM not in world.git(world.repo, "log", "-p", tip, "--not", "origin/develop")
    assert {"notes.md", "more.md"} <= set(
        world.git(world.bare, "ls-tree", "--name-only", tip).split()
    )
    assert not world.git(world.repo, "status", "--porcelain")


def _denylisted_not_checked_out(world: World) -> str:
    """Review 5 H1 (P2): HEAD is `main`; the refused branch must be switched to first."""
    command = _denylisted(world)
    world.git(world.repo, "checkout", "-q", "main")
    return command


#: H1: the operator's edit happens on the refused branch, after the switch.
_CLEAN_COMMIT_PUSH = f"printf 'a b\\n' > notes.md && {_COMMIT_PUSH}"


def _denylisted_advanced_integration(world: World) -> str:
    """Review 5 H2 (P3): origin's integration moved on after this work was cut."""
    _published(world)
    world.deny()
    world.commit("mine.md", "m\n", branch="feature/1.0.0")
    world.git(world.repo, "push", "-q", "-u", "origin", "feature/1.0.0")
    other = world.tmp / "other"
    world.git(world.tmp, "clone", "-q", "-b", "develop", world.bare.as_uri(), str(other))
    (other / "dep.txt").write_text("dependabot\n", encoding="utf-8")
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
    world.commit("notes.md", "n\n")  # real work rides the range: the amend keeps it
    return "git push -q origin feature/1.0.0"


def _rm_junk(world: World) -> None:
    world.git(world.repo, "rm", "-q", "specs/junk.md")


def _no_junk(world: World) -> None:
    tip = world.remote_heads()["feature/1.0.0"]
    assert "specs/junk.md" not in world.git(world.repo, "ls-tree", "-r", "--name-only", tip)


def _law_deleted(world: World) -> str:
    """law-deletion-refusal-reuses-the-denylist-rewrite-fix: the tip deletes a published
    law line citing no ADR — the uncommit-amend remedy loops; the reword clears it."""
    _published(world)
    world.commit("AGENTS.md", "- keep\n- drop\n", branch="feature/1.0.0")
    world.git(world.repo, "push", "-q", "origin", "feature/1.0.0")
    world.commit("AGENTS.md", "- keep\n")
    return "git push -q origin feature/1.0.0"


def _cite_adr(world: World) -> None:
    """Plays the printed act: the refusal named HEAD's commit and its law file."""
    shown = _single_fix(_gate(world, "git push -q origin feature/1.0.0"))
    assert f"reword commit {world.git(world.repo, 'rev-parse', 'HEAD')[:12]} " in shown
    assert shown.endswith("deletion of AGENTS.md"), shown
    world.git(world.repo, "commit", "-q", "--amend", "-m", "drop a law line (ADR 0151)")


def _associated_law_deleted(world: World) -> list[str]:
    """law-deletion-citation-accepts-any-adr-number: an associated repo (no specs/) cites
    ADR 9999; its owner's committed ledger (a malformed line, 0001 accepted) refuses it —
    through lib's real pre-push hook."""
    _associated_on_integration(world)
    world.commit("specs/ADRs/decisions.jsonl", 'not json\n{"id": "0001", "status": "accepted"}\n')
    lib = world.ws / "repos" / "lib"
    world.git(lib, "checkout", "-q", "--", ".")
    world.git(lib, "checkout", "-q", "-b", "feature/1.0.0")
    (lib / "AGENTS.md").write_text("- keep\n- drop\n", encoding="utf-8")
    world.git(lib, "add", "AGENTS.md")
    world.git(lib, "commit", "-qm", "law")
    world.git(lib, "push", "-q", "origin", "feature/1.0.0")
    (lib / "AGENTS.md").write_text("- keep\n", encoding="utf-8")
    world.git(lib, "commit", "-qam", "drop (ADR 9999)")
    return ["git", "-C", str(lib), "push", "-q", "origin", "feature/1.0.0"]


def _cite_accepted_adr(world: World) -> None:
    """Plays the printed act: the refusal named lib's HEAD and its law file."""
    lib = world.ws / "repos" / "lib"
    shown = _single_fix(world.run(["git", "push", "-q", "origin", "feature/1.0.0"], lib))
    assert f"reword commit {world.git(lib, 'rev-parse', 'HEAD')[:12]} " in shown
    assert shown.endswith("deletion of AGENTS.md"), shown
    world.git(lib, "commit", "-q", "--amend", "-m", "drop (ADR 0001)")


def _lib_pushed(world: World) -> None:
    lib = world.ws / "repos" / "lib"
    remote = world.git(world.tmp / "lib.git", "rev-parse", "feature/1.0.0")
    assert remote == world.git(lib, "rev-parse", "HEAD")
    assert "(ADR 0001)" in world.git(lib, "log", "-1", "--format=%s")


def _denylisted_in_a_worktree(world: World) -> str:
    """Review H-B (P10): the pushing repo is a worktree under repos/<slug>/."""
    _published(world)
    world.deny()
    wt = world.repo / ".claude" / "worktrees" / "agent-x"
    world.git(world.repo, "worktree", "add", "-q", "-b", "feature/1.0.0", str(wt), "origin/develop")
    (wt / "notes.md").write_text(f"a {_TERM} b\n", encoding="utf-8")
    world.git(wt, "add", "notes.md")
    world.git(wt, "commit", "-qm", "n")
    return f"git -C {wt} push -q origin feature/1.0.0"


def _drop_worktree_term(world: World) -> None:
    (world.repo / ".claude" / "worktrees" / "agent-x" / "notes.md").write_text("a b\n")


def _worktree_clean(world: World) -> None:
    tip = world.remote_heads()["feature/1.0.0"]
    assert _TERM not in world.git(world.repo, "log", "-p", tip, "--not", "origin/develop")
    assert "notes.md" in world.git(world.repo, "ls-tree", "--name-only", tip).splitlines()


def _denylisted_no_context(world: World) -> str:
    """Review deferred LOW (P6): no context owns the pushing repo — the fix adopts it,
    never a `<context>` placeholder."""
    command = _denylisted(world)
    JsonContextStore(world.ws / ".dadaia" / "states").delete("proj")
    return command


# ── baseline cases ───────────────────────────────────────────────────────────────────


def _no_identity(world: World) -> list[str]:
    world.clone()
    world.onboard()
    (world.tmp / "gitconfig").write_text(
        f"{GIT_QUIET_INCLUDE}[user]\n\tuseConfigOnly = true\n", encoding="utf-8"
    )
    return ["context", "baseline", "proj"]


def _secret_draft(world: World) -> list[str]:
    world.clone()
    world.onboard()
    (world.repo / "AGENTS.md").write_text(f"key {aws_key_shape()}\n", encoding="utf-8")
    return ["context", "baseline", "proj"]


def _drop_secret(world: World) -> None:
    (world.repo / "AGENTS.md").write_text("key\n", encoding="utf-8")


def _remote_back(world: World) -> None:
    (world.tmp / "away.git").rename(world.bare)


def _baseline_denylisted(world: World) -> list[str]:
    world.clone()
    world.onboard()
    world.deny()
    (world.repo / "AGENTS.md").write_text(f"a {_TERM}\n", encoding="utf-8")
    # Committed before the publish, so only the gate sees it: the in-process preflight
    # (AC5.6) refuses an untracked onboarding file first (_require_publishable#0).
    world.git(world.repo, "add", "AGENTS.md")
    world.git(world.repo, "commit", "-qm", "draft")
    return ["context", "baseline", "proj"]


def _drop_draft_term(world: World) -> None:
    (world.repo / "AGENTS.md").write_text("a\n", encoding="utf-8")


#: N3: the refusal's documented step after its reset — amend — then the publish again.
_AMEND_BASELINE = (
    "git commit -qa --amend --no-edit && ../../.dadaia/.venv/bin/dadaia context baseline proj"
)


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
    (other / "x.md").write_text("x\n", encoding="utf-8")
    world.git(other, "add", "x.md")
    world.git(other, "commit", "-qm", "x")
    world.git(other, "push", "-q", "origin", "feature/1.0.0")


def _no_checkout(world: World) -> list[str]:
    """Review M-A (P7a)."""
    _seeded(world)
    return ["context", "baseline", "proj"]


def _draft_principal_absent(world: World) -> list[str]:
    """S11 (SA-H3-3, design review C3/C6): origin publishes `main` under a malformed block;
    the draft names `trunk` — the one origin candidate is the fix's principal."""
    world.seed("---\nspecs_pattern_version: 7\ngitflow: {principal: main\n---\n# c\n", "main")
    world.clone()
    world.onboard(_constitution("trunk", "stage", "rel/"))
    return ["context", "baseline", "proj"]


def _never_onboarded(world: World) -> list[str]:
    """Design review C1 / AC4.5: no constitution on disk — the fix is onboarding's specs step."""
    world.seed(None)
    world.clone()
    return ["context", "baseline", "proj"]


def _unknown_context(world: World) -> list[str]:
    """Review M-A (P7c)."""
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


# ── dead cases ───────────────────────────────────────────────────────────────────────


def _dead_done(world: World) -> None:
    assert not world.repo.exists()


def _on_work(world: World) -> None:
    _published(world)
    world.git(world.repo, "checkout", "-q", "-b", "feature/1.0.0", "origin/develop")
    world.git(world.repo, "push", "-q", "-u", "origin", "feature/1.0.0")


def _untracked(world: World) -> list[str]:
    _on_work(world)
    (world.repo / "notes.md").write_text("n\n", encoding="utf-8")
    return ["context", "dead", "proj"]


def _discard_notes(world: World) -> None:
    (world.repo / "notes.md").unlink()


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
    (world.repo / "notes.txt").write_text("n\n", encoding="utf-8")
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
    """Review M4: an associated repo has no specs/ — its work branch is the main repo's."""
    _released(world)
    world.git(world.repo, "checkout", "-q", "-b", "feature/1.0.0", "origin/develop")
    world.git(world.repo, "push", "-q", "-u", "origin", "feature/1.0.0")
    lib, lib_bare = world.ws / "repos" / "lib", world.tmp / "lib.git"
    world.git(world.tmp, "init", "-q", "--bare", "-b", "main", str(lib_bare))
    world.git(world.tmp, "clone", "-q", lib_bare.as_uri(), str(lib))
    (lib / "README.md").write_text("r\n", encoding="utf-8")  # no specs/ of its own
    world.git(lib, "add", "README.md")
    world.git(lib, "commit", "-qm", "r")
    world.git(lib, "push", "-q", "origin", "HEAD:main", "HEAD:develop")
    world.git(lib, "checkout", "-q", "-b", "develop", "--track", "origin/develop")
    install_git_hooks(lib)
    (lib / "README.md").write_text("edited\n", encoding="utf-8")
    world.git(lib, "commit", "-qam", "edited")
    store = JsonContextStore(world.ws / ".dadaia" / "states")
    ctx = store.get("proj")
    assert ctx is not None
    store.update(replace(ctx, associated_repos=(AssociatedRepo("lib", lib_bare.as_uri()),)))
    return ["context", "dead", "proj"]


def _associated_dead(world: World) -> None:
    """dead-holds-main-repo-before-associated-push: every repo pushed before any is held."""
    assert "feature/1.0.0" in world.git(world.tmp / "lib.git", "branch")
    assert not world.repo.exists() and not (world.ws / "repos" / "lib").exists()


def _dead_denylisted(world: World) -> list[str]:
    _on_work(world)
    world.deny()
    world.commit("README.md", f"a {_TERM}\n")
    return ["context", "dead", "proj"]


def _unpushed_side_branch(world: World) -> list[str]:
    """sa-context-dead-removes-repos-outside-the-reaper#C3: a local branch other than HEAD's
    carries a commit origin lacks; unrecoverable-fix-line-pushes-a-wt-branch-the-pre-push-refuses:
    a non-work branch the gate refuses to push — already archived once, then advanced
    (ADR 0120: one archive tag per tip, never a collision)."""
    _published(world)
    world.git(world.repo, "checkout", "-q", "-b", "wt/0.5.0a", "origin/develop")
    world.commit("notes.md", "n\n")
    archived = world.git(world.repo, "rev-parse", "HEAD")[:7]
    world.git(world.repo, "push", "-q", "origin", f"HEAD:refs/tags/archive/wt/0.5.0a/{archived}")
    world.commit("notes.md", "m\n")
    world.git(world.repo, "checkout", "-q", "--detach", "origin/main")
    return ["context", "dead", "proj"]


def _stashed(world: World) -> list[str]:
    """context-dead-secret-fix-line-stashes-what-dead-then-destroys: a stash entry dies with
    the clone."""
    _on_work(world)
    (world.repo / "README.md").write_text("edited\n", encoding="utf-8")
    world.git(world.repo, "stash", "push", "-q", "-m", "wip")
    return ["context", "dead", "proj"]


def _play_stash_act(world: World) -> None:
    """The operator drops the stash entry, the second act the refusal names (a pop would
    leave a dirty checkout, which dead refuses)."""
    world.git(world.repo, "stash", "drop", "-q")


def _dead_twice(world: World) -> list[str]:
    """Review M-A: dead on a DEAD context."""
    _seeded(world)
    store = JsonContextStore(world.ws / ".dadaia" / "states")
    store.update(
        SpecContextProject(
            "proj", ContextState.DEAD, "proj", world.bare.as_uri(), "2026-01-01T00:00:00+00:00"
        )
    )
    return ["context", "dead", "proj"]


def _dead_clean_detached(world: World) -> list[str]:
    """Review LOW (P8): a clean published detached HEAD has nothing to push."""
    _published(world)
    world.git(world.repo, "checkout", "-q", "--detach", "origin/main")
    return ["context", "dead", "proj"]


def _drop_readme_term(world: World) -> None:
    (world.repo / "README.md").write_text("a\n", encoding="utf-8")


# ── the census ───────────────────────────────────────────────────────────────────────

_CHOKEPOINTS = {
    "branch_policy": _PKG / "features" / "chokepoints" / "branch_policy.py",
    "push_gate": _PKG / "features" / "chokepoints" / "push_gate.py",
}
#: Each module whose verbs raise, and the verbs — every ``raise`` reachable from them
#: (``self.<method>()`` and module-level calls, transitively) is a site.
_VERBS = {
    "ci": (_PKG / "cli" / "commands" / "ci.py", ("push_gate_check",)),
    "service": (_PKG / "features" / "spec_context" / "service.py", ("alive", "baseline", "dead")),
}

SITES: dict[str, tuple[Case | tuple[Case, ...] | Skip, ...]] = {
    "branch_policy._refuse_branch": (
        Case(_birth_published, _develop_at_main, replaces=True),
        (
            Case(_outside, _work_carries_topic, then=_MERGE_TOPIC),
            Case(_outside_with_work, _work_carries_topic, then=_MERGE_TOPIC),
            Case(_outside_detached, _work_carries_topic, then="git push -q origin feature/0.1.0"),
        ),
        Skip("an Operator action on the git host: the PR is no command to run"),
    ),
    "branch_policy.check_branch_policy": (
        Case(_mismatch, _work_pushed, then="git push -q origin feature/1.0.0"),
    ),
    "push_gate._rewrite_fix": (
        (
            Case(_denylisted_not_checked_out, _clean_publish, then=_CLEAN_COMMIT_PUSH),
            Case(_denylisted, _clean_publish, operator=_drop_term, then=_COMMIT_PUSH),
            Case(
                _denylisted_in_a_worktree,
                _worktree_clean,
                operator=_drop_worktree_term,
                then="git -C .claude/worktrees/agent-x commit -qa --amend --no-edit && "
                "git -C .claude/worktrees/agent-x push -q origin feature/1.0.0",
            ),
            Case(_denylisted_no_context, _clean_publish, operator=_drop_term, then=_COMMIT_PUSH),
            Case(
                _denylisted_advanced_integration,
                _nothing_reverted,
                operator=_drop_term,
                then="git commit -qa --amend --no-edit && git push -q origin feature/1.0.1",
            ),
            Case(_non_canon, _no_junk, operator=_rm_junk, then=_COMMIT_PUSH),
        ),
    ),
    "push_gate._read_failure": (Skip("needs a corrupted object store; `git fsck` names it"),),
    "push_gate.push_gate_decision": (
        Case(_malformed, lambda w: _work_pushed(w, _work(w)), replaces=True),
        (
            Case(_law_deleted, _work_pushed, operator=_cite_adr),
            Case(_associated_law_deleted, _lib_pushed, operator=_cite_accepted_adr),
        ),
    ),
    "ci._repo_root": (Skip("the pre-push hook always runs inside the repo it pushes"),),
    "ci.push_gate_check": (Skip("the gate's refusal: its fix is a branch_policy/push_gate site"),),
    "service.SpecContextService.show": (Case(_unknown_context, _cloned, operator=_create),),
    "service.SpecContextService.alive": (
        Case(_no_url_no_checkout, _cloned, operator=_clone),
        Case(_alive_remote_gone, _cloned, operator=_remote_back),
    ),
    "service.SpecContextService.baseline": (
        Case(_no_checkout, _cloned),
        Case(_no_identity, _baseline_done, operator=_identity),
        Case(_never_onboarded, _baseline_done),
        Case(_baseline_denylisted, _baseline_done, operator=_drop_draft_term, then=_AMEND_BASELINE),
    ),
    "service.SpecContextService._refuse_principal_absent": (
        Case(_draft_principal_absent, lambda w: _baseline_done(w, "rel/0.1.0", ("main", "stage"))),
    ),
    "service.SpecContextService._require_publishable": (
        Case(_secret_draft, _baseline_done, operator=_drop_secret),
    ),
    "service.SpecContextService._dead_preflight": (
        Case(_untracked, _dead_done, operator=_discard_notes),
        Case(_no_origin, _dead_done, operator=_origin),
        (
            Case(_unpushed_side_branch, _dead_done),
            Case(_commits_no_remote, _dead_done, operator=_origin),
            Case(_stashed, _dead_done, operator=_play_stash_act),
        ),
        (
            Case(_dirty_on_integration, _dead_via_work),
            Case(_associated_on_integration, _associated_dead),
        ),
    ),
    "service.SpecContextService.dead": (
        Case(_dead_twice, _dead_done),
        Case(
            _dead_denylisted,
            _dead_done,
            operator=_drop_readme_term,
            then="git commit -qa --amend --no-edit && "
            "../../.dadaia/.venv/bin/dadaia context dead proj",
        ),
        Skip("a refused hold (`repos/` outside the workspace): test_context_dead_holds.py"),
    ),
}


def _scopes(tree: ast.Module) -> dict[str, ast.FunctionDef]:
    scopes: dict[str, ast.FunctionDef] = {}
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            scopes |= {
                f"{node.name}.{f.name}": f for f in node.body if isinstance(f, ast.FunctionDef)
            }
        elif isinstance(node, ast.FunctionDef):
            scopes[node.name] = node
    return scopes


def _reachable(scopes: dict[str, ast.FunctionDef], roots: tuple[str, ...]) -> list[str]:
    """Every scope the *roots* reach through ``self.<m>()`` or a module-level call."""
    by_name = {qual.rsplit(".", 1)[-1]: qual for qual in scopes}
    todo, seen = [by_name[r] for r in roots], set()
    while todo:
        qual = todo.pop()
        if qual in seen:
            continue
        seen.add(qual)
        for node in ast.walk(scopes[qual]):
            func = node.func if isinstance(node, ast.Call) else None
            callee = (
                func.attr
                if isinstance(func, ast.Attribute)
                and isinstance(func.value, ast.Name)
                and func.value.id == "self"
                else func.id
                if isinstance(func, ast.Name)
                else None
            )
            if callee in by_name:
                todo.append(by_name[callee])
    return sorted(seen)


def _fix_sites() -> list[str]:
    """The chokepoints' refusals (a string constant carrying ``fix:`` or a call to
    branch_policy's ``_blocked``, whose own body is the renderer) and every ``raise``
    the verbs reach — one entry per refusal, keyed by its enclosing function."""
    sites: list[str] = []
    for stem, path in _CHOKEPOINTS.items():
        for name, fn in _scopes(ast.parse(path.read_text(encoding="utf-8"))).items():
            hits = [
                n
                for n in ast.walk(fn)
                if name != "_blocked"
                and (
                    (isinstance(n, ast.Constant) and isinstance(n.value, str) and "fix:" in n.value)
                    or (isinstance(n, ast.Call) and getattr(n.func, "id", "") == "_blocked")
                )
            ]
            sites += [f"{stem}.{name}"] * len(hits)
    for stem, (path, roots) in _VERBS.items():
        scopes = _scopes(ast.parse(path.read_text(encoding="utf-8")))
        for name in _reachable(scopes, roots):
            raises = [
                n
                for n in ast.walk(scopes[name])
                if (isinstance(n, ast.Raise) and n.exc)
                or (isinstance(n, ast.Call) and getattr(n.func, "id", "") == "fail")
            ]
            sites += [f"{stem}.{name}"] * len(raises)
    return sites


def test_every_fix_site_has_a_case() -> None:
    assert Counter(_fix_sites()) == {site: len(refusals) for site, refusals in SITES.items()}


_CASES = [
    pytest.param(case, id=case.build.__name__.strip("_"))
    for refusals in SITES.values()
    for entry in refusals
    if not isinstance(entry, Skip)
    for case in (entry if isinstance(entry, tuple) else (entry,))
]


def test_dead_leaves_a_clean_published_detached_head(world: World) -> None:
    done = _hit(world, _dead_clean_detached(world))
    assert done.returncode == 0, done.stdout + done.stderr
    _dead_done(world)


def test_dead_pushes_an_associated_repo_while_its_main_repo_is_absent(world: World) -> None:
    """pre-push-gate-crashes-when-owner-main-repo-absent: dead's preflight reads the gitflow
    through the same reader — an absent main repo is the default, never a traceback."""
    _associated_on_integration(world)
    world.git(world.ws / "repos" / "lib", "checkout", "-q", "-b", "feature/1.0.0")
    shutil.rmtree(world.repo)
    done = world.cli("context", "dead", "proj")
    assert done.returncode == 0, done.stdout + done.stderr
    _associated_dead(world)


@pytest.mark.parametrize("case", _CASES)
def test_the_fix_line_clears_the_refusal(case: Case, world: World) -> None:
    _drive(world, case)


def test_a_repaired_custom_gitflow_publishes_end_to_end(world: World) -> None:
    """C1 (r3-typo): on an empty origin the draft constitution names non-default branches —
    baseline publishes under those names, the shipped gate admitting every push."""
    world.clone()
    world.onboard(_constitution("trunk", "stage", "rel/"))
    done = world.cli("context", "baseline", "proj")
    assert done.returncode == 0, done.stdout + done.stderr
    _baseline_done(world, "rel/0.1.0", ("trunk", "stage"))


def test_a_clone_on_the_integration_branch_is_never_auto_committed(world: World) -> None:
    """H (dead on develop): the refusal comes before any commit — the local integration
    branch is exactly the remote's."""
    _dirty_on_integration(world)
    before = world.git(world.repo, "rev-parse", "develop")
    assert world.cli("context", "dead", "proj").returncode != 0
    assert world.git(world.repo, "rev-parse", "develop") == before


def test_every_fix_line_prints_on_one_line_without_a_tty(tmp_path: Path) -> None:
    """H (dead wrapping): a fix naming a path longer than 80 columns stays one line. The
    no-TTY sentinel of every family: gate, baseline, alive and dead refusals all print
    through the one ``cli/_fail.fail`` a real child process exercises here."""
    world = World(tmp_path / ("d" * 90))
    _unborn_dirty(world)
    fix = _single_fix(world.cli("context", "dead", "proj"))
    assert fix.endswith("notes.txt into a worktree, or discard it"), fix
    assert re.search(re.escape(str(world.ws)), fix)


def test_the_gate_is_read_only_and_its_rewrite_fix_uncommits_only_unpublished_work(
    world: World,
) -> None:
    """R13 rule 3 / review 5 H2: the denylist refusal's fix uncommits the refused ref's own
    unpublished range, down to its oldest unpublished commit (N3) — never a squash of
    published history, never a publish verb that rewrites."""
    command = _denylisted(world)
    oldest = world.git(world.repo, "rev-parse", "HEAD~1")
    fix = _single_fix(_hit(world, command))
    assert fix == shell_line("git", "-C", str(world.repo), "reset", "--soft", oldest)
    assert "--republish" not in world.cli("context", "baseline", "--help").stdout


def test_a_denylisted_tag_from_a_detached_head_on_an_empty_origin_prints_no_command(
    world: World,
) -> None:
    """Review 5 C1 (P1): the range reaches a root commit and the ref is a tag — the refusal
    names the operator action, prints no command, and the repo stays a repo."""
    world.clone()
    world.deny()
    world.commit("README.md", "r\n")
    world.commit("notes.md", f"a {_TERM}\n")
    world.git(world.repo, "tag", "v0.0.1")
    world.git(world.repo, "checkout", "-q", "--detach", "v0.0.1")
    done = _hit(world, "git push -q origin v0.0.1")
    output = done.stdout + done.stderr
    assert done.returncode != 0 and "\nfix: Operator action: " in output
    assert world.git(world.repo, "rev-parse", "HEAD") == world.git(
        world.repo, "rev-parse", "v0.0.1"
    )
    assert world.remote_heads() == {}


def test_dead_on_a_non_fast_forward_carries_gits_own_text_and_removes_nothing(
    world: World,
) -> None:
    """Review 5 H6: no pull fix row leads dead into a conflicted merge it would commit and
    push — git's own text stands alone; the checkout stays."""
    _on_work(world)
    _advance_origin_work(world)
    (world.repo / "README.md").write_text("edited\n", encoding="utf-8")
    world.git(world.repo, "commit", "-qam", "edited")
    done = world.cli("context", "dead", "proj")
    output = done.stdout + done.stderr
    assert done.returncode != 0 and "rejected" in output
    assert "\nfix: " not in output
    assert world.repo.is_dir() and not (world.repo / ".git" / "MERGE_HEAD").exists()


def test_a_refused_baseline_push_names_the_anchor_and_the_publish_as_the_next_step(
    world: World,
) -> None:
    """Design review C7 / C2: the gate refuses baseline's push — the refusal keeps the gate's
    one fix (reset to the oldest unpublished commit) and names the anchor and the publish
    as the step after the amend (a hand push would drop origin's merge parent)."""
    done = _hit(world, _baseline_denylisted(world))
    output = done.stdout + done.stderr
    assert done.returncode != 0 and _single_fix(done).startswith("git -C")
    assert f"onboarding commit {world.git(world.repo, 'rev-parse', 'HEAD')}" in output
    assert fix_line(world.ws, "context", "baseline", "proj") in output.replace("\n", "")


def test_dead_after_the_operator_pulls_into_a_conflict_publishes_no_markers(
    world: World,
) -> None:
    """Review 6 H6 (R7): the operator follows git's own `git pull` hint into a conflict;
    the unmerged file is a dirty checkout dead refuses — nothing published, the checkout kept."""
    _on_work(world)
    _advance_origin_work(world)
    other = world.tmp / "other"
    (other / "README.md").write_text("theirs\n", encoding="utf-8")
    world.git(other, "commit", "-qam", "t")
    world.git(other, "push", "-q", "origin", "feature/1.0.0")
    (world.repo / "README.md").write_text("mine\n", encoding="utf-8")
    world.git(world.repo, "commit", "-qam", "mine")
    world.run("git pull -q --no-rebase --no-edit origin feature/1.0.0", world.repo)
    published = world.remote_heads()["feature/1.0.0"]
    done = world.cli("context", "dead", "proj")
    output = done.stdout + done.stderr
    assert done.returncode != 0 and "README.md into a worktree, or discard it" in output, output
    assert world.repo.is_dir() and world.remote_heads()["feature/1.0.0"] == published
