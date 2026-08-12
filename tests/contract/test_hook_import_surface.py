"""Hooks never import the DI composition root (F-01, v0.5.0 six-axis review).

Hooks are one-shot processes on the write hot path: every gated tool call spawns a fresh
interpreter, so module-import cost is paid per write. The container is the composition
root — importing it pulls the whole application graph (~2s measured) for a resolution
that core.specs_resolver answers in ~10ms. The seam contract sanctions hooks as DIRECT
importers of the single authority; this test pins the consequence: importing any hook
module must not import ``dadaia_workspace.container`` (deferred function-local imports
of the container are equally forbidden on the resolution path — they would show up here
only if executed, so the gate/inject paths are exercised too).
"""

from __future__ import annotations

import json
import subprocess
import sys

import pytest

_HOOK_MODULES = (
    "dadaia_workspace.hooks.pre_gate",
    "dadaia_workspace.hooks.sdd_gate",
    "dadaia_workspace.hooks.sdd_post_gate",
    "dadaia_workspace.hooks.ctx_inject",
    "dadaia_workspace.hooks.root_whitelist",
    "dadaia_workspace.hooks.venv_guard",
)


@pytest.mark.parametrize("module", _HOOK_MODULES)
def test_importing_a_hook_never_imports_the_container(module: str) -> None:
    code = (
        f"import {module}, sys; "
        "assert 'dadaia_workspace.container' not in sys.modules, 'container imported'"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, timeout=120
    )
    assert result.returncode == 0, result.stderr


def test_gate_resolution_path_never_imports_the_container(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """Execute the gate's actual resolution path (not just the module import) in a
    hermetic workspace and assert the container stays unimported."""
    ws = tmp_path / "ws"
    (ws / ".dadaia" / "states").mkdir(parents=True)
    (ws / ".dadaia" / "states" / "spec_contexts.json").write_text(
        json.dumps({"schema_version": "2", "contexts": []}), encoding="utf-8"
    )
    (ws / "repos" / "demo").mkdir(parents=True)
    code = (
        "import sys\n"
        "from pathlib import Path\n"
        "from dadaia_workspace.hooks import sdd_gate\n"
        f"slug = sdd_gate._context_slug(Path({str(ws / 'repos' / 'demo' / 'f.py')!r}))\n"
        "assert slug == 'demo', slug\n"
        "assert 'dadaia_workspace.container' not in sys.modules, 'container imported'\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        timeout=120,
        env={"WORKSPACE_ROOT": str(ws), "PATH": "/usr/bin:/bin"},
    )
    assert result.returncode == 0, result.stderr
