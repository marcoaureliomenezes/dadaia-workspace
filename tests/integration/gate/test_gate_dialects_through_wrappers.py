"""Intent: CONTRACT — sa-gate-blind-on-cursor-copilot-devin (0.5.0 WP-12, AC1.4, ADR 0054).

sa-gate-blind-on-cursor-copilot-devin#B8: for every registry harness, a payload fixture in the harness's native shape
(``tests/fixtures/hook_payloads/<harness>/``, shapes from the bug record's vendor-doc
citations — authored, not recorded) through its rendered hook gets Claude's verdict for
a bare `dadaia` / a new root entry / a PROTECTED file / a worktree write of an unregistered slug (scope: allowed).
sa-gate-blind-on-cursor-copilot-devin#B1 Copilot's deny carries the venv guard's reason and fix line; sa-gate-blind-on-cursor-copilot-devin#B2 Cursor's preToolUse
deny reaches the model (agent_message) with a fix line; sa-gate-blind-on-cursor-copilot-devin#B3 Devin's hooks.v1.json has the
documented event -> [{matcher, hooks}] shape; sa-gate-blind-on-cursor-copilot-devin#B4 an allowed call prints nothing on the
translated harnesses; sa-gate-blind-on-cursor-copilot-devin#B5 Kimi's shim prints the reason with real newlines, `fix:` at a
line start, exit 2. AC1.2 (ADR 0103, ctx-inject-on-cursor-copilot): every harness's
rendered ctx-inject wrapper answers on stdout, Cursor and Copilot in their vendor key, at
every sessionStart. AC3.9: a truncated registry under a live bind still BLOCKs in every dialect.
Size: MEDIUM — runs the real generated wrappers/shim over the real pre_gate.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest

from dadaia_workspace.core import session_store
from dadaia_workspace.core.harness_registry import HARNESS_RECORDS
from dadaia_workspace.core.workspace_layout import MARKER_DIR
from dadaia_workspace.infrastructure.runtime_transforms.hook_wrappers import (
    hook_documents,
    hook_wrapper_contents,
)

pytestmark = [pytest.mark.integration, pytest.mark.slow]

_FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "hook_payloads"
#: Claude's verdict per case — the reference side of the parity (literal, not computed).
_CLAUDE = {"venv": "deny", "new-root": "deny", "protected": "deny", "scope": "allow"}


@pytest.fixture
def ws(tmp_path: Path) -> Path:
    (tmp_path / ".dadaia" / ".venv" / "bin").mkdir(parents=True)
    (tmp_path / ".dadaia" / ".venv" / "bin" / "python").symlink_to(sys.executable)
    (tmp_path / ".dadaia" / "states").mkdir()
    (tmp_path / ".dadaia" / "states" / "spec_contexts.json").write_text(
        '{"schema_version": "2", "contexts": [{"name": "demo", "state": "alive", "repo_slug": "demo"}]}'
    )  # the payloads write under worktrees/demo/
    ledger = {"relpath": "AGENTS.md", "sha256": "0" * 64, "family": "root", "kind": "file"}
    (tmp_path / ".dadaia" / "states" / "install_ledger.json").write_text(  # projects AGENTS.md
        json.dumps({"schema_version": "1", "entries": [ledger]})
    )
    (tmp_path / ".dadaia" / "hooks").mkdir()
    (tmp_path / "repos").mkdir()
    return tmp_path


def _run(ws: Path, harness: str, case: str, **env_extra: str) -> subprocess.CompletedProcess[str]:
    fixture, repos = (_FIXTURES / harness / f"{case}.json"), case == "repos"
    fixture = fixture.with_name("scope.json") if repos else fixture  # the scope write, in repos/
    payload = fixture.read_text().replace("{ws}", str(ws))
    payload = payload.replace("worktrees/demo/0.5.0a-impl/", "repos/demo/") if repos else payload
    if harness == "claude":
        argv = [str(ws / ".dadaia/.venv/bin/python"), "-B", "-m", "dadaia_workspace.hooks.pre_gate"]
    else:
        name = "dadaia-kimi-pre-gate.sh" if harness == "kimi-code" else f"{harness}-pre-gate"
        body = hook_wrapper_contents(HARNESS_RECORDS[harness])[name]
        (ws / ".dadaia" / "hooks" / name).write_text(body)
        argv = ["sh", str(ws / ".dadaia" / "hooks" / name)]
    env = {"PATH": os.environ["PATH"], "PYTHONPATH": os.environ.get("PYTHONPATH", ""), **env_extra}
    return subprocess.run(
        argv, input=payload, capture_output=True, text=True, cwd=ws, env=env, timeout=60
    )


def _verdict(harness: str, proc: subprocess.CompletedProcess[str]) -> str:
    if harness == "kimi-code":
        return "deny" if proc.returncode == 2 else "allow"
    out = json.loads(proc.stdout) if proc.stdout.strip() else {}
    key = {"cursor": "permission", "copilot": "permissionDecision"}.get(harness)
    decision = out.get(key) if key else out.get("hookSpecificOutput", {}).get("permissionDecision")
    return "deny" if decision == "deny" else "allow"


@pytest.mark.parametrize("case", sorted(_CLAUDE))
@pytest.mark.parametrize("harness", sorted(HARNESS_RECORDS))
def test_b8_every_harness_gets_claudes_verdict(ws: Path, harness: str, case: str) -> None:
    assert _verdict(harness, _run(ws, harness, case)) == _CLAUDE[case]


@pytest.mark.parametrize("case", ["protected", "new-root", "repos"])
@pytest.mark.parametrize("harness", sorted(HARNESS_RECORDS))
def test_ac3_9_a_bound_session_over_a_truncated_registry_still_blocks(
    ws: Path, harness: str, case: str
) -> None:
    """AC3.9 (PLAN §2.6): a session bound by its live record, its registry truncated: an
    unreadable registry is no bind, never a raise the pre-gate fails open on — a PROTECTED
    write, a new root entry and a direct `repos/<r>/` write (ADR 0105) each BLOCK in every
    dialect."""
    now = datetime.now(tz=UTC).isoformat()
    session_store.write_session(
        ws, "s", {"session_id": "s", "last_seen_at": now, "context": "demo"}
    )
    (ws / ".dadaia" / "states" / "spec_contexts.json").write_text('{"contexts": [{"na')
    assert _verdict(harness, _run(ws, harness, case, DADAIA_SESSION_ID="s")) == "deny"


@pytest.mark.parametrize(
    ("harness", "case", "decision", "reason", "text"),
    [
        ("copilot", "venv", "permissionDecision", "permissionDecisionReason", "[VENV GUARD]"),  # B1
        ("cursor", "new-root", "permission", "agent_message", "\nfix: "),  # B2
    ],
    ids=["b1-copilot-venv", "b2-cursor-new-root"],
)
def test_b1_b2_the_deny_reaches_the_agent_with_its_reason_and_fix(
    ws: Path, harness: str, case: str, decision: str, reason: str, text: str
) -> None:
    out = json.loads(_run(ws, harness, case).stdout)
    assert out[decision] == "deny"
    assert text in out[reason] and "\nfix: " in out[reason]


def test_b3_devin_hook_file_has_the_documented_shape_and_denies(ws: Path) -> None:
    document = hook_documents(HARNESS_RECORDS["devin"])["hooks.v1.json"]

    def row(lane: str, timeout: int) -> dict[str, object]:
        hook = {"type": "command", "command": f".dadaia/hooks/devin-{lane}", "timeout": timeout}
        return {"matcher": "", "hooks": [hook]}

    assert document == {
        "PreToolUse": [row("pre-gate", 10)],
        "UserPromptSubmit": [row("ctx-inject", 30)],
        "SessionStart": [row("ctx-inject", 30), row("doctor-expired", 30)],
    }
    assert _verdict("devin", _run(ws, "devin", "venv")) == "deny"


@pytest.mark.parametrize("harness", ["cursor", "copilot"])
def test_b4_an_allowed_call_prints_nothing(ws: Path, harness: str) -> None:
    assert _run(ws, harness, "scope").stdout == ""


def test_b5_kimi_prints_the_reason_with_real_newlines_and_exits_2(ws: Path) -> None:
    proc = _run(ws, "kimi-code", "protected")
    assert proc.returncode == 2
    assert any(line.startswith("fix: ") for line in proc.stderr.splitlines())
    assert "\\n" not in proc.stderr


@pytest.mark.parametrize("harness", sorted(HARNESS_RECORDS))
def test_ac1_2_every_ctx_inject_wrapper_answers_on_stdout(ws: Path, harness: str) -> None:
    """AC1.2: a bound id-less session gets its context on the wrapper's STDOUT (never
    ``>&2``); Cursor and Copilot twice, as two sessionStarts are two new sessions."""
    (ws / ".dadaia/states/spec_contexts.json").write_text(
        json.dumps({"contexts": [{"name": "alpha", "state": "alive", "repo_slug": "alpha"}]})
    )
    vendor = {"cursor": "additional_context", "copilot": "additionalContext"}.get(harness)
    env = {"PATH": os.environ["PATH"], "PYTHONPATH": os.environ.get("PYTHONPATH", "")}
    env |= {"DADAIA_FENCED_ROOTS": os.environ["DADAIA_FENCED_ROOTS"], "DADAIA_CONTEXT": "alpha"}
    wrappers = hook_wrapper_contents(HARNESS_RECORDS[harness])
    docs = json.dumps(hook_documents(HARNESS_RECORDS[harness]))  # registered, not only rendered
    names = sorted(n for n, body in wrappers.items() if "hooks.ctx_inject" in body and n in docs)
    assert names, harness
    for name in names:
        (ws / ".dadaia" / "hooks" / name).write_text(wrappers[name])
        shutil.rmtree(ws / MARKER_DIR, ignore_errors=True)  # each wrapper starts fresh
        for _ in range(2 if vendor else 1):
            out = subprocess.run(
                ["sh", str(ws / ".dadaia" / "hooks" / name)],
                input="{}", capture_output=True, text=True, cwd=ws, env=env, timeout=60,
            ).stdout  # fmt: skip
            assert "[alpha]" in (json.loads(out)[vendor] if vendor else out), (name, out)
