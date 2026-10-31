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
T3 = "t3-discovery"

# The documented onboarding, typed by hand.
_INIT = "dadaia init /workspace --harness claude --repo file:///srv/demo.git"
HAND = {"candidate": f"{_INIT} && /workspace/.dadaia/.venv/bin/dadaia specs init --context demo"}
# T3, candidate only, as typed inside the image: the lib wheel is installed by path, its
# dependencies resolve from the image's own environment, the venv's dadaia is called by path, the entry goes in a real lane.
_D = "/workspace/.dadaia/.venv/bin/dadaia"
_ONBOARD = "python3 -m venv /tmp/v && /tmp/v/bin/pip install -q /lib/*.whl && /tmp/v/bin/dadaia init /workspace --harness claude"
_FILE = (
    "python3 /workspace/.agents/skills/dd-backlog-definition/scripts/backlog.py new"
    " --title 'subtract in calc.py' --description 'add subtract with tests to calc.py'"
    " --provenance p try-it --specs"
)
ONBOARDED_NO_SPECS_T3 = f"{_ONBOARD} --repo file:///srv/demo.git"
ONBOARDED_T3 = f"{ONBOARDED_NO_SPECS_T3} && {_D} specs init --context demo"
RENAMED_T3 = (
    f"{_ONBOARD} && {_D} context create myproj --main-repo file:///srv/demo.git"
    f" && {_D} specs init --context myproj && {_FILE} /workspace/repos/demo/specs"
)
_RC = "/workspace/worktrees/demo/0.1.0/rc-1/wt-rc/specs"
_RUN = "python3 /workspace/.agents/skills"
_NEW = f"{_RUN}/dd-release-implementation/scripts/release.py new 0.1.0 --specs {_RC}"
_RC_TREE = f"{ONBOARDED_T3} && {_D} worktree new demo 0.1.0/rc-1/wt-rc"
STUB_T3 = f"{_RC_TREE} && {_NEW}"
SPEC_T3 = (
    f"{STUB_T3} && sed -i 's/(Describe the problem this release solves.)/Add a subtract function"
    f" with tests to calc.py./' {_RC}/releases/0.1.0/rc-1/SPEC.md"
)
TRACED_T3 = (
    f"{_RC_TREE} && {_FILE} {_RC} && {_NEW} --origin backlog:try-it"
    f" && {_RUN}/dd-backlog-definition/scripts/backlog.py exit try-it"
    f" --disposition delivered --release 0.1.0 --specs {_RC}"
)
HAND_T3 = (
    f"{ONBOARDED_T3} && {_D} worktree new demo 0.1.0/wt-backlog-x"
    f" && {_FILE} /workspace/worktrees/demo/0.1.0/wt-backlog-x/specs"
)
REJECTED_T3 = (
    f"{HAND_T3} && {_RUN}/dd-backlog-definition/scripts/backlog.py exit try-it"
    " --disposition rejected --reason no --specs /workspace/worktrees/demo/0.1.0/wt-backlog-x/specs"
)
# One act each, beside an onboarded workspace: the grader rewards onboarding and nothing past it.
_MAIN = "/workspace/repos/demo/specs"
_HAND = "mkdir -p {d} && echo x > {d}/hand.json"
WORKTREE_ONLY_T3 = f"{ONBOARDED_T3} && {_D} worktree new demo 0.1.0/wt-backlog-x"
MAIN_BACKLOG_T3 = f"{ONBOARDED_T3} && {_FILE} {_MAIN}"
MAIN_SPEC_T3 = f"{ONBOARDED_T3} && {_RUN}/dd-release-implementation/scripts/release.py new 0.1.0 --specs {_MAIN}"
VERDICT_T3 = f"{ONBOARDED_T3} && " + _HAND.format(d="/workspace/.dadaia/states/verdicts/demo")
_RECORD = (
    'mkdir -p /workspace/.dadaia/sessions && python3 -c "import json,datetime as d;'
    "json.dump({'session_id':'s1','last_seen_at':d.datetime.now(d.UTC).isoformat()},"
    "open('/workspace/.dadaia/sessions/s1.json','w'))\""
)
SESSION_T3 = f"{ONBOARDED_T3} && {_RECORD}"
REAPED_T3 = (
    f"{SESSION_T3} && mkdir -p /workspace/.dadaia/reaped/20260101/sessions"
    " && mv /workspace/.dadaia/sessions/s1.json /workspace/.dadaia/reaped/20260101/sessions/"
)
DOCTOR_ERROR_T3 = f"{ONBOARDED_T3} && rm -rf /workspace/.agents/skills/dd-backlog-definition"
# The project's code moved: each act is a change to calc.py beside an onboarded workspace.
_EDIT = "echo 'def subtract(a, b): return a - b' >> calc.py"
_CALC = f"{ONBOARDED_T3} && cd /workspace/repos/demo && "
CALC_UNCOMMITTED_T3 = f"{_CALC}{_EDIT}"
CALC_COMMIT_T3 = f"{_CALC}{_EDIT} && git commit -qam sub"
CALC_BRANCH_T3 = f"{_CALC}git checkout -q -b subtract && {_EDIT} && git commit -qam sub"
CALC_MERGE_T3 = (
    f"{CALC_BRANCH_T3} && git checkout -q feature/0.1.0 && git merge -q --no-edit subtract"
)
CALC_PUSH_T3 = (
    f"{ONBOARDED_T3} && git clone -q /srv/demo.git /root/demo && cd /root/demo"
    f" && {_EDIT} && git commit -qam sub && git push -q origin main"
)
CALC_WORKTREE_T3 = (
    f"{_CALC}git worktree add -q -b feat /root/wt && cd /root/wt && {_EDIT} && git commit -qam sub"
)
BASELINED_T3 = f"{ONBOARDED_T3} && {_D} context baseline demo"


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
