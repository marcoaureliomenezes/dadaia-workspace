"""Every committed governance record validates (0.4.7 FR6/FR7, T-047-03).

The 2026-09-12 lifecycle audit's one structural cause: **schemas existed for live
documents only, and were exercised against synthetic fixtures.** Six of ten ADR
records failed ``decision-record-v1`` while every doctor printed clean, and the three
``_histo.jsonl`` histories had no schema and no reader at all. A record class nobody
reads is a record class that drifts.

This module is the missing reader — ONE walk over every committed governance ledger,
ONE schema validation per record, ONE located issue type. It adds no validation logic
of its own: the shape of a record is its schema (``features.specs.schemas``), and the
only per-ledger parameter is which terminal words a history file may use
(``core.models.histo``'s subsets). Seven ledgers, seven rule rows, one table — a new
ledger is a row, never a new code path.

The rows are contributed to the ``ledgers`` section of the one doctor
(``core.doctor_rules``) exactly as ``features/backlog/doctor.py`` contributes its
BL-* rules: this feature keeps its own context and its own issue type, and the CLI
composition root is the only place the two rule groups meet — no cross-feature import.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from dadaia_workspace.core.doctor_rules import Rule
from dadaia_workspace.core.models.histo import (
    AUDITS_HISTO_DISPOSITIONS,
    BACKLOG_HISTO_DISPOSITIONS,
    RELEASES_HISTO_DISPOSITIONS,
)
from dadaia_workspace.features.specs.schemas import schema_errors

__all__ = [
    "LEDGERS",
    "RULES",
    "Ledger",
    "LedgerIssue",
    "LedgerRule",
    "LedgersContext",
    "build_ledgers_context",
    "ledger_issues",
]


@dataclass(frozen=True)
class LedgerIssue:
    """One invalid committed record. ``path`` is POSIX and relative to ``specs_dir``
    and ``unit`` is ``path:line`` — an issue is rendered by a doctor and pasted into a
    report, so it never carries a local absolute path (nor does ``message``:
    jsonschema names the instance property, never the file)."""

    code: str
    path: str
    line: int
    message: str

    @property
    def unit(self) -> str:
        return f"{self.path}:{self.line}"


@dataclass(frozen=True)
class Ledger:
    """One validated ledger: where its records live, which schema shapes them, and —
    for a history file — which terminal words it may use."""

    name: str
    #: Glob, relative to ``specs_dir``. ``BACKLOG.json`` is one whole-document record;
    #: every other ledger is JSONL, one record per non-blank line.
    glob: str
    schema: str
    jsonl: bool = True
    dispositions: tuple[str, ...] | None = None

    @property
    def code(self) -> str:
        return f"LEDGER-{self.name}-SCHEMA"


#: The seven committed governance ledgers. Every ``_RELEASE.json`` is deliberately
#: ABSENT: it is validated by ``validate_release_tree`` (T-047-01) in the ``specs``
#: section, and one record validated twice is one finding printed twice.
LEDGERS: tuple[Ledger, ...] = (
    Ledger("ADR", "ADRs/decisions.jsonl", "ADRs/decision-record-v1"),
    Ledger("BACKLOG", "backlog/BACKLOG.json", "backlog/backlog-v1", jsonl=False),
    Ledger("BUGS", "bugs/BUGS.jsonl", "bugs/bug-record-v1"),
    Ledger("FINDINGS", "audits/*/FINDINGS.jsonl", "audits/finding-record-v1"),
    Ledger(
        "BACKLOG-HISTO",
        "backlog/_archive/backlog_histo.jsonl",
        "histo/histo-record-v1",
        dispositions=BACKLOG_HISTO_DISPOSITIONS,
    ),
    Ledger(
        "AUDITS-HISTO",
        "audits/_archive/audits_histo.jsonl",
        "histo/histo-record-v1",
        dispositions=AUDITS_HISTO_DISPOSITIONS,
    ),
    Ledger(
        "RELEASES-HISTO",
        "releases/_archive/releases_histo.jsonl",
        "histo/histo-record-v1",
        dispositions=RELEASES_HISTO_DISPOSITIONS,
    ),
)


@dataclass(frozen=True)
class _Located:
    """One record as committed: where it sits and what it parsed to (``None`` = the
    line is not JSON at all)."""

    path: str
    line: int
    record: object | None
    parse_error: str | None = None


@dataclass(frozen=True)
class LedgersContext:
    """Every committed record of every ledger, read ONCE. The rules validate what this
    context holds — no rule touches the disk, so the section's denominator
    (:attr:`total_records`) and its findings can never disagree about what was read."""

    specs_dir: Path
    records: dict[str, tuple[_Located, ...]] = field(default_factory=dict)

    @property
    def total_records(self) -> int:
        return sum(len(located) for located in self.records.values())


def _read_jsonl(path: Path, rel: str) -> list[_Located]:
    out: list[_Located] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").split("\n"), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            out.append(_Located(rel, number, json.loads(stripped)))
        except json.JSONDecodeError as exc:
            out.append(_Located(rel, number, None, f"line is not valid JSON: {exc.msg}"))
    return out


def _read_json(path: Path, rel: str) -> list[_Located]:
    try:
        return [_Located(rel, 1, json.loads(path.read_text(encoding="utf-8")))]
    except json.JSONDecodeError as exc:
        return [_Located(rel, 1, None, f"document is not valid JSON: {exc.msg}")]


def build_ledgers_context(specs_dir: Path) -> LedgersContext:
    """Read every committed record of every ledger once. An absent ledger file is an
    empty list, never an issue: a young specs tree has no audits and no history yet."""
    records: dict[str, tuple[_Located, ...]] = {}
    for ledger in LEDGERS:
        located: list[_Located] = []
        for path in sorted(specs_dir.glob(ledger.glob)):
            if not path.is_file():
                continue
            rel = path.relative_to(specs_dir).as_posix()
            located.extend(_read_jsonl(path, rel) if ledger.jsonl else _read_json(path, rel))
        records[ledger.glob] = tuple(located)
    return LedgersContext(specs_dir=specs_dir, records=records)


def _validate(ledger: Ledger, ctx: LedgersContext) -> list[LedgerIssue]:
    issues: list[LedgerIssue] = []
    for located in ctx.records.get(ledger.glob, ()):
        if located.parse_error is not None:
            issues.append(LedgerIssue(ledger.code, located.path, located.line, located.parse_error))
            continue
        for message in schema_errors(located.record, ledger.schema):
            issues.append(LedgerIssue(ledger.code, located.path, located.line, message))
        if ledger.dispositions is None:
            continue
        disposition = (
            located.record.get("disposition") if isinstance(located.record, dict) else None
        )
        if isinstance(disposition, str) and disposition not in ledger.dispositions:
            issues.append(
                LedgerIssue(
                    ledger.code,
                    located.path,
                    located.line,
                    f"disposition {disposition!r} is not one of this ledger's terminal "
                    f"words: {', '.join(ledger.dispositions)}",
                )
            )
    return issues


#: This feature's binding of the ONE doctor rule record: the `ledgers` section's
#: schema rules run over :class:`LedgersContext` and emit :class:`LedgerIssue`.
type LedgerRule = Rule[LedgersContext, LedgerIssue]

SECTION = "ledgers"

#: One rule per ledger — the codes a reader greps for.
RULES: tuple[LedgerRule, ...] = tuple(
    Rule(
        (ledger.code,),
        SECTION,
        (lambda bound: lambda ctx: _validate(bound, ctx))(ledger),
    )
    for ledger in LEDGERS
)


def ledger_issues(specs_dir: Path) -> list[LedgerIssue]:
    """Every invalid committed record of every ledger — the one-shot path (the doctor
    runs the rules over a pre-built context instead, so it can score the denominator)."""
    ctx = build_ledgers_context(specs_dir)
    issues: list[LedgerIssue] = []
    for rule in RULES:
        issues.extend(rule.run(ctx))
    return issues
