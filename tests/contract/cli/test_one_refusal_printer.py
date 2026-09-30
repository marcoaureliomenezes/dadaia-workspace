"""Intent: CONTRACT — sa-rich-printer-wraps-fix-lines (0.5.0 WP-18).

One printer (``cli/_fail``): every refusal prints ``Error: <message>`` with its ``fix:``
lines whole, exits 1 (a Click usage error keeps 2), never through Rich or ``secho``.
Size: SMALL (AST over cli/) + MEDIUM (CliRunner over the real app, tmp roots).
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app

pytestmark = pytest.mark.contract

_CLI = Path(__file__).resolve().parents[3] / "dadaia_workspace" / "cli"
_runner = CliRunner()


def _printer_bypasses() -> list[str]:
    """Every refusal-printer call outside cli/_fail.py: secho, a stderr Console, or an
    exit code other than 0/1 (Click's own usage errors never pass through here)."""
    hits: list[str] = []
    for path in sorted(_CLI.rglob("*.py")):
        if path.name == "_fail.py":
            continue
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if not isinstance(node, ast.Call):
                continue
            name = getattr(node.func, "attr", getattr(node.func, "id", ""))
            codes = [a.value for a in node.args if isinstance(a, ast.Constant)]
            stderr = any(k.arg == "stderr" for k in node.keywords)
            if name == "secho" or (name == "Console" and stderr):
                hits.append(f"{path.name}:{node.lineno}:{name}")
            elif name in {"Exit", "exit"} and any(c not in (0, 1) for c in codes):
                hits.append(f"{path.name}:{node.lineno}:{name}{codes}")
    return hits


def test_s1_the_one_printer_is_cli_fail() -> None:
    """sa-rich-printer-wraps-fix-lines#S1: no refusal is printed or exited outside
    cli/_fail (no secho, no stderr Console, no exit 2/3)."""
    assert _printer_bypasses() == []


def test_s2_an_init_refusal_is_error_fix_exit_1(tmp_path: Path, monkeypatch) -> None:
    """sa-rich-printer-wraps-fix-lines#S2: a refusal (not a usage error) exits 1 with
    `Error:` and one whole `fix:` line."""
    monkeypatch.chdir(tmp_path)
    result = _runner.invoke(app, ["init", str(tmp_path / "ws")])

    assert result.exit_code == 1, result.output
    assert result.output.startswith("Error: ")
    assert [line for line in result.output.splitlines() if line.startswith("fix: ")]


def test_s4_an_unresolvable_specs_dir_is_error_exit_1(tmp_path: Path, monkeypatch) -> None:
    """sa-rich-printer-wraps-fix-lines#S4: a resolution error goes through the printer,
    never Click's Rich panel."""
    monkeypatch.chdir(tmp_path)
    for var in ("DADAIA_CONTEXT", "DADAIA_SESSION_ID", "CLAUDE_CODE_SESSION_ID"):
        monkeypatch.delenv(var, raising=False)
    result = _runner.invoke(app, ["specs", "upgrade"])

    assert result.exit_code == 1, result.output
    assert result.output.startswith("Error: Could not resolve specs_dir")
    assert "╭" not in result.output


def test_s5_specs_upgrade_below_the_floor_is_error_exit_1(tmp_path: Path) -> None:
    """sa-rich-printer-wraps-fix-lines#S5: `specs upgrade` on a tree below the floor prints
    `Error:` and exits 1."""
    specs = tmp_path / "specs"
    specs.mkdir()
    (specs / "constitution.md").write_text("# C\n", encoding="utf-8")

    result = _runner.invoke(app, ["specs", "upgrade", "--specs-dir", str(specs)])

    assert result.exit_code == 1, result.output
    assert result.output.startswith("Error: specs tree ")


def test_s6_reports_validate_refusals_exit_1(tmp_path: Path, monkeypatch) -> None:
    """sa-rich-printer-wraps-fix-lines#S6: a missing path, no paths, or no workspace all
    exit 1 through the printer."""
    monkeypatch.chdir(tmp_path)
    for argv in (["reports", "validate"], ["reports", "validate", str(tmp_path / "gone.json")]):
        result = _runner.invoke(app, argv)
        assert result.exit_code == 1, (argv, result.output)
        assert "Error: " in result.output
    json.dumps({})  # (keeps the json import honest for the payload helpers below)
