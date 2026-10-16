"""`tests.helpers.oslib` is the kernel's names and one launcher builder, nothing else."""

from __future__ import annotations

import stat
import sys
from pathlib import Path

import pytest

from dadaia_workspace.core.skill_owner import load_owner
from tests.helpers import oslib

K = load_owner("dd-bug-resolution", "_platform")
pytestmark = pytest.mark.medium
_RE_EXPORTED = [
    "Caps", "Undecodable", "canonical_cli", "cli_path", "command", "decode", "detect",
    "effective_uid",
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


def test_make_readonly_takes_the_write_bits_and_make_writable_gives_the_owners_back(
    tmp_path: Path,
) -> None:
    path = tmp_path / "f"
    oslib.write_text(path, "x")
    oslib.make_readonly(path)
    assert stat.S_IMODE(path.stat().st_mode) & 0o222 == 0
    oslib.make_writable(path)
    assert stat.S_IMODE(path.stat().st_mode) & 0o200 == 0o200


def test_a_readonly_file_refuses_a_write_where_permissions_are_enforced(tmp_path: Path) -> None:
    path = tmp_path / "f"
    oslib.write_text(path, "x")
    oslib.make_readonly(path)
    assert oslib.PERMISSIONS_ENFORCED is (oslib.effective_uid() not in (None, 0))
    if oslib.PERMISSIONS_ENFORCED:
        with pytest.raises(PermissionError):
            oslib.write_text(path, "y")


def test_run_line_runs_a_finished_line_in_the_host_shell() -> None:
    line = oslib.command(sys.executable, "-c", "print(6 * 7)")
    assert oslib.run_line(line).stdout.strip() == "42"


def test_the_shells_a_line_is_judged_in_follow_the_capabilities_it_is_spelled_for() -> None:
    assert oslib.shells_for(oslib.detect("linux")) == ["sh", "bash"]
    assert oslib.shells_for(oslib.detect("darwin")) == ["sh", "bash"]
    assert oslib.shells_for(oslib.detect("win32")) == ["cmd", "powershell", "pwsh", "bash"]
