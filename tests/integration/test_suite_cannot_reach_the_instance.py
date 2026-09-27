"""No process the suite spawns can resolve the operator instance it runs inside.

Intent: CONTRACT — bug test-subprocesses-resolve-the-live-instance. Size: MEDIUM
(spawns the interpreter: the bug lives at the process boundary, where the in-process
``_hermetic_cwd`` fixture never reached).

On a self-hosting machine the dev venv IS the instance venv, and a CLI subprocess
registered an ALIVE context plus a cloned repo in the live instance. The isolation is a
property of the process tree, not of each test: ``tests/conftest.py`` fences every
enclosing instance in ``DADAIA_FENCED_ROOTS`` at import, every child inherits it, and
the one resolver never returns a fenced root.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

_SENTINEL = Path(".dadaia") / "states" / "spec_contexts.json"
_PROBE = (
    "from dadaia_workspace.core.workspace_resolver import resolve_workspace_root as r; print(r())"
)


def _workspace(root: Path) -> Path:
    (root / _SENTINEL).parent.mkdir(parents=True)
    (root / _SENTINEL).write_text("{}", encoding="utf-8")
    (root / "repos" / "x").mkdir(parents=True)
    return root


def _resolve_in_child(cwd: Path, fence: str | None) -> subprocess.CompletedProcess[str]:
    """The child keeps the suite's own fence (the interpreter's venv may be an instance's,
    its first rung) and adds *fence*."""
    env = dict(os.environ)
    if fence is not None:
        env["DADAIA_FENCED_ROOTS"] = os.pathsep.join(
            filter(None, (env.get("DADAIA_FENCED_ROOTS"), fence))
        )
    return subprocess.run(
        [sys.executable, "-c", _PROBE],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )


def test_a_child_inside_a_fenced_workspace_cannot_resolve_it(tmp_path: Path) -> None:
    ws = _workspace(tmp_path / "instance")

    open_ = _resolve_in_child(ws / "repos" / "x", fence=None)
    fenced = _resolve_in_child(ws / "repos" / "x", fence=str(ws))

    assert open_.returncode == 0 and Path(open_.stdout.strip()) == ws.resolve(), open_.stderr
    assert fenced.returncode != 0
    assert "No initialized workspace" in fenced.stderr


def test_the_suite_fences_every_instance_enclosing_this_checkout() -> None:
    """Every ancestor of the checkout carrying the workspace sentinel is fenced for the
    whole session, so every child inherits it without a per-test helper."""
    checkout = Path(__file__).resolve().parents[2]
    enclosing = {str(p) for p in checkout.parents if (p / _SENTINEL).is_file()}
    fenced = set(filter(None, os.environ.get("DADAIA_FENCED_ROOTS", "").split(os.pathsep)))
    assert enclosing <= fenced
