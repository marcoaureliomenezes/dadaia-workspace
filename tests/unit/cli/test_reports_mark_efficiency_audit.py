"""Unit tests for ``dadaia reports mark-efficiency-audit`` (v0.1.60 FR7 writer verb).

The deterministic CLI writer records ``.dadaia/states/last_efficiency_audit.json`` with the
current RFC3339 timestamp — the production clear path for the doctor EFF-1 staleness issue.
The round-trip test (stale marker fires EFF-1 → writer clears it) is the coupling guard that
the writer and the EFF-1 reader agree on the marker filename + schema — the only test that
fails if either side drifts. Schema-field and default-by asserts fold in as extra asserts on
the same invocation.
"""

from __future__ import annotations

import json

import pytest

pytest.importorskip("fcntl")

from datetime import UTC, datetime, timedelta  # noqa: E402
from pathlib import Path  # noqa: E402

from typer.testing import CliRunner  # noqa: E402

from dadaia_workspace.cli.main import app  # noqa: E402
from dadaia_workspace.features.spec_context.doctor import DoctorService  # noqa: E402
from tests.fakes import FakeContextStore, FakeGitClient  # noqa: E402

_runner = CliRunner()


def _workspace(tmp_path: Path) -> Path:
    states = tmp_path / ".dadaia" / "states"
    states.mkdir(parents=True)
    (states / "spec_contexts.json").write_text(
        json.dumps({"schema_version": "2", "contexts": []}), encoding="utf-8"
    )
    (tmp_path / "repos").mkdir()
    (tmp_path / "AGENTS.md").write_text("# agents")
    return tmp_path


def _marker(tmp_path: Path) -> Path:
    return tmp_path / ".dadaia" / "states" / "last_efficiency_audit.json"


def _eff1_count(tmp_path: Path) -> int:
    issues = DoctorService(FakeContextStore(), FakeGitClient(), tmp_path).check()
    return sum(1 for i in issues if i.code == "EFF-1")


def test_writer_schema_default_by_and_round_trip_clears_eff1(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The writer round-trip is the load-bearing coupling guard: a pre-existing STALE
    marker fires EFF-1; running the writer clears it (fresh marker) — the only test that
    fails if filenames/schema drift apart between writer and reader. The canonical schema
    (with --by) and the default-by-empty-string case fold in as asserts on the writes.
    """
    ws = _workspace(tmp_path)
    monkeypatch.chdir(ws)

    # Canonical schema with --by.
    result = _runner.invoke(
        app,
        [
            "reports",
            "mark-efficiency-audit",
            "--report",
            ".dadaia/reports/x/eff.html",
            "--by",
            "ai-engineer",
        ],
    )
    assert result.exit_code == 0, result.output
    data = json.loads(_marker(tmp_path).read_text(encoding="utf-8"))
    assert data["schema_version"] == "1"
    assert data["by"] == "ai-engineer"
    assert data["report"] == ".dadaia/reports/x/eff.html"
    assert data["last_efficiency_audit"].endswith("Z")

    # --by defaults to empty string when omitted.
    default_result = _runner.invoke(app, ["reports", "mark-efficiency-audit", "--report", "r.html"])
    assert default_result.exit_code == 0, default_result.output
    assert json.loads(_marker(tmp_path).read_text(encoding="utf-8"))["by"] == ""

    # Round-trip: plant a STALE marker, confirm EFF-1 fires, then confirm the writer
    # clears it.
    _marker(ws).write_text(
        json.dumps(
            {
                "schema_version": "1",
                "last_efficiency_audit": (datetime.now(tz=UTC) - timedelta(days=45))
                .isoformat()
                .replace("+00:00", "Z"),
                "by": "",
                "report": "old.html",
            }
        ),
        encoding="utf-8",
    )
    assert _eff1_count(ws) == 1  # stale ⇒ EFF-1

    fresh_result = _runner.invoke(
        app, ["reports", "mark-efficiency-audit", "--report", "fresh.html"]
    )
    assert fresh_result.exit_code == 0, fresh_result.output
    assert _eff1_count(ws) == 0  # fresh marker ⇒ EFF-1 cleared (writer↔reader agree)
