"""The eval scripts `evals/scripts/scan.py` and `compare.py`, run as
a subprocess. scan exits 1 on a token, a missing path or `$SCAN_SECRET`'s value and 0 on a
clean tree; compare blocks when T1 < 3/3 or T2 or T3 < 2/3.

Owner: dd-sw-engineer-sr
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

from tests.helpers.oslib import run, write_text

pytestmark = pytest.mark.e2e

_ROOT = Path(__file__).resolve().parents[2]
_T1 = "t1-cold-onboarding"
_T2 = "t2-block-list-bug"
_T3 = "t3-discovery"
# Composed at runtime: no token-shaped literal is tracked.
_TOKEN = "sk-ant-" + "oat01-" + "PLANTED" * 6


def _run(script: str, *args: Path, env: dict[str, str] | None = None) -> int:
    full = {k: v for k, v in os.environ.items() if k != "SCAN_SECRET"} | (env or {})
    cmd = [sys.executable, str(_ROOT / "evals" / "scripts" / script), *map(str, args)]
    return run(cmd, env=full, timeout=60).returncode


def _scan(tmp_path: Path, content: str | bytes, name: str, env: dict[str, str] | None) -> int:
    trial = tmp_path / "jobs" / "trial"
    trial.mkdir(parents=True)
    (trial / name).write_bytes(content.encode() if isinstance(content, str) else content)
    return _run("scan.py", tmp_path / "jobs", env=env)


@pytest.mark.parametrize(
    ("content", "name", "env", "expected"),
    [
        (json.dumps({"t": _TOKEN}), "result.json", None, 1),
        (b"\x00\xff" + _TOKEN.encode() + b"\x00", "blob.bin", None, 1),
        ("log " + _TOKEN, "transcript.txt", None, 1),
        ("x planted-fake-value x", "transcript.txt", {"SCAN_SECRET": "planted-fake-value"}, 1),
        ("nothing here", "transcript.txt", {"SCAN_SECRET": "planted-fake-value"}, 0),
    ],
    ids=["token-in-json", "token-in-binary", "token-shape", "secret-value", "clean-tree"],
)
def test_scan_exit_code(
    tmp_path: Path, content: str | bytes, name: str, env: dict[str, str] | None, expected: int
) -> None:
    assert _scan(tmp_path, content, name, env) == expected


def test_scan_missing_path_is_red(tmp_path: Path) -> None:
    assert _run("scan.py", tmp_path / "no-such-dir") == 1


def _job(root: Path, task: str, rewards: list[float], harness: str | None = "claude-code") -> None:
    root.mkdir(parents=True, exist_ok=True)
    write_text(root / "result.json", json.dumps({"stats": {}}))
    for i, r in enumerate(rewards):
        d = root / f"{task}__{i}"
        d.mkdir(parents=True)
        body = {
            "task_name": f"dadaia-workspace-evals/{task}",
            "verifier_result": {"rewards": {"reward": r}},
        }
        if harness is not None:
            body["agent_info"] = {"name": harness}
        write_text(d / "result.json", json.dumps(body))


_ALL = {_T1: [1, 1, 1], _T2: [1, 1, 1], _T3: [1, 1, 1]}


@pytest.mark.parametrize(
    ("cand", "expected"),
    [
        ({**_ALL, _T1: [1, 1, 0]}, 1),
        ({**_ALL, _T1: [1, 1]}, 1),
        ({_T1: _ALL[_T1], _T3: _ALL[_T3]}, 1),
        ({**_ALL, _T1: [1, 1, 0.5]}, 1),
        ({_T2: _ALL[_T2], _T3: _ALL[_T3]}, 1),
        ({_T1: [1, 1, 1], _T2: [1, 1, 0], _T3: [1, 1, 0]}, 0),
        ({**_ALL, _T2: [1, 0, 0]}, 1),
        ({**_ALL, _T3: [1, 0, 0]}, 1),
    ],
    ids=[
        "t1-two-of-three",
        "missing-candidate-trial",
        "task-absent-from-candidate",
        "fractional-reward",
        "t1-absent",
        "passing-candidate",
        "t2-below-two-of-three",
        "t3-below-two-of-three",
    ],
)
def test_compare_gate(tmp_path: Path, cand: dict[str, list[float]], expected: int) -> None:
    for task, rewards in cand.items():
        _job(tmp_path, task, rewards)
    assert _run("compare.py", tmp_path) == expected


_VERDICT = (
    "python3 .agents/skills/dd-handoff-emitter/scripts/verdict.py wt --sha abc"
    " --context c --slug s --verdict APPROVED --reason ok"
)


def _bash_line(command: str, *, sidechain: bool) -> str:
    block = {"type": "tool_use", "id": "toolu_1", "name": "Bash", "input": {"command": command}}
    line = {
        "type": "assistant",
        "isSidechain": sidechain,
        "message": {"role": "assistant", "content": [block]},
    }
    return json.dumps(line) + "\n"


def _transcript(trial: Path, *, agent_type: str | None) -> None:
    """A Claude Code session under the trial's agent dir: the verdict in the main thread, or in a subagent file."""
    session = trial / "agent" / "sessions" / "projects" / "-app" / "s1"
    session.parent.mkdir(parents=True)
    main = _bash_line("ls", sidechain=False)
    if agent_type is None:
        main += _bash_line(_VERDICT, sidechain=False)
    write_text(session.parent / "s1.jsonl", main)
    if agent_type is not None:
        (session / "subagents").mkdir(parents=True)
        write_text(session / "subagents" / "agent-a1.jsonl", _bash_line(_VERDICT, sidechain=True))
        write_text(
            session / "subagents" / "agent-a1.meta.json", json.dumps({"agentType": agent_type})
        )


@pytest.mark.parametrize(
    ("agent_type", "expected"),
    [(None, "2/3"), ("general-purpose", "2/3"), ("dd-code-reviewer", "3/3")],
    ids=["main-thread", "other-subagent", "dispatched-reviewer"],
)
@pytest.mark.parametrize("task", [_T1, _T2, _T3], ids=["t1", "t2", "t3"])
def test_compare_zeroes_a_verdict_written_outside_the_reviewer(
    tmp_path: Path, task: str, agent_type: str | None, expected: str
) -> None:
    for t in (_T1, _T2, _T3):
        _job(tmp_path, t, [1, 1, 1])
    _transcript(tmp_path / f"{task}__0", agent_type=agent_type)
    out = run(
        [sys.executable, str(_ROOT / "evals" / "scripts" / "compare.py"), str(tmp_path)], timeout=60
    ).stdout
    assert f"| {task} | {expected} (3 found) |" in out


def _rollout(
    trial: Path, name: str, *, thread_source: str, agent_role: str | None, act: bool
) -> None:
    """A Codex rollout under the trial's agent dir: the session_meta record, then one shell act."""
    spawn = {"thread_spawn": {"agent_role": agent_role}}
    meta = {
        "creator_user_id": "user-synthetic-1",
        "creator_account_id": "acct-synthetic-1",
        "thread_source": thread_source,
        "agent_role": agent_role,
        "source": {"subagent": spawn} if thread_source == "subagent" else "cli",
    }
    command = _VERDICT if act else "ls"
    call = {"type": "custom_tool_call", "name": "exec", "input": f'text(await sh("{command}"))'}
    lines = [{"type": "session_meta", "payload": meta}, {"type": "response_item", "payload": call}]
    folder = trial / "agent" / "sessions" / "2026" / "10" / "24"
    folder.mkdir(parents=True, exist_ok=True)
    write_text(folder / f"rollout-{name}.jsonl", "".join(json.dumps(x) + "\n" for x in lines))


def _compare(root: Path) -> tuple[int, str]:
    done = run(
        [sys.executable, str(_ROOT / "evals" / "scripts" / "compare.py"), str(root)], timeout=60
    )
    return done.returncode, done.stdout


@pytest.mark.parametrize(
    ("thread_source", "agent_role", "expected", "passes"),
    [
        ("subagent", "dd-code-reviewer", "3/3", 3),
        ("user", None, "2/3", 2),
        ("subagent", "dd-sw-engineer-sr", "2/3", 2),
        ("subagent", None, "2/3", 2),
    ],
    ids=["dispatched-reviewer", "user-thread", "other-role", "null-role-subagent"],
)
@pytest.mark.parametrize("task", [_T1, _T2, _T3], ids=["t1", "t2", "t3"])
def test_compare_zeroes_a_codex_verdict_written_outside_the_reviewer(
    tmp_path: Path,
    task: str,
    thread_source: str,
    agent_role: str | None,
    expected: str,
    passes: int,
) -> None:
    for t in (_T1, _T2, _T3):
        _job(tmp_path, t, [1, 1, 1], harness="codex")
    trial = tmp_path / f"{task}__0"
    _rollout(trial, "main", thread_source="user", agent_role=None, act=False)
    _rollout(trial, "act", thread_source=thread_source, agent_role=agent_role, act=True)
    _, out = _compare(tmp_path)
    assert f"| {task} | {expected} (3 found) |" in out
    leg = json.loads((tmp_path / "leg.json").read_text(encoding="utf-8"))
    row = next(r for r in leg if r["task"] == task)
    assert row == {"harness": "codex", "task": task, "passes": passes, "errored": 0, "found": 3}


@pytest.mark.parametrize("harness", ["opencode", None], ids=["unknown-name", "no-agent-info"])
def test_compare_refuses_a_harness_with_no_identity_rule(
    tmp_path: Path, harness: str | None
) -> None:
    for t in (_T1, _T2, _T3):
        _job(tmp_path, t, [1, 1, 1], harness=harness)
    assert _compare(tmp_path)[0] == 1


def test_compare_never_passes_an_errored_trial(tmp_path: Path) -> None:
    for t in (_T1, _T2, _T3):
        _job(tmp_path, t, [1, 1, 1])
    trial = tmp_path / f"{_T1}__0" / "result.json"
    body = json.loads(trial.read_text(encoding="utf-8")) | {"exception_info": {"type": "Timeout"}}
    write_text(trial, json.dumps(body))
    code, _ = _compare(tmp_path)
    leg = json.loads((tmp_path / "leg.json").read_text(encoding="utf-8"))
    row = next(r for r in leg if r["task"] == _T1)
    assert (code, row["passes"], row["errored"]) == (1, 2, 1)
