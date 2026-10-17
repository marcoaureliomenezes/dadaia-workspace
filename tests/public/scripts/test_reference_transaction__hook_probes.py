"""The venv layouts the shell hooks probe are the kernel's, for both hosts: each hook is a
shell file that cannot ask `venv_tool`, so this is the one test that holds its probe to it.

Owner: dd-sw-engineer-sr
"""

from __future__ import annotations

import re
from pathlib import Path, PurePosixPath

import pytest

import dadaia_workspace
from dadaia_workspace.infrastructure.runtime_transforms.hook_wrappers import VENV_PYTHON
from tests.helpers.oslib import detect, read_text, venv_tool

_SCRIPTS = Path(dadaia_workspace.__file__).parent / "public" / "scripts"
_PROBE = re.compile(r"(?:\$1|\.venv)/((?:bin|Scripts)/[\w.]+)")


def _kernel(tool: str) -> set[str]:
    venv = PurePosixPath("v")
    return {
        venv_tool(venv, tool, detect(host)).relative_to(venv).as_posix()
        for host in ("linux", "win32")
    }


@pytest.mark.parametrize(
    ("text", "tool"),
    [
        pytest.param(
            read_text(_SCRIPTS / "reference-transaction.sh"), "python", id="reference-transaction"
        ),
        pytest.param(read_text(_SCRIPTS / "pre-push-ci-gate.sh"), "dadaia", id="pre-push"),
        pytest.param(VENV_PYTHON, "python", id="wrappers"),
    ],
)
def test_a_hook_probes_the_kernels_layout_of_both_hosts(text: str, tool: str) -> None:
    assert set(_PROBE.findall(text)) == _kernel(tool)
