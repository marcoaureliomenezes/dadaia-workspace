"""The `specs/ADRs/decisions.jsonl` reader — the ONE module that opens the ADR ledger.

It owns the ledger's rules (ADR-SUPERSEDED-CITATION over the tree that cites decisions,
LEDGER-ADR-SCHEMA over the records and their numbering), the resolver of an accepted
record's ``measured_by`` and the renderer of the ``adr-list`` block.

ADR-SUPERSEDED-CITATION: a memory atom, rule file or skill that cites
an ADR id whose record is ``superseded`` — ERROR. A rule pointing at a dead decision is
the drift the community asks CI to fail on; the successor lives in ``decisions.jsonl``.
"""

from __future__ import annotations

import re
from contextlib import suppress
from functools import cache
from pathlib import Path
from types import ModuleType

from dadaia_workspace.core.doctor_rules import Rule, SectionFinding
from dadaia_workspace.features.specs.doctor_types import Severity, specs_finding
from dadaia_workspace.infrastructure.git_subprocess import GitSubprocessClient
from dadaia_workspace.infrastructure.ledger_scripts import load_owner

#: The ADR ledger, relative to a specs tree.
LEDGER = "ADRs/decisions.jsonl"

#: The citation shapes of an ADR id in memory atoms, skills and rules: "ADR", a colon, space or
#: hyphen, four digits.
_ADR_CITATION_RE = re.compile(r"\bADR[:\s-]+(\d{4})\b")


class Unreadable(ValueError):
    """The ledger is not UTF-8; the text is the fix line."""


def _ledger_text(ledger: Path) -> str:
    """The ledger's text; raises :class:`Unreadable` when it is not UTF-8."""
    owner = load_owner("dd-bug-resolution", "_jsonl")
    try:
        return str(owner.read_text(ledger))
    except owner.Undecodable as bad:
        raise Unreadable(bad.fix) from bad


def _records(text: str, status: str) -> list[dict[str, object]]:
    """An unreadable line names nothing here; it is `adr_record_issues`' finding."""
    owner = load_owner("dd-bug-resolution", "_ledger")
    records: list[dict[str, object]] = []
    for raw in text.split("\n"):
        with suppress(owner.LineError):
            records += [r for r in owner.parse(raw) if r.get("status") == status]
    return records


def superseded_adr_citations(specs_dir: Path, public_dir: Path | None) -> list[SectionFinding]:
    """Every ``*.md`` under ``specs/memory`` and the library's skills, data and scaffold
    that cites a superseded decision id — one issue per (file, id)."""
    ledger = specs_dir / "ADRs" / "decisions.jsonl"
    if not ledger.is_file():
        return []
    try:
        text = _ledger_text(ledger)
    except Unreadable:  # `adr_record_issues` names the file
        return []
    superseded = {str(r.get("id")) for r in _records(text, "superseded")}
    if not superseded:
        return []
    roots = [specs_dir / "memory"]
    if public_dir is not None:
        roots.extend([public_dir / "skills", public_dir / "data", public_dir / "scaffold"])
    issues: list[SectionFinding] = []
    for root in roots:
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*.md")):
            cited = set(_ADR_CITATION_RE.findall(path.read_text(encoding="utf-8")))
            for adr_id in sorted(cited & superseded):
                issues.append(
                    specs_finding(
                        code="ADR-SUPERSEDED-CITATION",
                        severity=Severity.ERROR,
                        description=(
                            f"{path.name} cites ADR {adr_id}, a superseded decision — "
                            "point at its successor in decisions.jsonl."
                        ),
                        path=str(path),
                    )
                )
    return issues


_TOKEN_RE = re.compile(r"[\w./:-]+")
_CODE_RE = re.compile(r"""["']([A-Z][A-Z0-9]*(?:-[A-Z0-9]+)+)(?=[\s"':])""")


@cache
def _doctor_codes() -> frozenset[str]:
    """The rule codes the installed package's own source names."""
    package = Path(__file__).parents[2]
    return frozenset(
        code
        for path in package.rglob("*.py")
        for code in _CODE_RE.findall(path.read_text(encoding="utf-8", errors="replace"))
    )


def _accepted(specs_dir: Path) -> list[dict[str, object]]:
    ledger = specs_dir / LEDGER
    return _records(_ledger_text(ledger), "accepted") if ledger.is_file() else []


def unresolved_measured_by(specs_dir: Path) -> list[tuple[str, str]]:
    """``(id, measured_by)`` of every accepted record whose text holds no token that is a
    path of the specs repo's ``git ls-files`` set (tracked, or untracked and not ignored), a
    ``path::name`` node id of such a file naming its last segment (a test or a workflow job),
    or a rule code of the installed doctor."""
    root = specs_dir.parent
    tracked = GitSubprocessClient().tracked(root)

    def resolves(text: str) -> bool:
        for token in (t.rstrip(".:,") for t in _TOKEN_RE.findall(text)):
            path, *nodes = token.split("::")
            if path in tracked and (
                not nodes
                or nodes[-1] in (root / path).read_text(encoding="utf-8", errors="replace")
            ):
                return True
            if not nodes and token in _doctor_codes():
                return True
        return False

    return [
        (str(r["id"]), str(r.get("measured_by")))
        for r in _accepted(specs_dir)
        if not resolves(str(r.get("measured_by")))
    ]


def adr_list_block(specs_dir: Path) -> str:
    """The ``adr-list`` fragment: ``- <id> — <title>`` per accepted record, in id order;
    empty without a ledger.

    Raises ValueError, whose text is the one fix line, while an accepted record's
    ``measured_by`` resolves to nothing."""
    if unresolved := unresolved_measured_by(specs_dir):
        raise ValueError(
            "Operator action: set the measured_by of ADR "
            + ", ".join(i for i, _ in unresolved)
            + " to a tracked path, a path::name test or workflow-job id, or a rule code"
            " (an in-place `chore(adrs): repair` commit)."
        )
    return "".join(
        f"- {r['id']} — {r['title']}\n"
        for r in sorted(_accepted(specs_dir), key=lambda r: str(r["id"]))
    )


def adr_record_issues(specs_dir: Path) -> list[SectionFinding]:
    """Every record failing its schema, and the first id breaking 0001..N (file order).

    Located `path:line` relative to the specs tree: a finding pasted into a report never
    carries a local absolute path.
    """
    ledger = specs_dir / LEDGER
    if not ledger.is_file():
        return []
    issues: list[SectionFinding] = []
    records: list[tuple[int, dict[str, object]]] = []
    owner = load_owner("dd-bug-resolution", "_ledger")
    schema = owner.load_schema("decision-record-v1")
    try:
        lines = _ledger_text(ledger).split("\n")
    except Unreadable as bad:
        return [
            specs_finding(
                code="LEDGER-ADR-SCHEMA",
                severity=Severity.ERROR,
                description=f"{LEDGER} is not valid UTF-8",
                path=LEDGER,
                fix=str(bad),
            )
        ]
    for number, raw in enumerate(lines, start=1):
        try:
            parsed = owner.parse(raw)
        except owner.LineError as exc:
            issues.append(_record_issue(owner, ledger, number, f"line {exc}"))
            continue
        for record in parsed:
            records.append((number, record))
            issues.extend(
                _record_issue(owner, ledger, number, m)
                for m in owner.validate(record, schema, schema, "record")
            )
    for position, (number, record) in enumerate(records, start=1):
        if (adr_id := record.get("id")) != (want := f"{position:04d}"):
            issues.append(
                _record_issue(
                    owner, ledger, number, f"id {adr_id!r} breaks 0001..N: expected {want}"
                )
            )
            break
    accepted = {str(r.get("id")) for _, r in records if r.get("status") == "accepted"}
    for number, r in records:  # only a ruled record changes a ruled one
        named = f"{r.get('supersedes') or ''},{r.get('amends') or ''}".split(",")
        ruled = r.get("status") in ("accepted", "superseded") and "ruling" in r
        if r.get("status") != "rejected" and not ruled and (hit := sorted(accepted & set(named))):
            issues.append(
                _record_issue(owner, ledger, number, f"changes accepted {hit} without a ruling")
            )
    return issues


#: Who writes an ADR record, and the law forbidding a hand edit of one.
_VERBS, _LAW = "a `docs(adr)` propose or accept commit", "the ADR law, specs/ADRs/AGENTS.md"


def _record_issue(owner: ModuleType, ledger: Path, line: int, message: str) -> SectionFinding:
    return specs_finding(
        code="LEDGER-ADR-SCHEMA",
        severity=Severity.ERROR,
        description=message,
        path=f"{LEDGER}:{line}",
        fix=owner.unwritten(ledger, line, _VERBS, _LAW),
    )


LEDGER_RULES: tuple[Rule[Path], ...] = (
    Rule(
        ("LEDGER-ADR-SCHEMA",),
        "ledgers",
        adr_record_issues,
        fix_help=load_owner("dd-bug-resolution", "_ledger").unwritten(
            Path("<specs>") / LEDGER, "the record named", _VERBS, _LAW
        ),
    ),
)
