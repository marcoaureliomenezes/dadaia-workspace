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


def _job(root: Path, task: str, rewards: list[float]) -> None:
    root.mkdir(parents=True, exist_ok=True)
    write_text(root / "result.json", json.dumps({"stats": {}}))
    for i, r in enumerate(rewards):
        d = root / f"{task}__{i}"
        d.mkdir(parents=True)
        body = {
            "task_name": f"dadaia-workspace-evals/{task}",
            "verifier_result": {"rewards": {"reward": r}},
        }
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
