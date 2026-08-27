"""`dadaia bugs append --context <B>` routes the event to context B's ledger.

Bug ``bugs-append-ledger-ignores-context-flag``: with a session bound to context A,
an append whose ``--context`` names context B silently landed in A's ledger — the
stored event carried ``context: B`` while living in ``repos/A/specs/bugs/``, so A's
doctor/status reported a foreign bug and B's ledger missed it. The event's context
field is now the routing key when no explicit ``--specs-dir`` overrides it; a
``--context`` that names no ``repos/<name>/specs`` dir is refused loudly, and an
explicit ``--specs-dir`` always wins (unchanged).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app

_runner = CliRunner()


@pytest.fixture()
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A minimal initialized workspace with two context repos, cwd inside it."""
    (tmp_path / ".dadaia" / "states").mkdir(parents=True)
    (tmp_path / ".dadaia" / "states" / "spec_contexts.json").write_text(
        json.dumps({"version": 2, "contexts": []}), encoding="utf-8"
    )
    for slug in ("ctx-a", "ctx-b"):
        (tmp_path / "repos" / slug / "specs" / "bugs").mkdir(parents=True)
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("DADAIA_CONTEXT", raising=False)
    return tmp_path


def _append_args(context: str, *, specs_dir: Path | None = None) -> list[str]:
    args = [
        "bugs",
        "append",
        "--bug-id",
        "routing-probe",
        "--title",
        "routing probe",
        "--severity",
        "LOW",
        "--surface",
        "cli",
        "--component",
        "bugs",
        "--context",
        context,
        "--symptom",
        "sym",
        "--repro",
        "repro",
        "--expected",
        "exp",
    ]
    if specs_dir is not None:
        args += ["--specs-dir", str(specs_dir)]
    return args


def _ledger_events(specs: Path) -> list[dict[str, object]]:
    events: list[dict[str, object]] = []
    for log in sorted((specs / "bugs").glob("*.jsonl")):
        for line in log.read_text(encoding="utf-8").splitlines():
            if line.strip():
                events.append(json.loads(line))
    return events


def test_context_flag_routes_to_that_contexts_ledger(workspace: Path) -> None:
    """--context ctx-b lands in repos/ctx-b/specs/bugs — not the env/bound context."""
    result = _runner.invoke(app, _append_args("ctx-b"), env={"DADAIA_CONTEXT": "ctx-a"})
    assert result.exit_code == 0, result.output
    b_events = _ledger_events(workspace / "repos" / "ctx-b" / "specs")
    assert [e["id"] for e in b_events] == ["routing-probe"]
    assert b_events[0]["context"] == "ctx-b"
    assert _ledger_events(workspace / "repos" / "ctx-a" / "specs") == []


def test_context_flag_naming_unknown_repo_is_refused_and_writes_nothing(
    workspace: Path,
) -> None:
    result = _runner.invoke(app, _append_args("ctx-missing"))
    assert result.exit_code != 0
    assert "ctx-missing" in result.output
    assert _ledger_events(workspace / "repos" / "ctx-a" / "specs") == []
    assert _ledger_events(workspace / "repos" / "ctx-b" / "specs") == []


def test_explicit_specs_dir_still_wins_over_context_flag(workspace: Path) -> None:
    target = workspace / "repos" / "ctx-a" / "specs"
    result = _runner.invoke(app, _append_args("ctx-b", specs_dir=target))
    assert result.exit_code == 0, result.output
    a_events = _ledger_events(target)
    assert [e["id"] for e in a_events] == ["routing-probe"]
    assert _ledger_events(workspace / "repos" / "ctx-b" / "specs") == []
