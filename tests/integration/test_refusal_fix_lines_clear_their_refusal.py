"""Intent: CONTRACT — 0.5.0 c3 re-review (C1, H1-H4, M1): every refusal of the pre-push
gate (`ci push-gate-check`), `context baseline` and `context dead` prints ONE fix line
that, executed verbatim, clears the refusal.

The doctor has this harness (``test_doctor_fix_lines_clear_their_finding.py``); these
three verbs did not, and their fix lines failed review round after round, one site at a
time. Each case below builds the triggering state over ``file://`` remotes, runs the
real command as a child process with no TTY (what every agent harness sees — Rich wraps
at 80 columns there), takes the single ``fix:`` line, fills its documented
``<placeholders>``, runs it with ``sh -c`` and runs the command again. Progress rule:
the command then succeeds, or refuses with a DIFFERENT fix line (the next step), which is
followed the same way — at most four steps, never a repeated line. A fix that is itself
the publish (``git push …``, ``context baseline``) replaces the refused command: its
success is the clearance.

The census pins that every ``fix:`` producer in the four modules is accounted for — a
new refusal without a case (or a written reason it cannot run here) fails
:func:`test_every_fix_site_has_a_case`.

size: MEDIUM — real git and real CLI child processes, no network.
"""

from __future__ import annotations

import ast
import os
import re
import subprocess
import sys
import sysconfig
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import pytest

from dadaia_workspace.core.cli_line import cli_path, fix_line
from dadaia_workspace.core.models.spec_context import ContextState, SpecContextProject
from dadaia_workspace.core.specs_version import CANONICAL_SPECS_VERSION
from dadaia_workspace.features.spec_context.service import install_git_hooks
from dadaia_workspace.infrastructure.json_context_store import JsonContextStore
from tests.helpers.privacy_fixtures import aws_key_shape

pytestmark = [
    pytest.mark.integration,
    pytest.mark.slow(reason="real git remotes and CLI child processes per case"),
    pytest.mark.skipif(sys.platform == "win32", reason="the shipped pre-push hook is bash"),
]

_PKG = Path(__file__).resolve().parents[2] / "dadaia_workspace"
_TERM = "zorblaxquux"
_FILLS = {"<M.m.p>": "1.0.0", "<user.name>": "T", "<user.email>": "t@example.invalid"}


def _constitution(
    principal: str = "main", integration: str = "develop", work: str = "feature/"
) -> str:
    return (
        f"---\nspecs_pattern_version: {CANONICAL_SPECS_VERSION}\n"
        f"gitflow: {{principal: {principal}, integration: {integration}, work: {work}}}\n---\n# c\n"
    )


class World:
    """One workspace (registry + the CLI at the path ``fix_line`` spells), one context
    ``proj`` whose main repo ``repos/proj`` is a clone of the bare ``proj.git``."""

    def __init__(self, tmp: Path) -> None:
        self.tmp = tmp
        self.ws = tmp / "ws"
        self.repo = self.ws / "repos" / "proj"
        self.bare = tmp / "proj.git"
        self.elsewhere = tmp / "elsewhere"
        self.elsewhere.mkdir()
        (self.ws / "repos").mkdir(parents=True)
        (self.ws / ".dadaia" / "states").mkdir(parents=True)
        self.env = {k: v for k, v in os.environ.items() if k not in ("COLUMNS", "LINES")}
        for key in (
            "DADAIA_CONTEXT",
            "DADAIA_SESSION_ID",
            "DADAIA_BIN",
            "WORKSPACE_ROOT",
            "GIT_AUTHOR_NAME",
            "GIT_AUTHOR_EMAIL",
            "GIT_COMMITTER_NAME",
            "GIT_COMMITTER_EMAIL",
            "DADAIA_PRIVACY_DENYLIST",
        ):
            self.env.pop(key, None)
        self.env.update(
            GIT_CONFIG_GLOBAL=str(tmp / "gitconfig"),
            GIT_CONFIG_NOSYSTEM="1",
            TERM="dumb",
        )
        (tmp / "gitconfig").write_text(
            "[user]\n\tname = T\n\temail = t@example.invalid\n\tuseConfigOnly = true\n"
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
        self.fills = {**_FILLS, "<clone-url>": self.bare.as_uri(), "<keep-dir>": str(tmp / "kept")}

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

    def seed(self, constitution: str | None = None, *branches: str) -> None:
        """The bare remote carries *branches* (default ``main`` then ``develop``), each at
        one commit holding a README and, when given, ``specs/constitution.md``."""
        src = self.tmp / "seed"
        self.git(self.tmp, "init", "-q", str(src))
        (src / "README.md").write_text("r\n", encoding="utf-8")
        if constitution is not None:
            (src / "specs").mkdir()
            (src / "specs" / "constitution.md").write_text(constitution, encoding="utf-8")
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
            f'["{_TERM}"]', encoding="utf-8"
        )


def _single_fix(done: subprocess.CompletedProcess[str]) -> str:
    output = done.stdout + done.stderr
    lines = [line[len("fix: ") :] for line in output.splitlines() if line.startswith("fix: ")]
    assert len(lines) == 1, f"exactly one fix line expected, got {len(lines)}:\n{output}"
    return lines[0]


@dataclass(frozen=True)
class Case:
    """*build* plants the refusal and returns the command that hits it (argv, or a shell
    line run in the repo); *operator* is the documented human step the refusal text asks
    for before its fix (an edit); *then* replaces the re-run when the fix renames what the
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


def _drive(world: World, case: Case) -> None:
    command = case.build(world)
    done = _hit(world, command)
    assert done.returncode != 0, f"the case planted no refusal:\n{done.stdout}{done.stderr}"
    seen: list[str] = []
    for step in range(4):
        fix = _single_fix(done)
        assert fix not in seen, f"no progress — the same fix line again:\n{fix}"
        seen.append(fix)
        if step == 0 and case.operator is not None:
            case.operator(world)
        line = fix
        for placeholder, value in world.fills.items():
            line = line.replace(placeholder, value)
        assert "<" not in line.replace("<<", ""), f"an undocumented placeholder: {line}"
        cwd = world.repo if world.repo.is_dir() else world.elsewhere
        ran = world.run(line, cwd)
        assert ran.returncode == 0, f"the fix does not run:\n{line}\n{ran.stdout}{ran.stderr}"
        if case.replaces and step == 0:
            case.done(world)
            return
        done = _hit(world, case.then if case.then is not None else command)
        if done.returncode == 0:
            case.done(world)
            return
    pytest.fail("the refusal chain did not clear within four fix lines:\n" + "\n".join(seen))


# ── push-gate cases ──────────────────────────────────────────────────────────────────


def _published(world: World) -> None:
    world.seed(_constitution())
    world.clone()


def _outside(world: World) -> str:
    _published(world)
    world.commit("notes.md", "n\n", branch="topic")
    return "git push -q origin HEAD"


def _work_carries_topic(world: World) -> None:
    heads = world.remote_heads()
    assert heads.get("feature/1.0.0") == world.git(world.repo, "rev-parse", "HEAD")


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


def _birth_unpublished(world: World) -> str:
    world.clone()
    world.commit("README.md", "r\n")
    world.onboard()
    return "git push -q origin main"


def _baseline_done(
    world: World, work: str = "feature/0.1.0", gitflow: tuple[str, ...] = ("main", "develop")
) -> None:
    heads = world.remote_heads()
    assert {*gitflow, work} <= set(heads), heads
    shown = world.git(world.repo, "show", "--name-only", "--format=", heads[work])
    assert "specs/constitution.md" in shown.splitlines()


def _malformed(world: World) -> str:
    _published(world)
    world.commit("notes.md", "n\n", branch="feature/1.0.0")
    return f"printf 'not a ref line\\n' | {fix_line(world.ws, 'ci', 'push-gate-check')}"


def _work_pushed(world: World) -> None:
    assert world.remote_heads().get("feature/1.0.0") == world.git(
        world.repo, "rev-parse", "feature/1.0.0"
    )


def _denylisted(world: World) -> str:
    _published(world)
    world.deny()
    world.commit("notes.md", f"a {_TERM} b\n", branch="feature/1.0.0")
    world.commit("more.md", "m\n")
    return "git push -q origin feature/1.0.0"


def _drop_term(world: World) -> None:
    (world.repo / "notes.md").write_text("a b\n", encoding="utf-8")


def _clean_publish(world: World) -> None:
    tip = world.remote_heads()["feature/1.0.0"]
    assert _TERM not in world.git(world.repo, "log", "-p", tip, "--not", "origin/develop")
    assert (world.repo / "more.md").is_file()


def _non_canon(world: World) -> str:
    _published(world)
    world.commit("specs/junk.md", "j\n", branch="feature/1.0.0")
    return "git push -q origin feature/1.0.0"


def _rm_junk(world: World) -> None:
    world.git(world.repo, "rm", "-q", "specs/junk.md")


def _no_junk(world: World) -> None:
    tip = world.remote_heads()["feature/1.0.0"]
    assert "specs/junk.md" not in world.git(world.repo, "ls-tree", "-r", "--name-only", tip)


# ── baseline cases ───────────────────────────────────────────────────────────────────


def _no_identity(world: World) -> list[str]:
    world.clone()
    world.onboard()
    (world.tmp / "gitconfig").write_text("[user]\n\tuseConfigOnly = true\n", encoding="utf-8")
    return ["context", "baseline", "proj"]


def _foreign_change(world: World) -> list[str]:
    world.seed(None, "main")
    world.clone()
    world.onboard()
    (world.repo / "README.md").write_text("edited\n", encoding="utf-8")
    return ["context", "baseline", "proj"]


def _secret_draft(world: World) -> list[str]:
    world.clone()
    world.onboard()
    (world.repo / "specs" / "notes.md").write_text(f"key {aws_key_shape()}\n", encoding="utf-8")
    return ["context", "baseline", "proj"]


def _remote_gone(world: World) -> list[str]:
    world.clone()
    world.onboard()
    world.bare.rename(world.tmp / "away.git")
    return ["context", "baseline", "proj"]


def _remote_back(world: World) -> None:
    (world.tmp / "away.git").rename(world.bare)


def _baseline_denylisted(world: World) -> list[str]:
    world.clone()
    world.onboard()
    world.deny()
    (world.repo / "specs" / "notes.md").write_text(f"a {_TERM}\n", encoding="utf-8")
    return ["context", "baseline", "proj"]


def _drop_draft_term(world: World) -> None:
    (world.repo / "specs" / "notes.md").write_text("a\n", encoding="utf-8")


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


def _secret_untracked(world: World) -> list[str]:
    _on_work(world)
    (world.repo / "notes.md").write_text(f"key {aws_key_shape()}\n", encoding="utf-8")
    return ["context", "dead", "proj", "--commit"]


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
    _published(world)
    world.git(world.repo, "checkout", "-q", "develop")
    (world.repo / "README.md").write_text("edited\n", encoding="utf-8")
    return ["context", "dead", "proj"]


def _dead_via_work(world: World) -> None:
    heads = world.remote_heads()
    assert heads["develop"] == world.git(world.bare, "rev-parse", "main")
    assert "feature/1.0.0" in heads
    assert not world.repo.exists()


def _dead_remote_gone(world: World) -> list[str]:
    _on_work(world)
    (world.repo / "README.md").write_text("edited\n", encoding="utf-8")
    world.bare.rename(world.tmp / "away.git")
    return ["context", "dead", "proj"]


def _dead_denylisted(world: World) -> list[str]:
    _on_work(world)
    world.deny()
    (world.repo / "README.md").write_text(f"a {_TERM}\n", encoding="utf-8")
    return ["context", "dead", "proj"]


def _drop_readme_term(world: World) -> None:
    (world.repo / "README.md").write_text("a\n", encoding="utf-8")


# ── the census ───────────────────────────────────────────────────────────────────────

_MODULES = {
    "branch_policy": _PKG / "features" / "chokepoints" / "branch_policy.py",
    "push_gate": _PKG / "features" / "chokepoints" / "push_gate.py",
    "ci": _PKG / "cli" / "commands" / "ci.py",
    "service": _PKG / "features" / "spec_context" / "service.py",
}

_OUT_OF_SCOPE = Skip("`context alive`/`repo add` — outside the three verbs this harness owns")

SITES: dict[str, tuple[Case, ...] | Skip] = {
    "branch_policy._refuse_branch#0": (
        Case(_birth_published, _develop_at_main, replaces=True),
        Case(_birth_unpublished, _baseline_done, replaces=True),
    ),
    "branch_policy._refuse_branch#1": (Case(_outside, _work_carries_topic),),
    "branch_policy._refuse_branch#2": Skip("`gh pr create` needs GitHub; the PR path is the fix"),
    "branch_policy.check_branch_policy#0": (
        Case(_mismatch, _work_pushed, then="git push -q origin feature/1.0.0"),
    ),
    "push_gate._compose_denylist_refusal#0": (
        Case(_denylisted, _clean_publish, operator=_drop_term),
    ),
    "push_gate._run_denylist_scan#0": Skip("needs a corrupted object store; `git fsck` names it"),
    "push_gate._compose_specs_canon_refusal#0": (Case(_non_canon, _no_junk, operator=_rm_junk),),
    "push_gate.push_gate_decision#0": (Case(_malformed, _work_pushed, replaces=True),),
    "service.SpecContextService.alive#0": _OUT_OF_SCOPE,
    "service.SpecContextService.baseline#0": (Case(_no_identity, _baseline_done),),
    "service.SpecContextService._require_publishable#0": (
        Case(_foreign_change, _baseline_done),
        Case(_secret_draft, _baseline_done),
    ),
    "service._sync_failure#0": (
        Case(_remote_gone, _baseline_done, operator=_remote_back),
        Case(_baseline_denylisted, _baseline_done, operator=_drop_draft_term),
        Case(_dead_remote_gone, _dead_done, operator=_remote_back),
        Case(_dead_denylisted, _dead_done, operator=_drop_readme_term),
    ),
    "service.SpecContextService._enforce_dead_review_gate#0": Skip(
        "fires only when `git ls-files` itself fails on a git root"
    ),
    "service.SpecContextService._enforce_dead_review_gate#1": (
        Case(_untracked, _dead_done, replaces=True),
    ),
    "service.SpecContextService._enforce_dead_review_gate#2": (
        Case(_secret_untracked, _dead_done),
    ),
    "service.SpecContextService.dead#0": (Case(_no_origin, _dead_done),),
    "service.SpecContextService.dead#1": (Case(_unborn_dirty, _dead_done),),
    "service.SpecContextService.dead#2": (Case(_commits_no_remote, _dead_done),),
    "service.SpecContextService.dead#3": (Case(_dirty_on_integration, _dead_via_work),),
}


def _fix_sites() -> list[str]:
    """Every ``fix:`` producer, by enclosing function and order: a string constant
    carrying ``fix:`` or a call to branch_policy's ``_blocked`` (whose own body is the
    shared renderer, not a site)."""
    sites: list[str] = []
    for stem, path in _MODULES.items():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        scopes: list[tuple[str, ast.AST]] = []
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                scopes += [
                    (f"{node.name}.{f.name}", f)
                    for f in node.body
                    if isinstance(f, ast.FunctionDef)
                ]
            elif isinstance(node, ast.FunctionDef) and node.name != "_blocked":
                scopes.append((node.name, node))
        for name, fn in scopes:
            hits = sorted(
                n.lineno
                for n in ast.walk(fn)
                if (isinstance(n, ast.Constant) and isinstance(n.value, str) and "fix:" in n.value)
                or (
                    isinstance(n, ast.Call)
                    and isinstance(n.func, ast.Name)
                    and n.func.id == "_blocked"
                )
            )
            sites += [f"{stem}.{name}#{i}" for i in range(len(hits))]
    return sites


def test_every_fix_site_has_a_case() -> None:
    assert sorted(_fix_sites()) == sorted(SITES)


_CASES = [
    pytest.param(case, id=f"{site}-{n}")
    for site, entry in SITES.items()
    if not isinstance(entry, Skip)
    for n, case in enumerate(entry)
]


@pytest.mark.parametrize("case", _CASES)
def test_the_fix_line_clears_the_refusal(case: Case, tmp_path: Path) -> None:
    _drive(World(tmp_path), case)


def test_a_repaired_custom_gitflow_publishes_end_to_end(tmp_path: Path) -> None:
    """C1 (r3-typo): the committed constitution is malformed, the working tree carries
    the ADR 0047 repair naming non-default branches — baseline publishes under the
    repaired names, the shipped gate admitting every push."""
    world = World(tmp_path)
    world.seed("---\nspecs_pattern_version: 7\ngitflow: {principal: main\n---\n# c\n", "main")
    world.clone()
    world.onboard(_constitution("trunk", "stage", "rel/"))
    done = world.cli("context", "baseline", "proj")
    assert done.returncode == 0, done.stdout + done.stderr
    _baseline_done(world, "rel/0.1.0", ("trunk", "stage"))


def test_a_clone_on_the_integration_branch_is_never_auto_committed(tmp_path: Path) -> None:
    """H (dead on develop): the refusal comes before any commit — the local integration
    branch is exactly the remote's."""
    world = World(tmp_path)
    _dirty_on_integration(world)
    before = world.git(world.repo, "rev-parse", "develop")
    assert world.cli("context", "dead", "proj").returncode != 0
    assert world.git(world.repo, "rev-parse", "develop") == before


def test_every_fix_line_prints_on_one_line_without_a_tty(tmp_path: Path) -> None:
    """H (dead wrapping): a fix naming a path longer than 80 columns stays one line."""
    world = World(tmp_path / ("d" * 90))
    _unborn_dirty(world)
    fix = _single_fix(world.cli("context", "dead", "proj"))
    assert fix.endswith("'<keep-dir>'") or fix.endswith("<keep-dir>"), fix
    assert re.search(re.escape(str(world.repo)), fix)
