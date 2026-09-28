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

import re
import shlex
import subprocess
import sys
from collections.abc import Iterable
from dataclasses import replace
from pathlib import Path, PurePosixPath
from typing import Any

import pytest

from dadaia_workspace.core import doctor_rules
from dadaia_workspace.core.cli_line import fix_line
from dadaia_workspace.core.gitflow import DEFAULT
from dadaia_workspace.core.platform import PLATFORM
from dadaia_workspace.features.chokepoints import push_gate_decision
from dadaia_workspace.features.chokepoints.branch_policy import PushRef, parse_push_stdin
from dadaia_workspace.features.specs.canon import canon_violations
from dadaia_workspace.hooks import pre_gate
from dadaia_workspace.infrastructure.git_objects import GitSubprocessObjectReader
from tests.fakes import gate_fixes
from tests.fixtures.real_git import PushRepo

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


def _isolated_workspace(tmp_path: Path) -> Path:
    """A workspace at a >=61-char root whose OWN venv runs the CLI: a pyvenv.cfg and a
    symlinked base interpreter (no install), so the doctor never resolves another root."""
    ws = tmp_path / ("w" * max(1, 61 - len(str(tmp_path))))
    venv = ws / ".dadaia" / ".venv"
    tools = venv / PLATFORM.venv_scripts_dir  # the layout the doctor prints: bin/ or Scripts/*.exe
    tools.mkdir(parents=True)
    base = Path(sys.executable).resolve()
    (tools / f"python{PLATFORM.venv_exe_suffix}").symlink_to(base)
    (tools / f"dadaia{PLATFORM.venv_exe_suffix}").write_text("#!/bin/sh\n", encoding="utf-8")
    (tools / f"dadaia{PLATFORM.venv_exe_suffix}").chmod(0o755)
    (venv / "pyvenv.cfg").write_text(f"home = {base.parent}\n", encoding="utf-8")
    (ws / ".dadaia" / "states").mkdir()
    (ws / ".dadaia" / "states" / "spec_contexts.json").write_text('{"contexts": []}')
    return ws


def test_the_real_doctor_prints_every_fix_as_one_whole_runnable_line(tmp_path: Path) -> None:
    """The printer, not a synthetic render: a workspace finding (an expired tmp entry), an
    error-class specs finding (FIXED-1 on a symlinked QUALITY.md) and a ledger finding
    (a malformed BACKLOG.json), through a `dadaia doctor` subprocess at a 61-char root with
    COLUMNS unset: exit 1, and every `fix:` line is one line opening with an executable."""
    import os
    import shutil
    import site

    from dadaia_workspace.features.specs import canon

    ws = _isolated_workspace(tmp_path)
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
            str(
                ws
                / ".dadaia"
                / ".venv"
                / PLATFORM.venv_scripts_dir
                / f"python{PLATFORM.venv_exe_suffix}"
            ),
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
            assert re.search(r"(^|\s)/\S", fix) and not re.search(r"<[^<>]+>", fix), fix
            continue
        argv0 = shlex.split(fix)[0]
        assert Path(argv0).is_file() or shutil.which(argv0), f"not an executable: {fix}"
    # Whole lines: a wrapped fix would leave a continuation line that is neither a finding
    # (`CODE verdict …`) nor a `fix:` line.
    assert [ln for ln in lines if ln and not re.match(r"(fix: |[A-Z][A-Za-z0-9-]+ )", ln)] == []


# ── the PreToolUse gate ─────────────────────────────────────────────────────────


@pytest.fixture
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    (tmp_path / ".dadaia" / "states").mkdir(parents=True)
    (tmp_path / ".dadaia" / "states" / "spec_contexts.json").write_text("{}", encoding="utf-8")
    (tmp_path / ".dadaia" / "sessions").mkdir(parents=True)
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _write(path: Path) -> dict[str, Any]:
    return {"tool_name": "Write", "tool_input": {"file_path": str(path)}}


_GATE_BLOCKS: tuple[tuple[str, str], ...] = (
    ("protected-sessions", ".dadaia/sessions/some-session.json"),
    ("protected-projected", ".dadaia/states/install_ledger.json"),  # ledger-decided law
)


@pytest.mark.parametrize(("name", "rel"), _GATE_BLOCKS, ids=[n for n, _ in _GATE_BLOCKS])
def test_gate_block_carries_a_runnable_fix(workspace: Path, name: str, rel: str) -> None:
    block = pre_gate.evaluate_payload(_write(workspace / rel))
    assert block is not None, f"{name}: expected a BLOCK for {rel}"
    assert_block_carries_a_runnable_fix(block)


def test_the_root_block_fix_runs_from_a_repo_cwd_and_never_writes_the_exceptions_file(
    workspace: Path,
) -> None:
    """sa-gate-allows-root-entries-the-reaper-moves#E7: the root BLOCK's fix, executed
    verbatim from ``repos/demo``, exits 0 and leaves the exceptions file unwritten."""
    block = pre_gate.evaluate_payload(_write(workspace / "junk.txt"))
    assert block is not None
    assert_block_carries_a_runnable_fix(block)
    (workspace / "repos" / "demo").mkdir(parents=True)

    done = subprocess.run(
        _the_fix(block), shell=True, cwd=workspace / "repos" / "demo", check=False
    )

    again = subprocess.run(  # the usual case: the zone already exists
        _the_fix(block), shell=True, cwd=workspace / "repos" / "demo", check=False
    )

    assert done.returncode == 0
    assert again.returncode == 0
    assert (workspace / ".dadaia" / "tmp").is_dir()
    assert not (workspace / ".dadaia" / "states" / "instance_exceptions.txt").exists()


def test_venv_guard_block_carries_a_runnable_fix(
    workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The fix names the RUNNING CLI (ADR 0045); a host venv outside any workspace (CI's
    poetry venv) proves no expectation pins the instance's own spelling."""
    monkeypatch.setattr(sys, "prefix", str(workspace.parent / "host-venv"))
    block = pre_gate.evaluate_payload(
        {"tool_name": "Bash", "tool_input": {"command": "dadaia doctor --context x"}}
    )
    assert block is not None
    assert_block_carries_a_runnable_fix(block)


# ── ci push-gate-check ──────────────────────────────────────────────────────────


@pytest.fixture
def pushed(tmp_path: Path) -> tuple[PushRepo, str]:
    """A real work clone: ``main`` published on origin, one unpublished commit on HEAD."""
    repo = PushRepo(tmp_path)
    repo.commit({"README.md": "r\n"})
    repo.publish("main")
    return repo, repo.commit({"a.md": "a\n"})


def _decide(
    repo: PushRepo,
    refs: list[PushRef],
    *,
    malformed_lines: int = 0,
    denylist_terms: Iterable[tuple[str, str]] = (),
) -> str:
    decision = push_gate_decision(
        refs,
        gitflow=DEFAULT,
        fixes=replace(gate_fixes(), head="feature/0.0.1"),
        object_source=GitSubprocessObjectReader(),
        repo=repo.path,
        canon_violations_fn=canon_violations,
        malformed_lines=malformed_lines,
        denylist_terms=denylist_terms,
    )
    assert not decision.allowed, "expected a refusal"
    return decision.message


def _refs(*lines: str) -> list[PushRef]:
    return parse_push_stdin("\n".join(lines))[0]


def test_push_gate_malformed_stdin_carries_a_runnable_fix(pushed: tuple[PushRepo, str]) -> None:
    assert_block_carries_a_runnable_fix(_decide(pushed[0], [], malformed_lines=1))


@pytest.mark.parametrize(
    ("name", "line"),
    [
        ("main", "refs/heads/main {sha} refs/heads/main {other}"),
        ("develop", "refs/heads/develop {sha} refs/heads/develop {other}"),
        ("birth-with-content", "refs/heads/develop {sha} refs/heads/develop {zero}"),
        ("invalid-name", "refs/heads/wip/x {sha} refs/heads/wip/x {zero}"),
        ("not-a-branch-head", "refs/notes/x {sha} refs/notes/x {zero}"),
        ("refspec", "refs/heads/feature/0.0.1 {sha} refs/heads/develop {zero}"),
    ],
)
def test_push_gate_branch_policy_refusals_carry_a_runnable_fix(
    pushed: tuple[PushRepo, str], name: str, line: str
) -> None:
    repo, sha = pushed
    ref = line.format(sha=sha, other=_SHA_B, zero=_ZERO)
    assert_block_carries_a_runnable_fix(_decide(repo, _refs(ref)))


def _feature_ref(sha: str) -> list[PushRef]:
    return _refs(f"refs/heads/feature/0.0.1 {sha} refs/heads/feature/0.0.1 {_ZERO}")


def test_push_gate_specs_canon_refusal_carries_a_runnable_fix(
    pushed: tuple[PushRepo, str],
) -> None:
    repo, _ = pushed
    sha = repo.commit({"specs/not-a-canon-entry.md": "x\n"})
    assert_block_carries_a_runnable_fix(_decide(repo, _feature_ref(sha)))


def test_push_gate_denylist_refusal_carries_a_runnable_fix(pushed: tuple[PushRepo, str]) -> None:
    repo, _ = pushed
    sha = repo.commit({"b.md": "zz-secret-term\n"})
    message = _decide(repo, _feature_ref(sha), denylist_terms=[("zz-secret-term", "synthetic")])
    assert_block_carries_a_runnable_fix(message)


def test_push_gate_git_read_failure_carries_a_runnable_fix(pushed: tuple[PushRepo, str]) -> None:
    """A sha the repo does not hold: the real object read fails and the gate fails closed."""
    assert_block_carries_a_runnable_fix(_decide(pushed[0], _feature_ref(_SHA_A)))


# ── context heartbeat (exit 1) ──────────────────────────────────────────────────


# ── dadaia doctor (exit 1) ──────────────────────────────────────────────────────


def _every_doctor_rule() -> list[tuple[str, doctor_rules.Rule[Any, Any]]]:
    from dadaia_workspace.features.backlog.doctor import RULES as BACKLOG_RULES
    from dadaia_workspace.features.spec_context.doctor import workspace_rules
    from dadaia_workspace.features.specs.doctor_adr import LEDGER_RULES as ADR_LEDGER_RULES
    from dadaia_workspace.features.specs.rules import RULES as SPECS_RULES

    rules: list[tuple[str, doctor_rules.Rule[Any, Any]]] = []
    for rule in (
        *workspace_rules(expired_only=False),
        *SPECS_RULES,
        *BACKLOG_RULES,
        *ADR_LEDGER_RULES,
    ):
        rules.append(("/".join(rule.codes), rule))
    return rules


_DOCTOR_RULES = _every_doctor_rule()


# ── the live CLI tree, shared by the one fix-line rule below ───────────────────
#
# `test_every_doctor_fix_names_a_verb_the_cli_has` DELETED (0.4.7 c8 review F7). It
# walked the command tree for every fix line opening with the dadaia binary and SKIPPED
# every other shape — the same assertion `test_every_fix_target_resolves_on_disk` makes
# over a superset of the same lines (the doctor rules plus the ledger scripts). Two
# tests, one assertion, and a skip lane that grew as fix shapes did.


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


#: name the INSTALLED path (`.agents/skills/…`, what the operator pastes); the file it
#: names is the one this repo ships.
_REPO_ROOT = Path(__file__).resolve().parents[2]
_PUBLIC_SKILLS = _REPO_ROOT / "dadaia_workspace" / "public" / "skills"
_INSTALLED_PREFIX = ".agents/skills/"


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

#: Scaffold roots a fix line may name that this repo does not carry at that path: the
#: installed skill tree (`.agents/skills/…`, what the operator pastes) maps to the
#: `public/skills/` source this repo ships, and the venv-rooted binary is resolved by the
#: CLI arm below, never as a file.
_INSTALLED_SKILL_PREFIX = ".agents/skills/"
_VENV_BINARY_PREFIX = ".dadaia/"
#: ``script_line``'s two absolute heads, as literals of the running environment: the
#: interpreter running now and the skills this package ships (never a derived workspace).
_VENV_PYTHON = Path(sys.executable).as_posix()
_SKILLS = _PUBLIC_SKILLS.as_posix() + "/"

_PLACEHOLDER_RE = re.compile(r"<[^>]*>")
_FLAG_VALUE_RE = re.compile(r"^--[\w-]+=")


def _command_tokens(command: str) -> list[str]:
    """The command's tokens with their quoting INTACT (``posix=False``).

    Quoting is the signal that separates a path from a ``sed`` script: every fix line
    quotes its script and leaves its paths bare, so ``'s/<session id>/<redacted>/g'``
    keeps its quotes and is skipped while ``specs/bugs/BUGS.jsonl`` is not.
    """
    lexer = shlex.shlex(command, posix=False)
    lexer.whitespace_split = True
    return list(lexer)


def _path_token(token: str) -> str | None:
    """The path *token* names, or ``None`` when it names none.

    An UNQUOTED token containing a slash is a path — there is no suffix list and no
    root list to fall out of date (0.4.7 c8 review MEDIUM-3: ``.codex/…`` and
    ``.kimi-code/…`` fell out of a root list, and ``--in-place=<path>`` out of every
    list at once). A ``--flag=value`` carries its path in the value.
    """
    if not token or token.startswith(("'", '"')):
        return None
    token = _FLAG_VALUE_RE.sub("", token)
    if token.startswith(("-", ">", "&", "|")) or "/" not in token:
        return None
    return token


def _tracked_dirs() -> frozenset[str]:
    """Every directory the TRACKED tree carries, as repo-relative posix strings.

    The oracle is `git ls-files`, never `iterdir()` of the working tree (0.4.7 c8
    review MEDIUM-3): this checkout carries untracked `.claude/` and
    `.import_linter_cache/` directories that CI's does not, so a filesystem oracle
    answered differently on two machines for the same commit.
    """
    import subprocess  # noqa: PLC0415 — the tracked tree is git's answer, not the FS's

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
    """The deepest placeholder-free DIRECTORY the token names, as a repo-relative
    posix string.

    A fix creates, edits or deletes its leaf — `git rm specs/ACTIVE.md` names a file
    that must NOT exist — so the leaf itself is never required; the directory that
    holds it is. Everything from the first `<placeholder>` segment down is unknowable
    and drops away with it.
    """
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
    """ONE rule for every fix line, whatever shape it takes (0.4.7 c8 review F7).

    A ``fix:`` line is a free string — nothing tied it to a file or a verb that exists.
    Two Stalls came of that: ``backlog-doctor-fix-names-missing-update-verb`` (BL-SCHEMA
    and friends handed back ``dadaia backlog update``, a verb the CLI had dropped) and,
    after the ledger verbs moved to skill scripts, a fix line naming a path nobody
    ships. Both resolve HERE, and no shape is exempt: a ``dadaia`` fix walks the live
    command tree; a skill-script fix must exist under ``public/skills/*/scripts/`` with
    a subcommand that accepts ``--help``; and EVERY fix line — ``sed``, ``git mv``,
    ``printf`` included — has each path token it names resolved to a directory this
    repo ships or the specs canon guarantees. The membership allowlist that used to
    excuse the shell-command shapes is gone: it was a second rule whose only job was to
    let a row skip the first one.
    """
    import subprocess  # noqa: PLC0415 — a contract test executes the real script

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
    """The control: without it, a resolver that silently classified every token as
    "not a path" would pass the whole corpus and detect nothing.

    A ``sed`` script is not a path; a real path under a directory neither this repo nor
    the canon carries is — this is exactly the row the deleted allowlist waved through.
    """
    assert _unresolved_paths("sed -i 's/<session id>/<redacted>/g' specs/bugs/BUGS.jsonl") == []
    assert _unresolved_paths("git mv specs/audits/<name> specs/audits/<YYYYMMDD>-<slug>") == []
    assert _unresolved_paths("printf '%s\\n' '# <title>' >> specs/memory/<document>.md") == []
    assert _unresolved_paths("sed -i '\\|x|d' specs/nowhere/<id>/SPEC.md") == [
        "specs/nowhere/<id>/SPEC.md"
    ]
    assert _unresolved_paths("git rm dadaia_workspace/features/no_such_feature/doctor.py") == [
        "dadaia_workspace/features/no_such_feature/doctor.py"
    ]
    # c8 review MEDIUM-3: a projection root other than .agents/.dadaia, and a path
    # carried as a --flag=<value>. Both used to slip past as "not a path".
    assert _unresolved_paths("rm -rf .codex/prompts/dead-lane") == [".codex/prompts/dead-lane"]
    assert _unresolved_paths("sed -i '/x/d' --in-place=specs/ghost/atom.md") == [
        "specs/ghost/atom.md"
    ]


# ── every script-emitted fix line names its own folder's entry script ───────────

#: The one entry script of each skill that ships scripts — what an operator pastes.
#: A sibling `_module.py` has no `__main__`, so naming it is a Stall with a friendly face.
_ENTRY_SCRIPTS: dict[str, str] = {
    "dd-audit-project": "audit.py",
    "dd-backlog-definition": "backlog.py",
    "dd-bug-resolution": "bugs.py",
    "dd-cli-library": "registry.py",
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
    """A skill script's own `fix:` lines must name the script the operator can run.

    0.4.7 review fold (F3): `backlog.py subjects` printed
    ``fix: _backlog_subjects.py subjects …`` — a sibling module with no ``__main__``.
    The command was un-runnable, so the UNRESOLVED exit was a Stall. Every `fix:`
    literal that NAMES a `.py` file, and every `SCRIPT` constant a `Refusal` fix is
    built from, must name the entry script of the folder it is written in.
    """
    skill = module.parts[-3]
    entry = _ENTRY_SCRIPTS[skill]
    text = module.read_text(encoding="utf-8")
    for body in _LITERAL_FIX_RE.findall(text):
        assert "__file__" not in body, (
            f"{skill}/{module.name}: a fix line built from this module's own `__file__` "
            f"names the module, not the entry script {entry} — got {body!r}"
        )
        for named in _NAMED_SCRIPT_RE.findall(body):
            assert named.endswith(entry), (
                f"{skill}/{module.name}: a fix line names {entry}, never a sibling "
                f"module with no __main__ — got {named!r} in {body!r}"
            )
    for named in _SCRIPT_CONST_RE.findall(text):
        assert named == entry, f"{module.name}: SCRIPT names {named!r}, not {entry!r}"


# ── the law never names a verb the tooling dropped ──────────────────────────────

#: The retired release vocabulary. `rc-archive`, `fold` and `archive` were verbs;
#: `rc-N/` was the folder they wrote. None of the three exists: a closed candidate's
#: trio is overwritten in place and git is the archive.
_DEAD_RELEASE_VOCABULARY = re.compile(r"rc-archive|release\.py fold|release\.py archive|rc-N")

#: Where the law lives: the shipped AI-entity surface, the product's memory, and the
#: glossary every one of them borrows its nouns from. History (`_archive/`, the archive
#: folders a retired verb wrote, CHANGELOG.md) keeps its own words and is never rewritten.
_LAW_ROOTS = (
    _REPO_ROOT / "dadaia_workspace" / "public",
    _REPO_ROOT / "specs" / "memory",
)

#: Single law FILES outside those roots.
_LAW_FILES = (_REPO_ROOT / "CONTEXT.md",)


def _law_files() -> list[Path]:
    # Tracked files only: ignored bytecode is not law, and decoding it is a crash.
    roots = [str(root) for root in (*_LAW_ROOTS, *_LAW_FILES)]
    listed = subprocess.run(["git", "ls-files", "-z", "--", *roots], cwd=_REPO_ROOT,
                            capture_output=True, text=True, check=True).stdout  # fmt: skip
    return [_REPO_ROOT / rel for rel in listed.split("\0") if rel and "_archive" not in rel]


def test_no_law_file_names_a_retired_release_verb() -> None:
    """A rule that names a verb nobody ships is a Stall the doctor cannot catch.

    The agent reads the law, runs the verb, gets `invalid choice`, and has no fix line
    to fall back on — the same failure shape the fix-line cases above close from the
    tooling side. This closes it from the prose side: the shipped law and the memory
    atoms may only name vocabulary `release.py --help` still lists.
    """
    offenders = [
        f"{path.relative_to(_REPO_ROOT)}:{number}"
        for path in _law_files()
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1)
        if _DEAD_RELEASE_VOCABULARY.search(line)
    ]
    assert not offenders, (
        "the law names a retired release verb — delete the prose, never the check:\n"
        + "\n".join(offenders)
    )


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
