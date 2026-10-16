"""Every CLI entry prints non-ASCII marks whatever encoding the host pipe defaults to."""

import os
import subprocess
import sys

import pytest

_STUB = "from rich.console import Console;from dadaia_workspace.cli import main;{body};"
_ENTRIES = {
    "safe_app": "main._safe_app()",
    "python-m": "import runpy;runpy.run_module('dadaia_workspace', run_name='__main__')",
}


def _run(body: str, entry: str) -> subprocess.CompletedProcess[bytes]:
    env = {**os.environ, "PYTHONIOENCODING": "cp1252", "PYTHONUTF8": "0"}
    code = _STUB.format(body=f"main.app = lambda: {body}") + entry
    return subprocess.run([sys.executable, "-c", code], env=env, capture_output=True)


@pytest.mark.parametrize("entry", _ENTRIES.values(), ids=_ENTRIES.keys())
def test_entry_prints_the_check_mark_on_a_cp1252_pipe(entry: str) -> None:
    done = _run("Console().print('\\u2713 done')", entry)
    assert (done.returncode, done.stdout.decode("utf-8").strip()) == (0, "✓ done")


def test_stderr_keeps_its_error_handler_for_a_lone_surrogate() -> None:
    done = _run("print('bad \\udcff', file=__import__('sys').stderr)", _ENTRIES["safe_app"])
    assert (done.returncode, done.stderr) == (0, b"bad \\udcff\n")
