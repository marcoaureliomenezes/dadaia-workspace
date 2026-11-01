"""A specs document that is not UTF-8 is one `SPEC-DOC-002` finding with the act that re-encodes
it, whichever rule reads it first; `dadaia doctor` exits 1 and never raises."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app
from dadaia_workspace.core.doctor_rules import run_section
from dadaia_workspace.features.specs.doctor import SpecsDoctor
from dadaia_workspace.features.specs.rules import RULES
from tests.features.specs.test_doctor import _make_clean_specs_tree
from tests.helpers.oslib import write_text

pytestmark = pytest.mark.medium

_CP1252 = "# Qualidade — ação\n".encode("cp1252")


def _doctor_findings(root: Path) -> tuple[int, list[dict[str, str]]]:
    result = CliRunner().invoke(app, ["doctor", "--json", "--specs-dir", str(root / "specs")])
    assert result.exception is None or isinstance(result.exception, SystemExit), repr(
        result.exception
    )
    return result.exit_code, json.loads(result.output)["sections"]["specs"]["findings"]


def _reported(root: Path, rel: str) -> list[dict[str, str]]:
    path = root / "specs" / rel
    path.write_bytes(_CP1252)
    code, findings = _doctor_findings(root)
    assert code == 1
    return [f for f in findings if str(path) in f["message"]]


@pytest.mark.parametrize(
    "rel",
    [
        "memory/QUALITY.md",
        "memory/ARCHITECTURE.md",
        "memory/product/index.md",
        "memory/product/testarea/feature-a.md",
        "memory/AGENTS.md",
    ],
)
def test_a_non_utf8_memory_document_is_one_finding_and_never_a_crash(
    tmp_path: Path, rel: str
) -> None:
    _make_clean_specs_tree(tmp_path)
    write_text(tmp_path / "specs" / "memory" / "AGENTS.md", "# Memory law\n")

    (found,) = _reported(tmp_path, rel)

    path = (tmp_path / "specs" / rel).resolve()
    assert (found["code"], found["fix"]) == (
        "SPEC-DOC-002",
        f"Agent action: re-encode line 1 of {path} as UTF-8 in place; every other line stays",
    )


def test_a_non_utf8_library_document_is_one_reinstall_finding(tmp_path: Path) -> None:
    """The superseded-ADR walk reads the library's skills too: a skill that is not UTF-8 is
    reinstalled, never skipped and never re-encoded by hand."""
    specs = tmp_path / "specs"
    (specs / "ADRs").mkdir(parents=True)
    write_text(specs / "ADRs" / "decisions.jsonl", '{"id": "0005", "status": "superseded"}\n')
    skill = tmp_path / "public" / "skills" / "dd-x" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_bytes("ADR 0005 — ação\n".encode("cp1252"))
    rule = next(r for r in RULES if r.codes == ("ADR-SUPERSEDED-CITATION",))

    report = run_section("specs", [rule], SpecsDoctor(specs, tmp_path / "public"), None, specs)

    assert [(f.code, f.fix) for f in report.findings] == [
        (
            "SPEC-DOC-002",
            "Agent action: run `uvx dadaia-workspace init` with the workspace's directory as its first argument",
        )
    ]


def test_a_non_utf8_ledger_is_one_finding_across_the_whole_run(tmp_path: Path) -> None:
    """The specs and ledgers sections both read the ADR ledger; the run reports it once."""
    _make_clean_specs_tree(tmp_path)
    ledger = tmp_path / "specs" / "ADRs" / "decisions.jsonl"
    ledger.parent.mkdir(parents=True, exist_ok=True)
    ledger.write_bytes('{"id": "0001", "title": "ação"}\n'.encode("cp1252"))

    result = CliRunner().invoke(app, ["doctor", "--json", "--specs-dir", str(tmp_path / "specs")])

    sections = json.loads(result.output)["sections"]
    named = [f for s in sections.values() for f in s["findings"] if str(ledger) in f["message"]]
    assert [(f["code"], f["fix"]) for f in named] == [
        (
            "SPEC-DOC-002",
            f"Agent action: re-encode line 1 of {ledger.resolve()} as UTF-8 in place; every other line stays",
        )
    ]
