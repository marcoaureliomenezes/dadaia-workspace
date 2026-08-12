"""The no-real-venv backstop must hold for EVERY fixture scope.

Bug test-suite-real-venv-and-ci-longpole: ``_no_real_venv_in_tests`` was a
function-scoped autouse fixture, but pytest instantiates higher-scoped fixtures FIRST —
so a module- or session-scoped fixture calling ``WorkspaceService.init()`` (e.g. the
``projected`` fixture in test_claude_scaffold_is_loadable.py) ran the REAL
``ensure_workspace_venv`` before the guard existed, building a full venv + editable pip
install per module (~17 s unloaded, 159 s on a loaded host) — the exact disk/time cost
the backstop exists to prevent.

This module reproduces that escape with its own module-scoped fixture: if the backstop
ever regresses to a scope below ``module``, the fixture builds a real venv and the test
fails on the materialised interpreter.
"""

from pathlib import Path

import pytest

from dadaia_workspace.infrastructure.python_env import VenvPythonEnvironmentManager

pytestmark = pytest.mark.unit


@pytest.fixture(scope="module")
def module_scoped_venv(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Calls the venv seam from module scope — exactly how the escape happened."""
    workspace = tmp_path_factory.mktemp("backstop-scope") / "ws"
    workspace.mkdir(parents=True)
    VenvPythonEnvironmentManager().ensure_workspace_venv(str(workspace))
    return workspace


def test_backstop_covers_module_scoped_fixtures(module_scoped_venv: Path) -> None:
    venv_dir = module_scoped_venv / ".dadaia" / ".venv"
    assert venv_dir.is_dir(), "the backstop stub must still materialise the venv dir"
    # The stub creates a BARE directory. A real venv materialises pyvenv.cfg and
    # interpreter binaries — their presence means the guard did not apply.
    contents = sorted(p.name for p in venv_dir.iterdir())
    assert contents == [], (
        f"a REAL venv was built inside a module-scoped fixture (found {contents}) — "
        "the _no_real_venv_in_tests backstop no longer covers scopes above 'function'"
    )
