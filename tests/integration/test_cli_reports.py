"""Integration tests for `dadaia reports validate` CLI (T-AC-08).

Covers the 10 acceptance scenarios defined in TASKS.md:

1.  Happy path — single valid handoff, exit 0, "1 valid" in output.
2.  Schema violation in strict mode → exit 1 with field-path message.
3.  Schema violation in non-strict mode → exit 0 with warning in output.
4.  File not found → exit 2 with clear error.
5.  --all discovers all *.handoff.json files under workspace reports root.
6.  --json output is parseable JSON with `valid` count and `violations` (errors) array.
7.  --release filter narrows discovery to handoffs matching that release_id.
8.  Schema staged after `public install` — .dadaia/agentic/schemas/handoff-v1.schema.json exists.
9.  Schema NOT in .claude/schemas/ (FR1/A1 enforcement).
10. Workspace not initialized → exit 3.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app
from dadaia_workspace.features.workspace.service import WorkspaceService
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
from dadaia_workspace.infrastructure.python_env import VenvPythonEnvironmentManager

_runner = CliRunner()


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def _init_workspace(workspace: Path) -> None:
    """Initialize a workspace and stage public assets (including schemas)."""
    workspace.mkdir(parents=True, exist_ok=True)
    WorkspaceService(
        public_assets=FileSystemPublicAssetManager(),
        python_env=VenvPythonEnvironmentManager(),
    ).init(workspace)
    FileSystemPublicAssetManager().stage(workspace)


def _make_valid_handoff(
    base_dir: Path, stem: str = "report", release_id: str | None = None
) -> Path:
    """Create a minimal valid handoff.json file with a companion artifact."""
    artifact_path = base_dir / f"{stem}.html"
    artifact_path.write_text(f"<html>{stem}</html>", encoding="utf-8")
    content_hash = hashlib.sha256(artifact_path.read_bytes()).hexdigest()

    doc: dict = {
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
    if release_id is not None:
        doc["release_id"] = release_id

    handoff_path = base_dir / f"{stem}.handoff.json"
    handoff_path.write_text(json.dumps(doc), encoding="utf-8")
    return handoff_path


def _make_invalid_handoff(base_dir: Path, stem: str = "bad") -> Path:
    """Create an invalid handoff that is missing the required 'agent' field."""
    doc = {
        "schema_version": "handoff-v1",
        # "agent" intentionally omitted — required field
        "context": "dadaia-workspace",
        "produced_at": "2026-05-17T00:00:00Z",
        "artifact": {
            "type": "report",
            "path": f"{stem}.html",
            "content_hash": "a" * 64,
        },
    }
    handoff_path = base_dir / f"{stem}.handoff.json"
    handoff_path.write_text(json.dumps(doc), encoding="utf-8")
    return handoff_path


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_01_happy_path_valid_handoff_exits_0(tmp_path: Path, monkeypatch) -> None:
    """Test 1: single valid handoff → exit 0, '1 valid' in output."""
    _init_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)

    handoff_path = _make_valid_handoff(tmp_path)

    result = _runner.invoke(app, ["reports", "validate", str(handoff_path)])

    assert result.exit_code == 0, result.output
    assert "1 valid" in result.output


def test_02_schema_violation_strict_exits_1_with_field_path(tmp_path: Path, monkeypatch) -> None:
    """Test 2: missing required field in strict mode → exit 1 + field path in output."""
    _init_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)

    handoff_path = _make_invalid_handoff(tmp_path)

    result = _runner.invoke(app, ["reports", "validate", str(handoff_path), "--strict"])

    assert result.exit_code == 1, result.output
    # The field path for the missing 'agent' field must appear in output
    assert "agent" in result.output


def test_03_schema_violation_non_strict_exits_0_with_warning(tmp_path: Path, monkeypatch) -> None:
    """Test 3: schema violation in non-strict mode → exit 0, INVALID warning in output."""
    _init_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)

    handoff_path = _make_invalid_handoff(tmp_path)

    result = _runner.invoke(app, ["reports", "validate", str(handoff_path)])

    assert result.exit_code == 0, result.output
    # CLI must still print INVALID (warning) and show the field violation
    assert "INVALID" in result.output
    assert "agent" in result.output


def test_04_file_not_found_exits_2_with_error_message(tmp_path: Path, monkeypatch) -> None:
    """Test 4: non-existent file path → exit 2 with clear error message."""
    _init_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)

    missing = tmp_path / "ghost.handoff.json"

    result = _runner.invoke(app, ["reports", "validate", str(missing)])

    assert result.exit_code == 2, result.output
    assert "ghost.handoff.json" in result.output or "not found" in result.output.lower()


def test_05_all_flag_discovers_handoff_files_under_reports_root(
    tmp_path: Path, monkeypatch
) -> None:
    """Test 5: --all discovers all *.handoff.json files under the workspace reports root."""
    _init_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)

    reports_root = tmp_path / ".dadaia" / "reports"
    reports_root.mkdir(parents=True, exist_ok=True)

    # Place 3 valid handoffs under reports root
    for i in range(3):
        _make_valid_handoff(reports_root, stem=f"report-{i}")

    result = _runner.invoke(app, ["reports", "validate", "--all"])

    assert result.exit_code == 0, result.output
    assert "3 valid" in result.output


def test_06_json_output_is_parseable_with_valid_count_and_errors(
    tmp_path: Path, monkeypatch
) -> None:
    """Test 6: --json output is parseable JSON with 'valid' field and 'errors' array."""
    _init_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)

    handoff_path = _make_valid_handoff(tmp_path)

    result = _runner.invoke(app, ["reports", "validate", str(handoff_path), "--json"])

    assert result.exit_code == 0, result.output

    data = json.loads(result.output)
    assert isinstance(data, list)
    assert len(data) == 1

    entry = data[0]
    assert entry["valid"] is True
    assert "errors" in entry
    assert isinstance(entry["errors"], list)


def test_07_release_filter_narrows_discovery(tmp_path: Path, monkeypatch) -> None:
    """Test 7: --release <id> filters to handoffs with matching release_id."""
    _init_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)

    reports_root = tmp_path / ".dadaia" / "reports"
    reports_root.mkdir(parents=True, exist_ok=True)

    # 1 handoff with target release_id, 2 with different release
    _make_valid_handoff(reports_root, stem="agent-comms-report", release_id="agent-comms-v1")
    _make_valid_handoff(reports_root, stem="other-report-1", release_id="panel-v1")
    _make_valid_handoff(reports_root, stem="other-report-2", release_id="panel-v1")

    result = _runner.invoke(app, ["reports", "validate", "--all", "--release", "agent-comms-v1"])

    assert result.exit_code == 0, result.output
    assert "1 valid" in result.output
    # The path may wrap across lines in the terminal; compare without newlines
    assert "agent-comms-report" in result.output.replace("\n", "")


def test_08_schema_staged_after_public_install(tmp_path: Path, monkeypatch) -> None:
    """Test 8: after workspace init + stage, handoff-v1.schema.json exists in agentic/schemas/."""
    _init_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)

    schema_path = tmp_path / ".dadaia" / "agentic" / "schemas" / "handoff-v1.schema.json"
    assert schema_path.exists(), f"Schema not found at {schema_path}"

    # Verify the schema is valid JSON and the CLI can consume it
    schema_data = json.loads(schema_path.read_text(encoding="utf-8"))
    assert schema_data.get("$schema") == "https://json-schema.org/draft/2020-12/schema"

    # Confirm CLI is functional (can validate a handoff using the staged schema)
    handoff_path = _make_valid_handoff(tmp_path)
    result = _runner.invoke(app, ["reports", "validate", str(handoff_path)])
    assert result.exit_code == 0, result.output


def test_09_schema_not_in_claude_schemas_dir(tmp_path: Path, monkeypatch) -> None:
    """Test 9: FR1/A1 enforcement — schema must NOT be projected to .claude/schemas/."""
    _init_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)

    claude_schemas = tmp_path / ".claude" / "schemas"
    assert not claude_schemas.exists(), (
        f".claude/schemas/ must not exist after workspace init, but found {claude_schemas}"
    )


def test_10_workspace_not_initialized_exits_3(tmp_path: Path, monkeypatch) -> None:
    """Test 10: running validate in a directory with no .dadaia/agentic/schemas/ → exit 3."""
    # tmp_path has no workspace init — no .dadaia directory at all
    monkeypatch.chdir(tmp_path)

    result = _runner.invoke(app, ["reports", "validate", "--all"])

    assert result.exit_code == 3, result.output
    # Output should indicate schema or workspace initialization issue
    combined = result.output + (result.stderr or "")
    assert any(kw in combined.lower() for kw in ("schema", "workspace", "initialized", "not found"))
