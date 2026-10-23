"""Path taxonomy and bind scope of the SDD gate.

No repos/ path is ADDITIVE; LAW is decided by origin (the
projected set), never by basename; a write out of the bind's scope names `context bind`, and
every write under repos/<r>/ outside specs/audits/ names the worktree of the right kind.
"""

from __future__ import annotations

from pathlib import Path, PurePosixPath

import pytest

from dadaia_workspace.core.cli_line import fix_line, mkdir_line
from dadaia_workspace.core.skill_owner import load_owner
from dadaia_workspace.features.spec_context import gate_policy
from dadaia_workspace.features.spec_context.gate_policy import (
    Decision,
    PathClass,
    classify_path,
    evaluate,
)
from tests.helpers.oslib import cli_path, write_text

_ROOT = Path("/ws")
A, M, P = PathClass.ADDITIVE, PathClass.MUTATING, PathClass.PROTECTED
_IN_REPO = (
    "specs/bugs/BUGS.jsonl",
    "specs/audits/20260101-x/index.md",
    "src/engine/run.py",
    "README.md",
)


# fmt: off
@pytest.mark.parametrize(("path", "expected"), [
    # No specs path is always writable.
    *[pytest.param(f"repos/sample-engine/{rel}", M, id=f"in-repo-{rel}") for rel in _IN_REPO],
    *[pytest.param(rel, M, id=f"root-{rel}") for rel in _IN_REPO],
    pytest.param("/repos/foo/specs/bugs/a.md", M, id="leading-slash-stripped"),
    pytest.param(".dadaia/reports/ctx/r.html", A, id="root-dadaia-reports"),
    pytest.param(".dadaia/handoff/ctx/h.json", A, id="root-dadaia-handoff"),
    pytest.param(".dadaia/tmp/agent/x.txt", A, id="root-dadaia-tmp"),
    # The code floor needs no ledger.
    *[pytest.param(p, P, id=f"floor-{p}") for p in ("AGENTS.md", ".dadaiaignore", ".dadaia/sessions/runtime/ctx.ptr", ".dadaia/states/spec_contexts.json", ".dadaia/hooks/x.sh")],
    pytest.param("repos/sample-engine/AGENTS.md", M, id="repo-agents-md-is-not-the-floor"),
    pytest.param("CLAUDE.md", M, id="AC3.1-root-claude-md-is-not-law"),
    *[pytest.param(p, M, id=f"AC3.1-retired-mirror-{p}") for p in (".codex/AGENTS.md", ".kimi-code/AGENTS.md", ".agents/AGENTS.md", ".claude/rules/AGENTS.md")],
])
# fmt: on
def test_classification_matrix(path: str, expected: PathClass, tmp_path: Path) -> None:
    assert classify_path(path, root=tmp_path)[0] == expected


@pytest.mark.parametrize(
    "path",
    [
        "worktrees/r/a/b/secrets/k",
        "worktrees/r/0.5.0/wt-hotfix-b/secrets/k",
        "worktrees/r/0.5.0/wt-backlog-s/secrets/k",
        "worktrees/r/0.5.0/rc-1/wt-rc/secrets/k",
        "worktrees/r/0.5.0/rc-1/job-1/wt-main/secrets/k",
        "worktrees/r/0.5.0/rc-1/job-1/wt-task-001/secrets/k",
    ],
)
def test_a_protected_glob_holds_at_every_tree_depth(path: str, tmp_path: Path) -> None:
    assert classify_path(path, protected=("secrets/**",), root=tmp_path)[0] == P


_A: dict[str, object] = {"context": "ctx-a", "repos": frozenset({"ctx-a", "ctx-a-infra"})}
_DADAIA = str(cli_path(PurePosixPath("/ws")))
# /ws holds no workspace on disk, so the owner's projected act falls back to the init act.
_INIT = "Agent action: run `uvx dadaia-workspace init` with the workspace's directory as its first argument"


def _wt(repo: str) -> str:
    return f"fix: {_DADAIA} worktree list"


def _at(zone: str, repo: str, owner: str | None = None, **session: object) -> dict[str, object]:
    return {"zone": zone, "repo": repo, "owner": owner or repo, **session}


# fmt: off
@pytest.mark.parametrize(("path", "kwargs", "fix"), [
    pytest.param("specs/releases/_archive/releases_histo.jsonl", {}, None, id="root-path-in-scope-under-any-bind"),
    pytest.param("worktrees/ctx-a/0.5.0-rc1/j1/src/x.py", _at("worktree", "ctx-a", **_A), None, id="AC1.1-own-worktree-allowed"),
    pytest.param("worktrees/ctx-a-infra/0.5.0-rc1/j1/main.tf", _at("worktree", "ctx-a-infra", "ctx-a", **_A), None, id="associated-repo-worktree-in-scope"),
    pytest.param("repos/ctx-a/specs/audits/20260101-x/index.md", _at("audit", "ctx-a", **_A), None, id="AC1.1-own-audit-allowed"),
    pytest.param("repos/ctx-a/src/x.py", _at("repo", "ctx-a", **_A), _wt("ctx-a"), id="AC1.1-own-repo-code-is-merge-only"),
    pytest.param("repos/ctx-a/specs/bugs/BUGS.jsonl", _at("repo", "ctx-a", **_A), _wt("ctx-a"), id="ADR0124-ledger-no-longer-always-writable"),
    pytest.param("repos/ctx-a/specs/bugs/notes.md", _at("repo", "ctx-a", **_A), _wt("ctx-a"), id="F5-a-non-canon-path-is-still-merge-only"),
    pytest.param("repos/ctx-b/src/x.py", _at("repo", "ctx-b", **_A), f"fix: {_DADAIA} context bind ctx-b", id="write-outside-the-bind-scope-names-the-bind"),
    pytest.param("worktrees/ctx-b/0.5.0-rc1/j1/src/x.py", _at("worktree", "ctx-b"), f"fix: {_DADAIA} context bind ctx-b", id="unbound-native-session-refused-names-the-bind"),
    pytest.param("worktrees/ctx-b/0.5.0-rc1/j1/src/x.py", _at("worktree", "ctx-b", has_id=False), None, id="ADR0116-id-less-unbound-worktree-is-the-declared-gap"),
    pytest.param("repos/ctx-b/src/x.py", _at("repo", "ctx-b", has_id=False), _wt("ctx-b"), id="ADR0105-repos-refused-for-every-session"),
    pytest.param("repos/stranger/src/x.py", {**_at("repo", "stranger", **_A), "owner": None}, _wt("stranger"), id="unregistered-slug-still-merge-only"),
    pytest.param("repos/beta/x.py", _at("repo", "beta", context="alpha", repos=frozenset({"alpha"}), has_id=False), "fix: Operator action: relaunch this session with DADAIA_CONTEXT=beta", id="sa-bind-has-two-stores#S5-env-bound-is-told-an-operator-step"),
    pytest.param("AGENTS.md", {}, f"fix: {_INIT}", id="S6-floor-law-one-restore-command"),
    pytest.param(".dadaia/states/spec_contexts.json", {}, "fix: Agent action: use the verb or skill script that owns that state file instead of editing it", id="states-floor-names-the-owning-verb-not-public-install"),
    pytest.param(".dadaia/states/privacy_denylist.json", {}, f"fix: {mkdir_line(_ROOT / '.dadaia' / 'tmp')}", id="the-denylist-is-the-operators-own-file-not-a-verbs-state"),
    pytest.param(".dadaia/sessions/x.json", _A, f"fix: {_DADAIA} context bind ctx-a", id="AC4.4-session-floor-names-the-bound-context"),
    pytest.param(".dadaia/sessions/x.json", {}, f"fix: {_DADAIA} context list", id="AC4.4-session-floor-unbound-lists-contexts"),
    pytest.param(".dadaia/states/install_ledger.json", {"projected": frozenset({".dadaia/states/install_ledger.json"})}, f"fix: {_INIT}", id="H1-ledgered-floor-path-is-projected-law-first"),
    pytest.param("repos/x/secrets/k", {"protected": ("secrets",)}, f"fix: {mkdir_line(_ROOT / '.dadaia' / 'tmp')}", id="AC2.5-protected-glob-operator-drafts-in-tmp"),
])
# fmt: on
def test_evaluate_decides_allow_or_block_with_one_fix(path: str, kwargs: dict[str, object], fix: str | None) -> None:
    """Restoring either ALLOW turns its row red. A BLOCK ends in ONE command, no `&&`;
    memory authorship is audited, never gated."""
    decision, message = evaluate(path, root=_ROOT, **kwargs)  # type: ignore[arg-type]
    assert decision == (Decision.ALLOW if fix is None else Decision.BLOCK)
    if fix is None:
        assert "[GATE]" not in message
    else:
        assert message.splitlines()[-1] == fix and "&&" not in message
        assert "protected" not in kwargs or "'secrets'" in message and "<agent>/<YYYYMMDD>/" in message


def _linked_tree(root: Path, repo: str, name: str, *, backpointer: bool = True, fabricated: bool = False) -> str:
    """A tree under ``worktrees/<repo>/``; its ``.git`` file is git's own shape, or a planted one."""
    tree = root / "worktrees" / repo / "0.5.0" / name
    tree.mkdir(parents=True)
    gitdir = root / ("elsewhere" if fabricated else f"repos/{repo}/.git") / "worktrees" / name
    gitdir.mkdir(parents=True)
    (tree / ".git").write_text(f"gitdir: {gitdir}\n")
    if backpointer:
        (gitdir / "gitdir").write_text(f"{tree / '.git'}\n")
    return f"worktrees/{repo}/0.5.0/{name}/src/x.py"


def _bind(session: str) -> dict[str, object]:
    return _A if session == "bound-to-a" else {"context": None, "repos": frozenset()}


@pytest.mark.parametrize("session", ["bound-to-a", "id-and-no-bind"])
def test_a_write_in_a_linked_tree_of_another_context_is_in_scope(session: str, tmp_path: Path) -> None:
    kwargs = _bind(session)
    own = _linked_tree(tmp_path, "ctx-a", "rc-a")
    other = _linked_tree(tmp_path, "ctx-b", "rc-b")
    assert evaluate(other, root=tmp_path, **_at("worktree", "ctx-b", **kwargs))[0] == Decision.ALLOW  # type: ignore[arg-type]
    assert evaluate(own, root=tmp_path, **_at("worktree", "ctx-a", **_A))[0] == Decision.ALLOW  # type: ignore[arg-type]


@pytest.mark.parametrize("planted", ["fabricated-gitdir", "no-backpointer", "no-gitfile"])
def test_a_tree_that_git_did_not_link_grants_no_scope(planted: str, tmp_path: Path) -> None:
    if planted == "no-gitfile":
        (tmp_path / "worktrees/ctx-b/0.5.0/plain").mkdir(parents=True)
        path = "worktrees/ctx-b/0.5.0/plain/src/x.py"
    else:
        path = _linked_tree(
            tmp_path, "ctx-b", "rc-b", backpointer=planted != "no-backpointer", fabricated=planted == "fabricated-gitdir"
        )
    decision, message = evaluate(path, root=tmp_path, **_at("worktree", "ctx-b", **_A))  # type: ignore[arg-type]
    assert decision == Decision.BLOCK
    assert message.splitlines()[-1] == f"fix: {cli_path(tmp_path)} context bind ctx-b"


_VERDICT_RUN = "python3 .agents/skills/dd-handoff-emitter/scripts/verdict.py /t --sha a --context c --slug s --verdict APPROVED --reason r"
_DISPATCH = "fix: Agent action: dispatch dd-code-reviewer on the tree to judge; its verdict.py run writes the verdict"


@pytest.mark.parametrize(
    ("key", "who", "blocked"),
    [
        ("agent_type", None, True),
        ("agent_type", "dd-sw-engineer-sr", True),
        ("agent_type", "dd-code-reviewer", False),
        (None, None, False),
        (None, "dd-sw-engineer-sr", False),
    ],
)
def test_a_verdict_run_is_refused_unless_the_harness_names_the_reviewer(
    key: str | None, who: str | None, blocked: bool
) -> None:
    reason = gate_policy.verdict_act(_VERDICT_RUN, key=key, subagent=who)
    assert (reason is not None) is blocked
    if reason is not None:
        assert reason.splitlines()[-1] == _DISPATCH
        assert sum(line.startswith("fix: ") for line in reason.splitlines()) == 1


@pytest.mark.parametrize(
    "command",
    [
        "ls",
        "python3 .agents/skills/dd-handoff-emitter/scripts/verdict.py stats 0.5.0-rc22",
        "python3 .agents/skills/dd-handoff-emitter/scripts/verdict.py --help",
        "cat .agents/skills/dd-handoff-emitter/scripts/verdict.py",
        "git commit -m 'verdict APPROVED'",
        "cmd 2>&1 | grep -- --verdict",
    ],
)
def test_a_command_that_writes_no_verdict_is_never_judged(command: str) -> None:
    assert gate_policy.verdict_act(command, key="agent_type", subagent=None) is None


@pytest.mark.parametrize(
    "command",
    [
        _VERDICT_RUN.replace("--verdict APPROVED", "--verdict=APPROVED"),
        _VERDICT_RUN.replace("verdict.py", "Verdict.py"),
        _VERDICT_RUN.replace("python3 ", ""),
        f"cd /t && {_VERDICT_RUN}",
        f"ls | {_VERDICT_RUN}",
        f"echo ok; {_VERDICT_RUN}\n",
        _VERDICT_RUN.replace("python3 ", "python3 -X utf8 "),
        _VERDICT_RUN.replace("python3 ", "python3 -W ignore "),
        _VERDICT_RUN.replace("python3 ", "uv run python "),
        _VERDICT_RUN.replace("python3 ", "uv run "),
        "git log -p .agents/skills/dd-handoff-emitter/scripts/verdict.py | grep -- --verdict",
        "grep -n -- --verdict .agents/skills/dd-handoff-emitter/scripts/verdict.py; ls",
        "echo verdict.py && echo --verdict",
        "grep -n 'x; python3 verdict.py --verdict' notes.md",
        "git commit -m 'docs\n\npython3 verdict.py /t --verdict APPROVED'",
        _VERDICT_RUN.replace("python3 ", "env FOO=1 python3 "),
        _VERDICT_RUN.replace("python3 ", "FOO=1 python3 "),
        _VERDICT_RUN.replace("python3 ", "time python3 "),
        _VERDICT_RUN.replace("python3 ", "timeout 60 python3 "),
        _VERDICT_RUN.replace("python3 ", "py -3 ").replace("/", "\\"),
        _VERDICT_RUN.replace("python3 ", '"C:\\Program Files\\Python312\\python.exe" '),
        _VERDICT_RUN.replace(" /t --sha a ", " /t \\\n  --sha a \\\n  "),
        _VERDICT_RUN.replace("--context", "--reason 'a; b' --context"),
        _VERDICT_RUN.replace("--context", "--reason 'R&D' --context"),
        "{ " + _VERDICT_RUN + "; }",
        "(" + _VERDICT_RUN + ")",
        _VERDICT_RUN.replace(" /t", "\t/t"),
        "python3 -m verdict /t --sha a --context c --slug s --verdict APPROVED --reason r",
        _VERDICT_RUN + " 'unbalanced",
        _VERDICT_RUN.replace("--verdict", "2>&1 --verdict"),
        _VERDICT_RUN.replace("--verdict", "&>log --verdict"),
        _VERDICT_RUN.replace("--verdict", ">&2 --verdict"),
        _VERDICT_RUN.replace("--verdict", "--reason see-x/y#L10 --verdict"),
        "python3 -mverdict /t --sha a --context c --slug s --verdict APPROVED --reason r",
        f"bash -c '{_VERDICT_RUN}'",
        f'sh -c "{_VERDICT_RUN}"',
        "F='python3 .agents/skills/dd-handoff-emitter/scripts/verdict.py'; $F /t --sha a --context c --slug s --verdict APPROVED --reason r",
        f"echo $({_VERDICT_RUN})",
        f"x=`{_VERDICT_RUN}`",
        "python3 -c \"import runpy,sys; sys.argv=['v','/t','--verdict','APPROVED']; runpy.run_path('.agents/skills/dd-handoff-emitter/scripts/verdict.py', run_name='__main__')\"",
        "python3 verdict.p'y' --verdict APPROVED",
        "python3 verdict''.py --verdict APPROVED",
        "python3 verdict.py --ver''dict APPROVED",
        "python3 verdict.p\\y --verdict APPROVED",
    ],
)
def test_a_command_that_runs_the_writer_with_the_flag_is_refused_in_any_shell_position(
    command: str,
) -> None:
    assert gate_policy.verdict_act(command, key="agent_type", subagent=None) is not None


def test_the_law_floor_fix_is_the_owners_projected_act_of_its_workspace(tmp_path: Path) -> None:
    (tmp_path / ".dadaia" / "states").mkdir(parents=True)
    write_text(tmp_path / ".dadaia" / "states" / "spec_contexts.json", "{}")
    want = load_owner("dd-bug-resolution", "_jsonl").reinstall_fix(tmp_path, projected=True)
    _, message = evaluate("AGENTS.md", root=tmp_path)
    assert message.splitlines()[-1] == f"fix: {want}"
    assert want == fix_line(tmp_path.resolve(), "public", "install")
