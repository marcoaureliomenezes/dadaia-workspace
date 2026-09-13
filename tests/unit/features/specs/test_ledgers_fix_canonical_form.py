"""``LEDGER-BUGS-SCHEMA``'s fixer runs on the executed path — `dadaia doctor --fix`.

Intent: CONTRACT — T-047-25 (SPEC 0.4.7 FR1): the one ledger whose model invariant
ships a migration re-serializes every committed record, stripping the seven retired
derived-provenance keys and stamping a terminal record's ``closed_at`` from its own
filing date ``ts``.
Size: SMALL — one fixture ledger under tmp_path, the rule run over its own context
with the repair wired exactly as ``cli/commands/doctor.py`` wires it; no subprocess,
no CLI runner, no network, never the live ledger.

Structural frame: ``tests/unit/features/bugs/test_heal_closed_at.py`` covered the
predecessor (``BugService.heal_closed_at``) and was deleted with it at ``717c08ae``
when the git-history walk went; the replacement fixer
(``features/specs/ledgers.py::_fix_canonical_form`` →
``BugService.normalize_records``) shipped with no test that CALLS it, so
``QUALITY.md`` claimed a proof that did not run (T-047-34 operator finding 1).
``test_ledgers_validate.py`` locates the issue; this file runs the fix.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dadaia_workspace.cli.commands.bugs import build_bug_service
from dadaia_workspace.features.specs import ledgers

pytestmark = pytest.mark.unit

_TS = "2026-09-01T00:00:00Z"
#: Every key ``bug-record-v1`` requires today, canonical for an OPEN record.
_BUG: dict[str, object] = {
    "id": "a-fixture-bug",
    "ts": _TS,
    "reported_by": "software-engineer",
    "title": "a-fixture-bug",
    "severity": "LOW",
    "surface": "specs",
    "component": "fixture",
    "context": "fixture",
    "symptom": "fixture",
    "repro": "fixture",
    "expected": "fixture",
    "status": "open",
    "closed_at": None,
    "cause": None,
    "caused_by": None,
    "resolved_release": None,
    "solution": None,
    "evidence_loop": None,
    "evidence_seam": None,
    "evidence_diff": None,
    "diff_direction": None,
    "audited": None,
}


def _ledger(specs: Path) -> Path:
    return specs / "bugs" / "BUGS.jsonl"


def _write(specs: Path, records: list[dict[str, object]]) -> Path:
    path = _ledger(specs)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(r, sort_keys=True) + "\n" for r in records), encoding="utf-8"
    )
    return path


def _read(specs: Path) -> list[dict[str, object]]:
    text = _ledger(specs).read_text(encoding="utf-8")
    return [json.loads(line) for line in text.split("\n") if line.strip()]


def _fix(specs: Path) -> None:
    """The executed path: the `ledgers` rules run over one context whose repair is
    wired exactly as `cli/commands/doctor.py` wires it, and `--fix` calls a rule's
    fixer once per issue it reported."""
    ctx = ledgers.build_ledgers_context(
        specs,
        normalize_bug_records=build_bug_service(specs, with_archive=True).normalize_records,
    )
    for rule in ledgers.RULES:
        for issue in rule.run(ctx):
            if rule.fix is not None:
                rule.fix(ctx, issue)


def test_the_fixer_strips_a_retired_provenance_key_and_stamps_closed_at_from_ts(
    tmp_path: Path,
) -> None:
    """One pass, two classes of drift: a legacy record carrying the git-derived cache
    ``resolved_commit`` loses it losslessly, and a terminal record with no
    ``closed_at`` is stamped with its OWN filing date — never a later one, the bound
    ``BugRecord.__post_init__`` enforces."""
    specs = tmp_path / "specs"
    legacy = {**_BUG, "id": "legacy-bug", "resolved_commit": "0123456789abcdef"}
    terminal = {
        **_BUG,
        "id": "terminal-bug",
        "status": "resolved",
        "cause": "fixture cause",
        "resolved_release": "0.4.7",
        "solution": "fixture solution",
        "evidence_loop": "pytest -q",
        "evidence_seam": "tests/x.py::y",
        "evidence_diff": "net-negative: -1/+0",
        "diff_direction": "net-negative",
        "closed_at": None,
    }
    _write(specs, [legacy, terminal])

    _fix(specs)

    healed = {record["id"]: record for record in _read(specs)}
    assert "resolved_commit" not in healed["legacy-bug"]
    assert healed["terminal-bug"]["closed_at"] == _TS


def test_the_fixer_is_idempotent_over_an_already_canonical_ledger(tmp_path: Path) -> None:
    """A second pass costs nothing — load-bearing, because the doctor calls the fixer
    once per reported issue and only an idempotent pass lets ``--fix`` run on every
    tree without churning the ledger."""
    specs = tmp_path / "specs"
    _write(specs, [_BUG])

    _fix(specs)
    canonical = _ledger(specs).read_text(encoding="utf-8")
    _fix(specs)

    assert _ledger(specs).read_text(encoding="utf-8") == canonical


def test_the_fixer_preserves_a_line_it_cannot_parse(tmp_path: Path) -> None:
    """The pass runs on RAW lines precisely because an unconstructible record is what
    it repairs; a line this migration cannot read is preserved verbatim rather than
    dropped — a fixer never loses a record."""
    specs = tmp_path / "specs"
    path = _write(specs, [{**_BUG, "id": "terminal-bug", "status": "resolved", "cause": "c"}])
    path.write_text(path.read_text(encoding="utf-8") + "not json at all\n", encoding="utf-8")

    _fix(specs)

    lines = path.read_text(encoding="utf-8").split("\n")
    assert "not json at all" in lines
