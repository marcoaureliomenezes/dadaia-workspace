"""E2E tests for the handoff pipeline (T-AC-10).

4 tests that exercise the full handoff pipeline via subprocess CLI:

1. full_handoff_emit_and_validate  — write a valid handoff adjacent to a fake HTML
   report in a bootstrapped workspace; `dadaia reports validate <path>` exits 0
   with "1 valid" in output.

2. invalid_handoff_fails_strict    — write a broken handoff (missing required field);
   `dadaia reports validate <path> --strict` exits 1.

3. schema_projection_idempotent    — run `dadaia public install --target all --force`
   twice consecutively; second run's `git status --short` shows no changes; assert
   `.dadaia/agentic/schemas/handoff-v1.schema.json` still exists.

4. doctor_reports_schema_ok_after_install — after `dadaia public install --target all
   --force`, `dadaia public doctor` output includes
   `stage:schemas/handoff-v1.schema.json` with `[ok]`.

Each test bootstraps an independent tmp workspace via `dadaia init -w <tmp_path>`.
No external network or secrets required.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_CLI = [sys.executable, "-m", "dadaia_workspace.cli.main"]


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
        "artifact": {
            "type": "report",
            "path": f"{stem}.html",
            "content_hash": content_hash,
        },
    }
    handoff_path = base_dir / f"{stem}.handoff.json"
    handoff_path.write_text(json.dumps(doc), encoding="utf-8")
    return handoff_path


def _write_invalid_handoff(base_dir: Path, stem: str = "bad") -> Path:
    """Write a handoff missing the required 'artifact' field."""
    doc = {
        "schema_version": "handoff-v1",
        "agent": "software-engineer",
        "context": "dadaia-workspace",
        "produced_at": "2026-05-17T00:00:00Z",
        # 'artifact' intentionally omitted — required field
    }
    handoff_path = base_dir / f"{stem}.handoff.json"
    handoff_path.write_text(json.dumps(doc), encoding="utf-8")
    return handoff_path


def _git_init_and_commit(workspace: Path) -> None:
    """Initialise a git repo and commit all files (for idempotency diff check)."""
    for cmd in (
        ["git", "init"],
        ["git", "config", "user.email", "test@test.com"],
        ["git", "config", "user.name", "Test"],
        ["git", "add", "-A"],
        ["git", "commit", "-m", "snapshot"],
    ):
        subprocess.run(cmd, cwd=str(workspace), capture_output=True, check=True)


# ---------------------------------------------------------------------------
# Test 1 — Full handoff emit-and-validate
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Test 2 — Invalid handoff fails strict
# ---------------------------------------------------------------------------


def test_invalid_handoff_fails_strict(tmp_path: Path) -> None:
    """Bootstrap workspace, write invalid handoff, validate --strict → exit 1."""
    _bootstrap(tmp_path)

    handoff_path = _write_invalid_handoff(tmp_path, stem="broken-report")

    result = _run("reports", "validate", str(handoff_path), "--strict", cwd=tmp_path)

    assert result.returncode == 1, (
        f"dadaia reports validate --strict exited {result.returncode}; expected 1.\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
    # The output should mention the missing field
    assert "artifact" in result.stdout, (
        f"Expected 'artifact' in output (missing required field).\nstdout: {result.stdout}"
    )


# ---------------------------------------------------------------------------
# Test 3 — Schema projection idempotent
# ---------------------------------------------------------------------------


def test_schema_projection_idempotent(tmp_path: Path) -> None:
    """Run public install --force twice; second run produces zero git diff."""
    workspace = tmp_path / "ws"
    _bootstrap(workspace)

    # First install
    first = subprocess.run(
        [*_CLI, "public", "install", "--target", "all", "--force"],
        cwd=str(workspace),
        capture_output=True,
        text=True,
    )
    assert first.returncode == 0, (
        f"First install failed (exit {first.returncode}):\n"
        f"stdout: {first.stdout}\nstderr: {first.stderr}"
    )

    # Schema must be present after first install.
    schema_path = workspace / ".dadaia" / "agentic" / "schemas" / "handoff-v1.schema.json"
    assert schema_path.exists(), f"Schema missing after first install: {schema_path}"

    # Commit everything so the second run's git diff is meaningful.
    _git_init_and_commit(workspace)

    # Second install — idempotent run
    second = subprocess.run(
        [*_CLI, "public", "install", "--target", "all", "--force"],
        cwd=str(workspace),
        capture_output=True,
        text=True,
    )
    assert second.returncode == 0, (
        f"Second install failed (exit {second.returncode}):\n"
        f"stdout: {second.stdout}\nstderr: {second.stderr}"
    )

    # git status --short should be empty (clean working tree)
    status = subprocess.run(
        ["git", "status", "--short"],
        cwd=str(workspace),
        capture_output=True,
        text=True,
        check=True,
    )
    assert status.stdout.strip() == "", (
        f"git status --short is non-empty after second install — install is NOT idempotent.\n"
        f"git status output:\n{status.stdout}"
    )

    # Schema must still be present after second install.
    assert schema_path.exists(), f"Schema missing after second install: {schema_path}"


# ---------------------------------------------------------------------------
# Test 4 — Doctor reports schema OK after install
# ---------------------------------------------------------------------------


def test_doctor_reports_schema_ok_after_install(tmp_path: Path) -> None:
    """After install, `dadaia public doctor` includes [ok] for handoff-v1.schema.json."""
    workspace = tmp_path / "ws"
    _bootstrap(workspace)

    install = subprocess.run(
        [*_CLI, "public", "install", "--target", "all", "--force"],
        cwd=str(workspace),
        capture_output=True,
        text=True,
    )
    assert install.returncode == 0, (
        f"Install failed (exit {install.returncode}):\n"
        f"stdout: {install.stdout}\nstderr: {install.stderr}"
    )

    doctor = subprocess.run(
        [*_CLI, "public", "doctor"],
        cwd=str(workspace),
        capture_output=True,
        text=True,
    )
    assert doctor.returncode == 0, (
        f"dadaia public doctor exited {doctor.returncode}; expected 0.\n"
        f"stdout: {doctor.stdout}\nstderr: {doctor.stderr}"
    )

    # Rich console strips ANSI — but subprocess captures plain text.
    # The doctor line should match `[ok] stage:schemas/handoff-v1.schema.json`.
    output_lines = doctor.stdout.splitlines()
    schema_lines = [line for line in output_lines if "handoff-v1.schema.json" in line]
    assert schema_lines, (
        f"No line mentioning 'handoff-v1.schema.json' in doctor output.\n"
        f"Full output:\n{doctor.stdout}"
    )

    ok_schema_lines = [line for line in schema_lines if line.strip().startswith("[ok]")]
    assert ok_schema_lines, (
        "Found handoff-v1.schema.json lines but none starts with '[ok]'.\n"
        "Schema lines:\n" + "\n".join(schema_lines)
    )
    # Confirm the expected canonical form is present.
    assert any("stage:schemas/handoff-v1.schema.json" in line for line in ok_schema_lines), (
        "Expected 'stage:schemas/handoff-v1.schema.json' in [ok] line.\n"
        "Ok schema lines:\n" + "\n".join(ok_schema_lines)
    )
