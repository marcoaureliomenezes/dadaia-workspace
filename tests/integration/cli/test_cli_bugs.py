from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from dadaia_workspace.cli.main import app


def test_bugs_append_status_stats_cli(tmp_path: Path) -> None:
    specs = tmp_path / "specs"
    (specs / "bugs").mkdir(parents=True)
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "bugs",
            "append",
            "cli-bug",
            "reported",
            "--reported-by",
            "tester",
            "--title",
            "CLI bug",
            "--severity",
            "HIGH",
            "--surface",
            "cli",
            "--context",
            "dadaia-workspace",
            "--symptom",
            "broken",
            "--specs-dir",
            str(specs),
            "--json",
        ],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["event"]["bug_id"] == "cli-bug"

    status = runner.invoke(app, ["bugs", "status", "--specs-dir", str(specs), "--json"])
    assert status.exit_code == 0, status.output
    assert json.loads(status.output)["cli-bug"]["state"] == "reported"

    stats = runner.invoke(app, ["bugs", "stats", "--specs-dir", str(specs), "--json"])
    assert stats.exit_code == 0, stats.output
    assert json.loads(stats.output)["by_event"] == {"reported": 1}
