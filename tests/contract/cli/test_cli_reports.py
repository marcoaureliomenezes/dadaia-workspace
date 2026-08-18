"""Public CLI contracts for `dadaia reports validate`."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

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
        "scope": "dadaia-workspace/test",
        "metrics": {},
        "findings": [],
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
    """Create an invalid handoff that is missing the required 'agent' field.

    All other v1.1 required fields are present so the v1.0 compat check does
    not fire — only the schema 'agent' violation triggers.
    """
    doc = {
        "schema_version": "handoff-v1",
        # "agent" intentionally omitted — required field
        "context": "dadaia-workspace",
        "produced_at": "2026-05-17T00:00:00Z",
        "scope": "dadaia-workspace/test",
        "metrics": {},
        "findings": [],
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


def test_valid_handoff_exits_0_with_valid_count_and_json_shape(tmp_path: Path, monkeypatch) -> None:
    """Single valid handoff → exit 0, '1 valid' in output, and --json output is
    parseable JSON with a 'valid' field and an 'errors' array."""
    _init_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)

    handoff_path = _make_valid_handoff(tmp_path)

    result = _runner.invoke(app, ["reports", "validate", str(handoff_path)])
    assert result.exit_code == 0, result.output
    assert "1 valid" in result.output

    json_result = _runner.invoke(app, ["reports", "validate", str(handoff_path), "--json"])
    assert json_result.exit_code == 0, json_result.output
    # `.stdout` (pure stdout), not `.output` (stdout+stderr mixed, per Click 8.2's own
    # docstring): the resolved-workspace-root diagnostic (T-043-47/A30.5) writes to
    # stderr precisely so it never pollutes the --json stdout payload's list shape.
    data = json.loads(json_result.stdout)
    assert isinstance(data, list)
    assert len(data) == 1
    entry = data[0]
    assert entry["valid"] is True
    assert "errors" in entry
    assert isinstance(entry["errors"], list)


def test_schema_violation_always_exits_nonzero(tmp_path: Path, monkeypatch) -> None:
    """An INVALID file exits 1 in BOTH modes (exit-code truthfulness,
    validation-029 F-12): the old non-strict 'print INVALID, exit 0' contract masked
    tampered/malformed handoffs from every consuming script."""
    _init_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)

    handoff_path = _make_invalid_handoff(tmp_path)

    strict = _runner.invoke(app, ["reports", "validate", str(handoff_path), "--strict"])
    assert strict.exit_code == 1, strict.output
    assert "agent" in strict.output

    non_strict = _runner.invoke(app, ["reports", "validate", str(handoff_path)])
    assert non_strict.exit_code == 1, non_strict.output
    assert "INVALID" in non_strict.output
    assert "agent" in non_strict.output


def test_exit_code_matrix_not_found_and_uninitialized_workspace(
    tmp_path: Path, monkeypatch
) -> None:
    """Non-existent file path → exit 2 with a clear error message; running validate
    in a directory with no .dadaia/agentic/schemas/ at all → exit 3."""
    _init_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)

    missing = tmp_path / "ghost.handoff.json"
    result = _runner.invoke(app, ["reports", "validate", str(missing)])
    assert result.exit_code == 2, result.output
    assert "ghost.handoff.json" in result.output or "not found" in result.output.lower()

    uninitialized = tmp_path.parent / "uninitialized-workspace"
    uninitialized.mkdir()
    monkeypatch.chdir(uninitialized)
    result = _runner.invoke(app, ["reports", "validate", "--all"])
    assert result.exit_code == 3, result.output
    combined = result.output + (result.stderr or "")
    assert any(kw in combined.lower() for kw in ("schema", "workspace", "initialized", "not found"))


def test_all_flag_discovers_and_release_filter_narrows(tmp_path: Path, monkeypatch) -> None:
    """--all discovers all *.handoff.json files under the workspace handoff root, and
    --release <id> narrows discovery to handoffs with a matching release_id."""
    _init_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)

    handoff_root = tmp_path / ".dadaia" / "handoff" / "dadaia-workspace"
    handoff_root.mkdir(parents=True, exist_ok=True)

    for i in range(3):
        _make_valid_handoff(handoff_root, stem=f"report-{i}")

    result = _runner.invoke(app, ["reports", "validate", "--all"])
    assert result.exit_code == 0, result.output
    assert "3 valid" in result.output

    _make_valid_handoff(handoff_root, stem="agent-comms-report", release_id="agent-comms-v1")
    for stem in ("report-0", "report-1", "report-2"):
        (handoff_root / f"{stem}.handoff.json").unlink()
        (handoff_root / f"{stem}.html").unlink()
    _make_valid_handoff(handoff_root, stem="other-report-1", release_id="panel-v1")
    _make_valid_handoff(handoff_root, stem="other-report-2", release_id="panel-v1")

    filtered = _runner.invoke(app, ["reports", "validate", "--all", "--release", "agent-comms-v1"])
    assert filtered.exit_code == 0, filtered.output
    assert "1 valid" in filtered.output
    # The path may wrap across lines in the terminal; compare without newlines
    assert "agent-comms-report" in filtered.output.replace("\n", "")


def test_schema_staged_after_install_and_not_in_claude_schemas_dir(
    tmp_path: Path, monkeypatch
) -> None:
    """After workspace init + stage, handoff-v1.schema.json exists in
    agentic/schemas/ and is consumable by the CLI, while FR1/A1 enforces that the
    schema is NOT projected to .claude/schemas/."""
    _init_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)

    schema_path = tmp_path / ".dadaia" / "agentic" / "schemas" / "handoff-v1.schema.json"
    assert schema_path.exists(), f"Schema not found at {schema_path}"

    schema_data = json.loads(schema_path.read_text(encoding="utf-8"))
    assert schema_data.get("$schema") == "https://json-schema.org/draft/2020-12/schema"

    handoff_path = _make_valid_handoff(tmp_path)
    result = _runner.invoke(app, ["reports", "validate", str(handoff_path)])
    assert result.exit_code == 0, result.output

    claude_schemas = tmp_path / ".claude" / "schemas"
    assert not claude_schemas.exists(), (
        f".claude/schemas/ must not exist after workspace init, but found {claude_schemas}"
    )


# ---------------------------------------------------------------------------
# Bug ancestor-walk-workspace-root-silent-mistarget (T-043-47/A30.5) — a bare
# `dadaia reports validate <path>` run from a cwd outside the handoff's own workspace
# silently resolves artifact.path against the WRONG ancestor root and reports a false
# INVALID/missing_artifact. `--workspace` is the escape hatch, and the resolved root is
# always named in the command's output so a false negative is never misread.
# ---------------------------------------------------------------------------


def test_reports_validate_workspace_override_fixes_false_invalid(
    tmp_path: Path, monkeypatch
) -> None:
    other_ws = tmp_path / "other-workspace"
    _init_workspace(other_ws)

    target_ws = tmp_path / "target-workspace"
    _init_workspace(target_ws)
    handoff_path = _make_valid_handoff(target_ws, stem="report")

    # cwd is OUTSIDE target_ws (inside an unrelated initialized workspace) — the
    # ancestor-walk resolves the wrong root and must not silently return VALID.
    monkeypatch.chdir(other_ws)
    wrong = _runner.invoke(app, ["reports", "validate", str(handoff_path)])
    assert wrong.exit_code == 1, wrong.output
    assert "INVALID" in wrong.output
    assert "missing_artifact" in wrong.output

    # The wrong-root diagnostic names the (wrong) resolved workspace root so the false
    # INVALID above is traceable, not silently misread. (Path may wrap across lines.)
    assert str(other_ws.resolve()) in (wrong.stderr or "").replace("\n", "")

    # --workspace targets the handoff's own workspace explicitly — VALID.
    fixed = _runner.invoke(
        app, ["reports", "validate", str(handoff_path), "--workspace", str(target_ws)]
    )
    assert fixed.exit_code == 0, fixed.output
    assert "1 valid" in fixed.output
    assert str(target_ws.resolve()) in (fixed.stderr or "").replace("\n", "")


def test_reports_validate_always_emits_resolved_workspace_root_json_mode(
    tmp_path: Path, monkeypatch
) -> None:
    """The resolved-root diagnostic goes to stderr, never polluting the --json stdout
    payload's list shape."""
    _init_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)
    handoff_path = _make_valid_handoff(tmp_path)

    result = _runner.invoke(app, ["reports", "validate", str(handoff_path), "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.stdout)
    assert isinstance(data, list)
    assert str(tmp_path.resolve()) in (result.stderr or "").replace("\n", "")
