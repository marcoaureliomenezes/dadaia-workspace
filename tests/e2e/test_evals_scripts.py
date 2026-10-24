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


_HARNESSES = ("claude-code", "codex")


def _leg(path: Path, harness: str, passes: dict[str, int], errored: dict[str, int] | None = None):
    """Write a leg.json holding one row per task in `passes`; a task absent from it has no row."""
    rows = [
        {
            "harness": harness,
            "task": t,
            "passes": p,
            "errored": (errored or {}).get(t, 0),
            "found": 3,
        }
        for t, p in passes.items()
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    write_text(path, json.dumps(rows))
    return path


def _table(*legs: Path) -> tuple[int, list[list[str]]]:
    """Run `compare.py --table`; return the exit code and each row's cells."""
    cmd = [
        sys.executable,
        str(_ROOT / "evals" / "scripts" / "compare.py"),
        "--table",
        *map(str, legs),
    ]
    done = run(cmd, timeout=60)
    rows = [
        [c.strip() for c in line.strip("| \n").split("|")]
        for line in done.stdout.splitlines()
        if line.startswith("| ") and not line.startswith("| harness")
    ]
    return done.returncode, rows


# Columns: harness, task, passes, floor, errored, pass^3, interval, verdict.
@pytest.mark.parametrize(
    ("passes", "pass3", "interval"),
    [(3, "1", "[0.44, 1.00]"), (2, "0", "[0.21, 0.94]"), (0, "0", "[0.00, 0.56]")],
    ids=["three-of-three", "two-of-three", "zero-of-three"],
)
def test_table_statistics(tmp_path: Path, passes: int, pass3: str, interval: str) -> None:
    leg = _leg(tmp_path / "leg.json", "codex", {_T1: 3, _T2: 3, _T3: passes})
    _, rows = _table(leg)
    row = next(r for r in rows if r[:2] == ["codex", _T3])
    assert (row[2], row[5], row[6]) == (f"{passes}/3 (3 found)", pass3, interval)


def test_table_merges_two_harnesses_into_six_rows(tmp_path: Path) -> None:
    full = {_T1: 3, _T2: 3, _T3: 3}
    a = _leg(tmp_path / "a" / "leg.json", "claude-code", full)
    b = _leg(tmp_path / "b" / "leg.json", "codex", full)
    code, rows = _table(a, b)
    assert code == 0
    assert [(r[0], r[1]) for r in rows] == [(h, t) for h in _HARNESSES for t in (_T1, _T2, _T3)]


@pytest.mark.parametrize(
    ("task", "passes", "code"),
    [(_T1, 2, 1), (_T2, 2, 0), (_T2, 1, 1), (_T3, 1, 1)],
    ids=["t1-two", "t2-two", "t2-one", "t3-one"],
)
def test_table_floor_is_per_harness_and_task(
    tmp_path: Path, task: str, passes: int, code: int
) -> None:
    ok = _leg(tmp_path / "a" / "leg.json", "claude-code", {_T1: 3, _T2: 3, _T3: 3})
    bad = _leg(tmp_path / "b" / "leg.json", "codex", {_T1: 3, _T2: 3, _T3: 3} | {task: passes})
    got, rows = _table(ok, bad)
    row = next((r for r in rows if r[0] == "codex" and r[1] == task), [])
    assert (got, row[2:3]) == (code, [f"{passes}/3 (3 found)"])


def test_table_missing_leg_file_blocks(tmp_path: Path) -> None:
    only = _leg(tmp_path / "a" / "leg.json", "claude-code", {_T1: 3, _T2: 3, _T3: 3})
    code, rows = _table(only, tmp_path / "b" / "leg.json")
    missing = [r[2] for r in rows if r[0] == "codex"]
    assert (code, len(rows), missing) == (1, 6, ["0/3 (0 found)"] * 3)


def test_table_missing_task_row_blocks(tmp_path: Path) -> None:
    leg = _leg(tmp_path / "leg.json", "codex", {_T1: 3, _T2: 3})
    code, rows = _table(leg)
    row = next(r for r in rows if r[:2] == ["codex", _T3])
    assert (code, row[2]) == (1, "0/3 (0 found)")


def test_table_errored_column_counts_an_errored_trial(tmp_path: Path) -> None:
    leg = _leg(tmp_path / "leg.json", "codex", {_T1: 2, _T2: 3, _T3: 3}, {_T1: 1})
    code, rows = _table(leg)
    row = next(r for r in rows if r[:2] == ["codex", _T1])
    assert (code, row[2], row[4]) == (1, "2/3 (3 found)", "1")


# Composed at runtime: no key, JWT or account value is tracked whole.
_OPENAI_KEY = "sk-" + "proj-" + "PLANTED" * 5
_JWT = ".".join(["eyJ" + "hbGciOiJIUzI1NiJ9", "eyJ" + "zdWIiOiJwbGFudGVkIn0", "PLANTEDsig" * 3])
_ACCOUNT = "acct-" + "planted-" + "0042"
_REFRESH = "rt-" + "planted-" + "refresh-" + "77"
_CODEX_SECRET = json.dumps(
    {"tokens": {"id_token": "idt-planted-1", "refresh_token": _REFRESH}, "n": 1}
)


def _scan_out(tmp_path: Path, content: str, env: dict[str, str] | None) -> tuple[int, str]:
    trial = tmp_path / "jobs" / "trial"
    trial.mkdir(parents=True)
    (trial / "log.txt").write_text(content, encoding="utf-8")
    full = {k: v for k, v in os.environ.items() if k != "SCAN_SECRET"} | (env or {})
    cmd = [sys.executable, str(_ROOT / "evals" / "scripts" / "scan.py"), str(tmp_path / "jobs")]
    done = run(cmd, env=full, timeout=60)
    return done.returncode, done.stdout + done.stderr


@pytest.mark.parametrize(
    ("content", "env", "needle"),
    [
        (json.dumps({"k": _REFRESH}), {"SCAN_SECRET": _CODEX_SECRET}, _REFRESH),
        ("key " + _OPENAI_KEY, None, _OPENAI_KEY),
        ("jwt " + _JWT, None, _JWT),
        (json.dumps({"creator_account_id": _ACCOUNT}), None, _ACCOUNT),
        ("token " + _TOKEN, None, _TOKEN),
    ],
    ids=[
        "codex-json-leaf",
        "openai-key-shape",
        "jwt-shape",
        "creator-account-id",
        "anthropic-shape",
    ],
)
def test_scan_needle_kinds_name_the_file_and_never_the_needle(
    tmp_path: Path, content: str, env: dict[str, str] | None, needle: str
) -> None:
    code, out = _scan_out(tmp_path, content, env)
    assert code == 1
    assert "log.txt" in out
    assert needle not in out


def test_scan_clean_tree_with_a_codex_secret_exits_zero(tmp_path: Path) -> None:
    code, out = _scan_out(tmp_path, "nothing here", {"SCAN_SECRET": _CODEX_SECRET})
    assert (code, _REFRESH in out) == (0, False)


def _preflight(harness: str, secret: str | None) -> tuple[int, str]:
    env = {k: v for k, v in os.environ.items() if k != "MODEL_SECRET"}
    if secret is not None:
        env["MODEL_SECRET"] = secret
    cmd = [
        sys.executable,
        str(_ROOT / "evals" / "scripts" / "preflight.py"),
        harness,
        "MODEL_SECRET",
    ]
    done = run(cmd, env=env, timeout=60)
    return done.returncode, done.stdout + done.stderr


@pytest.mark.parametrize(
    ("harness", "secret", "code"),
    [
        ("claude-code", "", 1),
        ("codex", "", 1),
        ("claude-code", None, 1),
        ("codex", "not-json-" + "PLANTED", 1),
        ("claude-code", "not-json-" + "PLANTED", 0),
        ("codex", _CODEX_SECRET, 0),
    ],
    ids=[
        "claude-empty",
        "codex-empty",
        "claude-unset",
        "codex-non-json",
        "claude-plain",
        "codex-json",
    ],
)
def test_preflight_exit_and_output(harness: str, secret: str | None, code: int) -> None:
    got, out = _preflight(harness, secret)
    assert got == code
    if secret:
        assert secret not in out
        assert _REFRESH not in out


@pytest.mark.parametrize("harness", ["claude-code", "codex"])
def test_preflight_error_is_one_line_naming_harness_secret_and_reseed_doc(harness: str) -> None:
    code, out = _preflight(harness, "")
    lines = out.strip().splitlines()
    assert code == 1
    assert len(lines) == 1
    assert lines[0].startswith("::error::")
    assert harness in lines[0]
    assert "MODEL_SECRET" in lines[0]
    assert "evals/RESEED.md" in lines[0]


def test_scan_short_json_leaf_is_not_a_needle(tmp_path: Path) -> None:
    long_leaf = "tok-" + "planted-" + "long-leaf-" + "0123456789"
    secret = {"SCAN_SECRET": json.dumps({"auth_mode": "chatgpt", "tokens": {"access": long_leaf}})}
    short_code, short_out = _scan_out(tmp_path / "a", "mode chatgpt", secret)
    long_code, long_out = _scan_out(tmp_path / "b", "got " + long_leaf, secret)
    assert (short_code, short_out) == (0, "")
    assert long_code == 1
    assert "log.txt" in long_out
    assert long_leaf not in long_out
