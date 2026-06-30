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


def test_cli_doctor_reaches_coherence_check_on_incoherent_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An incoherent lease↔session pair → CLI doctor output names SPEC-DOC-029.

    The CLI resolves the workspace root from cwd; we chdir into the tmp workspace so
    ``_resolve_workspace_state_dir`` finds its ``.dadaia/`` and wires the backstop.
    """
    specs = _make_workspace(tmp_path)
    ctx = "ctx-a"

    # Production writers: a real lease record + incumbent ptr (holder = S1), then drift
    # the incumbent ptr to S2 and persist S2's session record → three-source divergence.
    lease.acquire(tmp_path, ctx, "sessS1", "rel-1", "implementation")
    session_identity.set_incumbent(tmp_path, ctx, "sessS2")
    session_identity.write_session(tmp_path, "sessS2", {"session_id": "sessS2"})

    monkeypatch.chdir(tmp_path)
    result = _runner.invoke(app, ["specs", "doctor", "--specs-dir", str(specs)])

    assert "SPEC-DOC-029" in result.output, result.output


def test_cli_doctor_coherent_state_has_no_doc_029(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A coherent lease↔session state → no SPEC-DOC-029 from the CLI."""
    specs = _make_workspace(tmp_path)
    ctx = "ctx-a"

    lease.acquire(tmp_path, ctx, "sessS1", "rel-1", "implementation")
    session_identity.write_session(tmp_path, "sessS1", {"session_id": "sessS1"})

    monkeypatch.chdir(tmp_path)
    result = _runner.invoke(app, ["specs", "doctor", "--specs-dir", str(specs)])

    assert "SPEC-DOC-029" not in result.output, result.output


def test_cli_doctor_external_specs_dir_does_not_scan_live_workspace_locks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A scoped --specs-dir outside cwd's workspace must not read that workspace's locks."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    _make_workspace(workspace)
    external = tmp_path / "external-specs"
    result = scaffold(
        specs_dir=external,
        project_name="external",
        force=False,
        templates_dir=_TEMPLATES_DIR,
    )
    assert result.errors == [], result.errors

    ctx = "ctx-a"
    lease.acquire(workspace, ctx, "sessS1", "rel-1", "implementation")
    session_identity.set_incumbent(workspace, ctx, "sessS2")
    session_identity.write_session(workspace, "sessS2", {"session_id": "sessS2"})

    monkeypatch.chdir(workspace)
    cli_result = _runner.invoke(app, ["specs", "doctor", "--specs-dir", str(external)])

    assert "SPEC-DOC-029" not in cli_result.output, cli_result.output
