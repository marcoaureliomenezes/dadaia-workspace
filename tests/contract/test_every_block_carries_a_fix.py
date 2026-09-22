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
import sys
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

from dadaia_workspace.core import doctor_rules
from dadaia_workspace.core.models.git_scan import GitObjectReadError, ScannedObject
from dadaia_workspace.features.chokepoints import push_gate_decision
from dadaia_workspace.features.chokepoints.branch_policy import PushRef, parse_push_refs
from dadaia_workspace.features.specs.canon import canon_violations
from dadaia_workspace.hooks import pre_gate

_FIX_LINE_RE = re.compile(r"^fix: (\S.*)$", re.MULTILINE)

_SHA_A = "a" * 40
_ZERO = "0" * 40


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
    head = command.split()[0]
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

    def parents(self, repo: Path, sha: str) -> tuple[str, ...]:
        return ()

    def resolve_ref(self, repo: Path, ref: str) -> str | None:
        return None

    def tree_matches(self, repo: Path, sha: str, patterns: Sequence[str]) -> set[str]:
        return set()


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
        object_source=source or _FakeObjectSource(),
        repo=Path("/nonexistent-repo"),
        canon_violations_fn=canon_violations,
        malformed_lines=malformed_lines,
        denylist_terms=denylist_terms,
    )
    assert not decision.allowed, "expected a refusal"
    return decision.message


def _refs(*lines: str) -> list[PushRef]:
    return parse_push_refs("\n".join(lines))


def test_push_gate_malformed_stdin_carries_a_runnable_fix() -> None:
    assert_block_carries_a_runnable_fix(_decide([], malformed_lines=1))


@pytest.mark.parametrize(
    ("name", "line"),
    [
        ("main", f"refs/heads/main {_SHA_A} refs/heads/main {_ZERO}"),
        ("develop", f"refs/heads/develop {_SHA_A} refs/heads/develop {_ZERO}"),
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
        fix=rule.fix_help,
    )
    assert_block_carries_a_runnable_fix(doctor_rules.render_finding(finding))


# ── every dadaia fix line names a verb the CLI tree really has ──────────────────


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


@pytest.mark.parametrize(
    ("codes", "rule"), _DOCTOR_RULES, ids=[codes for codes, _ in _DOCTOR_RULES]
)
def test_every_doctor_fix_names_a_verb_the_cli_has(
    codes: str, rule: doctor_rules.Rule[Any, Any]
) -> None:
    """A ``fix:`` that invokes the dadaia binary must name a verb the CLI tree has.

    Bug ``backlog-doctor-fix-names-missing-update-verb``: BL-SCHEMA, BL-CONFLICT and
    BL-STALE handed back ``dadaia backlog update``, a verb that no longer exists — the
    finding's only fix was not executable. A fix line is a free string; nothing tied it
    to the command tree, so a deleted verb could survive in a fix line forever. This
    test walks every ``fix_help`` that starts with the dadaia binary through the live
    command tree and fails on the first verb it cannot find.
    """
    from dadaia_workspace.core.kernel_tunables import DADAIA_BIN

    if rule.fix_help is None or not rule.fix_help.startswith(DADAIA_BIN):
        pytest.skip(f"{codes}: fix line is not a dadaia invocation")
    tokens = rule.fix_help.split()[1:]
    assert _cli_tree_has(tokens), (
        f"{codes}: fix line names a verb the CLI does not have: {rule.fix_help!r}"
    )


# ── every fix target resolves on disk ───────────────────────────────────────────

#: Where a script-form fix line must resolve: the library's own skills tree. A fix may
#: name the INSTALLED path (`.agents/skills/…`, what the operator pastes); the file it
#: names is the one this repo ships.
_PUBLIC_SKILLS = Path(__file__).resolve().parents[2] / "dadaia_workspace" / "public" / "skills"
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

    lines = [(codes, rule.fix_help) for codes, rule in _DOCTOR_RULES if rule.fix_help]
    lines.extend(
        (script.code, f"{script.invocation} check --specs specs") for script in LEDGER_SCRIPTS
    )
    return lines


_FIX_LINES = _fix_lines()

#: The fix lines that are a shell command over a named file, not a `dadaia` verb and not
#: a skill script: the finding is a hand edit the operator makes with the tool already on
#: the line. Their head token is proven executable by `_assert_one_command`; what cannot
#: be resolved here is a `sed`/`printf` placeholder, so each is listed ONCE with the tool
#: it hands over. A NEW unresolvable fix line fails instead of quietly skipping.
_SHELL_FIX_CODES: dict[str, str] = {
    "SPEC-DOC-001": "printf — append the missing constitution section",
    "SPEC-DOC-002/SPEC-DOC-002L/SPEC-DOC-008": "printf — append the missing memory title",
    "SPEC-DOC-003/SPEC-DOC-009": "git rm — delete the retired document",
    "SPEC-DOC-004": "sed — rewrite the document's Status line",
    "SPEC-DOC-007": "git rm — delete the orphan path",
    "SPEC-DOC-024": "sed — align the phase marker with _RELEASE.json",
    "SPEC-DOC-026": "git mv — de-duplicate the release directory",
    "SPEC-DOC-027": "git mv — rename the release directory to M.m.p",
    "SPEC-DOC-028": "sed — drop the dangling constitution reference",
    "SPEC-DOC-030": "git mv — rename the audit directory to YYYYMMDD-slug",
    "SPEC-DOC-037": "sed — drop the stale enum line",
    "SPEC-DOC-047": "sed — drop the stale memory task line",
    "SPEC-DOC-048": "sed — append the missing SPEC Origin line",
    "TREE-3": "printf — append the missing memory title",
    "TREE-7": "sed — redact the session id out of BUGS.jsonl",
    "LINT-1": "sed — insert the missing atom frontmatter field",
    "MEM-DRIFT-1": "sed — align ARCHITECTURE.md with the package on disk",
    "MEM-DRIFT-2": "sed — replace the dead citation",
    "ADR-SUPERSEDED-CITATION": "sed — cite the successor decision",
    "BL-SCHEMA": "sed — correct the offending BACKLOG.json line",
    "LEDGER-ADR-SCHEMA": "sed — correct the offending decisions.jsonl record",
    "RELEASE-TREE-SCHEMA/RELEASE-TREE-PARSE/RELEASE-TREE-TS-ORDER/RELEASE-TREE-PHASE/"
    "RELEASE-TREE-ARCHIVED/RELEASE-TREE-TRIO/RELEASE-TREE-STATE-MISSING": (
        "sed — correct the offending _RELEASE.json value"
    ),
}


@pytest.mark.parametrize(("codes", "command"), _FIX_LINES, ids=[c for c, _ in _FIX_LINES])
def test_every_fix_target_resolves_on_disk(codes: str, command: str) -> None:
    """A ``fix:`` line is a free string — nothing tied it to a file or a verb that exists.

    0.4.7 FR3: after the ledger verbs moved to skill scripts, a stale fix line names a
    path nobody ships instead of a verb nobody has, and the Stall is identical. Both
    forms are resolved HERE: a ``dadaia`` fix walks the live command tree; a script fix
    must exist under ``public/skills/*/scripts/`` and its subcommand must accept
    ``--help``.
    """
    import subprocess  # noqa: PLC0415 — a contract test executes the real script

    from dadaia_workspace.core.kernel_tunables import DADAIA_BIN

    if command.startswith(DADAIA_BIN) or command.startswith("dadaia "):
        tokens = command.split()[1:]
        assert _cli_tree_has(tokens), f"{codes}: no such verb: {command!r}"
        return
    target = _script_target(command)
    if target is None:
        assert codes in _SHELL_FIX_CODES, (
            f"{codes}: a fix line resolves against the CLI tree or a shipped skill "
            f"script — a new shell-command fix joins _SHELL_FIX_CODES with its reason "
            f"or names one of those two: {command!r}"
        )
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

_REPO_ROOT = Path(__file__).resolve().parents[2]

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
    return [
        path
        for root in _LAW_ROOTS
        for path in sorted(root.rglob("*"))
        if path.is_file() and "_archive" not in path.parts
    ] + [path for path in _LAW_FILES if path.is_file()]


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
