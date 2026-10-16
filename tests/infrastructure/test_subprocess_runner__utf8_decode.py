"""Every child-process site of the infrastructure decodes a child's bytes as UTF-8 whatever the
parent's locale: each site runs in a fresh interpreter whose locale encoding is ASCII, over a
child that writes the UTF-8 bytes of "é"."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

from tests.helpers.oslib import run, stub_cli

_HOSTILE = {"LC_ALL": "C", "PYTHONUTF8": "0", "PYTHONCOERCECLOCALE": "0"}
_PROGRAM = """
import os, sys
from pathlib import Path
EMIT = "import sys; sys.stdout.buffer.write(bytes.fromhex('c3a9'))"
ARGV = [sys.executable, "-c", EMIT]
tmp = Path(sys.argv[2])

def runner():
    from dadaia_workspace.infrastructure.subprocess_runner import SubprocessProcessRunner
    return SubprocessProcessRunner().run(ARGV).stdout

def certification_run():
    from dadaia_workspace.infrastructure.certification_process import SubprocessCertificationProcess
    return SubprocessCertificationProcess().run(ARGV, cwd=tmp, timeout=30).stdout

def certification_start():
    from dadaia_workspace.infrastructure.certification_process import SubprocessCertificationProcess
    proc = SubprocessCertificationProcess().start(ARGV, cwd=tmp, env=dict(os.environ))
    return proc._process.communicate()[0]

def git_client():
    from dadaia_workspace.infrastructure.git_subprocess import GitSubprocessClient
    return GitSubprocessClient().git(tmp, "config", "user.name")

def interpreter_probe():
    from dadaia_workspace.infrastructure import python_env
    python_env._VERSION_ARGS = ("-c", "import sys; print(*sys.version_info[:3], flush=True); " + EMIT)
    return python_env._interpreter_version(sys.executable) is not None

def venv_python():
    from dadaia_workspace.infrastructure.python_env import VenvPythonEnvironmentManager
    mgr = VenvPythonEnvironmentManager()
    mgr.python_executable = lambda root: sys.executable
    return mgr._run_venv("ws", "-c", EMIT).stdout

def venv_create():
    from dadaia_workspace.core.exceptions import WorkspaceVenvBootstrapError
    from dadaia_workspace.infrastructure.python_env import VenvPythonEnvironmentManager
    mgr = VenvPythonEnvironmentManager()
    mgr._resolve_child_venv_interpreter = lambda: sys.argv[3]
    try:
        mgr.ensure_workspace_venv(str(tmp / "ws"))
    except WorkspaceVenvBootstrapError as refusal:
        return "\\u00e9" in str(refusal)

print(ascii(globals()[sys.argv[1]]()))
"""


@pytest.mark.parametrize(
    ("site", "shown"),
    [
        ("runner", "'\\xe9'"),
        ("certification_run", "'\\xe9'"),
        ("certification_start", "'\\xe9'"),
        ("git_client", "'\\xe9'"),
        ("interpreter_probe", "True"),
        ("venv_python", "'\\xe9'"),
        ("venv_create", "True"),
    ],
)
def test_a_site_decodes_the_childs_bytes_as_utf8_under_a_hostile_locale(
    tmp_path: Path, site: str, shown: str
) -> None:
    run(["git", "init", "-q", str(tmp_path)], check=True)
    run(["git", "-C", str(tmp_path), "config", "user.name", "\u00e9"], check=True)
    emit = "import sys; sys.stderr.buffer.write(bytes.fromhex('c3a9')); sys.exit(1)"
    refuser = stub_cli(tmp_path, "refuser", f"#!python\n{emit}\n")
    env = {**os.environ, **_HOSTILE}

    done = run(
        [sys.executable, "-c", _PROGRAM, site, str(tmp_path), str(refuser)], env=env, cwd=tmp_path
    )

    assert (done.returncode, done.stdout.strip()) == (0, shown), done.stderr
