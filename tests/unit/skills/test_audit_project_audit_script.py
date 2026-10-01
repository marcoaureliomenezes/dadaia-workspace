"""Intent: CONTRACT — dd-audit-project/scripts/audit.py owns specs/audits/<dir>/
FINDINGS.jsonl and audits_histo.jsonl (0.4.7 c7 T-047-67: the audit ledger verbs move
into a stdlib skill script). Size: SMALL.

The script reads its two schemas from ``scripts/schemas/`` BESIDE itself — copies
`public stage` makes — so every test stages the folder exactly as stage does.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from tests.helpers.skill_scripts import stage_skill_scripts

pytestmark = pytest.mark.unit

_PUBLIC = Path(__file__).resolve().parents[3] / "dadaia_workspace" / "public"
_SCRIPTS = _PUBLIC / "skills" / "dd-audit-project" / "scripts"
_AUDIT = "20260101-window"


@pytest.fixture
def script(tmp_path: Path) -> Path:
    """The staged shape: audit.py with both schema copies beside it."""
    return stage_skill_scripts("dd-audit-project", tmp_path / "staged" / "scripts") / "audit.py"


def _finding(index: int, **over: object) -> dict[str, object]:
    record: dict[str, object] = {
        "id": f"{_AUDIT}-F{index:03d}",
        "pillar": "bugs",
        "severity": "HIGH",
        "refs": ["dadaia_workspace/cli/main.py:1"],
        "claim": "the claim",
        "evidence": "git show <sha> --stat -> 1 file changed",
        "disposition": "open",
        "release": None,
        "reason": None,
    }
    record.update(over)
    return record


@pytest.fixture
def specs(tmp_path: Path) -> Path:
    tree = tmp_path / "repo" / "specs"
    audit_dir = tree / "audits" / _AUDIT
    audit_dir.mkdir(parents=True)
    (tree / "audits" / "_archive").mkdir()
    (audit_dir / "AUDIT.md").write_text("# audit\n", encoding="utf-8")
    (audit_dir / "FINDINGS.jsonl").write_text(
        "".join(json.dumps(_finding(i), sort_keys=True) + "\n" for i in (1, 2)),
        encoding="utf-8",
    )
    return tree


def _run(script: Path, *argv: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script), *argv], capture_output=True, text=True, check=False
    )


def _histo(specs: Path) -> list[dict[str, object]]:
    path = specs / "audits" / "_archive" / "audits_histo.jsonl"
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


@pytest.mark.parametrize(
    ("argv", "finding", "needle"),
    [
        (("close", _AUDIT, "--sha", "abc1234"), _finding(1), "undispositioned"),
        (
            ("close", _AUDIT, "--sha", "abc1234"),
            _finding(1, severity="BANANA", disposition="resolved", release="0.4.8"),
            "does not pass check",
        ),
        (
            ("disposition", _AUDIT, f"{_AUDIT}-F001", "--disposition", "rejected", "--reason", "r"),
            _finding(1, severity="BANANA"),
            "does not pass check",
        ),
        (("close", "_archive", "--sha", "abc1234"), _finding(1), "does not name a live audit"),
    ],
)
def test_a_write_verb_refuses_and_leaves_every_byte(
    script: Path, specs: Path, argv: tuple[str, ...], finding: dict[str, object], needle: str
) -> None:
    """sa-audit-close-archives-without-validating#B43-1: a FINDINGS.jsonl failing check
    makes close exit non-zero, write no histo and keep the directory.
    sa-audit-close-archives-without-validating#B43-4: an `_archive` id is refused.
    sa-audit-close-archives-without-validating#B43-6: every write verb runs check over
    the candidate bytes."""
    for directory in (specs / "audits" / _AUDIT, specs / "audits" / "_archive"):
        (directory / "FINDINGS.jsonl").write_text(json.dumps(finding) + "\n", encoding="utf-8")
    before = (specs / "audits" / _AUDIT / "FINDINGS.jsonl").read_bytes()

    result = _run(script, *argv, "--specs", str(specs))

    assert result.returncode == 1
    assert needle in result.stderr and result.stderr.count("fix: ") == 1
    assert (specs / "audits" / _AUDIT / "FINDINGS.jsonl").read_bytes() == before
    assert (specs / "audits" / "_archive" / "FINDINGS.jsonl").is_file()
    assert _histo(specs) == []


def test_disposition_then_close_appends_the_histo_and_removes_the_directory(
    script: Path, specs: Path
) -> None:
    for index in (1, 2):
        done = _run(
            script, "disposition", _AUDIT, f"{_AUDIT}-F{index:03d}",
            "--disposition", "resolved", "--release", "0.4.8", "--specs", str(specs),
        )  # fmt: skip
        assert done.returncode == 0, done.stderr

    result = _run(script, "close", _AUDIT, "--sha", "abc1234", "--specs", str(specs))

    assert result.returncode == 0, result.stderr
    assert not (specs / "audits" / _AUDIT).exists()
    records = _histo(specs)
    assert len(records) == 1
    assert records[0]["id"] == _AUDIT
    assert records[0]["disposition"] == "resolved"
    assert records[0]["release"] == "0.4.8"
    assert records[0]["entry"] == {
        "sha": "abc1234",
        "pillars": {"bugs": 2, "specs": 0, "memory": 0},
        "dispositions": {"resolved": 2},
    }


def test_disposition_refuses_a_verdict_without_its_evidence(script: Path, specs: Path) -> None:
    result = _run(
        script, "disposition", _AUDIT, f"{_AUDIT}-F001",
        "--disposition", "deferred", "--specs", str(specs),
    )  # fmt: skip

    assert result.returncode == 1
    assert "--reason" in result.stderr
    assert (
        json.loads(
            (specs / "audits" / _AUDIT / "FINDINGS.jsonl").read_text("utf-8").split("\n")[0]
        )["disposition"]
        == "open"
    )


def test_check_passes_on_a_valid_tree_and_fails_on_a_broken_record(
    script: Path, specs: Path
) -> None:
    clean = _run(script, "check", "--specs", str(specs))
    assert clean.returncode == 0, clean.stdout + clean.stderr

    findings = specs / "audits" / _AUDIT / "FINDINGS.jsonl"
    findings.write_text(
        json.dumps(_finding(1, severity="URGENT"), sort_keys=True) + "\n", encoding="utf-8"
    )
    broken = _run(script, "check", "--specs", str(specs))

    assert broken.returncode == 1
    assert "LEDGER-FINDINGS-SCHEMA" in broken.stdout
    assert "severity" in broken.stdout


@pytest.mark.parametrize(
    ("verdicts", "expected"),
    [
        ((), "rejected"),
        (("deferred", "deferred"), "deferred"),
        (("rejected", "rejected"), "rejected"),
        (("deferred", "rejected"), "deferred"),
    ],
)
def test_close_without_a_resolved_finding_never_records_resolved(
    script: Path, specs: Path, verdicts: tuple[str, ...], expected: str
) -> None:
    """sa-audit-close-archives-without-validating#B43-3: all deferred/rejected gives the
    histo disposition deferred/rejected, never resolved; a clean audit
    (audit-close-refuses-a-clean-audit) still closes."""
    records = [_finding(i + 1, disposition=v, reason="r") for i, v in enumerate(verdicts)]
    (specs / "audits" / _AUDIT / "FINDINGS.jsonl").write_text(
        "".join(json.dumps(r) + "\n" for r in records), encoding="utf-8"
    )

    result = _run(script, "close", _AUDIT, "--sha", "abc1234", "--specs", str(specs))

    assert result.returncode == 0, result.stderr
    assert not (specs / "audits" / _AUDIT).exists()
    [record] = _histo(specs)
    assert (record["disposition"], record["release"]) == (expected, None)
    assert record["entry"]["pillars"] == {"bugs": len(verdicts), "specs": 0, "memory": 0}


def test_the_doctor_neither_folds_findings_nor_recommends_close() -> None:
    """sa-audit-close-archives-without-validating#B43-2: no doctor rule recommends
    `audit.py close`. sa-audit-close-archives-without-validating#B43-5: features/specs
    parses no finding record."""
    from dadaia_workspace.features.specs.rules import RULES

    assert not [r.codes for r in RULES if "close" in str(r.fix_help)]
    specs_src = Path(__file__).resolve().parents[3] / "dadaia_workspace" / "features" / "specs"
    assert not [p for p in specs_src.glob("*.py") if "from_dict" in p.read_text("utf-8")]
