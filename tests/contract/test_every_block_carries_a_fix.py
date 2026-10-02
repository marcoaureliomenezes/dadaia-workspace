"""Intent: CONTRACT — 0.4.7 FR2 (T-047-14); AC4.1, AC4.4, AC4.7, AC4.8 (T-050-149): every
BLOCK carries one fix line, in an ADR 0158 form, through the one renderer (ADR 0159).

The anti-stall invariant. A BLOCK that does not say, in one line, the exact act that clears
it is a Stall; worse is a fix the gate itself blocks — a closed loop. Each site is driven
through its PUBLIC seam: exactly one ``fix:`` line, either ``Operator action: <one act>`` or
a command whose argv0 exists, with no ``<…>``, no ``&&``, and allowed by
``pre_gate.evaluate_payload`` fed back as Bash; a fix runs verbatim in every host shell.
One walk over the package, the skill scripts and the shipped text scans what no seam drives.

size: SMALL.
"""

from __future__ import annotations

import ast
import functools
import importlib.util
import os
import re
import shlex
import shutil
import subprocess
import sys
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path, PurePosixPath
from typing import Any

import pytest

from dadaia_workspace.core import doctor_rules
from dadaia_workspace.core.cli_line import cli_path, fix_line, git_line, shell_line
from dadaia_workspace.core.gitflow import DEFAULT
from dadaia_workspace.features.chokepoints import push_gate_decision
from dadaia_workspace.features.chokepoints.branch_policy import parse_push_stdin
from dadaia_workspace.features.spec_context.service import install_git_hooks
from dadaia_workspace.features.specs.canon import canon_violations
from dadaia_workspace.features.specs.doctor_adr import cites_an_accepted_adr
from dadaia_workspace.hooks import pre_gate
from dadaia_workspace.infrastructure.git_objects import GitSubprocessObjectReader
from dadaia_workspace.infrastructure.runtime_transforms.hook_wrappers import VENV_MISSING
from tests.fakes import gate_fixes
from tests.fixtures.real_git import PushRepo
from tests.fixtures.stores import own_venv_python, own_venv_workspace

_REPO_ROOT = Path(__file__).resolve().parents[2]
_PKG = _REPO_ROOT / "dadaia_workspace"
_PUBLIC_SKILLS = _PKG / "public" / "skills"
_FIX_LINE_RE = re.compile(r"^fix: (\S.*)$", re.MULTILINE)
#: Not one act (ADR 0158): a `<…>` (in source, bar the `<specs>` `rule_fix` fills), an `&&`
#: chain, an `a|b` menu; a command also no ` or `/` then ` (sa-fix-lines-not-built-by-cli-line#S3).
_NOT_ONE_ACT_RE = re.compile(r"<(?!specs>)[^<>\n]+>|&&|\w\|\w")
_NOT_ONE_COMMAND_RE = re.compile(rf"{_NOT_ONE_ACT_RE.pattern}| or | then ")
#: The installer a workspace is born from (getting-started Level 1), absent from CI runners.
_PREREQUISITES = {"uvx"}
#: The executables a fix line opens with — a list, not `which`: a host may ship a binary
#: named like a prose verb (`/usr/bin/write`), and the judgement must not move with it.
_HEADS = {"chmod", "gh", "git", "grep", "ls", "mkdir", "rm", "sed", *_PREREQUISITES}


def _defect(fix: str) -> bool:
    """The ONE predicate: *fix* is `Operator action: <one act>`, or one command whose head is
    no prose word (a lowercase head is one of `_HEADS`); `·` is a value the source
    walk cannot know."""
    known = fix.split("·", 1)[0]  # the text before the first value the walk cannot know
    if fix.startswith("Operator action: ") or " " not in known and "·" in fix:
        return bool(_NOT_ONE_ACT_RE.search(fix))
    head = known.split(" ", 1)[0]
    prose = re.fullmatch(r"[a-z][a-z0-9-]*", head) and head not in _HEADS
    return bool(prose or _NOT_ONE_ACT_RE.search(fix) or _NOT_ONE_COMMAND_RE.search(known))


_SHA_B, _ZERO = "b" * 40, "0" * 40


def _the_fix(message: str | None) -> str:
    """The ONE ``fix:`` line of *message*, in a 0158 form the gate lets run."""
    assert message, "a BLOCK with an empty message is a Stall"
    fixes = _FIX_LINE_RE.findall(message)
    assert len(fixes) == 1, f"expected exactly one 'fix:' line, got {fixes} in:\n{message}"
    fix = fixes[0]
    assert not _defect(fix) and "<specs>" not in fix, f"not one act: {fix}"
    if fix.startswith("Operator action: "):
        return fix
    argv0 = shlex.split(fix)[0]  # an absolute file, or a bare name on PATH — never cwd-relative
    on_path = "/" not in argv0 and (shutil.which(argv0) or argv0 in _PREREQUISITES)
    assert on_path or (Path(argv0).is_absolute() and Path(argv0).is_file()), fix
    block = pre_gate.evaluate_payload({"tool_name": "Bash", "tool_input": {"command": fix}})
    assert block is None, f"the fix command is itself BLOCKED (a Stall):\n{fix}\n{block}"
    return fix


def _plant_cli(cli: Path) -> None:
    """A real executable exiting 0 with no argument, where a fix line spells the CLI."""
    stand_in = shutil.which("whoami" if sys.platform == "win32" else "true")
    assert stand_in, "the host has no stand-in executable"
    cli.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(stand_in, cli)


# ── the real `dadaia doctor` output (undo of b50f0c97: the printer is exercised) ──


def test_the_real_doctor_prints_every_fix_as_one_whole_runnable_line(tmp_path: Path) -> None:
    """The printer, not a synthetic render: a workspace finding (an expired tmp entry), an
    error-class specs finding (FIXED-1 on a symlinked QUALITY.md) and a ledger finding
    (a malformed BACKLOG.json), through a `dadaia doctor` subprocess at a 61-char root with
    COLUMNS unset: exit 1, and every `fix:` line is one whole line in a 0158 form."""
    import site

    from dadaia_workspace.features.specs import canon

    ws = own_venv_workspace(tmp_path / ("w" * max(1, 61 - len(str(tmp_path)))))  # 61-char root
    expired = ws / ".dadaia" / "tmp" / "agent" / "20200101"
    expired.mkdir(parents=True)
    os.utime(expired, (0, 0))
    specs = ws / "repos" / "demo" / "specs"
    canon.scaffold(specs, project_name="demo")
    outside = tmp_path / "outside.md"
    outside.write_text("# Quality\n", encoding="utf-8")
    (specs / "memory" / "QUALITY.md").unlink()
    (specs / "memory" / "QUALITY.md").symlink_to(outside)
    (specs / "backlog" / "BACKLOG.json").write_text("{}\n", encoding="utf-8")
    env = {k: v for k, v in os.environ.items() if k != "COLUMNS"}
    env["PYTHONPATH"] = os.pathsep.join([str(_REPO_ROOT), *site.getsitepackages()])
    argv = [str(own_venv_python(ws)), "-m", "dadaia_workspace", "doctor", "--specs-dir", str(specs)]
    run = subprocess.run(argv, cwd=ws, env=env, capture_output=True, text=True, timeout=120)

    assert run.returncode == 1, run.stdout + run.stderr
    lines = run.stdout.splitlines()
    assert {"WS-tmp-expired", "FIXED-1", "LEDGER-BACKLOG-SCHEMA"} <= {
        line.split(" ", 1)[0] for line in lines
    }, run.stdout
    fixes = [line for line in lines if line.startswith("fix: ")]
    assert fixes, run.stdout
    for fix in fixes:  # two shapes, no third (sa-unfixable-doctor-findings-say-doctor-fix#S1)
        if _the_fix(fix).startswith("Operator action: "):  # AC4.5: it names the file
            assert re.search(r"\s(/|\w:[\\/])\S", fix), fix
    # Whole lines: a wrapped fix would leave a continuation line that is neither a finding
    # (`CODE verdict …`) nor a `fix:` line.
    assert [ln for ln in lines if ln and not re.match(r"(fix: |[A-Z][A-Za-z0-9-]+ )", ln)] == []


# ── (producer, trigger): every refusal the gate, the hooks and the push gate emit ─


@pytest.fixture
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    return _workspace(tmp_path, monkeypatch)


@pytest.fixture
def blank_workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A workspace whose root holds a blank, so the fix's executable path must be quoted."""
    return _workspace(tmp_path / "my ws", monkeypatch)


def _workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    (tmp_path / ".dadaia" / "states").mkdir(parents=True)
    (tmp_path / ".dadaia" / "states" / "spec_contexts.json").write_text(
        '{"contexts": [{"repo_slug": "a", "state": "alive"}]}', encoding="utf-8"
    )
    (tmp_path / ".dadaia" / "sessions").mkdir(parents=True)
    (tmp_path / ".dadaiaignore").write_text("[protected]\nsecrets\n", encoding="utf-8")
    _plant_cli(cli_path(tmp_path))
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "prefix", sys.prefix)  # restored after _bare_cli moves it
    return tmp_path


def _gate(ws: Path, rel: str) -> str | None:
    return pre_gate.evaluate_payload({"tool_name": "Write", "tool_input": {"file_path": str(ws / rel)}})  # fmt: skip


def _scope_block(ws: Path, *, has_id: bool) -> str:
    """A write into a repo another context owns, outside the bind's repos (AC4.4)."""
    from dadaia_workspace.features.spec_context.gate_policy import evaluate

    return evaluate("repos/b/x.py", root=ws, zone="repo", repo="b", owner="b",
                    context="a", repos=frozenset({"a"}), has_id=has_id)[1]  # fmt: skip


def _bare_cli(ws: Path) -> str | None:
    """The fix names the RUNNING CLI (ADR 0045): a host venv outside any workspace (CI's
    poetry venv) proves no expectation pins the instance's own spelling."""
    sys.prefix = str(ws.parent / "host-venv")
    _plant_cli(Path(shlex.split(fix_line(None))[0]))
    return pre_gate.evaluate_payload(
        {"tool_name": "Bash", "tool_input": {"command": "dadaia doctor --context x"}}
    )


def _push(ws: Path, line: str = "", files: dict[str, str] | None = None, **kwargs: Any) -> str:
    """A consumer work clone (``main`` published, one unpublished commit, the installed
    pre-push hook — AC4.7: it names no library toolchain), pushing *line*."""
    (ws / "clone").mkdir()
    repo = PushRepo(ws / "clone")
    repo.commit({"README.md": "r\n"})
    repo.publish("main")
    for hook in install_git_hooks(repo.path):
        assert "ci preflight" not in hook.read_text(encoding="utf-8"), hook
    sha = repo.commit(files or {"a.md": "a\n"})
    fields = {"sha": sha, "other": _SHA_B, "zero": _ZERO, "a": "a" * 40}
    decision = push_gate_decision(
        parse_push_stdin(line.format(**fields))[0] if line else [],
        gitflow=DEFAULT,
        fixes=replace(gate_fixes(), head="feature/0.0.1"),
        object_source=GitSubprocessObjectReader(),
        repo=repo.path,
        canon_violations_fn=canon_violations,
        cites_accepted_adr=cites_an_accepted_adr(None),
        **{"malformed_lines": 0, "denylist_terms": (), **kwargs},
    )
    assert not decision.allowed, "expected a refusal"
    return decision.message


_FEATURE = "refs/heads/feature/0.0.1 {sha} refs/heads/feature/0.0.1 {zero}"
_BLOCKS: dict[str, Callable[[Path], str | None]] = {
    "gate-root-whitelist": lambda ws: _gate(ws, "junk.txt"),
    "gate-protected-sessions": lambda ws: _gate(ws, ".dadaia/sessions/some-session.json"),
    "gate-protected-projected": lambda ws: _gate(ws, ".dadaia/states/install_ledger.json"),
    "gate-protected-glob-dec-11": lambda ws: _gate(ws, "repos/a/secrets/k"),
    "gate-scope-names-the-bind": lambda ws: _scope_block(ws, has_id=True),
    "gate-id-less-session-relaunch": lambda ws: _scope_block(ws, has_id=False),
    "venv-guard-bare-cli": _bare_cli,
    "hook-missing-venv": lambda ws: VENV_MISSING.replace("$ROOT", ws.as_posix()),
    "push-malformed-stdin": lambda ws: _push(ws, malformed_lines=1),
    "push-main": lambda ws: _push(ws, "refs/heads/main {sha} refs/heads/main {other}"),
    "push-develop": lambda ws: _push(ws, "refs/heads/develop {sha} refs/heads/develop {other}"),
    "push-birth-with-content": lambda ws: _push(
        ws, "refs/heads/develop {sha} refs/heads/develop {zero}"
    ),
    "push-invalid-name": lambda ws: _push(ws, "refs/heads/wip/x {sha} refs/heads/wip/x {zero}"),
    "push-not-a-branch-head": lambda ws: _push(ws, "refs/notes/x {sha} refs/notes/x {zero}"),
    # bug every-block-fix-push-refspec-flaky-under-xdist
    "push-refspec": lambda ws: _push(
        ws, "refs/heads/feature/0.0.1 {sha} refs/heads/develop {zero}"
    ),
    "push-specs-canon": lambda ws: _push(ws, _FEATURE, {"specs/not-a-canon-entry.md": "x\n"}),
    "push-denylist": lambda ws: _push(
        ws, _FEATURE, {"b.md": "zz-secret-term\n"}, denylist_terms=[("zz-secret-term", "synthetic")]
    ),
    # a sha the repo does not hold: the real object read fails and the gate fails closed
    "push-git-read-failure": lambda ws: _push(ws, _FEATURE.replace("{sha}", "{a}")),
}


@pytest.mark.parametrize("block", list(_BLOCKS))
def test_every_block_carries_a_runnable_fix(workspace: Path, block: str) -> None:
    _the_fix(_BLOCKS[block](workspace))


def _shells() -> list[list[str]]:
    if sys.platform != "win32":
        return [["sh", "-c"]]
    git_bash = Path(os.environ.get("PROGRAMFILES", r"C:\Program Files"), "Git", "bin", "bash.exe")
    return [
        ["cmd", "/d", "/s", "/c"],
        ["powershell", "-NoProfile", "-Command"],
        [str(git_bash), "-c"],
    ]


@pytest.mark.parametrize("shell", _shells(), ids=lambda argv: Path(argv[0]).stem)
def test_a_fix_runs_verbatim_in_every_host_shell(blank_workspace: Path, shell: list[str]) -> None:
    """Review H5 (0.5.0 c3), sa-gate-allows-root-entries-the-reaper-moves#E7: the root
    BLOCK's fix and a CLI fix line run verbatim in each shell the host offers — POSIX
    ``sh``; on Windows cmd, PowerShell and Git Bash — the root fix from ``repos/demo``,
    twice (the zone usually exists), never writing the exceptions file; bug
    windows-quoted-executable-fix-not-runnable-in-powershell: the root holds a blank."""
    workspace = blank_workspace
    if shell[0].endswith("bash.exe") and not Path(shell[0]).is_file():
        pytest.skip(f"Git Bash is not installed at {shell[0]}")
    (workspace / ".dadaiaignore").unlink()
    root_fix = _the_fix(_gate(workspace, "junk.txt"))
    (workspace / "repos" / "demo").mkdir(parents=True)
    # The timeout only guards a hang: a PowerShell cold start on a loaded Windows runner
    # exceeded 25 s (run 36269883321) while the line itself was fine.
    runs = [
        subprocess.run(
            # cmd /s strips the outer quotes of its raw tail (Node's shell:true form);
            # list2cmdline's \" is not cmd syntax.
            f'{subprocess.list2cmdline(shell)} "{line}"' if shell[0] == "cmd" else [*shell, line],
            cwd=workspace / "repos" / "demo",
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )  # fmt: skip
        for line in (root_fix, root_fix, fix_line(workspace))
    ]
    assert [r.returncode for r in runs] == [0, 0, 0], [r.stderr for r in runs]
    assert (workspace / ".dadaia" / "tmp").is_dir()
    assert not (workspace / ".dadaiaignore").exists()  # the fix never writes the operator's file


def test_cli_line_and_the_scripts_render_one_argv_as_one_line(tmp_path: Path) -> None:
    """ADR 0159's pinned pair: one argv through ``core/cli_line`` and the scripts' ``_specs``
    renders one line — a blank, a quote and a ``$`` included."""
    loader = importlib.util.spec_from_file_location(
        "_specs_pinned", _PUBLIC_SKILLS / "dd-bug-resolution" / "scripts" / "_specs.py"
    )
    assert loader and loader.loader
    specs = importlib.util.module_from_spec(loader)
    loader.loader.exec_module(specs)
    rest = ["commit", "-m", "it's $HOME"]
    assert specs.git_line(tmp_path / "a b", *rest) == git_line(tmp_path / "a b", *rest)
    script = tmp_path / "s p" / "x.py"
    assert specs.script(script) == shell_line(sys.executable, str(script.resolve()))


# ── dadaia doctor rules: every fix rendered by `rule_fix` ───────────────────────


def _every_doctor_rule() -> list[tuple[str, doctor_rules.Rule[Any]]]:
    from dadaia_workspace.features.backlog.doctor import RULES as BACKLOG_RULES
    from dadaia_workspace.features.spec_context.doctor import workspace_rules
    from dadaia_workspace.features.specs.doctor_adr import LEDGER_RULES as ADR_LEDGER_RULES
    from dadaia_workspace.features.specs.rules import RULES as SPECS_RULES

    rules = (*workspace_rules(expired_only=False), *SPECS_RULES, *BACKLOG_RULES, *ADR_LEDGER_RULES)
    return [("/".join(rule.codes), rule) for rule in rules]


#: Every doctor rule's fix on a `specs` tree (a ledger's operator action is proven in
#: test_workspace_fix_lines_clear_their_finding).
_FIX_LINES = [
    (codes, doctor_rules.rule_fix(rule, Path(), Path("specs")))
    for codes, rule in _every_doctor_rule()
    if rule.fix_help
]
#: The installed skill tree maps to the `public/skills/` source; the venv-rooted binary is
#: resolved by the CLI arm, never as a file.
_INSTALLED_SKILL_PREFIX = ".agents/skills/"
#: ``script_line``'s two absolute heads, as literals of the running environment: the
#: interpreter running now (normalized session-wide by tests/conftest.py), and the skills this
#: package ships (never a derived workspace).
_VENV_PYTHON = Path(sys.executable).as_posix()
_SKILLS = _PUBLIC_SKILLS.as_posix() + "/"
_FLAG_VALUE_RE = re.compile(r"^--[\w-]+=")


@functools.cache
def _cli_root() -> Any:
    import typer.main

    from dadaia_workspace.cli.main import app

    return typer.main.get_command(app)


def _cli_command(tokens: list[str]) -> Any:
    """The leaf of the live Typer tree *tokens* walk to (options stop the walk), else None."""
    cmd = _cli_root()
    for token in tokens:
        if token.startswith("-") or not getattr(cmd, "commands", None):
            break
        if token not in cmd.commands:
            return None
        cmd = cmd.commands[token]
    return (
        None
        if tokens and getattr(cmd, "commands", None) and not cmd.invoke_without_command
        else cmd
    )


def _tracked_dirs() -> frozenset[str]:
    """Every tracked directory — git's answer, never the working tree's, which differs
    between a local checkout and CI's (0.4.7 c8 review MEDIUM-3)."""
    listed = subprocess.run(["git", "-C", str(_REPO_ROOT), "ls-files", "-z"],
                            capture_output=True, text=True, check=True, timeout=60).stdout  # fmt: skip
    return frozenset(
        PurePosixPath(*parts[:depth]).as_posix()
        for parts in (PurePosixPath(t).parts for t in listed.split("\0") if t)
        for depth in range(1, len(parts))
    ) | {""}


def _canon_dirs() -> frozenset[str]:
    """Every directory the specs canon guarantees — a consumer's tree carries these even
    when this repo's own does not."""
    from dadaia_workspace.core.workspace_layout import SPECS_CANON

    parts = [PurePosixPath(entry.shape).parts for entry in SPECS_CANON]
    return frozenset(PurePosixPath("specs", *p[:d]).as_posix() for p in parts for d in range(len(p)))  # fmt: skip


_KNOWN_DIRS = _tracked_dirs() | _canon_dirs()


def _unresolved_paths(command: str) -> list[str]:
    """Every unquoted path token (a slash, no root list to go stale — 0.4.7 c8 review
    MEDIUM-3; a ``--flag=value`` carries it in the value) whose directory is neither
    tracked here nor guaranteed by the specs canon: a fix creates, edits or deletes its
    leaf, so only the directory holding it must exist."""
    lexer = shlex.shlex(command, posix=False)
    lexer.whitespace_split = True
    unresolved: list[str] = []
    for raw in lexer:
        token = _FLAG_VALUE_RE.sub("", raw.removeprefix(_REPO_ROOT.as_posix() + "/"))
        if raw == _VENV_PYTHON or token.startswith((".dadaia/", "'", '"', "-", ">", "&", "|")):
            continue  # the interpreter, the venv binary (the CLI arm), a quoted script
        if "/" not in token:
            continue
        if token.startswith(_INSTALLED_SKILL_PREFIX):
            token = "dadaia_workspace/public/skills/" + token.removeprefix(_INSTALLED_SKILL_PREFIX)
        if PurePosixPath(token).parent.as_posix().removesuffix(".") not in _KNOWN_DIRS:
            unresolved.append(token)
    return unresolved


@pytest.mark.parametrize(("codes", "command"), _FIX_LINES, ids=[c for c, _ in _FIX_LINES])
def test_every_doctor_fix_target_resolves_on_disk(codes: str, command: str) -> None:
    """0.4.7 c8 review F7, bug backlog-doctor-fix-names-missing-update-verb, AC4.4: no
    ``<…>``; every path token resolves to a directory this repo tracks or the specs canon
    guarantees; a ``dadaia`` fix walks the live command tree to a leaf; a skill-script fix
    (sa-fix-lines-not-built-by-cli-line#S8) runs the venv interpreter and a shipped script
    by absolute path, whose subcommand takes ``--help``."""
    assert not _defect(command) and "<specs>" not in command, command
    assert _unresolved_paths(command) == [], f"{codes}: {command!r}"
    tokens = shlex.split(command)
    if command.startswith(fix_line(Path())):
        assert _cli_command(tokens[1:]), f"{codes}: no such verb: {command!r}"
    if "/scripts/" not in command:
        return
    assert tokens[0] == _VENV_PYTHON and Path(tokens[1]).is_absolute(), command
    assert tokens[1].startswith(_SKILLS) and Path(tokens[1]).is_file(), command
    verb = next(t for t in tokens[2:] if not t.startswith("-"))
    help_run = subprocess.run([sys.executable, tokens[1], verb, "--help"],
                              capture_output=True, text=True, timeout=60)  # fmt: skip
    assert help_run.returncode == 0, f"{codes}: {tokens[1]} rejects {verb!r}: {help_run.stderr}"


# ── every script-emitted fix line names its own folder's entry script ───────────

#: The one entry script of each skill that ships scripts — what an operator pastes.
_ENTRY_SCRIPTS: dict[str, str] = {
    "dd-audit-project": "audit.py",
    "dd-backlog-definition": "backlog.py",
    "dd-bug-resolution": "bugs.py",
    "dd-cli-library": "registry.py",
    "dd-gitflow-default": "worktree.py",
    "dd-release-implementation": "release.py",
    "dd-spec-navigator": "memory.py",
}
_LITERAL_FIX_RE = re.compile(r'"fix: ([^"]*)')
_SCRIPT_CONST_RE = re.compile(r'^SCRIPT = Path\(__file__\)\.parent / "([^"]+)"', re.MULTILINE)
_NAMED_SCRIPT_RE = re.compile(r"[\w.{}\[\]()/-]*\.py")
_SCRIPT_MODULES = sorted(_PUBLIC_SKILLS.glob("*/scripts/*.py"))


@pytest.mark.parametrize(
    "module", _SCRIPT_MODULES, ids=[f"{m.parts[-3]}/{m.name}" for m in _SCRIPT_MODULES]
)
def test_every_script_fix_line_names_its_folders_entry_script(module: Path) -> None:
    """0.4.7 review fold (F3): every `fix:` literal naming a `.py` file, and every `SCRIPT`
    constant a `Refusal` fix is built from, names its folder's entry script — never a sibling
    module with no ``__main__`` (an un-runnable fix is a Stall)."""
    entry = _ENTRY_SCRIPTS[module.parts[-3]]
    text = module.read_text(encoding="utf-8")
    for body in _LITERAL_FIX_RE.findall(text):
        assert "__file__" not in body, f"{module.name}: {body!r}"
        assert all(n.endswith(entry) for n in _NAMED_SCRIPT_RE.findall(body)), body
    for named in _SCRIPT_CONST_RE.findall(text):
        assert named == entry, f"{module.name}: SCRIPT names {named!r}, not {entry!r}"


# ── the one walk: every fix the code prints, every command line the shipped text holds ──

#: A fix callee: a `cli_line` builder's or a fix producer's arguments are fix text.
_FIX_CALL_RE = re.compile(r"(_line|_fix|^script)$")
#: A hand-built CLI spelling in a fix (sa-fix-lines-not-built-by-cli-line, ADR 0045).
_SPELLING = re.compile(r"\.dadaia[/\\]\.venv|(?<![\w./-])dadaia\s")
_HAND_BUILT = {"DADAIA_BIN", "cli_path"}
#: A fix's positional index in a constructor no `def` declares (onboarding `Step`, `Refusal`).
_FIX_CTORS = {"Step": 3, "Refusal": 1}
#: B1's other fix positions: a value bound to, or returned by, a `fix`-named name.
_FIX_NAME = re.compile(r"(?i)(?:^|_)fix(?:es)?(?:$|_)")
#: A builder spelling a command inside error prose with no `fix:` line (PLAN §2.8 not-sites).
_PROSE = {"dadaia_workspace/cli/_specs_resolution.py:64", "dadaia_workspace/core/invocation.py:250"}
#: The builder module: the one place the CLI is spelled by hand.
_BUILDER = "dadaia_workspace/core/cli_line.py"


def _callee(node: ast.Call) -> str:
    return getattr(node.func, "id", getattr(node.func, "attr", ""))


def _render(
    node: Any, scope: dict[str, list[Any]], returns: dict[str, list[Any]], depth: int = 0
) -> str:
    """The text *node* can print; alternatives and unknown values join as `·`; a
    hand-built CLI name renders as the spelling it builds."""
    again = lambda n: _render(n, scope, returns, depth + 1) if depth < 12 else "·"  # noqa: E731
    match node:
        case ast.Constant(value=str() as text):
            return text
        case ast.Name(id=name) | ast.Attribute(attr=name) | ast.Call(func=ast.Name(id=name)) if name in _HAND_BUILT:  # fmt: skip
            return ".dadaia/.venv "
        case ast.JoinedStr(values=parts):
            return "".join(map(again, parts))
        case ast.List(elts=parts) | ast.Tuple(elts=parts) | ast.Dict(values=parts) | ast.BoolOp(values=parts):  # fmt: skip
            return "·".join(map(again, parts))
        case ast.FormattedValue(value=v) | ast.Starred(value=v) | ast.Subscript(value=v):
            return again(v)
        case ast.ListComp(elt=v) | ast.GeneratorExp(elt=v) | ast.Lambda(body=v):
            return again(v)
        case ast.BinOp(left=left, right=right):
            return again(left) + again(right)
        case ast.IfExp(body=body, orelse=orelse):
            return f"{again(body)}·{again(orelse)}"
        case ast.Name(id=name):
            return "·".join(map(again, scope.get(name, []))) or "·"
        case ast.Attribute(attr=attr):  # a gitflow pattern renders its default
            return str(getattr(DEFAULT, attr, "·"))
        case ast.Call(func=ast.Attribute(attr="join"), args=[arg]):
            return again(arg)
        case ast.Call(func=ast.Attribute(attr="get", value=table)):  # a fix table's lookup
            return again(table)
        case ast.Call(func=ast.Attribute(value=receiver)) if not isinstance(receiver, ast.Name):
            return again(receiver)
        case ast.Call() if _callee(node) in returns:  # a local producer: what it returns
            return "·".join(map(again, returns[_callee(node)]))
        case ast.Call() if _FIX_CALL_RE.search(_callee(node)) or _callee(node)[:1].isupper():
            return " ".join(map(again, [*node.args, *(k.value for k in node.keywords)]))
    return "·"


def _scope(node: Any, outer: dict[str, list[Any]]) -> dict[str, list[Any]]:
    """Every value a name is bound to in *node*: its defaults and assignments, then *outer*'s."""
    bound: dict[str, list[Any]] = {}
    if isinstance(node, ast.FunctionDef):
        args = node.args
        named = [*args.args[len(args.args) - len(args.defaults) :], *args.kwonlyargs]
        for arg, default in zip(named, [*args.defaults, *args.kw_defaults], strict=True):
            bound[arg.arg] = [default]
    for child in ast.walk(node):
        if isinstance(child, ast.Assign):
            for name in (n for t in child.targets for n in ast.walk(t) if isinstance(n, ast.Name)):
                bound.setdefault(name.id, []).append(child.value)
    return {**outer, **bound}


def _code_sites(trees: dict[str, ast.Module]) -> list[str]:
    """`file:line` of each fix a module can print that is not one command through the one
    renderer — a `<…>`, an `&&`, an `a|b` menu or a hand-built CLI spelling in a `fix:` text,
    a `fix` parameter's argument or a builder's arguments — and of each non-docstring
    literal instructing a hand-run `dadaia <verb>`. Ceilings — what the walk cannot see: a
    helper's return in another module, `str.format`, `print("fix:", x)` with separate
    arguments, and a returned dict literal."""
    from dadaia_workspace.cli.help_digest import command_paths

    verbs = "|".join(sorted({path[0] for path in command_paths() if path}))
    instruction = re.compile(rf"(?:['`]|\$\(|\b[Rr]e-?run:? |\b[Rr]un:? |\bwith |\buntil |\bthen )dadaia ({verbs})\b")  # fmt: skip

    def fix_params(owners: Any) -> dict[str, int]:
        """Each callable taking `fix` (a class: its __init__), and its position."""
        return {
            (owner.name if fn.name == "__init__" else fn.name): names.index("fix")
            for owner in owners
            for fn in (owner.body if isinstance(owner, ast.ClassDef) else [owner])
            if isinstance(fn, ast.FunctionDef)
            and "fix" in (names := [a.arg for a in fn.args.args if a.arg != "self"])
        }

    local = {rel: fix_params(ast.walk(t)) for rel, t in trees.items()}
    every = {**_FIX_CTORS, **{n: at for params in local.values() for n, at in params.items()}}
    every |= {f"{PurePosixPath(rel).stem}.{n}": at for rel, params in local.items() for n, at in params.items()}  # fmt: skip
    sites: set[str] = set()
    for rel, tree in trees.items():
        fix_param = {**every, **local[rel]}  # a local `def` wins its name
        defs = {n.name: n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
        returns = {name: [r.value for r in ast.walk(d) if isinstance(r, ast.Return) and r.value] for name, d in defs.items()}  # fmt: skip
        docs = {id(n.body[0].value) for n in ast.walk(tree)
                if isinstance(n, ast.Module | ast.FunctionDef | ast.ClassDef) and n.body
                and isinstance(n.body[0], ast.Expr)}  # fmt: skip
        spelled = rel == _BUILDER or "/public/" in rel  # stdlib scripts spell via `_specs`
        module = _scope(tree, {})
        for unit in [tree, *defs.values()]:
            scope = module if unit is tree else _scope(unit, module)
            for node in ast.walk(unit):
                fixes: list[str] = []
                if isinstance(node, ast.Call):
                    owner = getattr(node.func, "value", None)
                    qualified = f"{owner.id}.{_callee(node)}" if isinstance(owner, ast.Name) else ""
                    at = fix_param.get(qualified, fix_param.get(_callee(node), -1))
                    carried = [*node.args[at : at + 1 if at >= 0 else 0],
                               *(k.value for k in node.keywords if k.arg in ("fix", "fix_help"))]  # fmt: skip
                    if _FIX_CALL_RE.search(_callee(node)):
                        carried.append(node)
                    fixes = [_render(c, scope, returns) for c in carried]
                elif (
                    isinstance(node, ast.Constant | ast.JoinedStr | ast.BinOp)
                    and id(node) not in docs
                ):
                    fixes = _render(node, scope, returns).split("fix: ")[1:]
                elif isinstance(node, ast.Assign | ast.AnnAssign) and node.value is not None:
                    names = [
                        ast.unparse(t)
                        for t in (node.targets if isinstance(node, ast.Assign) else [node.target])
                    ]
                    fixes = (
                        [_render(node.value, scope, returns)]
                        if any(map(_FIX_NAME.search, names))
                        else []
                    )
                elif isinstance(node, ast.FunctionDef) and _FIX_NAME.search(node.name):
                    fixes = [
                        _render(r.value, scope, returns)
                        for r in ast.walk(node)
                        if isinstance(r, ast.Return) and r.value
                    ]
                text = getattr(node, "value", None) if isinstance(node, ast.Constant) else None
                told = isinstance(text, str) and id(node) not in docs and instruction.search(text)
                # a value carrying its own message keeps only what follows its `fix: `
                alts = [a.strip() for f in fixes for a in f.split("fix: ")[1:] or [f] if a.strip()]
                hand = not spelled and any(_SPELLING.search(a) for a in alts)
                if hand or any(map(_defect, alts)) or (told and rel != _BUILDER):
                    sites.add(f"{rel}:{node.lineno}")
    return sorted(sites - _PROSE)


#: AC4.8: a command line spelling the CLI — a code span or a fenced line naming it.
_CODE_SPAN = re.compile(r"`([^`\n]+)`")
_CLI_WORDS = re.compile(r"(?:^|(?<=[\s(]))(\S*(?<![\w-])dadaia)(?![\w.-])((?: [^\s|;&`]+)*)")


def _bad_command(text: str) -> bool:
    """A bare `dadaia <verb>`, `$DADAIA_BIN`, or a venv CLI line whose verb or flag the
    live command tree lacks."""
    if "$DADAIA_BIN" in text:
        return True
    for match in _CLI_WORDS.finditer(text):
        head, words = match.group(1), match.group(2).split()
        if head == "dadaia" and words and words[0] in _cli_root().commands:
            return True
        if head.endswith(".venv/bin/dadaia"):
            cmd = _cli_command(words)
            flags = {w.split("=")[0] for w in words if w.startswith("--")} - {"--help"}
            if cmd is None or flags - {o for p in cmd.params for o in p.opts}:
                return True
    return False


#: Dead law words: retired release verbs, rc-N, bug-resolve-law-names-flags-the-script-does-not-have
_DEAD_RELEASE_VOCABULARY = re.compile(r"rc-archive|release\.py (fold|archive)|rc-N|resolve` carrying")  # fmt: skip
#: `memory.py check` decides only the generated catalog pair; LINT-1 owns the atoms (bug
#: memory-done-criterion-names-a-script-that-never-validates-atoms).
_NON_AUTHORITY_DONE = re.compile(r"memory\.py check`? exit 0")


def _text_rows(rel: str) -> list[Callable[[str], object]]:
    """The scans a tracked text file's lines take, by where it ships: the law (the shipped
    surface, product memory, the glossary) names no retired verb; what ships names no
    `memory.py check` done criterion; consumer guidance no library toolchain (AC4.7);
    `public/**/*.md` command lines spell the live CLI (AC4.8); a script's git fix goes through
    `_specs.git_line`, never a hand-spelled unquoted `git -C {…}`."""
    rows: list[Callable[[str], object]] = []
    if rel.startswith(("dadaia_workspace/public/", "specs/memory/")) or rel == "CONTEXT.md":
        rows.append(_DEAD_RELEASE_VOCABULARY.search)
    if not rel.startswith("specs/"):
        rows.append(_NON_AUTHORITY_DONE.search)
    if rel == "docs/getting-started.md":
        rows.append(re.compile("release-please").search)
    if rel.startswith("dadaia_workspace/public/") and rel.endswith(".md"):
        rows.append(lambda line: any(_bad_command(span) for span in _CODE_SPAN.findall(line)))
    if rel.startswith("dadaia_workspace/public/") and rel.endswith(".py"):
        rows.append(re.compile(r"git -C \{").search)
    return rows


def _text_sites(texts: dict[str, str]) -> list[str]:
    """`file:line` of each line a row of :func:`_text_rows` bites; a fenced line is a
    command line whole."""
    sites: list[str] = []
    for rel, text in texts.items():
        rows, fenced = _text_rows(rel), False
        for number, line in enumerate(text.splitlines(), start=1):
            fenced ^= line.startswith("```")
            whole = fenced and rel.startswith("dadaia_workspace/public/") and _bad_command(line)
            if whole or any(row(line) for row in rows):
                sites.append(f"{rel}:{number}")
    return sites


def test_no_fix_or_shipped_line_bypasses_the_one_renderer() -> None:
    """Intent: CONTRACT — AC4.1, AC4.4 (DEL fix-lines-are-not-one-runnable-command, ADR
    0158), AC4.7, AC4.8, sa-fix-lines-not-built-by-cli-line#S1: one walk over every package
    module and `public/skills` script, every doctor rule's `rule_fix`, and every tracked
    law, docs and shipped text file (bug law-file-scan-reads-untracked-bytecode)."""
    listed = subprocess.run(["git", "ls-files", "-z", "--", "dadaia_workspace", "specs/memory",
                             "CONTEXT.md", "docs"], cwd=_REPO_ROOT, capture_output=True,
                            text=True, check=True).stdout.split("\0")  # fmt: skip
    files = {rel: _REPO_ROOT / rel for rel in listed if rel and "_archive" not in rel}
    code = {rel: ast.parse(p.read_text(encoding="utf-8")) for rel, p in files.items() if rel.endswith(".py")}  # fmt: skip
    texts = {rel: p.read_text(encoding="utf-8") for rel, p in files.items()
             if not rel.startswith(("dadaia_workspace/", "docs/")) or rel.startswith("dadaia_workspace/public/") or rel.endswith(".md")}  # fmt: skip
    rendered = [
        f"{codes}: {fix}"
        for codes, rule in _every_doctor_rule()
        if _defect(fix := doctor_rules.rule_fix(rule, Path(), Path("specs")))
    ]
    assert [*_code_sites(code), *_text_sites(texts), *rendered] == []


def test_the_scans_bite() -> None:
    """The control: each scan above, fed a planted offender, names it — and a clean
    sibling passes (a scan answering "clean" to everything would pass the corpus)."""
    assert _unresolved_paths("sed -i 's/x/y/g' specs/bugs/BUGS.jsonl") == []
    assert _unresolved_paths("git rm dadaia_workspace/features/no_such_feature/doctor.py") == [
        "dadaia_workspace/features/no_such_feature/doctor.py"
    ]
    assert _unresolved_paths("rm -rf .codex/prompts/dead-lane") == [".codex/prompts/dead-lane"]
    assert _unresolved_paths("sed -i '/x/d' --in-place=specs/ghost/atom.md") == [
        "specs/ghost/atom.md"
    ]
    source = (
        'X = f"fix: {DADAIA_BIN} doctor"\n'
        'Step("r", "command", "why", ".dadaia/.venv/bin/dadaia doctor")\n'
        'Y = "fix: release.py ship --pr <n>"\n'
        'Z = "Run: dadaia doctor"\n'
        'identity_fix = ".dadaia/.venv/bin/dadaia doctor"\n'
        'def make_fix():\n    return "finish the task by hand"\n'
        'raise Refusal("m", "git fetch origin then git push origin")\n'
        'W = "fix: Operator action: run `bugs.py resolve|supersede` on it"\n'
        'OK = "fix: Operator action: open the PR"\n'
        'raise Refusal("m", "git push origin")\n'
    )
    assert _code_sites({"m.py": ast.parse(source)}) == [
        f"m.py:{n}" for n in (1, 2, 3, 4, 5, 6, 8, 9)
    ]
    shipped = (
        "made by `dadaia public install`\n"
        "`.dadaia/.venv/bin/dadaia nosuchverb`\n"
        "`.dadaia/.venv/bin/dadaia doctor --nosuchflag`\n"
        "`.dadaia/.venv/bin/dadaia doctor --context x` and a bare `dadaia`\n"
        "the `rc-archive` verb\n"
    )
    script = 'fix = git_line(repo, "switch", work)\nfix = f"git -C {repo} switch {work}"\n'
    assert _text_sites({"dadaia_workspace/public/s.py": script}) == [
        "dadaia_workspace/public/s.py:2"
    ]
    assert _text_sites({"dadaia_workspace/public/x.md": shipped}) == [
        f"dadaia_workspace/public/x.md:{n}" for n in (1, 2, 3, 5)
    ]
    assert _text_sites({"docs/getting-started.md": "release-please\n"}) == [
        "docs/getting-started.md:1"
    ]
