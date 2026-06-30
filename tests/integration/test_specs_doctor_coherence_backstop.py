"""Integration test for the SPEC-DOC-029 lease↔session coherence backstop (D-2).

Release v0.1.10 / T-010-30 (audit A1). The backstop is the *only* after-the-fact
coverage for Bash-tool writes that bypass the SDD gate (Decision D-2). The original
implementation globbed ``*.lock`` while production writes ``<ctx>.lock.json`` — the
invariant could never fire on any real artifact, and its unit fixture fabricated a
file production never produces.

These tests exercise the wired backstop end-to-end against a **real initialized
workspace**, creating the lease/session/pointer artifacts exclusively through the
PRODUCTION writers (``lease.acquire`` + ``session_identity`` writers) — never by hand —
and asserting the doctor service function flags (incoherent) / clears (coherent) the
SPEC-DOC-029 ERROR.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.features.spec_context import lease, session_identity
from dadaia_workspace.features.specs import Severity, SpecsDoctor
from dadaia_workspace.features.workspace.service import WorkspaceService
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
from dadaia_workspace.infrastructure.python_env import VenvPythonEnvironmentManager

pytestmark = [pytest.mark.integration]

_CTX = "demo-ctx"


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    WorkspaceService(
        public_assets=FileSystemPublicAssetManager(),
        python_env=VenvPythonEnvironmentManager(),
    ).init(tmp_path)
    return tmp_path


def _doctor(workspace: Path) -> SpecsDoctor:
    return SpecsDoctor(
        workspace / "specs",
        public_dir=workspace / "dadaia_workspace" / "public",
        workspace_state_dir=workspace / ".dadaia",
    )


def test_doctor_flags_incoherent_lease_session_created_by_production_writers(
    workspace: Path,
) -> None:
    """A drifted incumbent pointer vs a live lease holder → SPEC-DOC-029 ERROR.

    Sequence (all production writers):

    1. ``lease.acquire`` writes the genuine ``<ctx>.lock.json`` record (holder = ``S1``)
       and the incumbent ``<ctx>.ptr`` (= ``S1``).
    2. ``set_incumbent`` drifts the pointer to ``S2`` and ``write_session`` persists S2's
       session record — the out-of-band drift the D-2 backstop exists to catch.
    """
    lease.acquire(workspace, _CTX, "sessAlpha", "rel-1", "implementation")
    session_identity.set_incumbent(workspace, _CTX, "sessBeta")
    session_identity.write_session(workspace, "sessBeta", {"session_id": "sessBeta"})

    issues = _doctor(workspace).check()
    doc_029 = [i for i in issues if i.code == "SPEC-DOC-029"]

    assert doc_029, [i.to_dict() for i in issues]
    assert all(i.severity == Severity.ERROR for i in doc_029)
    # Reports the REAL record name production writes — not a fabricated *.lock file.
    assert all(i.path.endswith(f"{_CTX}.lock.json") for i in doc_029)


def test_doctor_clears_coherent_lease_session_created_by_production_writers(
    workspace: Path,
) -> None:
    """Lock holder, incumbent pointer, and session record all naming S1 → no flag."""
    lease.acquire(workspace, _CTX, "sessAlpha", "rel-1", "implementation")
    session_identity.write_session(workspace, "sessAlpha", {"session_id": "sessAlpha"})

    issues = _doctor(workspace).check()
    assert [i.to_dict() for i in issues if i.code == "SPEC-DOC-029"] == []


def test_doctor_clears_harness_uuid_lock_with_cli_session_bind(
    workspace: Path,
) -> None:
    """Harness UUID lock holder + CLI sess_* incumbent for same context is not forgery."""
    harness_sid = "f4f75564-4c92-4ad0-9ce3-93d0411db60c"
    cli_sid = "sess_0bac2bc0"
    lease.acquire(workspace, _CTX, harness_sid, "rel-1", "implementation")
    session_identity.set_incumbent(workspace, _CTX, cli_sid)
    session_identity.write_session(
        workspace,
        cli_sid,
        {"session_id": cli_sid, "context": _CTX, "mode": "BOUND_IMPLEMENTATION"},
    )

    issues = _doctor(workspace).check()
    assert [i.to_dict() for i in issues if i.code == "SPEC-DOC-029"] == []
