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

import json
import re
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
    ("protected-law", "DADAIA.md"),
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


# ── the release verbs ───────────────────────────────────────────────────────────


def _specs_tree(tmp_path: Path) -> Path:
    specs = tmp_path / "specs"
    (specs / "releases").mkdir(parents=True)
    return specs


def test_release_new_refuses_a_second_live_release_with_a_runnable_fix(tmp_path: Path) -> None:
    from dadaia_workspace.features.specs import canon

    specs = _specs_tree(tmp_path)
    (specs / "releases" / "0.0.1").mkdir()
    with pytest.raises(FileExistsError) as exc:
        canon.release_new(specs, "0.0.2")
    assert_block_carries_a_runnable_fix(str(exc.value))


@pytest.mark.parametrize(
    ("name", "kwargs"),
    [
        ("bad-sha", {"shipped_sha": "nope", "pr": 1, "next_release": "0.0.2"}),
        ("bad-pr", {"shipped_sha": "a" * 40, "pr": 0, "next_release": "0.0.2"}),
        ("bad-next", {"shipped_sha": "a" * 40, "pr": 1, "next_release": "nope"}),
    ],
)
def test_archive_release_argument_refusals_carry_a_runnable_fix(
    name: str, kwargs: dict[str, Any], tmp_path: Path
) -> None:
    from dadaia_workspace.features.specs import candidate

    specs = _specs_tree(tmp_path)
    with pytest.raises(candidate.ArchiveError) as exc:
        candidate.archive_release(specs, "0.0.1", histo_append=lambda _r: None, **kwargs)
    assert_block_carries_a_runnable_fix(str(exc.value))


@pytest.mark.parametrize("verb", ["archive_release", "archive_candidate"])
def test_archive_verbs_refuse_without_a_live_release_with_a_runnable_fix(
    verb: str, tmp_path: Path
) -> None:
    from dadaia_workspace.features.specs import candidate

    specs = _specs_tree(tmp_path)
    with pytest.raises(candidate.ArchiveError) as exc:
        if verb == "archive_release":
            candidate.archive_release(
                specs,
                "0.0.1",
                shipped_sha="a" * 40,
                pr=1,
                next_release="0.0.2",
                histo_append=lambda _r: None,
            )
        else:
            candidate.archive_candidate(specs)
    assert_block_carries_a_runnable_fix(str(exc.value))


# ── the governance verbs (0.4.7 FR3/FR4/FR5) ───────────────────────────────────


def _backlog_tree(tmp_path: Path) -> Path:
    specs = _specs_tree(tmp_path)
    (specs / "backlog").mkdir()
    (specs / "backlog" / "BACKLOG.json").write_text(
        '{"schema": "backlog-v1", "active": [{"id": "a-thing", "title": "t", '
        '"opened": "2026-01-01", "status": "picked", "description": "d", '
        '"provenance": "operator request"}]}',
        encoding="utf-8",
    )
    return specs


@pytest.mark.parametrize(
    ("name", "kwargs"),
    [
        ("unknown-disposition", {"disposition": "nope", "reason": "r", "release": "0.0.1"}),
        (
            "delivered-without-release",
            {"disposition": "delivered", "reason": None, "release": None},
        ),
        ("rejected-without-reason", {"disposition": "rejected", "reason": None, "release": None}),
        ("unknown-release", {"disposition": "delivered", "reason": None, "release": "9.9.9"}),
    ],
)
def test_backlog_exit_refusals_carry_a_runnable_fix(
    name: str, kwargs: dict[str, Any], tmp_path: Path
) -> None:
    from dadaia_workspace.features.backlog import document

    specs = _backlog_tree(tmp_path)
    with pytest.raises(document.BacklogExitError) as exc:
        document.backlog_exit(specs, "a-thing", histo_store=None, denylist_terms=(), **kwargs)
    assert_block_carries_a_runnable_fix(str(exc.value))


def test_backlog_exit_unknown_slug_carries_a_runnable_fix(tmp_path: Path) -> None:
    from dadaia_workspace.features.backlog import document

    specs = _backlog_tree(tmp_path)
    with pytest.raises(document.BacklogExitError) as exc:
        document.backlog_exit(
            specs,
            "never-existed",
            histo_store=None,
            disposition="rejected",
            reason="r",
            release=None,
            denylist_terms=(),
        )
    assert_block_carries_a_runnable_fix(str(exc.value))


def _audit_tree(tmp_path: Path, disposition: str = "open") -> Path:
    specs = _specs_tree(tmp_path)
    audit = specs / "audits" / "20260101-slug"
    audit.mkdir(parents=True)
    (audit / "FINDINGS.jsonl").write_text(
        json.dumps(
            {
                "id": "20260101-slug-F001",
                "pillar": "bugs",
                "severity": "LOW",
                "refs": ["a"],
                "claim": "c",
                "evidence": "e",
                "disposition": disposition,
                "release": "0.0.1" if disposition != "open" else None,
                "reason": None,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    return specs


@pytest.mark.parametrize(
    ("name", "audit", "finding", "kwargs"),
    [
        (
            "unknown-audit",
            "nope",
            "20260101-slug-F001",
            {"disposition": "resolved", "release": "0.0.1"},
        ),
        (
            "unknown-finding",
            "20260101-slug",
            "F999",
            {"disposition": "resolved", "release": "0.0.1"},
        ),
        ("retired-word", "20260101-slug", "20260101-slug-F001", {"disposition": "fixed"}),
        (
            "deferred-without-reason",
            "20260101-slug",
            "20260101-slug-F001",
            {"disposition": "deferred"},
        ),
    ],
)
def test_audit_disposition_refusals_carry_a_runnable_fix(
    name: str, audit: str, finding: str, kwargs: dict[str, Any], tmp_path: Path
) -> None:
    from dadaia_workspace.features.specs import audit as audit_feature

    specs = _audit_tree(tmp_path)
    with pytest.raises(audit_feature.AuditError) as exc:
        audit_feature.disposition_finding(specs, audit, finding, **kwargs)
    assert_block_carries_a_runnable_fix(str(exc.value))


def test_audit_close_with_an_open_finding_carries_a_runnable_fix(tmp_path: Path) -> None:
    from dadaia_workspace.features.specs import audit as audit_feature

    specs = _audit_tree(tmp_path)
    with pytest.raises(audit_feature.AuditError) as exc:
        audit_feature.close_audit(
            specs, "20260101-slug", sha="abc1234", histo_append=lambda _r: None, denylist_terms=()
        )
    assert_block_carries_a_runnable_fix(str(exc.value))


def _phase_tree(tmp_path: Path, *, phase: str, status: str = "Approved", tasks: str) -> Path:
    specs = _specs_tree(tmp_path)
    rdir = specs / "releases" / "0.0.1"
    rdir.mkdir()
    (rdir / "SPEC.md").write_text("# S\n\n**Status:** Approved\n", encoding="utf-8")
    (rdir / "PLAN.md").write_text(f"# P\n\n**Status:** {status}\n", encoding="utf-8")
    (rdir / "TASKS.md").write_text(f"# T\n\n**Status:** Approved\n\n{tasks}", encoding="utf-8")
    (rdir / "_RELEASE.json").write_text(
        json.dumps(
            {
                "schema": "release-state-v1",
                "release": "0.0.1",
                "phase": phase,
                "rc": None,
                "defined": None,
                "implemented": None,
                "shipped": None,
                "log": [],
            }
        ),
        encoding="utf-8",
    )
    return specs


@pytest.mark.parametrize(
    ("name", "tree", "target", "sha"),
    [
        ("bad-sha", {"phase": "DEFINITION", "tasks": "- [x] T-1\n"}, "IMPLEMENTATION", "nope"),
        ("out-of-order", {"phase": "DEFINITION", "tasks": "- [x] T-1\n"}, "CLOSURE", _SHA_A),
        ("re-run", {"phase": "IMPLEMENTATION", "tasks": "- [x] T-1\n"}, "IMPLEMENTATION", _SHA_A),
        (
            "unapproved-plan",
            {"phase": "DEFINITION", "status": "Draft", "tasks": "- [x] T-1\n"},
            "IMPLEMENTATION",
            _SHA_A,
        ),
        (
            "unfinished-task",
            {"phase": "IMPLEMENTATION", "tasks": "- [-] T-1\n"},
            "CLOSURE",
            _SHA_A,
        ),
        ("unknown-phase", {"phase": "DEFINITION", "tasks": "- [x] T-1\n"}, "DEFINITION", _SHA_A),
    ],
)
def test_release_phase_refusals_carry_a_runnable_fix(
    name: str, tree: dict[str, str], target: str, sha: str, tmp_path: Path
) -> None:
    from dadaia_workspace.features.specs import candidate

    specs = _phase_tree(tmp_path, **tree)
    with pytest.raises(candidate.ArchiveError) as exc:
        candidate.set_phase(specs, target, sha=sha)
    assert_block_carries_a_runnable_fix(str(exc.value))


# ── context heartbeat (exit 1) ──────────────────────────────────────────────────


# ── dadaia doctor (exit 1) ──────────────────────────────────────────────────────


def _every_doctor_rule() -> list[tuple[str, doctor_rules.Rule[Any, Any]]]:
    from dadaia_workspace.features.backlog.doctor import RULES as BACKLOG_RULES
    from dadaia_workspace.features.spec_context.doctor import workspace_rules
    from dadaia_workspace.features.specs.ledgers import RULES as LEDGER_SCHEMA_RULES
    from dadaia_workspace.features.specs.rules import RULES as SPECS_RULES

    rules: list[tuple[str, doctor_rules.Rule[Any, Any]]] = []
    for rule in (
        *workspace_rules(expired_only=False),
        *SPECS_RULES,
        *BACKLOG_RULES,
        *LEDGER_SCHEMA_RULES,
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
