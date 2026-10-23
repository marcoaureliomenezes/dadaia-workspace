"""Every refusal of the pre-push gate (`ci push-gate-check`), `context baseline` and
`context dead` prints ONE fix line that, executed verbatim, clears the refusal.

Each case (in `tests/fixtures/fix_world.py`) builds the triggering state over ``file://`` remotes and hits the refusal:
a push-gate case feeds the ref lines git hands its hook to an in-process
``ci push-gate-check`` (80 columns, no TTY); a baseline/alive/dead case runs the real
command as a child process. It takes the single ``fix:`` line and runs it with ``sh -c`` —
an ``Agent action:`` or ``Operator action:`` line is played by the case's *before* step instead — and runs the real
command (the real push through the shipped hook) again. One line without a TTY — every
family prints through ``cli/_fail.fail`` — is proven on a real child by
:func:`test_every_fix_line_prints_on_one_line_without_a_tty`. Progress rule:
the command then succeeds, or refuses with a DIFFERENT fix line (the next step), which is
followed the same way — at most four steps, never a repeated line. A fix that is itself
the publish (``git push …``, ``context baseline``) replaces the refused command: its
success is the clearance.

The census (an AST sweep of the package and the skill scripts) lists every function that spells a
``fix:`` line: a new site with neither a case, a ``Skip`` reason nor an entry of ``_EXEMPT`` fails
:func:`test_every_fix_site_has_a_case`.

size: MEDIUM — real git and real CLI child processes, no network.
"""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

import pytest

from dadaia_workspace.core.cli_line import fix_line
from tests.fixtures.fix_census import fix_sites
from tests.fixtures.fix_world import (
    _REFUSALS,
    _TERM,
    Case,
    Skip,
    Templates,
    World,
    WtCase,
    _advance_origin_work,
    _associated_dead,
    _associated_on_integration,
    _baseline_denylisted,
    _baseline_done,
    _constitution,
    _dead_clean_detached,
    _dead_done,
    _denylisted,
    _dirty_on_integration,
    _hit,
    _on_work,
    _push_gate,
    _rmtree,
    _single_fix,
    _unborn_dirty,
)
from tests.helpers import worktree_ws as wt
from tests.helpers.oslib import write_text

pytestmark = [
    pytest.mark.medium,  # the processes start in the shared world, which the size rule cannot see
    pytest.mark.slow(reason="real git remotes and CLI child processes per case"),
]


@pytest.fixture(scope="module")
def templates(tmp_path_factory: pytest.TempPathFactory) -> Templates:
    return Templates(tmp_path_factory.mktemp("templates"))


@pytest.fixture
def world(tmp_path: Path, templates: Templates) -> World:
    return World(tmp_path, templates)


def _drive(world: World, case: Case) -> None:
    command = case.build(world)
    if isinstance(command, str) and " push " in command:
        done = _push_gate(world, command)
    else:
        done = _hit(world, command)
    assert done.returncode != 0, f"the case planted no refusal:\n{done.stdout}{done.stderr}"
    seen: list[str] = []
    for step in range(4):
        fix = _single_fix(done)
        assert fix not in seen, f"no progress — the same fix line again:\n{fix}"
        seen.append(fix)
        act = fix.startswith(("Agent action: ", "Operator action: "))
        if act or step == 0:
            case.play(world, fix)
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


_SERVICE = "features/spec_context/service."
#: A path prefix (a module or folder) or one ``<path>.<function>`` of the sweep, with why this
#: harness cannot drive it. The driven modules are exempt function by function.
_EXEMPT = {
    "cli/": "a verb whose refusal the CLI's own command tests run",
    "core/": "a kernel reader whose fix the verbs above it print; their cases cover the chain",
    "hooks/": "a hook entry whose fix its own tests run",
    "infrastructure/": "an adapter whose fix the verbs above it print; their cases cover the chain",
    "features/export/": "the export verb: its own tests run the fix",
    "features/migrate/": "the migrate verb: its own tests run the fix",
    "features/reconcile/": "the reconcile verb: its own tests run the fix",
    "features/specs/": "a doctor finding, not a refusal: the doctor tests run its fix",
    "features/workspace/": "an onboarding step: its property test runs every step's fix",
    "features/spec_context/doctor": "a doctor finding: the doctor tests run its fix",
    "features/spec_context/gate_policy": "the tool gate's block: the hook tests run its fix",
    "features/spec_context/sweep": "the sweep's own tests run the fix",
    "public/skills/": "a skill script: its own tests run the printed fix",
    "features/chokepoints/push_gate.read_failure_fix": "needs a corrupted object store",
    **dict.fromkeys(
        (
            f"{_SERVICE}SpecContextService.{name}"
            for name in ("_refuse_slug", "_validate", "add_repo", "delete", "remove_repo")
        ),
        "a registry edit, no publish-chain step: the service tests run it",
    ),
    f"{_SERVICE}_require_allowlisted": "a registry edit: the service tests run it",
    f"{_SERVICE}install_git_hooks": "the hook installer: its own tests run it",
}


def _covered(site: str) -> bool:
    return site.rsplit("/", 1)[-1] in _REFUSALS or any(site.startswith(p) for p in _EXEMPT)


def test_every_fix_site_has_a_case() -> None:
    sites = fix_sites()
    assert [site for site in sites if not _covered(site)] == []
    found = Counter(site.rsplit("/", 1)[-1] for site in sites)
    assert {k: found[k] for k in _REFUSALS} == {k: len(v) for k, v in _REFUSALS.items()}
    assert [p for p in _EXEMPT if not any(s.startswith(p) for s in sites)] == []


_CASES = [
    pytest.param(case, id=case.build.__name__.strip("_"))
    for refusals in _REFUSALS.values()
    for entry in refusals
    if not isinstance(entry, (Skip, WtCase))
    for case in (entry if isinstance(entry, tuple) else (entry,))
]


_WT_CASES = [
    pytest.param(case, id=key.strip("_") + f"-{n}")
    for key, refusals in _REFUSALS.items()
    for n, case in enumerate(refusals)
    if isinstance(case, WtCase)
]


@pytest.mark.parametrize("case", _WT_CASES)
def test_the_worktree_fix_line_clears_the_refusal(case: WtCase, tmp_path: Path) -> None:
    root = tmp_path / "ws"
    root.mkdir()
    wt.make_workspace(root)
    argv = case.build(root)
    done = wt.run(root, *argv)
    assert done.returncode != 0, f"the case planted no refusal:\n{done.stdout}{done.stderr}"
    seen: list[str] = []
    for _ in range(4):
        (fix,) = wt.fixes(done)
        assert fix not in seen, f"no progress — the same fix line again:\n{fix}"
        seen.append(fix)
        if fix.startswith(("fix: Agent action: ", "fix: Operator action: ")):
            if case.play is not None:
                case.play(root)
        else:
            wt.run_fix(root, done)
        argv = case.then(root) if callable(case.then) else case.then or argv
        done = wt.run(root, *argv)
        if done.returncode == 0:
            return
    pytest.fail("the refusal chain did not clear within four fix lines:\n" + "\n".join(seen))


def test_dead_leaves_a_clean_published_detached_head(world: World) -> None:
    done = _hit(world, _dead_clean_detached(world))
    assert done.returncode == 0, done.stdout + done.stderr
    _dead_done(world)


def test_dead_pushes_an_associated_repo_while_its_main_repo_is_absent(world: World) -> None:
    """Dead's preflight reads the gitflow
    through the same reader — an absent main repo is the default, never a traceback."""
    _associated_on_integration(world)
    world.git(world.ws / "repos" / "lib", "checkout", "-q", "-b", "feature/1.0.0")
    _rmtree(world.repo)
    done = world.cli("context", "dead", "proj")
    assert done.returncode == 0, done.stdout + done.stderr
    _associated_dead(world)


@pytest.mark.parametrize("case", _CASES)
def test_the_fix_line_clears_the_refusal(case: Case, world: World) -> None:
    _drive(world, case)


def test_a_repaired_custom_gitflow_publishes_end_to_end(world: World) -> None:
    """On an empty origin the draft constitution names non-default branches —
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
    assert fix.startswith("Agent action: move ") and fix.endswith("notes.txt into a worktree"), fix
    assert re.search(re.escape(str(world.ws)), fix)


def test_the_gate_is_read_only_and_its_fix_is_one_agent_action_naming_the_listed_path(
    world: World,
) -> None:
    """The denylist refusal's one fix is an Agent action naming the listed path; the gate
    offers no history rewrite and no publish verb that rewrites."""
    command = _denylisted(world)
    fix = _single_fix(_hit(world, command))
    assert fix.startswith("Agent action: ") and "notes.md" in fix, fix
    assert "--rewrite-from" not in fix
    assert "--republish" not in world.cli("context", "baseline", "--help").stdout


def test_a_denylisted_tag_from_a_detached_head_on_an_empty_origin_prints_no_command(
    world: World,
) -> None:
    """The range reaches a root commit and the ref is a tag — the refusal
    names the agent action, prints no command, and the repo stays a repo."""
    world.clone()
    world.deny()
    world.commit("README.md", "r\n")
    world.commit("notes.md", f"a {_TERM}\n")
    world.git(world.repo, "tag", "v0.0.1")
    world.git(world.repo, "checkout", "-q", "--detach", "v0.0.1")
    done = _hit(world, "git push -q origin v0.0.1")
    output = done.stdout + done.stderr
    assert done.returncode != 0 and "\nfix: Agent action: " in output
    assert world.git(world.repo, "rev-parse", "HEAD") == world.git(
        world.repo, "rev-parse", "v0.0.1"
    )
    assert world.remote_heads() == {}


def test_dead_on_a_non_fast_forward_carries_gits_own_text_and_removes_nothing(
    world: World,
) -> None:
    """No pull fix row leads dead into a conflicted merge it would commit and
    push — git's own text stands alone; the checkout stays."""
    _on_work(world)
    _advance_origin_work(world)
    write_text(world.repo / "README.md", "edited\n")
    world.git(world.repo, "commit", "-qam", "edited")
    done = world.cli("context", "dead", "proj")
    output = done.stdout + done.stderr
    assert done.returncode != 0 and "rejected" in output
    assert "\nfix: " not in output
    assert world.repo.is_dir() and not (world.repo / ".git" / "MERGE_HEAD").exists()


def test_a_refused_baseline_push_names_the_anchor_and_the_publish_as_the_next_step(
    world: World,
) -> None:
    """The gate refuses baseline's push — the refusal keeps the gate's
    one fix (an Agent action naming the listed path) and names the anchor and the publish
    as the step after that fix (a hand push would drop origin's merge parent)."""
    done = _hit(world, _baseline_denylisted(world))
    output = done.stdout + done.stderr
    assert done.returncode != 0 and _single_fix(done).startswith("Agent action: ")
    assert f"onboarding commit {world.git(world.repo, 'rev-parse', 'HEAD')}" in output
    assert fix_line(world.ws, "context", "baseline", "proj") in output.replace("\n", "")


def test_dead_after_the_operator_pulls_into_a_conflict_publishes_no_markers(
    world: World,
) -> None:
    """The operator follows git's own `git pull` hint into a conflict;
    the unmerged file is a dirty checkout dead refuses — nothing published, the checkout kept."""
    _on_work(world)
    _advance_origin_work(world)
    other = world.tmp / "other"
    write_text(other / "README.md", "theirs\n")
    world.git(other, "commit", "-qam", "t")
    world.git(other, "push", "-q", "origin", "feature/1.0.0")
    write_text(world.repo / "README.md", "mine\n")
    world.git(world.repo, "commit", "-qam", "mine")
    world.run("git pull -q --no-rebase --no-edit origin feature/1.0.0", world.repo)
    published = world.remote_heads()["feature/1.0.0"]
    done = world.cli("context", "dead", "proj")
    output = done.stdout + done.stderr
    fix = _single_fix(done)
    assert done.returncode != 0 and "README.md" in fix and "x.md" in fix, output
    assert fix.startswith("Agent action: move ") and fix.endswith("into a worktree"), output
    assert world.repo.is_dir() and world.remote_heads()["feature/1.0.0"] == published
