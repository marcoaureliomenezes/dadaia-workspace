"""Unit tests for the pre-push CI gate runner-resolution probe.

T-010-26 / bug pre-push-gate-cannot-locate-workspace-venv. The gate
(`public/scripts/pre-push-ci-gate.sh`) must resolve the dadaia runner in this
priority order:

  1. walk UP from the repo root to ``<ws>/.dadaia/.venv/bin/dadaia``
  2. repo-local ``.venv/bin/dadaia``
  None found → fail CLOSED with a clear error.

These tests build fake directory trees + stub executables and drive the real
shell script through ``bash`` in ``--probe-only`` mode, which prints the
resolved runner label and exits 0 (or fails closed with exit 1). They are
Linux-only by the same convention as the other shell-hook subprocess suites
(`tests/integration/test_hooks.py`): bash is required and the probe is a POSIX
shell contract.

CRIT-adjacent (never-push-red): the fail-closed row (none-found) is the load-bearing one.
"""

from __future__ import annotations

import shutil
import stat
import subprocess
import sys
from pathlib import Path

import pytest

import dadaia_workspace

# Shell-script subprocess tests require bash; Linux-only (see test_hooks.py).
pytestmark = pytest.mark.skipif(
    sys.platform != "linux",
    reason="pre-push-ci-gate.sh probe is a bash contract (Linux only)",
)

GATE_SCRIPT = Path(dadaia_workspace.__file__).parent / "public" / "scripts" / "pre-push-ci-gate.sh"

# Absolute bash path so the subprocess does not depend on the controlled PATH.
_BASH = shutil.which("bash") or "/usr/bin/bash"

# System bin dirs appended AFTER the stub dir, so real `dirname`/coreutils
# resolve while the stub `git`/`poetry`/`dadaia` keep precedence. The probe
# subprocess PATH is built from scratch (stub dir + these), so a host poetry
# or dadaia elsewhere (workspace venv, ~/.local/bin, poetry env) cannot leak
# in. Only a real runner inside the system bin dirs themselves could — guard
# exactly that, not the host PATH (asserting on the host PATH broke collection
# under a `poetry run` invocation).
_SYS_BINS = [Path("/usr/bin"), Path("/bin")]
for _tool in ("poetry", "dadaia"):
    for _bin in _SYS_BINS:
        assert not (_bin / _tool).exists(), (
            f"{_bin / _tool} exists: a system-bin runner would leak into probe tests"
        )


def _write_executable(path: Path, body: str = "#!/usr/bin/env bash\nexit 0\n") -> None:
    """Create an executable stub at *path* with *body*."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body)
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _make_repo_with_fake_git(tmp_path: Path, repo_dir: Path) -> Path:
    """Create a PATH dir holding a stub `git` whose `rev-parse --show-toplevel`
    prints *repo_dir*, isolating the script from the real workspace.
    """
    bin_dir = tmp_path / "stubbin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    _write_executable(
        bin_dir / "git",
        f'#!/usr/bin/env bash\nif [ "$1 $2" = "rev-parse --show-toplevel" ]; then\n'
        f'  echo "{repo_dir}"\nfi\nexit 0\n',
    )
    return bin_dir


def _run_probe(repo_dir: Path, *, path_dirs: list[Path]) -> subprocess.CompletedProcess[str]:
    """Run the gate in --probe-only mode with a controlled PATH (no real
    poetry/git leak in).
    """
    env: dict[str, str] = {
        "PATH": ":".join(str(p) for p in [*path_dirs, *_SYS_BINS]),
        "HOME": str(repo_dir),
    }
    return subprocess.run(
        [_BASH, str(GATE_SCRIPT), "--probe-only"],
        cwd=str(repo_dir),
        env=env,
        capture_output=True,
        text=True,
    )


@pytest.mark.parametrize(
    ("name", "setup_fn", "expect_label"),
    [
        (
            # Walk up from <ws>/repos/<slug> to <ws>/.dadaia/.venv/bin/dadaia; it precedes poetry.
            "walk_up_to_workspace_venv",
            None,  # handled specially below
            "workspace-venv",
        ),
        (
            # No workspace venv → repo-local .venv/bin/dadaia.
            "repo_local_venv",
            None,  # handled specially below
            "repo-venv",
        ),
    ],
)
def test_runner_resolution_branch_table(
    tmp_path: Path, name: str, setup_fn: object, expect_label: str
) -> None:
    if name == "walk_up_to_workspace_venv":
        ws = tmp_path / "ws"
        repo = ws / "repos" / "slug"
        repo.mkdir(parents=True)
        ws_dadaia = ws / ".dadaia" / ".venv" / "bin" / "dadaia"
        _write_executable(ws_dadaia)
        bin_dir = _make_repo_with_fake_git(tmp_path, repo)
        _write_executable(bin_dir / "poetry")
        res = _run_probe(repo, path_dirs=[bin_dir])
        assert res.returncode == 0, res.stderr
        assert expect_label in res.stdout
        assert str(ws_dadaia) in res.stdout
        assert "poetry" not in res.stdout
        return

    # repo_local_venv
    repo = tmp_path / "repo-with-local-venv"
    repo.mkdir(parents=True)
    _write_executable(repo / ".venv" / "bin" / "dadaia")
    bin_dir = _make_repo_with_fake_git(tmp_path, repo)
    res = _run_probe(repo, path_dirs=[bin_dir])
    assert res.returncode == 0, res.stderr
    assert expect_label in res.stdout
