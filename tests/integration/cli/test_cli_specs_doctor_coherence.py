"""Integration test: SPEC-DOC-029 retirement (v0.1.76 T-4, FR7, NO-LOCKS DOCTRINE).

The doctor's former lease<->session coherence backstop (SPEC-DOC-029) is retired: the
lease acquisition/CAS authority it diagnosed forgery against is gone (T-3), so a residual
``<ctx>.lock.json`` is legacy/diagnostic noise, not a security-relevant divergence. This
test asserts the CLI-level doctor NEVER emits SPEC-DOC-029, even against a workspace that
carries a residual, genuinely-diverged lock record on disk (the exact fixture shape the
retired backstop used to flag as possible forgery).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app
from dadaia_workspace.features.spec_context import session_identity
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


def _seed_lock_record(workspace: Path, ctx: str, session_id: str, *, pid: int = 4242) -> None:
    """Plant a raw ``<ctx>.lock.json`` — a v0.1.76 T-3 residual-record fixture.

    ``lease.acquire`` is DELETED (the acquisition/CAS machinery it belonged to is gone);
    seeding one directly (matching the schema ``acquire`` used to write) reproduces the
    exact residue a pre-doctrine install might still carry on disk.
    """
    now = datetime.now(tz=UTC).isoformat()
    lock_dir = workspace / ".dadaia" / "states" / "ctx_locks"
    lock_dir.mkdir(parents=True, exist_ok=True)
    record = {
        "context": ctx,
        "release": "rel-1",
        "session_id": session_id,
        "mode": "IMPLEMENTATION",
        "pid": pid,
        "acquired_at": now,
        "heartbeat": now,
        "ttl": 120,
    }
    (lock_dir / f"{ctx}.lock.json").write_text(json.dumps(record, indent=2), encoding="utf-8")


def test_cli_doctor_never_emits_retired_spec_doc_029(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A residual, genuinely-diverged lock<->incumbent pair never surfaces SPEC-DOC-029
    from the CLI — the retired check has no seam left to wire it through."""
    specs = _make_workspace(tmp_path)
    ctx = "ctx-a"

    _seed_lock_record(tmp_path, ctx, "sessForged")
    monkeypatch.chdir(tmp_path)
    result = _runner.invoke(app, ["specs", "doctor", "--specs-dir", str(specs)])
    assert "SPEC-DOC-029" not in result.output, result.output
