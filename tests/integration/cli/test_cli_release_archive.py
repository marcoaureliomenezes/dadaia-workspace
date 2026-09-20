"""``dadaia release archive`` end to end through the CLI (0.4.7 FR3, T-047-09).

Intent: CONTRACT — T-047-09: the promote verb writes the archive, the histo record and
the next release through the real stores, sweeps `bugs archive`, prints the three
`next:` git lines, and NEVER runs git; a refusal exits non-zero with a `fix:` line.
Size: MEDIUM — CliRunner over a tmp_path specs tree; no subprocess, no network.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app
from dadaia_workspace.core.models.histo import HistoRecord

_runner = CliRunner()
_SHA = "c" * 40


@pytest.fixture()
def specs(tmp_path: Path) -> Path:
    s = tmp_path / "specs"
    s.mkdir()
    result = _runner.invoke(app, ["release", "new", "1.0.0", "--specs-dir", str(s)])
    assert result.exit_code == 0, result.output
    rdir = s / "releases" / "1.0.0"
    (rdir / "PLAN.md").write_text("# PLAN\n", encoding="utf-8")
    (rdir / "TASKS.md").write_text("# TASKS\n\n- [x] T-1\n", encoding="utf-8")
    state = json.loads((rdir / "_RELEASE.json").read_text(encoding="utf-8"))
    state["phase"] = "CLOSURE"
    state["rc"] = 1
    state["implemented"] = {"sha": "d" * 40, "ts": "2999-01-01T00:00:00Z", "rc": 1}
    (rdir / "_RELEASE.json").write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    return s


def _archive(specs: Path, *extra: str) -> object:
    return _runner.invoke(
        app,
        [
            "release",
            "archive",
            "1.0.0",
            "--shipped",
            _SHA,
            "--pr",
            "251",
            "--next",
            "1.0.1",
            "--specs-dir",
            str(specs),
            *extra,
        ],
    )


def test_archive_writes_the_tree_the_histo_record_and_prints_the_git_lines(specs: Path) -> None:
    result = _archive(specs)

    assert result.exit_code == 0, result.output  # type: ignore[attr-defined]
    out: str = result.output  # type: ignore[attr-defined]
    assert (specs / "releases" / "_archive" / "1.0.0" / "SPEC.md").is_file()
    assert (specs / "releases" / "1.0.1" / "_RELEASE.json").is_file()

    histo_path = specs / "releases" / "_archive" / "releases_histo.jsonl"
    lines = [line for line in histo_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(lines) == 1
    record = HistoRecord.from_dict(json.loads(lines[0]))
    assert record.id == "1.0.0" and record.disposition == "delivered"

    assert (
        'next: git add -A specs/releases specs/bugs && git commit -m "chore(specs): '
        f'archive release 1.0.0 — shipped {_SHA} (PR #251); 1.0.1 born"' in out
    )
    assert "next: git push origin --delete feature/1.0.0" in out
    assert "next: git checkout -b feature/1.0.1 main && git merge -s ours origin/develop" in out


def test_an_open_task_exits_non_zero_with_a_fix_line_and_writes_nothing(specs: Path) -> None:
    (specs / "releases" / "1.0.0" / "TASKS.md").write_text(
        "# TASKS\n\n- [-] T-1\n", encoding="utf-8"
    )

    result = _archive(specs)

    assert result.exit_code == 1  # type: ignore[attr-defined]
    assert "fix: flip the open task markers to [x]" in result.output  # type: ignore[attr-defined]
    assert (specs / "releases" / "1.0.0" / "SPEC.md").is_file()
    assert not (specs / "releases" / "_archive").exists()
    assert not (specs / "releases" / "1.0.1").exists()


def test_rc_archive_runs_the_same_bugs_archive_sweep(specs: Path) -> None:
    """FR3: `rc-archive` shares the validator and the `bugs archive` call — the ledger
    sweep rides both archive verbs, never an agent's memory."""
    result = _runner.invoke(app, ["release", "rc-archive", "--specs-dir", str(specs)])

    assert result.exit_code == 0, result.output
    assert (specs / "releases" / "1.0.0" / "rc-1" / "SPEC.md").is_file()
