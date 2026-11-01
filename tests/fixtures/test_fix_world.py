"""The host spellings the refusal worlds use, judged on a posix and a faked win32 host."""

import pytest

from tests.fixtures.fix_world import _host_path, _repo_cli
from tests.helpers.oslib import detect


@pytest.mark.parametrize(
    ("platform", "printed", "host"),
    [
        ("linux", "/c/Users/Shared/ws", "/c/Users/Shared/ws"),
        ("win32", "/c/Users/Shared/ws", "c:/Users/Shared/ws"),
        ("win32", "D:/already/host", "D:/already/host"),
    ],
)
def test_a_posix_shell_path_becomes_the_hosts_own(platform: str, printed: str, host: str) -> None:
    assert _host_path(printed, detect(platform)) == host


@pytest.mark.parametrize(
    ("platform", "line"),
    [
        ("linux", "../../.dadaia/.venv/bin/dadaia context dead proj"),
        ("win32", "../../.dadaia/.venv/Scripts/dadaia.exe context dead proj"),
    ],
)
def test_the_clone_relative_cli_line_names_the_hosts_launcher(platform: str, line: str) -> None:
    assert _repo_cli("context", "dead", "proj", caps=detect(platform)) == line
