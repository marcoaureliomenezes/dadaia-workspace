"""Unit tests for the DoctorService venv-health invariant.

The doctor reports a VENV-* finding when the workspace venv is missing or its ``dadaia``
entrypoint is absent / non-executable. A healthy synthetic tree reports nothing, and every
VENV-* finding is non-fixable (rebuilding a venv is an agent action).

All fixtures are SYNTHETIC trees (mkdir/touch/chmod) — NEVER a real venv build
(quality-assurance memory law: building real venvs in tests exhausts disk).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.features.spec_context.doctor import DoctorService  # noqa: E402
from dadaia_workspace.infrastructure.git_subprocess import GitSubprocessClient
from tests.fixtures.stores import context_store
from tests.helpers.oslib import cli_path, detect, make_executable, write_text


def _make_doctor(workspace_root: Path) -> DoctorService:
    return DoctorService(
        context_store(workspace_root / ".dadaia" / "states"),
        GitSubprocessClient(),
        workspace_root,
    )


def _init_workspace(root: Path) -> None:
    (root / ".dadaia" / "states").mkdir(parents=True)
    write_text(
        root / ".dadaia" / "states" / "spec_contexts.json",
        '{"schema_version": "2", "contexts": []}',
    )
    (root / "repos").mkdir(parents=True)
    write_text(root / "AGENTS.md", "# agents")


def _venv_bin(root: Path) -> Path:
    return cli_path(root).parent


def _make_healthy_venv(root: Path) -> Path:
    """Create a SYNTHETIC venv tree with an executable ``dadaia`` entrypoint."""
    entry = cli_path(root)
    entry.parent.mkdir(parents=True)
    write_text(entry, "#!/bin/sh\n")
    make_executable(entry)
    return entry


def _setup_non_executable(tp: Path) -> None:
    entry = cli_path(tp)
    entry.parent.mkdir(parents=True)
    write_text(entry, "#!/bin/sh\n")  # a new file carries no exec bit


@pytest.mark.parametrize(
    ("case", "setup", "expect_finding"),
    [
        pytest.param(
            "healthy", lambda tp: _make_healthy_venv(tp), False, id="healthy-venv-no-finding"
        ),
        pytest.param("missing-dir", lambda tp: None, True, id="missing-venv-dir-triggers-finding"),
        pytest.param(
            "missing-entrypoint",
            lambda tp: _venv_bin(tp).mkdir(parents=True),
            True,
            id="missing-dadaia-entrypoint-triggers-finding",
        ),
        pytest.param(
            "non-executable",
            _setup_non_executable,
            True,
            id="non-executable-entrypoint-triggers-finding",
        ),
    ],
)
def test_venv_health_matrix(tmp_path: Path, case: str, setup, expect_finding: bool) -> None:  # type: ignore[no-untyped-def]
    _init_workspace(tmp_path)
    setup(tmp_path)
    if case == "non-executable":  # the exec bit is the host's: Windows runs any file
        expect_finding = not detect().windows
    venv = [i for i in _make_doctor(tmp_path).check() if i.code.startswith("VENV")]
    assert bool(venv) is expect_finding
    assert not any(i.fixable for i in venv)  # rebuilding a venv is an agent action
