#!/usr/bin/env python3
"""The BUGS.jsonl validator — the read half of the one bugs writer (`bugs.py`).

Every write in `bugs.py` runs :func:`findings_for` over the bytes it is about to
commit, so a writer/validator disagreement is unrepresentable. The schema is
``schemas/bug-record-v1.schema.json`` beside this file, a copy `public stage` makes.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _ledger  # noqa: E402
from _specs import quote, script, with_specs  # noqa: E402

CODE = "LEDGER-BUGS-SCHEMA"
LEDGER = "bugs/BUGS.jsonl"
HISTO = "bugs/_archive/bugs_histo.jsonl"
#: The job files' task id; `_worktree_freeze._ID` keeps its twin (ADR 0150), pinned equal by a parity test.
TASK_ID = r"J[\dA-Z]+\.S\d+\.T\d+"
TERMINAL = ("resolved", "superseded", "deferred", "rejected")
_VERBS, _LAW = (
    "`bugs.py append` or `bugs.py update`",
    "specs/bugs/AGENTS.md: never hand-edit BUGS.jsonl",
)


def load_schema() -> dict[str, Any]:
    return _ledger.load_schema("bug-record-v1")


def invariant_errors(record: dict[str, Any]) -> Iterator[str]:
    """The record's own cross-field law: ``closed_at`` is non-null if and only if
    ``status`` is terminal, and never earlier than ``ts``."""
    status, closed_at, ts = record["status"], record["closed_at"], record["ts"]
    terminal = status in TERMINAL
    if terminal and closed_at is None:
        yield f"record {record['id']!r} is terminal ({status!r}) but carries no 'closed_at'"
    if not terminal and closed_at is not None:
        yield (
            f"record {record['id']!r} is open but carries closed_at={closed_at!r} — "
            "closed_at is stamped only by a terminal transition"
        )
    if isinstance(closed_at, str) and closed_at < ts:
        yield f"record {record['id']!r} closed_at={closed_at!r} precedes its filing date ts={ts!r}"


def tasks(root: Path) -> set[str]:
    """Every task id under *root*`/releases/`, `_archive/` included: a closed rc's `TASKS.md`
    carries `T-…`, a job rc's `tasks/<job>.md` carries `J<n>.S<m>.T<k>` (`JR.…`);
    bounded: an id glued to a word or a hyphen (a doctor code, a placeholder) is no task."""
    bounded = re.compile(rf"(?<![\w-])(?:T-\d+(?:-\d+)*|{TASK_ID})(?![\w-])")
    files = [*root.glob("releases/**/TASKS.md"), *root.glob("releases/**/tasks/*.md")]
    return {t for f in files for t in bounded.findall(f.read_text(encoding="utf-8"))}


def findings_for(
    text: str, rel: str = LEDGER, archived: frozenset[str] = frozenset(), root: Path = _ledger.SPECS
) -> list[dict[str, Any]]:
    """Every finding the ledger *text* carries — the ONE validation path, run both by
    ``check`` over the committed file and by every write over its own candidate bytes.
    Lineage (AC3.8): a `caused_by` names a record of *text* or *archived*, or a task a
    `TASKS.md` under *root*`/releases/` carries, and never loops."""
    schema = load_schema()
    lines: dict[int, list[str]] = {}
    fixes: dict[int, str] = {}  # a line a governance verb clears
    seen: dict[str, int] = {}
    links: dict[str, object] = {}

    def add(line: int, message: str) -> None:
        lines.setdefault(line, []).append(message)

    for number, raw in enumerate(text.split("\n"), start=1):
        if not raw.strip():
            continue
        try:
            record = json.loads(raw)
        except json.JSONDecodeError as exc:
            add(number, f"line is not valid JSON: {exc.msg}")
            continue
        messages = list(_ledger.validate(record, schema, schema, "record"))
        for message in messages or invariant_errors(record):
            add(number, message)
        if messages:
            continue
        first = seen.setdefault(record["id"], number)
        if first != number:
            add(number, f"duplicate record id {record['id']!r} (first appended at line {first})")
        links.setdefault(record["id"], record["caused_by"])
    known = {None, "none", *links, *archived, *tasks(root)}
    for bug_id, target in links.items():
        chain, at = [bug_id], target
        while at in links and at not in chain:
            chain.append(str(at))
            at = links[str(at)]
        if target not in known or at == bug_id:
            why = f"forms a cycle: {' -> '.join(chain)}" if at == bug_id else "names no record"
            add(seen[bug_id], f"{bug_id!r} caused_by {why}")
            bugs = script(Path(__file__).with_name("bugs.py"))
            fixes[seen[bug_id]] = (  # a cycle's wrong link is a judgement; a dangling one is not
                f"Operator action: decide which of {', '.join(chain)} names the wrong cause and "
                f"set its caused_by to the real cause's id, or none, through `{bugs} update "
                f"--specs {quote(str(root))}` ({_LAW})" if at == bug_id
                else with_specs(f"{bugs} update {quote(bug_id)} --set caused_by=none", root)
            )  # fmt: skip
    return [
        _ledger.finding(CODE, rel, n, "; ".join(m),
                        fixes.get(n) or _ledger.unwritten(root / rel, n, _VERBS, _LAW))
        for n, m in sorted(lines.items())
    ]  # fmt: skip


def accepted_adrs(root: Path) -> set[str]:
    """The ids of every accepted ADR in *root*'s ``ADRs/decisions.jsonl``."""
    decisions = root / "ADRs" / "decisions.jsonl"
    rows = _ledger.records(decisions) if decisions.is_file() else []
    return {str(r.get("id")) for r in rows if r.get("status") == "accepted"}


def histo_findings(text: str, root: Path = _ledger.SPECS) -> list[dict[str, Any]]:
    """The archive's lines: each a bug-record-v1 record moved by the accepted ADR its
    ``archived_by`` names, or a pre-v6 ``event`` line that predates the record shape and is
    history, never rewritten."""
    schema, accepted = load_schema(), accepted_adrs(root)
    out: list[dict[str, Any]] = []
    for number, raw in enumerate(text.split("\n"), start=1):
        try:
            record = json.loads(raw) if raw.strip() else None
        except json.JSONDecodeError as exc:
            record, messages = None, [f"line is not valid JSON: {exc.msg}"]
        else:
            legacy = isinstance(record, dict) and "event" in record
            messages = (
                []
                if record is None or legacy
                else list(_ledger.validate(record, schema, schema, "record"))
            )
            if record is not None and not legacy and record.get("archived_by") not in accepted:
                messages.append(f"archived_by {record.get('archived_by')!r} names no accepted ADR")
        if messages:
            fix = _ledger.unwritten(root / HISTO, number, "`bugs.py archive`", _LAW)
            out.append(_ledger.finding(CODE, HISTO, number, "; ".join(messages), fix))
    return out


def archived_ids(text: str) -> frozenset[str]:
    """The record ids of the archive *text*; an unreadable line is `histo_findings`' to name."""
    out = set()
    for raw in text.split("\n"):
        try:
            record = json.loads(raw) if raw.strip() else None
        except json.JSONDecodeError:
            continue
        if isinstance(record, dict) and "id" in record:
            out.add(str(record["id"]))
    return frozenset(out)


def check(specs: Path) -> list[dict[str, Any]]:
    """Validate the committed ledger and its archive; a young specs tree with neither is
    not a finding. A merge can join two valid writes into a cycle: check re-judges."""
    ledger, histo = specs / LEDGER, specs / HISTO
    text = ledger.read_text(encoding="utf-8") if ledger.is_file() else ""
    archived = histo.read_text(encoding="utf-8") if histo.is_file() else ""
    root = specs.resolve()
    return findings_for(text, archived=archived_ids(archived), root=root) + histo_findings(
        archived, root
    )
