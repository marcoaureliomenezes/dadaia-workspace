"""The kernel's process liveness, listener scan and file-owner facts."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from dadaia_workspace.core.skill_owner import load_owner
from tests.helpers.oslib import write_text

K = load_owner("dd-bug-resolution", "_platform")
POSIX, WIN = K.detect("linux"), K.detect("win32")
_SS = (
    "State  Recv-Q Send-Q Local Address:Port Peer Address:Port Process\n"
    'LISTEN 0 4096 127.0.0.1:3000 0.0.0.0:* users:(("node",pid=123,fd=19))\n'
    "LISTEN 0 4096 *:3001 *:*\n"
    'LISTEN 0 4096 [::]:3002 [::]:* users:(("py",pid=124,fd=3))\n'
)


def test_the_running_pid_is_alive_and_an_exited_child_is_not() -> None:
    child = subprocess.Popen([sys.executable, "-c", "pass"])
    child.wait()
    assert (K.pid_alive(os.getpid()), K.pid_alive(child.pid)) == (True, False)


def test_a_windows_host_asks_the_windows_probe(monkeypatch: pytest.MonkeyPatch) -> None:
    asked: list[int] = []
    monkeypatch.setattr(K, "_win_alive", lambda pid: asked.append(pid) or False)
    assert K.pid_alive(4242, WIN) is False
    assert asked == [4242]


def test_ss_lines_parse_to_port_bind_and_pid() -> None:
    assert [K.parse_ss_line(line) for line in _SS.splitlines()] == [
        None,
        (3000, "127.0.0.1", 123),
        (3001, "0.0.0.0", None),
        (3002, "::", 124),
    ]


def test_listeners_read_the_cmdline_of_each_pid(tmp_path: Path) -> None:
    proc = tmp_path / "proc"
    (proc / "123").mkdir(parents=True)
    (proc / "123" / "cmdline").write_bytes(b"node\0server.js\0")
    found = K.listeners(proc=proc, ss=lambda: _SS)
    assert [(f.port, f.bind, f.pid, f.cmdline) for f in found] == [
        (3000, "127.0.0.1", 123, "node server.js"),
        (3001, "0.0.0.0", None, ""),
        (3002, "::", 124, ""),
    ]


def test_listeners_are_unknown_where_there_is_no_proc_tree(tmp_path: Path) -> None:
    assert K.listeners(proc=tmp_path / "absent", ss=lambda: _SS) is None


def test_listeners_are_unknown_when_ss_cannot_run(tmp_path: Path) -> None:
    assert K.listeners(proc=tmp_path, ss=lambda: None) is None


def test_the_owner_of_a_file_is_the_effective_user_or_unknown_together(tmp_path: Path) -> None:
    path = tmp_path / "f"
    write_text(path, "x")
    owner, uid = K.file_owner(path), K.effective_uid()
    assert (owner is None) == (uid is None)
    assert owner is None or owner[0] == uid


def test_can_write_a_fresh_file(tmp_path: Path) -> None:
    path = tmp_path / "f"
    write_text(path, "x")
    assert (K.can_write(path), K.can_write(tmp_path / "absent")) == (True, False)
