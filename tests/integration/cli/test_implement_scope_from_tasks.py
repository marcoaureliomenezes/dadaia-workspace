"""FR3 (v0.1.68) — implement write-scope is derived from TASKS.md (executed-path).

RED-first proof for ``pipeline-does-not-derive-write-scope-from-tasks`` (SPEC
AC3(repro)): a fixture ``TASKS.md`` carries a ``[-]`` task whose ``Write set:`` lists
``foo/bar.py``. Driving a real ``dadaia lifecycle pipeline`` implement step — with NO
``--write-scope`` flag — must produce a built request whose ``allowed_paths`` contains
``foo/bar.py``. On current (pre-FR3) code ``extra_allowed_paths`` is populated ONLY
from ``--write-scope``, so this assertion fails.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace import container
from dadaia_workspace.cli.main import app
from dadaia_workspace.core.models.lifecycle import AgentRunResult, AgentRuntimeKind
from dadaia_workspace.core.protocols.agent_runtime import AgentRuntimePort
from dadaia_workspace.features.workspace.service import WorkspaceService
from dadaia_workspace.infrastructure.fake_runtime import FakeAgentRuntime
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
from dadaia_workspace.infrastructure.python_env import VenvPythonEnvironmentManager

_runner = CliRunner()
_CONTEXT = "dadaia-workspace"
_RELEASE = "v0168-fr3-repro"


def _init_workspace(path: Path) -> Path:
    WorkspaceService(
        public_assets=FileSystemPublicAssetManager(),
        python_env=VenvPythonEnvironmentManager(),
    ).init(path)
    return path


def _seed_tasks(workspace: Path, release: str) -> None:
    """Write a fixture ``TASKS.md`` with one reserved ``[-]`` task and a real
    ``Write set:`` — resolved via the ``dadaia-workspace`` fallback specs tree
    (``workspace_root/specs`` when no ``repos/dadaia-workspace/specs`` exists)."""
    tasks_dir = workspace / "specs" / "releases" / release
    tasks_dir.mkdir(parents=True, exist_ok=True)
    (tasks_dir / "TASKS.md").write_text(
        """# TASKS — fixture

### T-fr3-01 — implement the thing `[-]`
- **Owner:** software-engineer
- **Write set:** `foo/bar.py`
- **Task:** implement the thing.
""",
        encoding="utf-8",
    )


def _capture_first_fake_request(monkeypatch: pytest.MonkeyPatch) -> list[object]:
    """Swap FAKE-kind adapters for a request-recording FakeAgentRuntime."""
    real_build = container.build_agent_runtime
    captured: list[object] = []

    def fake_build(
        kind: AgentRuntimeKind, *, cwd: Path | None = None, model: object = None
    ) -> AgentRuntimePort:
        if kind is AgentRuntimeKind.FAKE:
            runtime = FakeAgentRuntime(
                on_run=lambda req: captured.append(req) if not captured else None
            )
            return runtime
        return real_build(kind, cwd=cwd)

    monkeypatch.setattr(container, "build_agent_runtime", fake_build)
    return captured


def test_implement_scope_derived_from_tasks(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC3(repro) RED half — T-68-05.

    Drives ``dadaia lifecycle pipeline`` with NO ``--write-scope`` flag against a
    fixture TASKS.md carrying a reserved ``[-]`` task with ``Write set: `foo/bar.py```.
    The implement step's built request ``allowed_paths`` must contain ``foo/bar.py``.
    """
    workspace = _init_workspace(tmp_path)
    _seed_tasks(workspace, _RELEASE)
    captured = _capture_first_fake_request(monkeypatch)
    monkeypatch.chdir(workspace)

    _runner.invoke(
        app,
        [
            "lifecycle",
            "pipeline",
            "--release-id",
            _RELEASE,
            "--run-id",
            "pipe-fr3-repro",
            "--harness",
            "fake",
            "--json",
        ],
    )

    assert captured, "the fake implement worker must have been invoked at least once"
    implement_request = captured[0]
    assert "foo/bar.py" in implement_request.allowed_paths, (
        "the implement step's allowed_paths must include the TASKS.md-derived write "
        f"set even with no --write-scope flag; got {implement_request.allowed_paths!r}"
    )
