"""The CLI entry prints non-ASCII marks whatever encoding the host pipe defaults to."""

import os
import subprocess
import sys

_ENTRY = (
    "from rich.console import Console;"
    "from dadaia_workspace.cli import main;"
    "main.app = lambda: Console().print('\\u2713 done');"
    "main._safe_app()"
)


def test_safe_app_prints_the_check_mark_on_a_cp1252_pipe():
    env = {**os.environ, "PYTHONIOENCODING": "cp1252", "PYTHONUTF8": "0"}
    done = subprocess.run([sys.executable, "-c", _ENTRY], env=env, capture_output=True)
    assert (done.returncode, done.stdout.decode("utf-8").strip()) == (0, "✓ done")
