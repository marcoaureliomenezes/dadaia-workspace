"""`dadaia doctor` over an explicit ``--specs-dir`` needs no
instance around it.

CI runs the doctor over a bare checkout (``dadaia doctor --specs-dir specs``): there
is no ``.dadaia/states/`` above the runner's cwd. The `specs` and `ledgers` sections
read the tree they were pointed at; the `workspace` section, with no instance to
walk, is empty (0/0) — never a refusal. With NOTHING to read (no instance, no
explicit tree) the run still refuses with the one initialization message.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app
from dadaia_workspace.core.specs_version import state
from dadaia_workspace.features.specs.canon import scaffold
from dadaia_workspace.infrastructure.ledger_scripts import script_repairs

_runner = CliRunner()
_REPO_ROOT = Path(__file__).resolve().parents[3]
_TEMPLATES_DIR = _REPO_ROOT / "dadaia_workspace" / "public" / "templates"


@pytest.fixture
def no_instance(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("DADAIA_CONTEXT", raising=False)
    return tmp_path


@pytest.mark.medium
def test_explicit_specs_dir_is_read_with_no_instance_around(no_instance: Path) -> None:
    specs = no_instance / "specs"
    scaffold(specs, project_name="bare", force=False, public_dir=_TEMPLATES_DIR.parent)
    script_repairs(specs)  # the catalog pair's one writer, as `specs init` runs it

    run = _runner.invoke(app, ["doctor", "--json", "--specs-dir", str(specs)])

    payload = json.loads(run.output)
    assert set(payload["sections"]) == {"workspace", "specs", "ledgers"}, run.output
    assert payload["sections"]["workspace"]["findings"] == []
    assert "specs" in payload["sections"] and "ledgers" in payload["sections"]
    assert run.exit_code == 0, run.output


@pytest.mark.medium
def test_an_absent_specs_dir_is_one_finding_and_its_fix_clears_the_doctor(
    no_instance: Path,
) -> None:
    specs = no_instance / "specs"

    run = _runner.invoke(app, ["doctor", "--json", "--specs-dir", str(specs)])

    sections = json.loads(run.output)["sections"]
    found = [f for section in sections.values() for f in section["findings"]]
    assert [f["fix"] for f in found] == [state(specs)[1]], run.output
    assert run.exit_code == 1
    assert _runner.invoke(app, ["specs", "init", "--specs-dir", str(specs)]).exit_code == 0
    assert _runner.invoke(app, ["doctor", "--specs-dir", str(specs)]).exit_code == 0


@pytest.mark.medium
def test_a_file_at_the_specs_dir_is_one_finding_and_moving_it_aside_clears_the_doctor(
    no_instance: Path,
) -> None:
    specs = no_instance / "specs"
    specs.write_text("", encoding="utf-8")

    run = _runner.invoke(app, ["doctor", "--json", "--specs-dir", str(specs)])

    sections = json.loads(run.output)["sections"]
    found = [f for section in sections.values() for f in section["findings"]]
    assert [(f["code"], f["fix"]) for f in found] == [
        ("SPECS-ABSENT", f"Operator action: move {specs} aside, it is a file, not a directory")
    ], run.output
    assert run.exit_code == 1
    specs.rename(no_instance / "moved-aside")
    assert _runner.invoke(app, ["specs", "init", "--specs-dir", str(specs)]).exit_code == 0
    assert _runner.invoke(app, ["doctor", "--specs-dir", str(specs)]).exit_code == 0


def test_nothing_to_read_refuses_with_one_fix(no_instance: Path) -> None:
    run = _runner.invoke(app, ["doctor"])

    assert run.exit_code == 1
    assert run.output.count("\nfix: ") == 1


def test_two_trees_is_a_usage_error_before_any_resolution(no_instance: Path) -> None:
    run = _runner.invoke(app, ["doctor", "--context", "ctx", "--specs-dir", str(no_instance)])

    assert run.exit_code == 2, run.output
    # Rich box-wraps the usage error at the runner's width and may split a token across
    # lines: strip ANSI codes and box glyphs before asserting the tokens are named.
    clean = re.sub(r"\x1b\[[0-9;]*m", "", run.output)
    clean = re.sub(r"[\u2500-\u257f\n ]", "", clean)
    assert "--context" in clean and "--specs-dir" in clean, run.output
