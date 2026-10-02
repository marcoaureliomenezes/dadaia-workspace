"""Intent: CONTRACT — 0.4.7 FR2 (T-047-14): every BLOCK carries one executable fix line.

The anti-stall invariant. A BLOCK that does not say, in one line, the exact command that
clears it is a Stall: the agent is stopped with no way out, and the bug ledger's gate
family (``sdd-gate-memory-phase-resolves-empty…``, ``minted-feature-branch-without-live-
release-blocks-every-memory-write``, ``context-bind-implementation-requires-release-id-
stall-when-none-live``) is what that costs. Worse still is a BLOCK whose own fix is
blocked by another enforcement point — a closed loop.

Every enforcement point is driven through its PUBLIC seam and its message asserted to
carry exactly one ``fix: <command>`` line; that command is then fed back through
``pre_gate.evaluate_payload`` as a Bash payload and asserted ALLOW.

size: SMALL.
"""

from __future__ import annotations

import ast
import os
import re
import shlex
import subprocess
import sys
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path, PurePosixPath
from typing import Any

import pytest

from dadaia_workspace.core import doctor_rules
from dadaia_workspace.core.cli_line import fix_line
from dadaia_workspace.core.gitflow import DEFAULT
from dadaia_workspace.features.chokepoints import push_gate_decision
from dadaia_workspace.features.chokepoints.branch_policy import parse_push_stdin
from dadaia_workspace.features.specs.canon import canon_violations
from dadaia_workspace.hooks import pre_gate
from dadaia_workspace.infrastructure.git_objects import GitSubprocessObjectReader
from tests.fakes import gate_fixes
from tests.fixtures.real_git import PushRepo
from tests.fixtures.stores import own_venv_python, own_venv_workspace

_FIX_LINE_RE = re.compile(r"^fix: (\S.*)$", re.MULTILINE)

#: The workspace CLI as a fix line spells it, relative to its root (``fix_line``).
_CLI = fix_line(Path())

_SHA_A = "a" * 40
_ZERO = "0" * 40
_SHA_B = "b" * 40


def _the_fix(message: str) -> str:
    """Return the ONE ``fix:`` command carried by *message* (fails the test otherwise)."""
    assert message, "a BLOCK with an empty message is a Stall"
    fixes = _FIX_LINE_RE.findall(message)
    assert len(fixes) == 1, f"expected exactly one 'fix:' line, got {fixes} in:\n{message}"
    return fixes[0]


def _assert_one_command(command: str) -> None:
    """sa-fix-lines-not-built-by-cli-line#S3: a fix is ONE command — no ``&&`` chain, no prose."""
    for marker in ("&&", " or ", " then "):
        assert marker not in command, f"a fix line is ONE command — {marker!r}:\n{command}"


def _assert_runnable(command: str) -> None:
    """The fix must itself pass the PreToolUse gate — a blocked fix is a closed loop."""
    block = pre_gate.evaluate_payload({"tool_name": "Bash", "tool_input": {"command": command}})
    assert block is None, f"the fix command is itself BLOCKED (a Stall):\n{command}\n{block}"


def assert_block_carries_a_runnable_fix(message: str) -> None:
    command = _the_fix(message)
    _assert_one_command(command)
    _assert_runnable(command)


# ── the real `dadaia doctor` output (undo of b50f0c97: the printer is exercised) ──


def test_the_real_doctor_prints_every_fix_as_one_whole_runnable_line(tmp_path: Path) -> None:
    """The printer, not a synthetic render: a workspace finding (an expired tmp entry), an
    error-class specs finding (FIXED-1 on a symlinked QUALITY.md) and a ledger finding
    (a malformed BACKLOG.json), through a `dadaia doctor` subprocess at a 61-char root with
    COLUMNS unset: exit 1, and every `fix:` line is one line opening with an executable."""
    import os
    import shutil
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
    env["PYTHONPATH"] = os.pathsep.join(
        [str(Path(__file__).resolve().parents[2]), *site.getsitepackages()]
    )

    run = subprocess.run(
        [
            str(own_venv_python(ws)),
            "-m",
            "dadaia_workspace",
            "doctor",
            "--specs-dir",
            str(specs),
        ],
        cwd=ws,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )

    assert run.returncode == 1, run.stdout + run.stderr
    lines = run.stdout.splitlines()
    codes = {line.split(" ", 1)[0] for line in lines}
    assert {"WS-tmp-expired", "FIXED-1", "LEDGER-BACKLOG-SCHEMA"} <= codes, run.stdout
    fixes = [line.removeprefix("fix: ") for line in lines if line.startswith("fix: ")]
    assert fixes, run.stdout
    for fix in fixes:  # two shapes, no third (sa-unfixable-doctor-findings-say-doctor-fix#S1)
        if fix.startswith("Operator action: "):
            assert re.search(r"\s(/|\w:\\)\S", fix) and not re.search(r"<[^<>]+>", fix), fix
            continue
        argv0 = shlex.split(fix)[0]
        assert Path(argv0).is_file() or shutil.which(argv0), (
            f"not an executable: {fix}\n{run.stdout}"
        )
    # Whole lines: a wrapped fix would leave a continuation line that is neither a finding
    # (`CODE verdict …`) nor a `fix:` line.
    assert [ln for ln in lines if ln and not re.match(r"(fix: |[A-Z][A-Za-z0-9-]+ )", ln)] == []


# ── (producer, trigger): every refusal the gate and the push gate emit ──────────


@pytest.fixture
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    (tmp_path / ".dadaia" / "states").mkdir(parents=True)
    (tmp_path / ".dadaia" / "states" / "spec_contexts.json").write_text("{}", encoding="utf-8")
    (tmp_path / ".dadaia" / "sessions").mkdir(parents=True)
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _write(path: Path) -> dict[str, Any]:
    return {"tool_name": "Write", "tool_input": {"file_path": str(path)}}


def _gate(ws: Path, rel: str) -> str | None:
    return pre_gate.evaluate_payload(_write(ws / rel))


def _bare_cli(ws: Path) -> str | None:
    """The fix names the RUNNING CLI (ADR 0045): a host venv outside any workspace (CI's
    poetry venv) proves no expectation pins the instance's own spelling."""
    sys.prefix = str(ws.parent / "host-venv")
    return pre_gate.evaluate_payload(
        {"tool_name": "Bash", "tool_input": {"command": "dadaia doctor --context x"}}
    )


def _push(ws: Path, line: str = "", files: dict[str, str] | None = None, **kwargs: Any) -> str:
    """A real work clone (``main`` published, one unpublished commit), pushing *line*."""
    (ws / "clone").mkdir()
    repo = PushRepo(ws / "clone")
    repo.commit({"README.md": "r\n"})
    repo.publish("main")
    sha = repo.commit(files or {"a.md": "a\n"})
    refs = (
        parse_push_stdin(line.format(sha=sha, other=_SHA_B, zero=_ZERO, a=_SHA_A))[0]
        if line
        else []
    )
    decision = push_gate_decision(
        refs,
        gitflow=DEFAULT,
        fixes=replace(gate_fixes(), head="feature/0.0.1"),
        object_source=GitSubprocessObjectReader(),
        repo=repo.path,
        canon_violations_fn=canon_violations,
        **{"malformed_lines": 0, "denylist_terms": (), **kwargs},
    )
    assert not decision.allowed, "expected a refusal"
    return decision.message


_FEATURE = "refs/heads/feature/0.0.1 {sha} refs/heads/feature/0.0.1 {zero}"
_BLOCKS: dict[str, Callable[[Path], str | None]] = {
    "gate-protected-sessions": lambda ws: _gate(ws, ".dadaia/sessions/some-session.json"),
    "gate-protected-projected": lambda ws: _gate(ws, ".dadaia/states/install_ledger.json"),
    "venv-guard-bare-cli": _bare_cli,
    "push-malformed-stdin": lambda ws: _push(ws, malformed_lines=1),
    "push-main": lambda ws: _push(ws, "refs/heads/main {sha} refs/heads/main {other}"),
    "push-develop": lambda ws: _push(ws, "refs/heads/develop {sha} refs/heads/develop {other}"),
    "push-birth-with-content": lambda ws: _push(
        ws, "refs/heads/develop {sha} refs/heads/develop {zero}"
    ),
    "push-invalid-name": lambda ws: _push(ws, "refs/heads/wip/x {sha} refs/heads/wip/x {zero}"),
    "push-not-a-branch-head": lambda ws: _push(ws, "refs/notes/x {sha} refs/notes/x {zero}"),
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
def test_every_block_carries_a_runnable_fix(
    workspace: Path, monkeypatch: pytest.MonkeyPatch, block: str
) -> None:
    monkeypatch.setattr(sys, "prefix", sys.prefix)  # restored after _bare_cli moves it
    message = _BLOCKS[block](workspace)
    assert message is not None, f"{block}: expected a BLOCK"
    assert_block_carries_a_runnable_fix(message)


def test_the_root_block_fix_runs_from_a_repo_cwd_and_never_writes_the_exceptions_file(
    workspace: Path,
) -> None:
    """sa-gate-allows-root-entries-the-reaper-moves#E7: the root BLOCK's fix, executed
    verbatim from ``repos/demo`` (twice: the zone usually exists), exits 0 and leaves the
    exceptions file unwritten."""
    block = pre_gate.evaluate_payload(_write(workspace / "junk.txt"))
    assert block is not None
    assert_block_carries_a_runnable_fix(block)
    (workspace / "repos" / "demo").mkdir(parents=True)
    runs = [
        subprocess.run(_the_fix(block), shell=True, cwd=workspace / "repos" / "demo", check=False)
        for _ in range(2)
    ]
    assert [r.returncode for r in runs] == [0, 0]
    assert (workspace / ".dadaia" / "tmp").is_dir()
    assert not (workspace / ".dadaiaignore").exists()  # the fix never writes the operator's file


# ── dadaia doctor (exit 1) ──────────────────────────────────────────────────────


def _every_doctor_rule() -> list[tuple[str, doctor_rules.Rule[Any]]]:
    from dadaia_workspace.features.backlog.doctor import RULES as BACKLOG_RULES
    from dadaia_workspace.features.spec_context.doctor import workspace_rules
    from dadaia_workspace.features.specs.doctor_adr import LEDGER_RULES as ADR_LEDGER_RULES
    from dadaia_workspace.features.specs.rules import RULES as SPECS_RULES

    rules: list[tuple[str, doctor_rules.Rule[Any]]] = []
    for rule in (
        *workspace_rules(expired_only=False),
        *SPECS_RULES,
        *BACKLOG_RULES,
        *ADR_LEDGER_RULES,
    ):
        rules.append(("/".join(rule.codes), rule))
    return rules


_DOCTOR_RULES = _every_doctor_rule()


def _cli_tree_has(tokens: list[str]) -> bool:
    """True when ``tokens`` (the words after the dadaia binary, up to the first option
    or placeholder) walk the live Typer command tree down to a leaf command."""
    import typer.main

    from dadaia_workspace.cli.main import app

    root = typer.main.get_command(app)
    ctx = root.make_context("dadaia", [], resilient_parsing=True)
    cmd: Any = root
    for token in tokens:
        if token.startswith(("-", "<")):
            break
        subcommands = cmd.list_commands(ctx) if hasattr(cmd, "list_commands") else []
        if token not in subcommands:
            return False
        cmd = cmd.get_command(ctx, token)
    return not (hasattr(cmd, "list_commands") and cmd.list_commands(ctx))


_REPO_ROOT = Path(__file__).resolve().parents[2]
_PUBLIC_SKILLS = _REPO_ROOT / "dadaia_workspace" / "public" / "skills"


def _script_target(command: str) -> tuple[Path, str] | None:
    """The (shipped script, subcommand) a ``python3 …/scripts/x.py <verb>`` fix names."""
    tokens = command.split()
    if tokens[0] != _VENV_PYTHON or not tokens[1].startswith(_SKILLS):
        return None
    relative = tokens[1].removeprefix(_SKILLS)
    verb = next((token for token in tokens[2:] if not token.startswith(("-", "<"))), "")
    return _PUBLIC_SKILLS / relative, verb


def _fix_lines() -> list[tuple[str, str]]:
    """Every doctor rule's fix line (a ledger's operator action is proven in
    test_workspace_fix_lines_clear_their_finding)."""
    return [
        (codes, doctor_rules.rule_fix(rule, Path()))
        for codes, rule in _DOCTOR_RULES
        if rule.fix_help
    ]


_FIX_LINES = _fix_lines()

#: The installed skill tree maps to the `public/skills/` source; the venv-rooted binary is
#: resolved by the CLI arm, never as a file.
_INSTALLED_SKILL_PREFIX = ".agents/skills/"
_VENV_BINARY_PREFIX = ".dadaia/"
#: ``script_line``'s two absolute heads, as literals of the running environment: the
#: interpreter running now, normalized as `sys.prefix` is (a `../` launch path keeps its dots in
#: `sys.executable`), and the skills this package ships (never a derived workspace).
_VENV_PYTHON = Path(os.path.normpath(sys.executable)).as_posix()
_SKILLS = _PUBLIC_SKILLS.as_posix() + "/"

_PLACEHOLDER_RE = re.compile(r"<[^>]*>")
_FLAG_VALUE_RE = re.compile(r"^--[\w-]+=")


def _command_tokens(command: str) -> list[str]:
    """Tokens with quoting intact: a quoted ``sed`` script is never a path, a bare path is."""
    lexer = shlex.shlex(command, posix=False)
    lexer.whitespace_split = True
    return list(lexer)


def _path_token(token: str) -> str | None:
    """An unquoted token with a slash is a path (no root list to go stale, 0.4.7 c8 review
    MEDIUM-3); a ``--flag=value`` carries its path in the value."""
    if not token or token.startswith(("'", '"')):
        return None
    token = _FLAG_VALUE_RE.sub("", token)
    if token.startswith(("-", ">", "&", "|")) or "/" not in token:
        return None
    return token


def _tracked_dirs() -> frozenset[str]:
    """Every tracked directory — git's answer, never the working tree's, which differs
    between a local checkout and CI's (0.4.7 c8 review MEDIUM-3)."""
    listed = subprocess.run(  # noqa: S603
        ["git", "-C", str(_REPO_ROOT), "ls-files", "-z"],  # noqa: S607
        capture_output=True,
        text=True,
        check=True,
        timeout=60,
    ).stdout
    dirs: set[str] = {""}
    for tracked in listed.split("\0"):
        if not tracked:
            continue
        parts = PurePosixPath(tracked).parts
        for depth in range(1, len(parts)):
            dirs.add(PurePosixPath(*parts[:depth]).as_posix())
    return frozenset(dirs)


def _resolvable_prefix(token: str) -> str:
    """The deepest placeholder-free directory the token names: a fix creates, edits or
    deletes its leaf, so only the directory holding it must exist."""
    if token.startswith(_INSTALLED_SKILL_PREFIX):
        relative = token.split(_INSTALLED_SKILL_PREFIX, 1)[1]
        segments = ("dadaia_workspace", "public", "skills", *relative.split("/"))
    else:
        segments = tuple(token.split("/"))
    kept: list[str] = []
    for segment in segments:
        if _PLACEHOLDER_RE.search(segment):
            break
        kept.append(segment)
    if len(kept) == len(segments):
        kept = kept[:-1]  # the leaf is created, edited or deleted by the fix itself
    return PurePosixPath(*kept).as_posix() if kept else ""


def _canon_dirs() -> frozenset[str]:
    """Every directory the specs canon guarantees, as `specs/`-rooted posix strings —
    a consumer's tree carries these even when this repo's own does not."""
    from dadaia_workspace.core.workspace_layout import SPECS_CANON

    dirs: set[str] = {"specs"}
    for entry in SPECS_CANON:
        parts = PurePosixPath(entry.shape).parts
        for depth in range(len(parts)):
            dirs.add(PurePosixPath("specs", *parts[:depth]).as_posix())
    return frozenset(dirs)


_CANON_DIRS = _canon_dirs()
_TRACKED_DIRS = _tracked_dirs()


def _unresolved_paths(command: str) -> list[str]:
    """Every path token in *command* whose directory is neither tracked in this repo nor
    a directory the specs canon guarantees."""
    unresolved: list[str] = []
    for raw in _command_tokens(command):
        if raw == _VENV_PYTHON:
            continue  # the running interpreter: an executable, not a repo path
        raw = raw.removeprefix(_REPO_ROOT.as_posix() + "/")
        if raw.startswith(_VENV_BINARY_PREFIX):
            continue  # the venv-rooted binary is resolved by the CLI arm, not as a file
        token = _path_token(raw)
        if token is None:
            continue
        target = _resolvable_prefix(token)
        if target not in _TRACKED_DIRS and target not in _CANON_DIRS:
            unresolved.append(token)
    return unresolved


_SCRIPT_FIXES = [(c, cmd) for c, cmd in _FIX_LINES if "/scripts/" in cmd]


@pytest.mark.parametrize(("codes", "command"), _SCRIPT_FIXES, ids=[c for c, _ in _SCRIPT_FIXES])
def test_every_ledger_fix_runs_its_script_by_absolute_path(codes: str, command: str) -> None:
    """Intent: sa-fix-lines-not-built-by-cli-line#S8 — a ledger/rules fix names the venv
    interpreter and the script by absolute path (``script_line``), so it runs from any cwd."""
    interpreter, script = shlex.split(command)[:2]
    assert interpreter == _VENV_PYTHON
    assert Path(script).is_absolute() and Path(script).is_file(), script


def test_the_bug_script_is_one_ledger_row() -> None:
    """Intent: sa-fix-lines-not-built-by-cli-line#S8, sa-ledger-script-paths-in-two-tables —
    bugs.py is named by its one LEDGER_SCRIPTS row."""
    from dadaia_workspace.infrastructure.ledger_scripts import BUGS_SCRIPT, LEDGER_SCRIPTS

    assert BUGS_SCRIPT in LEDGER_SCRIPTS
    bugs = f"{_SKILLS}dd-bug-resolution/scripts/bugs.py"
    assert dict(_FIX_LINES)["SPEC-DOC-041"] == f"{_VENV_PYTHON} {bugs} archive --specs <specs>"


@pytest.mark.parametrize(("codes", "command"), _FIX_LINES, ids=[c for c, _ in _FIX_LINES])
def test_every_fix_target_resolves_on_disk(codes: str, command: str) -> None:
    """ONE rule for every fix line (0.4.7 c8 review F7; bug
    backlog-doctor-fix-names-missing-update-verb): every path token resolves to a directory
    this repo tracks or the specs canon guarantees; a ``dadaia`` fix walks the live command
    tree to a leaf; a skill-script fix names a shipped script whose subcommand takes ``--help``.
    """
    unresolved = _unresolved_paths(command)
    assert unresolved == [], (
        f"{codes}: fix line names a path neither this repo nor the specs canon "
        f"carries: {unresolved} in {command!r}"
    )

    if command.startswith(_CLI) or command.startswith("dadaia "):
        tokens = command.split()[1:]
        assert _cli_tree_has(tokens), f"{codes}: no such verb: {command!r}"
        return
    target = _script_target(command)
    if target is None:
        return
    script, verb = target
    assert script.is_file(), f"{codes}: fix line names a script this repo does not ship: {script}"
    assert verb, f"{codes}: a script fix line names no subcommand: {command!r}"
    help_run = subprocess.run(  # noqa: S603
        [sys.executable, str(script), verb, "--help"],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert help_run.returncode == 0, f"{codes}: {script.name} rejects {verb!r}: {help_run.stderr}"


def test_the_path_rule_bites_a_fix_naming_a_directory_nobody_ships() -> None:
    """The control: a resolver classifying every token as "not a path" would pass the corpus."""
    assert _unresolved_paths("sed -i 's/<session id>/<redacted>/g' specs/bugs/BUGS.jsonl") == []
    assert _unresolved_paths("git mv specs/audits/<name> specs/audits/<YYYYMMDD>-<slug>") == []
    assert _unresolved_paths("printf '%s\\n' '# <title>' >> specs/memory/<document>.md") == []
    assert _unresolved_paths("sed -i '\\|x|d' specs/nowhere/<id>/SPEC.md") == [
        "specs/nowhere/<id>/SPEC.md"
    ]
    assert _unresolved_paths("git rm dadaia_workspace/features/no_such_feature/doctor.py") == [
        "dadaia_workspace/features/no_such_feature/doctor.py"
    ]
    assert _unresolved_paths("rm -rf .codex/prompts/dead-lane") == [".codex/prompts/dead-lane"]
    assert _unresolved_paths("sed -i '/x/d' --in-place=specs/ghost/atom.md") == [
        "specs/ghost/atom.md"
    ]


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


def _script_modules() -> list[Path]:
    return sorted(_PUBLIC_SKILLS.glob("*/scripts/*.py"))


_SCRIPT_MODULES = _script_modules()


@pytest.mark.parametrize(
    "module", _SCRIPT_MODULES, ids=[f"{m.parts[-3]}/{m.name}" for m in _SCRIPT_MODULES]
)
def test_every_script_fix_line_names_its_folders_entry_script(module: Path) -> None:
    """0.4.7 review fold (F3): every `fix:` literal naming a `.py` file, and every `SCRIPT`
    constant a `Refusal` fix is built from, names its folder's entry script — never a sibling
    module with no ``__main__`` (an un-runnable fix is a Stall)."""
    skill = module.parts[-3]
    entry = _ENTRY_SCRIPTS[skill]
    text = module.read_text(encoding="utf-8")
    for body in _LITERAL_FIX_RE.findall(text):
        assert "__file__" not in body, f"{module.name}: {body!r}"
        assert all(n.endswith(entry) for n in _NAMED_SCRIPT_RE.findall(body)), (
            f"{module.name}: {body!r}"
        )
    for named in _SCRIPT_CONST_RE.findall(text):
        assert named == entry, f"{module.name}: SCRIPT names {named!r}, not {entry!r}"


# ── the law never names a verb the tooling dropped ──────────────────────────────

#: Dead law words: retired release verbs, rc-N, bug-resolve-law-names-flags-the-script-does-not-have
_DEAD_RELEASE_VOCABULARY = re.compile(r"rc-archive|release\.py (fold|archive)|rc-N|resolve` carrying")  # fmt: skip

#: The law: the shipped surface, product memory and the glossary; history keeps its words.
_LAW_ROOTS = (
    _REPO_ROOT / "dadaia_workspace" / "public",
    _REPO_ROOT / "specs" / "memory",
)

_LAW_FILES = (_REPO_ROOT / "CONTEXT.md",)


def _law_files() -> list[Path]:
    roots = [str(root) for root in (*_LAW_ROOTS, *_LAW_FILES)]
    listed = subprocess.run(["git", "ls-files", "-z", "--", *roots], cwd=_REPO_ROOT,
                            capture_output=True, text=True, check=True).stdout  # fmt: skip
    return [_REPO_ROOT / rel for rel in listed.split("\0") if rel and "_archive" not in rel]


def test_no_law_file_names_a_retired_release_verb() -> None:
    """A law naming a verb nobody ships is a Stall (the agent gets `invalid choice` and no fix);
    bug law-file-scan-reads-untracked-bytecode: tracked files only."""
    offenders = [
        f"{path.relative_to(_REPO_ROOT)}:{number}"
        for path in _law_files()
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1)
        if _DEAD_RELEASE_VOCABULARY.search(line)
    ]
    assert not offenders, "\n".join(offenders)


#: `memory.py check` decides only the generated catalog pair; the atoms' schema (tldr
#: length and the rest) is LINT-1's alone. A law line making that script's exit 0 the
#: mark of a finished memory elects a validator that never reads the rule.
_NON_AUTHORITY_DONE = re.compile(r"memory\.py check`? exit 0")


def test_no_shipped_text_makes_memory_py_check_the_memory_done_criterion() -> None:
    """Intent: CONTRACT — bug memory-done-criterion-names-a-script-that-never-validates-atoms.

    The one authority for a valid memory tree is `dadaia doctor` (LINT-1 over the atoms,
    LEDGER-MEMORY over the pair). Product memory is its owner's to re-derive, so this
    scan covers what ships: `public/`, `CONTEXT.md` and `docs/`.
    """
    memory = _REPO_ROOT / "specs" / "memory"
    shipped = [path for path in _law_files() if memory not in path.parents]
    offenders = [
        f"{path.relative_to(_REPO_ROOT)}:{number}"
        for path in [*shipped, *sorted((_REPO_ROOT / "docs").glob("*.md"))]
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1)
        if _NON_AUTHORITY_DONE.search(line)
    ]
    assert not offenders, "\n".join(offenders)


# ── no fix the package prints carries a placeholder or a chain (AC4.4, ADR 0158) ──

#: `<…>` (bar the `<specs>` `rule_fix` fills), an `&&` chain, an `a|b` menu of verbs.
_NOT_ONE_COMMAND_RE = re.compile(r"<(?!specs>)[^<>\n]+>|&&|\w\|\w")
#: A `cli_line` builder's or a fix producer's arguments are fix text.
_FIX_CALL_RE = re.compile(r"(_line|_fix|^script)$")
#: Pending until T-050-149 (2026-10-02), which owns the `ship --pr <n>` sites of these two
#: scripts (release.py:109, _release_phase.py:81) and deletes this entry.
_PENDING_T_050_149 = ("release.py", "_release_phase.py")


def _callee(node: ast.Call) -> str:
    return getattr(node.func, "id", getattr(node.func, "attr", ""))


def _render(node: Any, scope: dict[str, list[Any]], defs: dict[str, Any], depth: int = 0) -> str:
    """The text *node* can print; alternatives and unknown values join as `·`."""
    again = lambda n: _render(n, scope, defs, depth + 1) if depth < 12 else "·"  # noqa: E731
    match node:
        case ast.Constant(value=str() as text):
            return text
        case ast.JoinedStr(values=parts):
            return "".join(map(again, parts))
        case ast.List(elts=parts) | ast.Tuple(elts=parts) | ast.Dict(values=parts) | ast.BoolOp(values=parts):  # fmt: skip
            return "·".join(map(again, parts))
        case ast.FormattedValue(value=v) | ast.Starred(value=v) | ast.Subscript(value=v):
            return again(v)
        case ast.ListComp(elt=v) | ast.GeneratorExp(elt=v):
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
        case ast.Call(func=ast.Attribute(value=receiver)) if not isinstance(receiver, ast.Name):
            return again(receiver)
        case ast.Call() if _FIX_CALL_RE.search(_callee(node)) or _callee(node)[:1].isupper():
            return " ".join(map(again, [*node.args, *(k.value for k in node.keywords)]))
        case ast.Call() if _callee(node) in defs:
            return "·".join(again(n.value) for n in ast.walk(defs[_callee(node)]) if isinstance(n, ast.Return))  # fmt: skip
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


def _placeholder_sites() -> list[str]:
    """`file:line` of each fix a package module or a `public/skills` script can print that
    is not one command: a `fix:` text, a `fix` parameter's argument, a builder's arguments."""
    modules = sorted((_REPO_ROOT / "dadaia_workspace").rglob("*.py"))
    trees = {path: ast.parse(path.read_text(encoding="utf-8")) for path in modules}
    fix_param = {  # each callable taking `fix` (a class: its __init__), and its position
        (owner.name if fn.name == "__init__" else fn.name): names.index("fix")
        for owner in (n for t in trees.values() for n in ast.walk(t))
        for fn in (owner.body if isinstance(owner, ast.ClassDef) else [owner])
        if isinstance(fn, ast.FunctionDef)
        and "fix" in (names := [a.arg for a in fn.args.args if a.arg != "self"])
    }
    sites: set[str] = set()
    for path, tree in trees.items():
        defs = {n.name: n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
        prose = {id(v.value) for n in ast.walk(tree) if isinstance(n, ast.JoinedStr)  # `Run '…'`
                 and not any("fix: " in str(getattr(v, "value", "")) for v in n.values)
                 for v in n.values if isinstance(v, ast.FormattedValue)
                 and isinstance(v.value, ast.Call) and _callee(v.value).endswith("_line")}  # fmt: skip
        module = _scope(tree, {})
        for unit in [tree, *defs.values()]:
            scope = module if unit is tree else _scope(unit, module)
            for node in ast.walk(unit):
                fixes: list[str] = []
                if isinstance(node, ast.Call):
                    at = fix_param.get(_callee(node), -1)
                    carried = [*node.args[at : at + 1 if at >= 0 else 0],
                               *(k.value for k in node.keywords if k.arg == "fix")]  # fmt: skip
                    if _FIX_CALL_RE.search(_callee(node)) and id(node) not in prose:
                        carried.append(node)
                    fixes = [_render(c, scope, defs) for c in carried]
                elif isinstance(node, ast.Constant | ast.JoinedStr | ast.BinOp):
                    fixes = _render(node, scope, defs).split("fix: ")[1:]
                for fix in fixes:
                    pending = path.name in _PENDING_T_050_149 and "--pr <n>" in fix
                    if _NOT_ONE_COMMAND_RE.search(fix) and not pending:
                        sites.add(f"{path.relative_to(_REPO_ROOT)}:{node.lineno}")
    return sorted(sites)


def test_no_fix_the_package_prints_carries_a_placeholder_or_a_chain() -> None:
    """Intent: CONTRACT — AC4.4 (DEL fix-lines-are-not-one-runnable-command, ADR 0158):
    every fix the package or a skill script prints, literal or assembled, and every doctor
    rule's fix rendered by `rule_fix`, is its real value or `Operator action: <one act>` —
    no `<…>`, no `&&`, no `a|b` menu."""
    rendered = [
        f"{codes}: {fix}"
        for codes, rule in _DOCTOR_RULES
        if _NOT_ONE_COMMAND_RE.search(fix := doctor_rules.rule_fix(rule, Path(), Path("specs")))
    ]
    assert [*_placeholder_sites(), *rendered] == []
