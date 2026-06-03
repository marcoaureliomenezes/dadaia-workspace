"""E2E handoff pipeline journey via the real CLI process."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_CLI = [sys.executable, "-m", "dadaia_workspace.cli.main"]
pytestmark = [pytest.mark.e2e, pytest.mark.slow]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    """Run a dadaia CLI command; always capture stdout+stderr as text."""
    return subprocess.run(
        [*_CLI, *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
    )


def _bootstrap(workspace: Path) -> None:
    """Bootstrap a fresh dadaia workspace via `dadaia init -w <workspace>`."""
    workspace.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        [*_CLI, "init", "-w", str(workspace)],
        cwd=str(workspace),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"dadaia init failed (exit {result.returncode}):\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
    # Confirm schema was staged during init.
    schema = workspace / ".dadaia" / "agentic" / "schemas" / "handoff-v1.schema.json"
    assert schema.exists(), f"Schema not found after init: {schema}"


def _write_valid_handoff(base_dir: Path, stem: str = "report") -> Path:
    """Write a minimal valid .handoff.json with a companion HTML artifact."""
    artifact = base_dir / f"{stem}.html"
    artifact.write_text(f"<html>{stem}</html>", encoding="utf-8")
    content_hash = hashlib.sha256(artifact.read_bytes()).hexdigest()

    doc = {
        "schema_version": "handoff-v1",
        "agent": "software-engineer",
        "context": "dadaia-workspace",
        "produced_at": "2026-05-17T00:00:00Z",
        "scope": "dadaia-workspace/test",
        "metrics": {},
        "findings": [],
        "artifact": {
            "type": "report",
            "path": f"{stem}.html",
            "content_hash": content_hash,
        },
    }
    handoff_path = base_dir / f"{stem}.handoff.json"
    handoff_path.write_text(json.dumps(doc), encoding="utf-8")
    return handoff_path


def test_full_handoff_emit_and_validate(tmp_path: Path) -> None:
    """Bootstrap workspace, write valid handoff, validate → exit 0, '1 valid'."""
    _bootstrap(tmp_path)

    # Write a valid handoff adjacent to a fake HTML report.
    handoff_path = _write_valid_handoff(tmp_path, stem="my-report")

    result = _run("reports", "validate", str(handoff_path), cwd=tmp_path)

    assert result.returncode == 0, (
        f"dadaia reports validate exited {result.returncode}; expected 0.\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
    assert "1 valid" in result.stdout, f"Expected '1 valid' in stdout.\nstdout: {result.stdout}"
