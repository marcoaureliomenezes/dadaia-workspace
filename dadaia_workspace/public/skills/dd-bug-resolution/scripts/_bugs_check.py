#!/usr/bin/env python3
"""The BUGS.jsonl validator — the read half of the one bugs writer (`bugs.py`).

Every write in `bugs.py` runs :func:`findings_for` over the bytes it is about to
commit, so a writer/validator disagreement is unrepresentable. The schema is
``schemas/bug-record-v1.schema.json`` beside this file.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import _findings
import _git
import _jsonl
import _ledger
from _grammar import HISTORICAL_TASK_RE, TASK_ID_RE
from _platform import act, git_line, read_text
from _specs import script

CODE = "LEDGER-BUGS-SCHEMA"
LEDGER = "bugs/BUGS.jsonl"
HISTO = "bugs/_archive/bugs_histo.jsonl"
#: The status words are the schema's enum; the one non-terminal status is listed first.
OPEN, *TERMINAL = _ledger.load_schema("bug-record-v1")["properties"]["status"]["enum"]
#: The only place the terminal verbs meet their words.
STATUS_BY_VERB = {"resolve": "resolved", "supersede": "superseded", "reject": "rejected"}
_VERBS, _LAW = (
    "`bugs.py append` or `bugs.py update`",
    "specs/bugs/AGENTS.md: never hand-edit BUGS.jsonl",
)
_LEGACY_MARKERS = frozenset({"audited", "resolved_release"})


def _schema_record(record: Any, schema: dict[str, Any]) -> Any:
    """Project historical records onto the lean shape without admitting retired fields
    on records written by the current CLI.

    Every pre-lean record carries both legacy governance markers. Current writers expose
    neither marker, so their candidate bytes still receive strict additional-property
    validation.
    """
    if isinstance(record, dict) and record.keys() >= _LEGACY_MARKERS:
        allowed = schema["properties"]
        return {key: value for key, value in record.items() if key in allowed}
    return record


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
    """The ids under *root*`/releases/` (`_archive/` included) in every `TASKS.md` and
    `tasks/*.md`: the id at the head of each checklist item or table cell, in either grammar,
    plus every table cell that is a current-grammar id."""
    files = [*root.glob("releases/**/TASKS.md"), *root.glob("releases/**/tasks/*.md")]
    lines = [ln for file in files for ln in read_text(file).splitlines()]
    found = {m[1] for ln in lines if (m := HISTORICAL_TASK_RE.match(ln))}
    return found | {
        c for ln in lines for p in ln.split("|") if TASK_ID_RE.fullmatch(c := p.strip())
    }


def findings_for(
    text: str, rel: str = LEDGER, archived: str = "", root: Path = _ledger.SPECS
) -> list[dict[str, Any]]:
    """Every finding the ledger *text* carries — the ONE validation path, run both by
    ``check`` over the committed file and by every write over its own candidate bytes.
    Lineage: a `caused_by` names a record of *text* or of the archive text *archived*, or a task
    a `TASKS.md` under *root*`/releases/` carries, and never loops. An id holds at most one plain
    record across *text* and *archived*; a pre-v6 event line is not a record."""
    schema = load_schema()
    lines: dict[int, list[str]] = {}
    fixes: dict[int, str] = {}  # a line a governance verb clears
    seen: dict[str, int] = {}
    links: dict[str, object] = {}
    legacy_ids: set[str] = set()
    plain: dict[str, int] = {}
    twice: list[dict[str, Any]] = []
    for number, record in _archive_lines(archived, events=False):
        if (first := plain.setdefault(str(record["id"]), number)) != number:
            twice.append(_findings.finding(
                CODE, HISTO, number,
                f"duplicate record id {record['id']!r} (first archived at line {first})",
                _ledger.unwritten(root / HISTO, number, "`bugs.py archive`", _LAW),
            ))  # fmt: skip

    def add(line: int, message: str) -> None:
        lines.setdefault(line, []).append(message)

    for number, record, why in _jsonl.walk(text):
        if why:
            add(number, f"line is not valid JSON: {why}")
            continue
        messages = list(_ledger.validate(_schema_record(record, schema), schema, schema, "record"))
        for message in messages or invariant_errors(record):
            add(number, message)
        if messages:
            continue
        first = seen.setdefault(record["id"], number)
        if first != number:
            add(number, f"duplicate record id {record['id']!r} (first appended at line {first})")
        if record["id"] in plain:
            add(number, f"record id {record['id']!r} is also a record of the archive "
                f"(line {plain[record['id']]} of {HISTO})")  # fmt: skip
        links.setdefault(record["id"], record["caused_by"])
        if record.keys() >= _LEGACY_MARKERS:
            legacy_ids.add(record["id"])
    known = {
        None,
        "none",
        *links,
        *(str(r["id"]) for r in archived_records(archived)),
        *tasks(root),
    }
    for bug_id, target in links.items():
        if bug_id in legacy_ids:
            continue
        chain, at = [bug_id], target
        while at in links and at not in chain:
            chain.append(str(at))
            at = links[str(at)]
        if target not in known or at == bug_id:
            why = f"forms a cycle: {' -> '.join(chain)}" if at == bug_id else "names no record"
            add(seen[bug_id], f"{bug_id!r} caused_by {why}")
            bugs = script(Path(__file__).with_name("bugs.py"))
            fixes[seen[bug_id]] = (  # a cycle's wrong link is a judgement; a dangling one is not
                act("agent", f"decide which of {', '.join(chain)} names the wrong cause and "
                    f"set its caused_by to the real cause's id, or none, through `{bugs.inline('update', specs=root)}` ({_LAW})") if at == bug_id
                else bugs("update", bug_id, "--set", "caused_by=none", specs=root)
            )  # fmt: skip
    return [
        _findings.finding(CODE, rel, n, "; ".join(m),
                        fixes.get(n) or _ledger.unwritten(root / rel, n, _VERBS, _LAW))
        for n, m in sorted(lines.items())
    ] + twice  # fmt: skip


def histo_findings(text: str, root: Path = _ledger.SPECS) -> list[dict[str, Any]]:
    """The archive's bug records plus the older event lines, which stay readable."""
    schema = load_schema()

    def problems(record: Any) -> list[str]:
        if isinstance(record, dict) and "event" in record:
            return []
        return list(_ledger.validate(_schema_record(record, schema), schema, schema, "record"))

    return _findings.histo_findings(
        text, HISTO, CODE, problems,
        lambda n: _ledger.unwritten(root / HISTO, n, "`bugs.py archive`", _LAW),
    )  # fmt: skip


def _archive_lines(text: str, events: bool = True) -> Iterator[tuple[int, dict[str, Any]]]:
    """The `(line, record)` pairs of the archive *text*: a plain line is a record, an event line
    contributes its `data` when *events*; a line with no `id` or an unreadable one is
    `histo_findings`' to name."""
    for number, record, why in _jsonl.walk(text):
        if why or not isinstance(record, dict):
            continue
        if events and "event" in record and isinstance(record.get("data"), dict):
            record = record["data"]
        if "id" in record:
            yield number, record


def archived_records(text: str) -> list[dict[str, Any]]:
    """The records of the archive *text*, event lines' `data` included."""
    return [record for _, record in _archive_lines(text)]


def plain_ids(text: str) -> frozenset[str]:
    """The ids of the archive *text*'s plain records: the ids no new record may take."""
    return frozenset(str(record["id"]) for _, record in _archive_lines(text, events=False))


def _uncited(specs: Path, text: str) -> list[dict[str, Any]]:
    """The live records that carry a `fix_sha` and whose id line no commit of the main repo or a repo beside it reaches from its HEAD, one finding each, every one fixed by the one archive of all the misses; where a repo is a shallow clone a miss cannot be judged, so the misses are one finding for the cut. The sha is a hint, never judged."""
    held = {str(r["id"]): (n, r["fix_sha"]) for n, r, why in _jsonl.walk(text) if not why and isinstance(r, dict) and r.get("fix_sha")}  # fmt: skip
    found = _git.fix_commit(specs.parent, held)
    repos = _git.context_repos(specs.parent)
    missed = [i for i in held if i not in found]
    if missed and (cut := next((p for p in repos if _git.shallow(p)), None)):
        return [_findings.finding(CODE, LEDGER, held[missed[0]][0], "the clone is shallow: its misses cannot be judged", git_line(cut, "fetch", "--unshallow"))]  # fmt: skip
    return [
        _findings.finding(
            CODE, LEDGER, held[i][0], f"{i!r} fix_sha {held[i][1]} has no commit in HEAD of {', '.join(p.name for p in repos)} holding the line `fix(bugs): {i} — …`",
            script(Path(__file__).with_name("bugs.py"))("archive", *missed, specs=specs),
        )
        for i in missed
    ]  # fmt: skip


@_findings.decodable(CODE)
def check(specs: Path) -> list[dict[str, Any]]:
    """Validate the committed ledger and its archive; a young specs tree with neither is
    not a finding. A merge can join two valid writes into a cycle: check re-judges."""
    ledger, histo = specs / LEDGER, specs / HISTO
    text = read_text(ledger) if ledger.is_file() else ""
    archived = read_text(histo) if histo.is_file() else ""
    root = specs.resolve()
    unreached = _uncited(specs, text)
    return sorted(
        findings_for(text, archived=archived, root=root) + unreached,
        key=lambda f: (f["path"], f["line"]),
    ) + histo_findings(archived, root)
