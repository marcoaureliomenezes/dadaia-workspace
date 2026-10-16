"""`tests.helpers.oslib` is the kernel's names and one launcher builder, nothing else."""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.core.skill_owner import load_owner
from tests.helpers import oslib

K = load_owner("dd-bug-resolution", "_platform")
pytestmark = pytest.mark.medium
_RE_EXPORTED = [
    "Caps", "Undecodable", "canonical_cli", "cli_path", "command", "decode", "detect",
    "git_line", "head", "home_env", "is_executable", "is_fully_qualified", "is_link", "link",
    "make_executable", "make_writable", "norm_sep", "pid_alive", "popen", "popen_bytes",
    "python_in", "quote", "read_text", "replace", "run", "run_bytes", "spell", "venv_dir",
    "venv_tool", "write_text",
]  # fmt: skip


@pytest.mark.parametrize("name", _RE_EXPORTED)
def test_a_name_of_the_helper_is_the_kernels_own_object(name: str) -> None:
    assert getattr(oslib, name) is getattr(K, name)


def test_a_stub_cli_is_started_by_its_path_without_a_shell(tmp_path: Path) -> None:
    cli = oslib.stub_cli(tmp_path, "dadaia", "#!python\nimport sys\nprint('hi', *sys.argv[1:])\n")
    assert oslib.run([str(cli), "a"]).stdout.strip() == "hi a"


def test_a_stub_cli_path_carries_the_host_exe_suffix(tmp_path: Path) -> None:
    cli = oslib.stub_cli(tmp_path, "dadaia", "#!python\npass\n")
    assert cli == tmp_path / f"dadaia{oslib.detect().exe_suffix}"
    assert cli.is_file()
