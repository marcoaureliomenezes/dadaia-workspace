"""The kernel's child-process runners: UTF-8 text with replacement, or bytes."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from dadaia_workspace.core.skill_owner import load_owner

K = load_owner("dd-bug-resolution", "_platform")
_EMIT = "import sys; sys.stdout.buffer.write(bytes.fromhex(sys.argv[1]))"


def test_run_decodes_utf8_output() -> None:
    done = K.run([sys.executable, "-c", _EMIT, "c3a9"])
    assert (done.returncode, done.stdout, done.stderr) == (0, "é", "")


def test_run_replaces_bytes_that_are_not_utf8() -> None:
    assert K.run([sys.executable, "-c", _EMIT, "e9"]).stdout == "�"


def test_run_sends_input_as_utf8_and_runs_in_cwd(tmp_path: Path) -> None:
    code = "import sys, os; print(sys.stdin.read() + os.getcwd())"
    done = K.run([sys.executable, "-c", code], cwd=tmp_path, input="x")
    assert done.stdout.strip() == f"x{tmp_path.resolve()}"


def test_run_passes_the_env_it_is_given() -> None:
    code = "import os; print(os.environ['KERNEL_PROBE'])"
    done = K.run([sys.executable, "-c", code], env={**os.environ, "KERNEL_PROBE": "7"})
    assert done.stdout.strip() == "7"


def test_run_check_raises_the_called_process_error() -> None:
    with pytest.raises(subprocess.CalledProcessError):
        K.run([sys.executable, "-c", "raise SystemExit(3)"], check=True)


def test_run_does_not_raise_on_a_non_zero_exit() -> None:
    assert K.run([sys.executable, "-c", "raise SystemExit(3)"]).returncode == 3


def test_run_bytes_returns_the_raw_stdout() -> None:
    assert K.run_bytes([sys.executable, "-c", _EMIT, "e9ff"]).stdout == b"\xe9\xff"


def test_run_bytes_feeds_bytes_to_stdin() -> None:
    code = "import sys; sys.stdout.buffer.write(sys.stdin.buffer.read())"
    assert K.run_bytes([sys.executable, "-c", code], input=b"\x00\xe9").stdout == b"\x00\xe9"


def test_popen_streams_decoded_text() -> None:
    proc = K.popen([sys.executable, "-c", _EMIT, "c3a9"])
    out, _ = proc.communicate()
    assert (out, proc.returncode) == ("é", 0)


def test_popen_bytes_streams_raw_bytes() -> None:
    proc = K.popen_bytes([sys.executable, "-c", _EMIT, "e9"])
    out, _ = proc.communicate()
    assert (out, proc.returncode) == (b"\xe9", 0)
