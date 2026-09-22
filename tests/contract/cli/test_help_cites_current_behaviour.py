"""Intent: CONTRACT — help-texts-and-bug-schema-cite-behaviour-that-is-gone.

Help and schema text state current behaviour only: preflight names its five checks
and no hook that calls it; bind carries no retired-flag history; the bug-record schema
cites no retired verb.
"""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from dadaia_workspace.cli.main import app

_SCHEMA = (
    Path(__file__).parents[3] / "dadaia_workspace/public/schemas/bugs/bug-record-v1.schema.json"
)


def _help(*argv: str) -> str:
    result = CliRunner().invoke(app, [*argv, "--help"], env={"COLUMNS": "400"})
    assert result.exit_code == 0, result.output
    return " ".join(result.output.split())


def test_preflight_help_names_its_five_checks_and_no_hook() -> None:
    text = _help("ci", "preflight")
    assert "pre-push" not in text
    for check in ("ruff format", "ruff check", "mypy --strict", "lint-imports", "pytest"):
        assert check in text, check


def test_bind_help_carries_no_history() -> None:
    text = _help("context", "bind")
    for gone in ("--mode", "--release", "--force", "--reason", "0.4.7"):
        assert gone not in text, gone


def test_bug_schema_cites_no_retired_verb() -> None:
    text = _SCHEMA.read_text(encoding="utf-8")
    assert "dadaia bugs append" not in text
    assert "features/specs/schemas.py" not in text
