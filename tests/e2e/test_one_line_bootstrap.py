"""``dadaia init <dir> --harness claude --repo <url>`` end to end, through the console script.

Intent: CONTRACT — 0.4.7 FR1 / AC1.1 (T-047-79).

Size: LARGE, justified — AC1.1 is a statement about the *installed* distribution, not
about any in-process wiring: an operator types one line and the workspace that appears
must pass its own ``doctor``. Every seam below (venv provisioning, asset install, the
clone, the context store, the session binding, the git chokepoint, the doctor's zone
walk) is crossed by a REAL ``dadaia`` process, so nothing this test asserts survives
being demoted to the CLI runner. This is the suite's ONE test that exercises the
installed console script; every narrower contract of FR1 is already covered MEDIUM in
``tests/integration/test_init_with_repo.py``.

Hermetic by construction — no network, no container:

* ``--repo`` is a LOCAL bare repository, so the clone is the real git path with no remote.
* ``HOME`` is a tmp dir and the child environment carries no inherited ``DADAIA_*``.
* The workspace venv is pre-seeded (see ``_seed_venv_entrypoint``). ``tests/conftest.py``'s
  ``_no_real_venv_in_tests`` backstop is an in-process monkeypatch and cannot reach a
  child process, so this test honours the same law on the child's own terms: it uses
  ``ensure_workspace_venv``'s documented idempotent-repair contract (a venv directory
  that already carries an executable ``dadaia`` entrypoint is left alone), which is also
  exactly what doctor's VENV-1 check asserts. No ``venv.create``, no ``pip install``.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

from dadaia_workspace.core import workspace_layout
from dadaia_workspace.core.platform import PLATFORM

pytestmark = [pytest.mark.e2e, pytest.mark.slow]

_TIMEOUT = 180.0

_CONSOLE_SCRIPT = Path(sys.executable).parent / f"dadaia{PLATFORM.venv_exe_suffix}"


def _child_env(home: Path) -> dict[str, str]:
    """A clean environment: no inherited ``DADAIA_*``, a tmp ``HOME``, a git identity."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("DADAIA_")}
    env.update(
        HOME=str(home),
        XDG_CONFIG_HOME=str(home / ".config"),
        PATH=f"{_CONSOLE_SCRIPT.parent}{os.pathsep}{env.get('PATH', '')}",
        COLUMNS="200",
        NO_COLOR="1",
        GIT_AUTHOR_NAME="t",
        GIT_AUTHOR_EMAIL="t@example.invalid",
        GIT_COMMITTER_NAME="t",
        GIT_COMMITTER_EMAIL="t@example.invalid",
        GIT_CONFIG_GLOBAL=str(home / "gitconfig"),
        GIT_CONFIG_SYSTEM=os.devnull,
    )
    return env


def _dadaia(
    *argv: str, cwd: Path, home: Path, extra_env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    env = _child_env(home)
    env.update(extra_env or {})
    return subprocess.run(
        [str(_CONSOLE_SCRIPT), *argv],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        timeout=_TIMEOUT,
    )


def _git(*args: str, cwd: Path, home: Path) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, env=_child_env(home))


def _seed_venv_entrypoint(workspace: Path) -> None:
    """Materialise ``.dadaia/.venv`` with an executable ``dadaia`` entrypoint.

    The child process' equivalent of the suite's no-real-venv backstop: with the
    entrypoint already present, ``ensure_workspace_venv`` takes its idempotent no-op
    path and the test never builds a 30-50 MB venv nor runs ``pip``.
    """
    bin_dir = workspace / ".dadaia" / ".venv" / PLATFORM.venv_scripts_dir
    bin_dir.mkdir(parents=True)
    entry = bin_dir / f"dadaia{PLATFORM.venv_exe_suffix}"
    entry.write_text(f"#!{sys.executable}\n", encoding="utf-8")
    entry.chmod(0o755)


@pytest.fixture()
def home(tmp_path: Path) -> Path:
    path = tmp_path / "home"
    path.mkdir()
    return path


@pytest.fixture()
def origin(tmp_path: Path, home: Path) -> Path:
    """A local bare repo ``demo-project.git`` carrying one commit on ``main``."""
    bare = tmp_path / "origin" / "demo-project.git"
    bare.parent.mkdir(parents=True)
    _git("init", "--bare", "--initial-branch=main", str(bare), cwd=tmp_path, home=home)
    work = tmp_path / "seed"
    work.mkdir()
    _git("init", "--initial-branch=main", cwd=work, home=home)
    (work / "README.md").write_text("# demo-project\n", encoding="utf-8")
    _git("add", "README.md", cwd=work, home=home)
    _git("commit", "-m", "seed", cwd=work, home=home)
    _git("remote", "add", "origin", str(bare), cwd=work, home=home)
    _git("push", "-u", "origin", "main", cwd=work, home=home)
    return bare


@pytest.mark.skipif(
    not _CONSOLE_SCRIPT.is_file(),
    reason=f"the dadaia console script is not installed next to {sys.executable}",
)
def test_one_line_bootstrap_yields_a_doctor_clean_workspace(
    tmp_path: Path, home: Path, origin: Path
) -> None:
    """AC1.1: one line, then ``doctor`` exit 0 and the repo ALIVE as ``main_repo``."""
    workspace = tmp_path / "demo"
    workspace.mkdir()
    _seed_venv_entrypoint(workspace)

    init = _dadaia(
        "init", "demo", "--harness", "claude", "--repo", str(origin), cwd=tmp_path, home=home
    )
    assert init.returncode == 0, f"init failed:\n{init.stdout}\n{init.stderr}"

    # With --repo the closing notes are replaced by the binding's export lines.
    assert "Sessions launch at the workspace root." not in init.stdout
    assert "instructionFiles" not in init.stdout
    assert "Projects live under repos/" not in init.stdout

    doctor = _dadaia("doctor", cwd=workspace, home=home)
    assert doctor.returncode == 0, f"doctor is not clean:\n{doctor.stdout}\n{doctor.stderr}"

    # The operator's next act is `eval $(...)` on the printed export lines — the binding
    # those lines carry is what makes `context show` answer about THIS workspace.
    binding = dict(re.findall(r"export (DADAIA_[A-Z_]+)=(\S+)", init.stdout))
    assert set(binding) == {"DADAIA_CONTEXT", "DADAIA_SESSION_ID"}, init.stdout

    show = _dadaia("context", "show", "--json", cwd=workspace, home=home, extra_env=binding)
    assert show.returncode == 0, f"context show failed:\n{show.stdout}\n{show.stderr}"
    record = json.loads(show.stdout)
    assert record["main_repo"] == "demo-project"
    assert record["state"] == "alive"

    # The git chokepoint is installed from — and byte-equal to — the shipped gate.
    target, source = workspace_layout.INSTALLED_GIT_HOOKS[0]
    installed = workspace / "repos" / "demo-project" / ".git" / "hooks" / target
    assert installed.read_bytes() == (workspace_layout.public_scripts_dir() / source).read_bytes()
