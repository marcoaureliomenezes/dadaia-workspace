"""Integration test: `dadaia specs doctor` wires workspace_state_dir → SPEC-DOC-029.

The doctor's lease↔session coherence backstop (SPEC-DOC-029) only runs when a caller
injects ``workspace_state_dir``. Before this wiring the CLI never passed it, so the
backstop was a no-op from the CLI. This test asserts the CLI-level doctor reaches the
coherence check: an incoherent lease↔session pair (created via the production writers)
makes the CLI doctor output contain SPEC-DOC-029.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app
from dadaia_workspace.features.spec_context import lease, session_identity
from dadaia_workspace.features.specs.scaffolder import scaffold

_runner = CliRunner()

_REPO_ROOT = Path(__file__).parent.parent.parent.parent
_TEMPLATES_DIR = _REPO_ROOT / "dadaia_workspace" / "public" / "templates"


def _make_workspace(root: Path) -> Path:
    """A tmp workspace root: ``.dadaia/states/spec_contexts.json`` sentinel + a specs tree."""
    states = root / ".dadaia" / "states"
    states.mkdir(parents=True)
    # The sentinel resolve_workspace_root() looks for.
    (states / "spec_contexts.json").write_text('{"contexts": []}', encoding="utf-8")
    specs = root / "specs"
    result = scaffold(
        specs_dir=specs,
        project_name="ws-coherence",
        force=False,
        templates_dir=_TEMPLATES_DIR,
    )
    assert result.errors == [], result.errors
    return specs


def test_cli_doctor_reaches_coherence_check_incoherent_and_coherent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An incoherent lease↔session pair → CLI doctor output names SPEC-DOC-029;
    a coherent pair → no SPEC-DOC-029.

    The CLI resolves the workspace root from cwd; we chdir into the tmp workspace so
    ``_resolve_workspace_state_dir`` finds its ``.dadaia/`` and wires the backstop.
    """
    specs = _make_workspace(tmp_path)
    ctx = "ctx-a"

    # v0.1.50 FR2 (holder-confirmation): a REAL acquire writes the by-session index
    # (acquisition evidence), so a drifted ptr alone is no longer forgery. The 029
    # ERROR now requires an EVIDENCE-LESS live holder: forge the lock record
    # directly (out-of-band edit, no index entry), then diverge the incumbent ptr.
    lease.acquire(tmp_path, ctx, "sessS1", "rel-1", "implementation")
    rec = lease.read_record(tmp_path, ctx)
    assert rec is not None
    rec["session_id"] = "sessForged"
    lease._write_record(lease._record_path(tmp_path, ctx), rec)
    session_identity.set_incumbent(tmp_path, ctx, "sessS2")
    session_identity.write_session(tmp_path, "sessS2", {"session_id": "sessS2"})

    monkeypatch.chdir(tmp_path)
    result = _runner.invoke(app, ["specs", "doctor", "--specs-dir", str(specs)])
    assert "SPEC-DOC-029" in result.output, result.output

    # Coherent case: a second, independent context whose lock/session both name S1.
    specs2 = _make_workspace(tmp_path / "coherent-case")
    ctx2 = "ctx-b"
    lease.acquire(tmp_path / "coherent-case", ctx2, "sessS1", "rel-1", "implementation")
    session_identity.write_session(tmp_path / "coherent-case", "sessS1", {"session_id": "sessS1"})
    monkeypatch.chdir(tmp_path / "coherent-case")
    result2 = _runner.invoke(app, ["specs", "doctor", "--specs-dir", str(specs2)])
    assert "SPEC-DOC-029" not in result2.output, result2.output


def test_cli_doctor_external_specs_dir_isolates_live_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """v0.1.50 FR2 (audit F-4): an explicit --specs-dir OUTSIDE the workspace never
    reads the live workspace's lock/session state — fixture doctor runs report no
    SPEC-DOC-029 sourced from the live tree."""
    ws_root = tmp_path / "ws"
    ws_root.mkdir()
    _make_workspace(ws_root)
    # Plant an INCOHERENT live state in the workspace: an evidence-less forged
    # holder (no index entry) + a drifted incumbent ptr — the 029 ERROR shape.
    lease.acquire(ws_root, "ctxa", "sess_holder", "v1", "IMPLEMENTATION", pid=4321)
    rec = lease.read_record(ws_root, "ctxa")
    assert rec is not None
    rec["session_id"] = "sess_forged"
    lease._write_record(lease._record_path(ws_root, "ctxa"), rec)
    session_identity.set_incumbent(ws_root, "ctxa", "sess_drift")

    # A fixture specs tree OUTSIDE the workspace root.
    outside = tmp_path / "elsewhere" / "specs"
    result = scaffold(
        specs_dir=outside,
        project_name="fixture-tree",
        force=False,
        templates_dir=_TEMPLATES_DIR,
    )
    assert result.errors == [], result.errors

    monkeypatch.chdir(ws_root)
    run = _runner.invoke(app, ["specs", "doctor", "--specs-dir", str(outside)])
    assert "SPEC-DOC-029" not in run.output
