"""Intent: CONTRACT — AC1.3, AC1.4, AC7.3 (T-050-18): no onboarding step can stall.

Over random real-state starts (remote unborn / principal only / both, a tag or not, a
session identity or not), the loop takes the printed step, executes its fix line (the
operator placeholders ``<name>``/``<clone-url>`` are the only substitutions; the ``agent``
step runs a scripted stand-in that fills memory) and asserts I3 — the step is no longer
pending — and I4 — the printed step's index strictly increases, so the loop ends within
``len(STEP_IDS)`` iterations.

MEDIUM: real git over ``file://`` bare remotes; the workspace pre-push hook is pointed
at an empty hooks dir (the chokepoint is T-050-14's contract, not this one's).
"""

from __future__ import annotations

import json
import os
import shlex
import subprocess
import tempfile
from pathlib import Path

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app
from dadaia_workspace.core.harness_registry import L1_ENTRY_HARNESSES
from dadaia_workspace.core.invocation import alive_context_trees
from dadaia_workspace.features.workspace.onboarding import STEP_IDS, Step, next_step
from dadaia_workspace.features.workspace.service import WorkspaceService
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
from dadaia_workspace.infrastructure.python_env import VenvPythonEnvironmentManager

pytest.importorskip("fcntl")

_runner = CliRunner()


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


def _remote(parent: Path, branches: tuple[str, ...], tag: bool) -> Path:
    bare = parent / "proj.git"
    _git(parent, "init", "-q", "--bare", "-b", "main", str(bare))
    if branches:
        seed = parent / "seed"
        _git(parent, "init", "-q", "-b", branches[0], str(seed))
        (seed / "README.md").write_text("seed\n", encoding="utf-8")
        _git(seed, "add", "README.md")
        _git(seed, "commit", "-qm", "seed")
        for branch in branches[1:]:
            _git(seed, "branch", branch)
        if tag:
            _git(seed, "tag", "v1.4.2")
        _git(seed, "push", "-q", "--tags", bare.as_uri(), *branches)
    return bare


def _fill_memory(root: Path) -> None:
    """The scripted stand-in for the ``agent`` step: an audit that writes real memory."""
    for specs in alive_context_trees(root).values():
        for stub in ("ARCHITECTURE.md", "QUALITY.md"):
            (specs / "memory" / stub).write_text(f"# {stub}\n\naudited\n", encoding="utf-8")
        catalog = specs / "memory" / "product" / "catalog.json"
        catalog.parent.mkdir(parents=True, exist_ok=True)
        catalog.write_text(json.dumps({"features": [{"slug": "core"}]}), encoding="utf-8")


def _run_fix(step: Step, root: Path, bare: Path) -> None:
    if step.kind == "agent":
        _fill_memory(root)
        return
    argv = shlex.split(step.command)
    assert Path(argv[0]).name.startswith("dadaia"), step.command
    argv = [{"<name>": "proj", "<clone-url>": bare.as_uri()}.get(a, a) for a in argv[1:]]
    done = _runner.invoke(app, argv)
    assert done.exit_code == 0, f"{step.command}\n{done.output}"


@pytest.fixture(autouse=True)
def _git_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    hooks = tmp_path / "no-hooks"
    hooks.mkdir()
    pairs = {"core.hooksPath": str(hooks), "user.name": "T", "user.email": "t@example.invalid"}
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(tmp_path / "gitconfig"))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    monkeypatch.setenv("GIT_CONFIG_COUNT", str(len(pairs)))
    for n, (key, value) in enumerate(pairs.items()):
        monkeypatch.setenv(f"GIT_CONFIG_KEY_{n}", key)
        monkeypatch.setenv(f"GIT_CONFIG_VALUE_{n}", value)
    for var in ("CLAUDE_CODE_SESSION_ID", "CODEX_SESSION_ID", "CODEX_THREAD_ID", "DADAIA_CONTEXT"):
        monkeypatch.delenv(var, raising=False)


@settings(
    max_examples=12, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@given(
    branches=st.sampled_from([(), ("main",), ("main", "develop")]),
    tag=st.booleans(),
    session=st.sampled_from([None, "sess_prop01"]),
)
def test_every_command_fix_clears_its_step_and_the_loop_advances(
    branches: tuple[str, ...], tag: bool, session: str | None, tmp_path: Path
) -> None:
    cwd = Path.cwd()
    with tempfile.TemporaryDirectory(dir=tmp_path) as scratch:
        base = Path(scratch)
        root = base / "ws"
        root.mkdir()
        WorkspaceService(
            public_assets=FileSystemPublicAssetManager(),
            python_env=VenvPythonEnvironmentManager(),
        ).init(root, harnesses=L1_ENTRY_HARNESSES)
        bare = _remote(base, branches, tag and bool(branches))
        env_before = os.environ.pop("DADAIA_SESSION_ID", None)
        if session:
            os.environ["DADAIA_SESSION_ID"] = session
        os.chdir(root)
        try:
            seen: list[int] = []
            for _ in range(len(STEP_IDS) + 1):
                step = next_step(root, alive_context_trees(root), None, session)
                if step is None:
                    break
                index = STEP_IDS.index(step.id)
                assert not seen or index > seen[-1], f"I4: {step.id} after {STEP_IDS[seen[-1]]}"
                seen.append(index)
                _run_fix(step, root, bare)
                after = next_step(root, alive_context_trees(root), None, session)
                assert after is None or after.id != step.id, f"I3: {step.id} still pending"
            else:
                pytest.fail(f"I4: the loop did not end within {len(STEP_IDS)} steps")
            assert ("bind" in [STEP_IDS[i] for i in seen]) == (session is not None)  # AC7.3
            assert STEP_IDS[seen[-1]] == "publish"
        finally:
            os.chdir(cwd)
            os.environ.pop("DADAIA_SESSION_ID", None)
            if env_before is not None:
                os.environ["DADAIA_SESSION_ID"] = env_before
