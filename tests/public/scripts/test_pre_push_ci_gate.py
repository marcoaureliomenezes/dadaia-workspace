"""Hooks gate only at the publication boundary: pre-commit is advisory, the pre-push gate
fails closed.

Each test drives the REAL shipped shell script through ``bash``, never its text:

* :func:`test_pre_commit_exits_0_on_a_staged_set_backlog_doctor_would_reject` —
  ``pre-commit-presence-gate.sh`` exits 0 on a staged set the backlog doctor would reject.
* :func:`test_unresolvable_runner_still_refuses_the_push` — with no resolvable dadaia
  runner anywhere, ``pre-push-ci-gate.sh`` refuses the push (exit 1), never skips it.

The invalid-branch and denylist refusals are proven at the real CLI boundary by the e2e
journeys in ``tests/e2e/``; this module adds no duplicate coverage of them.

Owner: dd-sw-engineer-sr
"""

from __future__ import annotations

import json
import shutil
import stat
import subprocess
import sys
from pathlib import Path

import pytest

import dadaia_workspace

pytestmark = pytest.mark.skipif(
    sys.platform != "linux",
    reason="pre-commit-presence-gate.sh / pre-push-ci-gate.sh are bash contracts (Linux only)",
)

_SCRIPTS_DIR = Path(dadaia_workspace.__file__).parent / "public" / "scripts"
_PRE_PUSH_SCRIPT = _SCRIPTS_DIR / "pre-push-ci-gate.sh"

_BASH = shutil.which("bash") or "/usr/bin/bash"
_DEADLINE = 30.0
_ZERO = "0" * 40

#: Synthetic git identity on an RFC-2606 reserved domain, which privacy_baseline.json
#: excludes; one placeholder is reused at both git-identity call sites in this module.
_SYNTHETIC_GIT_EMAIL = "test@example.invalid"


def _write_executable(path: Path, body: str) -> None:
    path.write_text(body, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _write_dadaia_forwarder(path: Path) -> None:
    """A `dadaia` stub that forwards every verb into the REAL CLI through THIS
    interpreter — same technique as tests/e2e/test_push_denylist_journey.py."""
    _write_executable(
        path,
        "#!/usr/bin/env bash\nset -euo pipefail\n"
        f'exec "{sys.executable}" -m dadaia_workspace.cli.main "$@"\n',
    )


def _init_context_repo(workspace: Path, slug: str) -> Path:
    """A real git repo at <workspace>/repos/<slug>, laid out as a Spec Context repo
    (the shape `dadaia ci pre-commit-check` resolves the workspace + specs/ against)."""
    (workspace / ".dadaia" / "states").mkdir(parents=True, exist_ok=True)
    (workspace / ".dadaia" / "states" / "spec_contexts.json").write_text("{}", encoding="utf-8")
    repo = workspace / "repos" / slug
    (repo / "specs" / "backlog").mkdir(parents=True)
    (repo / "specs" / "memory" / "product").mkdir(parents=True)
    (repo / "specs" / "memory" / "product" / "catalog.json").write_text(
        '{"features": []}', encoding="utf-8"
    )
    (repo / "dadaia_workspace").mkdir()
    (repo / "dadaia_workspace" / "m.py").write_text("class Widget:\n    pass\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", _SYNTHETIC_GIT_EMAIL], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    return repo


def _plant_backlog_doctor_violation(repo: Path) -> None:
    """A BL-SCHEMA violation (an unresolved subject symbol) in ``BACKLOG.json``."""
    (repo / "specs" / "backlog" / "BACKLOG.json").write_text(
        json.dumps(
            {
                "schema": "backlog-v1",
                "active": [
                    {
                        "id": "bad-item",
                        "title": "Bad",
                        "opened": "2026-08-15",
                        "status": "candidate",
                        "description": "references a phantom symbol.",
                        "provenance": "operator request",
                        "intents": [
                            {
                                "subject": {"kind": "code", "ref": "dadaia_workspace/m.py#Ghost"},
                                "change": "x",
                            }
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )


def test_unresolvable_runner_still_refuses_the_push(tmp_path: Path) -> None:
    """With no workspace venv, no poetry, and no repo-local venv, ``pre-push-ci-gate.sh``
    refuses the push (exit 1), never skips it. Pre-push keeps fail-closed runner resolution;
    pre-commit always exits 0."""
    workspace = tmp_path
    repo = workspace / "isolated-repo"
    repo.mkdir(parents=True)
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", _SYNTHETIC_GIT_EMAIL], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)

    # A fully controlled PATH with no poetry/dadaia reachable — same isolation
    # technique as tests/public/scripts/test_pre_push_ci_gate__pre_push_gate_venv_probe.py.
    env = {"PATH": "/usr/bin:/bin", "HOME": str(repo)}

    stdin_text = f"refs/heads/feature/0.0.1 {'a' * 40} refs/heads/feature/0.0.1 {_ZERO}\n"
    result = subprocess.run(
        [_BASH, str(_PRE_PUSH_SCRIPT)],
        cwd=repo,
        input=stdin_text,
        capture_output=True,
        text=True,
        env=env,
        timeout=_DEADLINE,
    )
    out = result.stdout + result.stderr
    assert result.returncode == 1, out
    assert "could not locate the dadaia runner" in out, out
