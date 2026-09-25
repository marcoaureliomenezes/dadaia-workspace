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
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any

import pytest

from dadaia_workspace.core import doctor_rules
from dadaia_workspace.core.cli_line import cli_path
from dadaia_workspace.core.gitflow import DEFAULT
from dadaia_workspace.core.models.git_scan import GitObjectReadError, ScannedObject
from dadaia_workspace.core.platform import PLATFORM
from dadaia_workspace.features.chokepoints import push_gate_decision
from dadaia_workspace.features.chokepoints.branch_policy import PushRef, parse_push_stdin
from dadaia_workspace.features.specs.canon import canon_violations
from dadaia_workspace.hooks import pre_gate

_FIX_LINE_RE = re.compile(r"^fix: (\S.*)$", re.MULTILINE)

#: The workspace CLI as a fix line spells it, relative to its root (``fix_line``).
_CLI = str(cli_path(Path()))

_SHA_A = "a" * 40
_ZERO = "0" * 40
_SHA_B = "b" * 40


def _the_fix(message: str) -> str:
    """Return the ONE ``fix:`` command carried by *message* (fails the test otherwise)."""
    assert message, "a BLOCK with an empty message is a Stall"
    fixes = _FIX_LINE_RE.findall(message)
    assert len(fixes) == 1, f"expected exactly one 'fix:' line, got {fixes} in:\n{message}"
    return fixes[0]


#: The executable tokens a ``fix:`` line may open with. ``dadaia`` bare is admitted only
#: where the venv-rooted path cannot be spelled (a message rendered outside the
#: workspace); everything else is a real binary the operator already has.
_EXECUTABLE_TOKENS: frozenset[str] = frozenset(
    {
        ".dadaia/.venv/bin/dadaia",
        "dadaia",
        "git",
        "gh",
        "rm",
        "mv",
        "mkdir",
        "printf",
        "grep",
        "sed",
        "cp",
        "bash",
        # 0.4.7 FR2: a ledger fix names its skill script, run through the interpreter
        # (Windows has no exec bit), never a retired CLI verb.
        "python3",
    }
)

#: Words that betray prose or a second alternative inside one fix line.
_PROSE_MARKERS: tuple[str, ...] = (" or ", ", then ", " then ", " and then ")


def _assert_one_command(command: str) -> None:
    """FR2's grammar: the fix is ONE executable command, not an instruction.

    A ``&&`` chain of the same tool counts as one command — it is still a single line
    the operator pastes. Prose ("author the missing document", "fix it and then push")
    does not: an agent cannot run it, so the BLOCK is a Stall with a friendly face.
    """
    # Windows fix lines follow MSVCRT quoting (backslash paths), which POSIX shlex eats.
    windows = bool(PLATFORM.venv_exe_suffix)
    head = shlex.split(command, posix=not windows)[0].strip('"')
    if head.endswith(_CLI):  # ``fix_line`` roots the CLI at the workspace it runs in
        head = ".dadaia/.venv/bin/dadaia"
    assert head in _EXECUTABLE_TOKENS, (
        f"a fix line opens with an executable, not prose — got {head!r} in:\n{command}"
    )
    for marker in _PROSE_MARKERS:
        assert marker not in command, (
            f"a fix line is ONE command — {marker!r} makes it two:\n{command}"
        )


def _assert_runnable(command: str) -> None:
    """The fix must itself pass the PreToolUse gate — a blocked fix is a closed loop."""
    block = pre_gate.evaluate_payload({"tool_name": "Bash", "tool_input": {"command": command}})
    assert block is None, f"the fix command is itself BLOCKED (a Stall):\n{command}\n{block}"


def assert_block_carries_a_runnable_fix(message: str) -> None:
    command = _the_fix(message)
    _assert_one_command(command)
    _assert_runnable(command)


# ── the PreToolUse gate ─────────────────────────────────────────────────────────


@pytest.fixture
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    (tmp_path / ".dadaia" / "states").mkdir(parents=True)
    (tmp_path / ".dadaia" / "sessions").mkdir(parents=True)
    monkeypatch.setenv("WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _write(path: Path) -> dict[str, Any]:
    return {"tool_name": "Write", "tool_input": {"file_path": str(path)}}


_GATE_BLOCKS: tuple[tuple[str, str], ...] = (
    ("root-whitelist", "junk.txt"),
    ("protected-sessions", ".dadaia/sessions/some-session.json"),
    ("protected-law", "AGENTS.md"),
)


@pytest.mark.parametrize(("name", "rel"), _GATE_BLOCKS, ids=[n for n, _ in _GATE_BLOCKS])
def test_gate_block_carries_a_runnable_fix(workspace: Path, name: str, rel: str) -> None:
    block = pre_gate.evaluate_payload(_write(workspace / rel))
    assert block is not None, f"{name}: expected a BLOCK for {rel}"
    assert_block_carries_a_runnable_fix(block)


def test_venv_guard_block_carries_a_runnable_fix(workspace: Path) -> None:
    block = pre_gate.evaluate_payload(
        {"tool_name": "Bash", "tool_input": {"command": "dadaia doctor --context x"}}
    )
    assert block is not None
    assert_block_carries_a_runnable_fix(block)


# ── ci push-gate-check ──────────────────────────────────────────────────────────


@dataclass
class _FakeObjectSource:
    objects: list[ScannedObject] = field(default_factory=list)
    tree_paths: list[str] = field(default_factory=list)

    def new_objects(self, repo: Path, local_sha: str, remote_sha: str) -> Iterable[ScannedObject]:
        return self.objects

    def publishes_nothing(self, repo: Path, sha: str) -> bool:
        return False


class _FailingObjectSource(_FakeObjectSource):
    def new_objects(self, repo: Path, local_sha: str, remote_sha: str) -> Iterable[ScannedObject]:
        raise GitObjectReadError("simulated git rev-list failure")


def _decide(
    refs: list[PushRef],
    *,
    source: _FakeObjectSource | None = None,
    malformed_lines: int = 0,
    denylist_terms: Iterable[tuple[str, str]] = (),
) -> str:
    decision = push_gate_decision(
        refs,
        gitflow=DEFAULT,
        object_source=source or _FakeObjectSource(),
        repo=Path("/nonexistent-repo"),
        canon_violations_fn=canon_violations,
        malformed_lines=malformed_lines,
        denylist_terms=denylist_terms,
    )
    assert not decision.allowed, "expected a refusal"
    return decision.message


def _refs(*lines: str) -> list[PushRef]:
    return parse_push_stdin("\n".join(lines))[0]


def test_push_gate_malformed_stdin_carries_a_runnable_fix() -> None:
    assert_block_carries_a_runnable_fix(_decide([], malformed_lines=1))


@pytest.mark.parametrize(
    ("name", "line"),
    [
        ("main", f"refs/heads/main {_SHA_A} refs/heads/main {_SHA_B}"),
        ("develop", f"refs/heads/develop {_SHA_A} refs/heads/develop {_SHA_B}"),
        ("birth-with-content", f"refs/heads/develop {_SHA_A} refs/heads/develop {_ZERO}"),
        ("invalid-name", f"refs/heads/wip/x {_SHA_A} refs/heads/wip/x {_ZERO}"),
        ("not-a-branch-head", f"refs/notes/x {_SHA_A} refs/notes/x {_ZERO}"),
        ("refspec", f"refs/heads/feature/0.0.1 {_SHA_A} refs/heads/develop {_ZERO}"),
    ],
)
def test_push_gate_branch_policy_refusals_carry_a_runnable_fix(name: str, line: str) -> None:
    assert_block_carries_a_runnable_fix(_decide(_refs(line)))


def _feature_ref() -> list[PushRef]:
    return _refs(f"refs/heads/feature/0.0.1 {_SHA_A} refs/heads/feature/0.0.1 {_ZERO}")


def test_push_gate_specs_canon_refusal_carries_a_runnable_fix() -> None:
    stray = "specs/not-a-canon-entry.md"
    source = _FakeObjectSource(
        objects=[ScannedObject(path=stray, sha="blob0", text="", decodable=True)],
        tree_paths=[stray],
    )
    assert_block_carries_a_runnable_fix(_decide(_feature_ref(), source=source))


def test_push_gate_denylist_refusal_carries_a_runnable_fix() -> None:
    source = _FakeObjectSource(
        objects=[ScannedObject(path="a.md", sha="cafef00d", text="zz-secret-term", decodable=True)]
    )
    message = _decide(
        _feature_ref(), source=source, denylist_terms=[("zz-secret-term", "synthetic")]
    )
    assert_block_carries_a_runnable_fix(message)


def test_push_gate_git_read_failure_carries_a_runnable_fix() -> None:
    assert_block_carries_a_runnable_fix(_decide(_feature_ref(), source=_FailingObjectSource()))


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


@pytest.mark.parametrize(
    ("codes", "rule"), _DOCTOR_RULES, ids=[codes for codes, _ in _DOCTOR_RULES]
)
def test_every_doctor_rule_renders_a_runnable_fix(
    codes: str, rule: doctor_rules.Rule[Any, Any]
) -> None:
    """An error-class doctor finding exits 1 — the operator gets one command back.

    A rule with NO ``fix_help`` is judgment-only: it emits WARNING findings, which never
    exit 1, so there is nothing to hand back and nothing to prove here. That its findings
    really are WARNING is proven by executing each rule in
    ``tests/integration/test_doctor_fix_lines_clear_their_finding.py``.
    """
    if rule.fix_help is None:
        pytest.skip(f"{codes} is judgment-only: WARNING findings, no fix line")
    finding = doctor_rules.SectionFinding(
        code=rule.codes[0],
        verdict="error",
        message="synthetic finding",
        canonical=False,
        error=True,
        fix=doctor_rules.rule_fix(rule, Path()),
    )
    assert_block_carries_a_runnable_fix(doctor_rules.render_finding(finding))


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
    if tokens[0] != "python3" or _INSTALLED_PREFIX not in tokens[1]:
        return None
    relative = tokens[1].split(_INSTALLED_PREFIX, 1)[1]
    verb = next((token for token in tokens[2:] if not token.startswith(("-", "<"))), "")
    return _PUBLIC_SKILLS / relative, verb


def _fix_lines() -> list[tuple[str, str]]:
    """Every doctor rule's fix line, plus the ledger scripts' own delegated fix."""
    from dadaia_workspace.infrastructure.ledger_scripts import LEDGER_SCRIPTS

    lines = [
        (codes, doctor_rules.rule_fix(rule, Path()))
        for codes, rule in _DOCTOR_RULES
        if rule.fix_help
    ]
    lines.extend(
        (script.code, f"{script.invocation} check --specs specs") for script in LEDGER_SCRIPTS
    )
    return lines


_FIX_LINES = _fix_lines()

#: Scaffold roots a fix line may name that this repo does not carry at that path: the
#: installed skill tree (`.agents/skills/…`, what the operator pastes) maps to the
#: `public/skills/` source this repo ships, and the venv-rooted binary is resolved by the
#: CLI arm below, never as a file.
_INSTALLED_SKILL_PREFIX = ".agents/skills/"
_VENV_BINARY_PREFIX = ".dadaia/"

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
        if raw.startswith(_VENV_BINARY_PREFIX):
            continue  # the venv-rooted binary is resolved by the CLI arm, not as a file
        token = _path_token(raw)
        if token is None:
            continue
        target = _resolvable_prefix(token)
        if target not in _TRACKED_DIRS and target not in _CANON_DIRS:
            unresolved.append(token)
    return unresolved


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
