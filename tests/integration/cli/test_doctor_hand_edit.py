"""A hand edit of a verb-owned record is one WARNING line (0.4.7 FR6, T-047-30).

Intent: CONTRACT — 0.4.7 FR6 (`bugs resolve` then a file-tool edit of that record
yields one `LEDGER-BUGS-HANDEDIT` line and exit 0; a hand-flipped `phase` yields
`RELEASE-TREE-HANDEDIT`; a workspace with no telemetry store carries neither).
Size: MEDIUM — the real doctor CLI against a tmp_path specs tree and a tmp_path HOME.

Structural frame: a governance record used to change with no trace of whether a verb
or a text editor changed it. The event is the trace; this is the reader that speaks it.
A hand edit is MEASURED, never blocked — every assertion below pins exit code 0.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace import container
from dadaia_workspace.cli.main import app

_runner = CliRunner()


@pytest.fixture()
def home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.delenv("DADAIA_CONTEXT", raising=False)
    monkeypatch.setenv("DADAIA_SESSION_ID", "session-under-test")
    return tmp_path / "home"


@pytest.fixture()
def specs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A tmp workspace root (`.dadaia/`) with a tmp specs tree, entered — so the
    doctor's `workspace` section scans THIS tree and the run's exit code is the
    verdict of the records under test, nothing else."""
    from dadaia_workspace.core.platform import PLATFORM
    from dadaia_workspace.features.workspace.service import WorkspaceService
    from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
    from dadaia_workspace.infrastructure.python_env import VenvPythonEnvironmentManager

    WorkspaceService(
        public_assets=FileSystemPublicAssetManager(),
        python_env=VenvPythonEnvironmentManager(),
    ).init(tmp_path)
    # VENV-1 skeleton (the conftest backstop fakes the venv builder) — as
    # tests/integration/test_cli_doctor.py materializes it, so the exit code under
    # test is the verdict of the records, never a missing entrypoint.
    venv_bin = tmp_path / ".dadaia" / ".venv" / PLATFORM.venv_scripts_dir
    venv_bin.mkdir(parents=True, exist_ok=True)
    entry = venv_bin / f"dadaia{PLATFORM.venv_exe_suffix}"
    entry.write_text("#!/bin/sh\n")
    entry.chmod(0o755)

    # The tree is the SELF-HOSTING root ``specs/`` of one registered context, so writer
    # and reader derive the same name from the tree itself — no $DADAIA_CONTEXT, which
    # names a session bind the --specs-dir under test overrides anyway.
    registry = tmp_path / ".dadaia" / "states" / "spec_contexts.json"
    document = json.loads(registry.read_text(encoding="utf-8"))
    document["contexts"] = [
        {
            "name": "lib-ws",
            "state": "alive",
            "repo_slug": "lib-ws",
            "repo_url": "https://example.invalid/lib-ws.git",
            "created_at": "2026-01-01T00:00:00+00:00",
            "alive_since": "2026-01-01T00:00:00+00:00",
            "dead_since": None,
            "current_branch": "main",
            "associated_repos": [],
        }
    ]
    registry.write_text(json.dumps(document), encoding="utf-8")

    target = tmp_path / "specs"
    (target / "bugs").mkdir(parents=True)
    (target / "releases").mkdir()
    monkeypatch.chdir(tmp_path)
    return target


def _run(*args: str) -> None:
    result = _runner.invoke(app, list(args))
    assert result.exit_code == 0, result.output


def _doctor(specs_dir: Path) -> tuple[int, dict[str, object]]:
    result = _runner.invoke(app, ["doctor", "--specs-dir", str(specs_dir), "--json"])
    assert result.stdout.startswith("{"), (result.stdout, result.exception)
    return result.exit_code, json.loads(result.stdout)


def _codes(payload: dict[str, object]) -> list[str]:
    return [str(finding["code"]) for finding in _findings(payload)]


def _findings(payload: dict[str, object]) -> list[dict[str, object]]:
    sections = payload["sections"]
    assert isinstance(sections, dict)
    return [finding for section in sections.values() for finding in section["findings"]]


def _append_bug(specs_dir: Path, bug_id: str) -> None:
    _run(
        "bugs", "append", "--specs-dir", str(specs_dir), "--bug-id", bug_id,
        "--title", bug_id, "--severity", "LOW", "--surface", "bugs",
        "--component", "c", "--context", "dadaia-workspace",
        "--symptom", "s", "--repro", "r", "--expected", "e",
    )  # fmt: skip


def _resolve_bug(specs_dir: Path, bug_id: str) -> None:
    _run(
        "bugs", "resolve", bug_id, "--specs-dir", str(specs_dir),
        "--cause", "the cause", "--caused-by", "none", "--resolved-release", "0.4.7",
        "--solution", "s", "--evidence-loop", "pytest -k hand_edit",
        "--evidence-seam", "tests/integration/cli/test_doctor_hand_edit.py",
        "--evidence-diff", "net-neutral: test only",
    )  # fmt: skip


def _hand_edit_bug(specs_dir: Path, bug_id: str) -> None:
    """What a file tool does: rewrite the record's `cause` in place, no verb."""
    path = specs_dir / "bugs" / "BUGS.jsonl"
    lines = path.read_text(encoding="utf-8").splitlines()
    out = []
    for line in lines:
        record = json.loads(line)
        if record.get("id") == bug_id:
            record["cause"] = "a cause nobody's verb ever wrote"
        out.append(json.dumps(record, sort_keys=True, ensure_ascii=False))
    path.write_text("\n".join(out) + "\n", encoding="utf-8")


def test_file_edit_after_bugs_resolve_is_one_ledger_bugs_handedit_warning(
    home: Path, specs: Path
) -> None:
    _append_bug(specs, "handedit-probe")
    _resolve_bug(specs, "handedit-probe")
    before_exit, before = _doctor(specs)
    assert "LEDGER-BUGS-HANDEDIT" not in _codes(before)

    _hand_edit_bug(specs, "handedit-probe")

    exit_code, payload = _doctor(specs)
    assert _codes(payload).count("LEDGER-BUGS-HANDEDIT") == 1
    finding = next(f for f in _findings(payload) if f["code"] == "LEDGER-BUGS-HANDEDIT")
    assert finding["verdict"] == "warning"
    assert "resolve" in str(finding["message"])
    # Measured, never blocked: the hand edit adds a line and moves no exit code.
    assert exit_code == before_exit


def test_hand_flipped_release_phase_is_one_release_tree_handedit_warning(
    home: Path, specs: Path
) -> None:
    _run("release", "new", "1.0.0", "--specs-dir", str(specs))
    before_exit, before = _doctor(specs)
    assert "RELEASE-TREE-HANDEDIT" not in _codes(before)

    state = specs / "releases" / "1.0.0" / "_RELEASE.json"
    document = json.loads(state.read_text(encoding="utf-8"))
    document["phase"] = "IMPLEMENTATION"
    state.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")

    exit_code, payload = _doctor(specs)
    assert _codes(payload).count("RELEASE-TREE-HANDEDIT") == 1
    finding = next(f for f in _findings(payload) if f["code"] == "RELEASE-TREE-HANDEDIT")
    assert finding["verdict"] == "warning"
    assert exit_code == before_exit


def test_a_workspace_with_no_telemetry_store_carries_no_handedit_finding(
    home: Path, specs: Path
) -> None:
    """A consumer without telemetry is not a consumer with drift: the records below are
    written by hand, and with no store to compare against the doctor stays silent."""
    (specs / "bugs" / "BUGS.jsonl").write_text(
        json.dumps(
            {
                "id": "hand-written",
                "ts": "2099-01-01T00:00:00Z",
                "status": "open",
                "reported_by": "software-engineer",
                "title": "t",
                "severity": "LOW",
                "surface": "bugs",
                "component": "c",
                "context": "dadaia-workspace",
                "symptom": "s",
                "repro": "r",
                "expected": "e",
            },
            sort_keys=True,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    assert not (container.telemetry_state_dir() / "telemetry.sqlite").exists()

    _exit_code, payload = _doctor(specs)
    assert [code for code in _codes(payload) if code.endswith("HANDEDIT")] == []
