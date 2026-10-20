"""Docker helpers for the evals graders' no-model rows (ported from the retired evals repo, commit c075ed6).

An image is the task's ``environment/`` plus a ``lib/`` layer written per run: this checkout's
wheel (the one builder, ``_build_wheel``); no published dadaia-workspace is ever installed. A missing ``evals/tasks/<task>``
or a missing ``docker`` fails the row by ``AssertionError``; nothing here skips.
"""

from __future__ import annotations

import atexit
import functools
import shutil
import tempfile
from pathlib import Path

from tests.e2e.test_one_line_bootstrap import _build_wheel
from tests.helpers.oslib import run, write_text

ROOT = Path(__file__).resolve().parents[2]
VERSIONS = ("candidate",)
T1 = "t1-cold-onboarding"
T2 = "t2-block-list-bug"

# The documented onboarding, typed by hand.
_INIT = "dadaia init /workspace --harness claude --repo file:///srv/demo.git"
HAND = {"candidate": f"{_INIT} && /workspace/.dadaia/.venv/bin/dadaia specs init --context demo"}


def sh(*cmd: str) -> str:
    assert shutil.which(cmd[0]), f"{cmd[0]} is required: a missing tool fails the row"
    p = run(cmd)
    assert p.returncode == 0, f"{cmd}: exit {p.returncode}\n{p.stderr[-3000:]}"
    return p.stdout


def task_dir(task: str) -> Path:
    path = ROOT / "evals" / "tasks" / task
    assert path.is_dir(), f"{path} does not exist"
    return path


@functools.cache
def wheel() -> Path:
    out = Path(tempfile.mkdtemp())
    atexit.register(shutil.rmtree, out, ignore_errors=True)
    return _build_wheel(ROOT, out)


@functools.cache
def image(task: str, version: str) -> str:
    """``evals/tasks/<task>/environment`` built with this checkout's wheel as its lib layer."""
    src = task_dir(task) / "environment"
    with tempfile.TemporaryDirectory() as d:
        ctx = Path(d) / "environment"
        shutil.copytree(src, ctx)
        (ctx / "lib").mkdir()
        shutil.copy(wheel(), ctx / "lib")
        write_text(ctx / "lib" / "requirements.txt", f"/lib/{wheel().name}\n")
        tag = f"dadaia-workspace-evals-{task}:{version}"
        sh("docker", "build", "-q", "-t", tag, str(ctx))
    return tag


def reward(task: str, version: str, script: str) -> str:
    """Run ``script`` in a fresh container, then the task's grader as Harbor does; the reward written."""
    tests = task_dir(task) / "tests"
    out = sh(
        "docker", "run", "--rm", "--mount", f"type=bind,src={tests},dst=/tests,readonly",
        image(task, version), "bash", "-c",
        f"({script}) >&2; mkdir -p /logs/verifier; bash /tests/test.sh >&2; cat /logs/verifier/reward.txt",
    )  # fmt: skip
    return out.strip()
