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
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path

from dadaia_workspace.core.doctor_rules import Rule
from dadaia_workspace.core.kernel_tunables import DADAIA_BIN
from dadaia_workspace.core.models.bugs import BugRecord
from dadaia_workspace.core.models.histo import (
    AUDITS_HISTO_DISPOSITIONS,
    BACKLOG_HISTO_DISPOSITIONS,
    RELEASES_HISTO_DISPOSITIONS,
)
from dadaia_workspace.core.models.telemetry import GovernanceBaseline
from dadaia_workspace.features.specs.doctor_types import Severity
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
    #: This issue's OWN word (``error``/``warning``) — a record is either invalid (an
    #: error: the shape is wrong) or merely unexplained (a warning: the shape is right
    #: and no verb claims it). One field, no mapping table at the render seam.
    verdict: str = Severity.ERROR.value
    #: This issue's OWN executable remediation, when the rule's generic ``fix_help``
    #: would not repair it. Empty = the rule's ``fix_help`` stands. A hand-editable
    #: schema violation and a model invariant with a shipped migration are the same code
    #: and a different fix; printing one command for both is a Stall for whichever it
    #: does not fix.
    fix: str = ""

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
    #: Why this ledger's committed record is not in the canonical shape its model emits
    #: today (``None`` = the record is fine) — the ONE column whose issues the injected
    #: fixer repairs. Two drifts, one authority, because both are the same statement:
    #: a model invariant the JSON Schema cannot express ("``closed_at`` is non-null IF
    #: AND ONLY IF ``status`` is terminal", bug
    #: ``bugs-update-cannot-heal-terminal-record-missing-closed-at``), and a record
    #: carrying keys its model has retired (0.4.7 FR1's seven derived-provenance keys).
    #: The model that owns the shape reports it; nothing here restates a rule.
    canonical_issue: Callable[[Mapping[str, object]], str | None] | None = None

    #: The governance-event namespace whose events are written OVER this ledger's
    #: records (``GovernanceEvent.ledger``) — the join key of the hand-edit rule
    #: (0.4.7 FR6). ``None`` = no verb owns this ledger's records, so a hand edit of
    #: them is not measurable and the rule does not exist for it: ``BACKLOG.json``
    #: maturation and `audits/*/FINDINGS.jsonl` stay hand-written by design (SPEC Q3),
    #: and ADRs are flipped by the operator alone.
    events_ledger: str | None = None

    @property
    def code(self) -> str:
        return f"LEDGER-{self.name}-SCHEMA"

    @property
    def hand_edit_code(self) -> str:
        return f"LEDGER-{self.name}-HANDEDIT"


def _bug_canonical_issue(record: Mapping[str, object]) -> str | None:
    """``BugRecord``'s own answer to "is this committed line what you would write?" —
    never a second copy of either rule. ``BugRecord.__post_init__`` is the one authority
    on non-null-iff-terminal ``closed_at``, and ``to_dict`` is the one authority on which
    keys a record still has."""
    try:
        canonical = BugRecord.from_dict(record).to_dict()
    except (TypeError, ValueError) as exc:
        return str(exc)
    retired = sorted(set(record) - set(canonical))
    if retired:
        return f"record carries retired key(s) {', '.join(retired)} (0.4.7 FR1)"
    return None


#: The seven committed governance ledgers. Every ``_RELEASE.json`` is deliberately
#: ABSENT: it is validated by ``validate_release_tree`` (T-047-01) in the ``specs``
#: section, and one record validated twice is one finding printed twice.
LEDGERS: tuple[Ledger, ...] = (
    Ledger("ADR", "ADRs/decisions.jsonl", "ADRs/decision-record-v1"),
    Ledger("BACKLOG", "backlog/BACKLOG.json", "backlog/backlog-v1", jsonl=False),
    Ledger(
        "BUGS",
        "bugs/BUGS.jsonl",
        "bugs/bug-record-v1",
        canonical_issue=_bug_canonical_issue,
        events_ledger="bugs",
    ),
    Ledger("FINDINGS", "audits/*/FINDINGS.jsonl", "audits/finding-record-v1"),
    Ledger(
        "BACKLOG-HISTO",
        "backlog/_archive/backlog_histo.jsonl",
        "histo/histo-record-v1",
        dispositions=BACKLOG_HISTO_DISPOSITIONS,
        events_ledger="backlog",
    ),
    Ledger(
        "AUDITS-HISTO",
        "audits/_archive/audits_histo.jsonl",
        "histo/histo-record-v1",
        dispositions=AUDITS_HISTO_DISPOSITIONS,
        events_ledger="audits",
    ),
    Ledger(
        "RELEASES-HISTO",
        "releases/_archive/releases_histo.jsonl",
        "histo/histo-record-v1",
        dispositions=RELEASES_HISTO_DISPOSITIONS,
        events_ledger="releases-histo",
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
    #: Injected at the CLI composition root (``cli/commands/doctor.py``), exactly as
    #: ``bug_store_factory`` is injected into the specs doctor — this feature never
    #: imports ``features.bugs``. ``None`` = no repair is wired and the rule reports only.
    normalize_bug_records: Callable[[], int] | None = field(default=None, compare=False)
    #: The governance events, read ONCE at the CLI composition root and passed in as
    #: plain data (0.4.7 FR6) — exactly as ``live_shas`` travels into the specs doctor,
    #: so ``features/specs`` never imports ``features/telemetry``. ``None`` = no store
    #: (a consumer without telemetry, CI, a fresh machine) and every hand-edit rule is
    #: silent.
    governance: GovernanceBaseline | None = None

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


def build_ledgers_context(
    specs_dir: Path,
    *,
    normalize_bug_records: Callable[[], int] | None = None,
    governance: GovernanceBaseline | None = None,
) -> LedgersContext:
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
    return LedgersContext(
        specs_dir=specs_dir,
        records=records,
        normalize_bug_records=normalize_bug_records,
        governance=governance,
    )


def _validate(ledger: Ledger, ctx: LedgersContext) -> list[LedgerIssue]:
    issues: list[LedgerIssue] = []
    for located in ctx.records.get(ledger.glob, ()):
        if located.parse_error is not None:
            issues.append(LedgerIssue(ledger.code, located.path, located.line, located.parse_error))
            continue
        # A record the ledger's own model can re-serialize is repairable, so EVERY issue
        # it raises carries the executable fix — including the schema's own
        # "additionalProperties" message about a retired key, which re-serialization is
        # exactly what removes. One decision per record, never one per message.
        drift = (
            ledger.canonical_issue(located.record)
            if ledger.canonical_issue is not None and isinstance(located.record, dict)
            else None
        )
        fix = _FIX_COMMAND if drift is not None else ""
        schema_messages = list(schema_errors(located.record, ledger.schema))
        for message in schema_messages:
            issues.append(LedgerIssue(ledger.code, located.path, located.line, message, fix=fix))
        if not schema_messages and drift is not None:
            issues.append(
                LedgerIssue(ledger.code, located.path, located.line, drift, fix=_FIX_COMMAND)
            )
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


def _hand_edits(ledger: Ledger, ctx: LedgersContext) -> list[LedgerIssue]:
    """Every record of *ledger* no governance verb wrote (0.4.7 FR6).

    The judgment itself lives in ``core.models.telemetry.GovernanceBaseline.hand_edit``
    — the ONE definition of "a hand edit", shared with the release-tree rule. This
    function only supplies the join key (``events_ledger`` + the record's own id) and
    the record's own timestamp, which is what makes the rule a table row rather than a
    fourth code path.

    WARNING, never an error, and it disqualifies no compliance unit: the record is
    VALID (the schema rules score that) — what is unexplained is its provenance, and
    whether to re-run the verb or accept the edit is the operator's judgment, not a
    failure. Measured, never blocked (SPEC 0.4.7 FR6).
    """
    if ctx.governance is None or ledger.events_ledger is None:
        return []
    issues: list[LedgerIssue] = []
    for located in ctx.records.get(ledger.glob, ()):
        record = located.record
        if not isinstance(record, dict):
            continue
        record_id = record.get("id")
        if not isinstance(record_id, str):
            continue
        ts = record.get("ts")
        message = ctx.governance.hand_edit(
            ledger=ledger.events_ledger,
            record_id=record_id,
            record=record,
            record_ts=ts if isinstance(ts, str) else None,
        )
        if message is not None:
            issues.append(
                LedgerIssue(
                    ledger.hand_edit_code,
                    located.path,
                    located.line,
                    message,
                    verdict=Severity.WARNING.value,
                )
            )
    return issues


#: This feature's binding of the ONE doctor rule record: the `ledgers` section's
#: schema rules run over :class:`LedgersContext` and emit :class:`LedgerIssue`.
type LedgerRule = Rule[LedgersContext, LedgerIssue]

SECTION = "ledgers"

#: The ONE executable remediation for a model-invariant issue that ships a migration.
_FIX_COMMAND = f"{DADAIA_BIN} doctor --fix"


def _fix_canonical_form(ctx: LedgersContext, issue: LedgerIssue) -> None:
    """Re-serialize every non-canonical committed record of this ledger. An issue the
    fixer cannot repair (``issue.fix`` empty — a mistyped field, a bad enum value) is
    hand-edited, never auto-repaired: this reader cannot know what a wrong value was
    MEANT to say, and guessing would corrupt a record."""
    if issue.fix != _FIX_COMMAND or ctx.normalize_bug_records is None:
        return
    ctx.normalize_bug_records()


#: One rule per ledger — the codes a reader greps for. Only the ledger whose model
#: invariant ships a migration carries a fixer; the rest are hand-edited.
RULES: tuple[LedgerRule, ...] = tuple(
    Rule(
        (ledger.code,),
        SECTION,
        (lambda bound: lambda ctx: _validate(bound, ctx))(ledger),
        fix=_fix_canonical_form if ledger.canonical_issue is not None else None,
        fix_help=(f"sed -i '<line>s|.*|<the corrected record>|' specs/{ledger.glob}"),
    )
    for ledger in LEDGERS
) + tuple(
    Rule(
        (ledger.hand_edit_code,),
        SECTION,
        (lambda bound: lambda ctx: _hand_edits(bound, ctx))(ledger),
        # No fix line: re-running the verb and accepting the edit are both correct
        # answers, and printing one of them would be a guess. WARNING-only, so the run
        # never exits 1 on it and no `fix:` is owed.
    )
    for ledger in LEDGERS
    if ledger.events_ledger is not None
)


def ledger_issues(specs_dir: Path) -> list[LedgerIssue]:
    """Every invalid committed record of every ledger — the one-shot path (the doctor
    runs the rules over a pre-built context instead, so it can score the denominator)."""
    ctx = build_ledgers_context(specs_dir)
    issues: list[LedgerIssue] = []
    for rule in RULES:
        issues.extend(rule.run(ctx))
    return issues
