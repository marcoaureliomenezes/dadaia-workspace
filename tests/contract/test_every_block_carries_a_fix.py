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
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from dadaia_workspace.core import doctor_rules
from dadaia_workspace.core.models.git_scan import GitObjectReadError, ScannedObject
from dadaia_workspace.features.chokepoints import push_gate_decision
from dadaia_workspace.features.chokepoints.branch_policy import PushRef, parse_push_refs
from dadaia_workspace.features.specs.canon import canon_violations, verdict_violations
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


def _assert_runnable(command: str) -> None:
    """The fix must itself pass the PreToolUse gate — a blocked fix is a closed loop."""
    block = pre_gate.evaluate_payload({"tool_name": "Bash", "tool_input": {"command": command}})
    assert block is None, f"the fix command is itself BLOCKED (a Stall):\n{command}\n{block}"


def assert_block_carries_a_runnable_fix(message: str) -> None:
    _assert_runnable(_the_fix(message))


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

    def list_tree_paths(self, repo: Path, sha: str, prefix: str) -> list[str]:
        return self.tree_paths

    def first_parent(self, repo: Path, sha: str) -> str | None:
        return None

    def resolve_ref(self, repo: Path, ref: str) -> str | None:
        return None


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
        verdict_violations_fn=verdict_violations,
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
    source = _FakeObjectSource(tree_paths=["specs/not-a-canon-entry.md"])
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


# ── ci verdict-check ────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("name", "args"),
    [
        ("bad-head", ["--head", "nope"]),
        ("bad-release-id", ["--head", _SHA_A, "--release-id", "not a release"]),
        ("no-verdict", ["--head", _SHA_A, "--release-id", "0.0.1"]),
    ],
)
def test_verdict_check_refusals_carry_a_runnable_fix(
    name: str, args: list[str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from dadaia_workspace.cli.commands import ci

    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(ci.app, ["verdict-check", *args])
    assert result.exit_code == 1, result.output
    assert_block_carries_a_runnable_fix(result.output)


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


# ── dadaia doctor (exit 1) ──────────────────────────────────────────────────────


def _every_doctor_rule() -> list[tuple[str, doctor_rules.Rule[Any, Any]]]:
    from dadaia_workspace.features.backlog.doctor import RULES as LEDGER_RULES
    from dadaia_workspace.features.spec_context.doctor import workspace_rules
    from dadaia_workspace.features.specs.rules import RULES as SPECS_RULES

    rules: list[tuple[str, doctor_rules.Rule[Any, Any]]] = []
    for rule in (*workspace_rules(expired_only=False), *SPECS_RULES, *LEDGER_RULES):
        rules.append(("/".join(rule.codes), rule))
    return rules


_DOCTOR_RULES = _every_doctor_rule()


@pytest.mark.parametrize(
    ("codes", "rule"), _DOCTOR_RULES, ids=[codes for codes, _ in _DOCTOR_RULES]
)
def test_every_doctor_rule_renders_a_runnable_fix(
    codes: str, rule: doctor_rules.Rule[Any, Any]
) -> None:
    """An error-class doctor finding exits 1 — the operator gets one command back."""
    assert rule.fix_help, f"doctor rule {codes} carries no fix_help — an exit-1 Stall"
    finding = doctor_rules.SectionFinding(
        code=rule.codes[0],
        verdict="error",
        message="synthetic finding",
        canonical=False,
        error=True,
        fix=rule.fix_help,
    )
    assert_block_carries_a_runnable_fix(doctor_rules.render_finding(finding))
