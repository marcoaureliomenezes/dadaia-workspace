"""Every registry harness, through its rendered hook, gets Claude's verdict for a payload in its
native shape.

The payloads (``tests/fixtures/hook_payloads/<harness>/``) cover a new root entry, a PROTECTED
file and a worktree write of an unregistered slug (scope: allowed). Cursor's preToolUse deny
reaches the model with a fix line; Devin's hooks.v1.json uses the documented event shape; an
allowed call prints nothing on the translated harnesses; Kimi's shim prints the reason with real
newlines, ``fix:`` at a line start, exit 2. Every harness's ctx-inject wrapper answers on stdout,
Cursor and Copilot in their vendor key, at every sessionStart. A truncated registry under a live
bind still blocks in every dialect.

Size: MEDIUM — runs the real generated wrappers/shim over the real pre_gate.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pytest

from dadaia_workspace.core import session_store
from dadaia_workspace.core.harness_registry import HARNESS_RECORDS
from dadaia_workspace.core.workspace_layout import MARKER_DIR
from dadaia_workspace.infrastructure.runtime_transforms.hook_wrappers import (
    HOOK_DIALECTS,
    hook_documents,
    hook_wrapper_contents,
)
from tests.fixtures.harness_env import fire_kimi, git_bash, suite_env
from tests.fixtures.stores import fake_venv, own_venv_python
from tests.helpers.oslib import read_text, run, write_text

pytestmark = pytest.mark.slow

_FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "hook_payloads"
#: Claude's verdict per case — the reference side of the parity (literal, not computed).
_CLAUDE = {"new-root": "deny", "protected": "deny", "scope": "allow"}


@pytest.fixture
def ws(tmp_path: Path) -> Path:
    fake_venv(tmp_path)
    (tmp_path / ".dadaia" / "states").mkdir()
    write_text(
        tmp_path / ".dadaia" / "states" / "spec_contexts.json",
        '{"schema_version": "2", "contexts": [{"name": "demo", "state": "alive", "repo_slug": "demo"}]}',
    )  # the payloads write under worktrees/demo/
    ledger = {"relpath": "AGENTS.md", "sha256": "0" * 64, "family": "root", "kind": "file"}
    write_text(
        tmp_path / ".dadaia" / "states" / "install_ledger.json",
        json.dumps({"schema_version": "1", "entries": [ledger]}),
    )
    (tmp_path / ".dadaia" / "hooks").mkdir()
    (tmp_path / "repos").mkdir()
    return tmp_path


def _run(ws: Path, harness: str, case: str, **env_extra: str) -> subprocess.CompletedProcess[str]:
    fixture, repos = (_FIXTURES / harness / f"{case}.json"), case == "repos"
    fixture = fixture.with_name("scope.json") if repos else fixture  # the scope write, in repos/
    payload = read_text(fixture).replace("{ws}", ws.as_posix())
    payload = (
        payload.replace("worktrees/demo/0.5.0/rc-1/job-1/wt-main/", "repos/demo/")
        if repos
        else payload
    )
    if harness == "kimi-code":  # the registered command, run by the host's own shell
        return fire_kimi(ws.with_name(f"{ws.name}-kimi"), "pre-gate", ws, payload, overrides=env_extra)  # fmt: skip
    if harness == "claude":
        argv = [str(own_venv_python(ws)), "-B", "-m", "dadaia_workspace.hooks.pre_gate"]
    else:
        name = f"{harness}-pre-gate"
        body = hook_wrapper_contents(HARNESS_RECORDS[harness])[name]
        write_text(ws / ".dadaia" / "hooks" / name, body)
        argv = [git_bash(), str(ws / ".dadaia" / "hooks" / name)]
    env = suite_env(os.environ, Path.home(), overrides=env_extra)
    return run(argv, input=payload, cwd=ws, env=env, timeout=60)


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


@pytest.mark.parametrize(
    "body",
    ['{"contexts": [{"na', '{"contexts": ' + "[" * 100_000],
    ids=["truncated", "deep-nesting"],
)
@pytest.mark.parametrize("case", ["protected", "new-root", "repos"])
@pytest.mark.parametrize("harness", sorted(HARNESS_RECORDS))
def test_ac3_9_a_bound_session_over_a_truncated_registry_still_blocks(
    ws: Path, harness: str, case: str, body: str
) -> None:
    """A session bound by its live record, its registry truncated: an unreadable registry is no
    bind, never a raise the pre-gate fails open on. A PROTECTED write, a new root entry and a
    direct `repos/<r>/` write each BLOCK in every dialect."""
    now = datetime.now(tz=UTC).isoformat()
    session_store.write_session(
        ws, "s", {"session_id": "s", "last_seen_at": now, "context": "demo"}
    )
    write_text(ws / ".dadaia" / "states" / "spec_contexts.json", body)
    assert _verdict(harness, _run(ws, harness, case, DADAIA_SESSION_ID="s")) == "deny"


def test_b2_cursor_deny_reaches_the_agent_with_its_reason_and_fix(ws: Path) -> None:
    out = json.loads(_run(ws, "cursor", "new-root").stdout)
    assert out["permission"] == "deny"
    assert "\nfix: " in out["agent_message"]


def test_b3_devin_hook_file_has_the_documented_shape() -> None:
    document = hook_documents(HARNESS_RECORDS["devin"])["hooks.v1.json"]

    def row(lane: str, timeout: int) -> dict[str, object]:
        hook = {"type": "command", "command": f".dadaia/hooks/devin-{lane}", "timeout": timeout}
        return {"matcher": "", "hooks": [hook]}

    assert document == {
        "PreToolUse": [row("pre-gate", 10)],
        "UserPromptSubmit": [row("ctx-inject", 30)],
        "SessionStart": [row("ctx-inject", 30), row("doctor-expired", 30)],
    }


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
    """A bound id-less session gets its context on the wrapper's STDOUT (never ``>&2``); Cursor
    and Copilot twice, as two sessionStarts are two new sessions."""
    write_text(
        ws / ".dadaia/states/spec_contexts.json",
        json.dumps({"contexts": [{"name": "alpha", "state": "alive", "repo_slug": "alpha"}]}),
    )
    vendor = {"cursor": "additional_context", "copilot": "additionalContext"}.get(harness)
    env = suite_env(os.environ, Path.home(), overrides={"DADAIA_CONTEXT": "alpha"})
    if harness == "kimi-code":  # the registered commands, run by the host's own shell
        for lane in ("ctx-inject", "post-compact"):
            out = fire_kimi(ws.with_name(f"{ws.name}-kimi"), lane, ws, "{}", overrides={"DADAIA_CONTEXT": "alpha"}).stdout  # fmt: skip
            assert "[alpha]" in out, (lane, out)
        return
    wrappers = hook_wrapper_contents(HARNESS_RECORDS[harness])
    docs = json.dumps(hook_documents(HARNESS_RECORDS[harness]))  # registered, not only rendered
    names = sorted(n for n, body in wrappers.items() if "hooks.ctx_inject" in body and n in docs)
    assert names, harness
    for name in names:
        write_text(ws / ".dadaia" / "hooks" / name, wrappers[name])
        shutil.rmtree(ws / MARKER_DIR, ignore_errors=True)  # each wrapper starts fresh
        for _ in range(2 if vendor else 1):
            out = run([git_bash(), str(ws / ".dadaia" / "hooks" / name)], input="{}", cwd=ws, env=env, timeout=60).stdout  # fmt: skip
            assert "[alpha]" in (json.loads(out)[vendor] if vendor else out), (name, out)


def test_only_a_harness_naming_its_subagent_and_matching_the_shell_tool_judges_the_verdict_act() -> (
    None
):
    """Of the harnesses naming a subagent key, Claude's pre-gate matcher carries Bash and Codex's
    does not: a Codex shell matcher would refuse the reviewer, its payload carrying no agent_type."""
    seen = {
        name: any(
            not matcher or re.search(matcher, "Bash")
            for _, lane, matcher in HOOK_DIALECTS[rec.hooks].files[0].events
            if lane == "pre-gate"
        )
        for name, rec in HARNESS_RECORDS.items()
        if rec.subagent_key
    }
    assert seen == {"claude": True, "codex": False}
