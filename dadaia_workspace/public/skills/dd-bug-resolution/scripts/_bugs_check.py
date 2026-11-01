#!/usr/bin/env python3
"""The BUGS.jsonl validator — the read half of the one bugs writer (`bugs.py`).

Every write in `bugs.py` runs :func:`findings_for` over the bytes it is about to
commit, so a writer/validator disagreement is unrepresentable. The schema is
``schemas/bug-record-v1.schema.json`` beside this file.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import _findings
import _git
import _jsonl
import _ledger
from _grammar import CANDIDATE_RE, TASK_ID_ANY_RE
from _platform import act, git_line, read_text
from _specs import context_repos, script

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


def tasks(root: Path) -> dict[str, list[str]]:
    """Each task id under *root*`/releases/` (`_archive/` included) that heads a checklist item
    or fills a table cell of a `TASKS.md` or `tasks/*.md`, with the `<M.m.p>-rc<N>/<id>` form of
    every candidate that carries it."""
    found: dict[str, set[str]] = {}
    for file in [*root.glob("releases/**/TASKS.md"), *root.glob("releases/**/tasks/*.md")]:
        parts = file.relative_to(root / "releases").parts
        rc = next((i for i, p in enumerate(parts) if CANDIDATE_RE.match(p)), 0)
        where = f"{parts[rc - 1]}-{parts[rc].replace('-', '')}/" if rc else ""
        for line in read_text(file).splitlines():
            item = re.match(r"- \[.\]\s*", line)
            cells = (
                line.split("|") if line.startswith("|") else [line[item.end() :]] if item else []
            )
            for cell in cells:
                if m := TASK_ID_ANY_RE.match(cell.strip().lstrip("*")):
                    found.setdefault(m[0], set()).update([f"{where}{m[0]}"] if where else [])
    return {task: sorted(forms) for task, forms in found.items()}


def ambiguous(root: Path, target: str) -> list[str]:
    """The candidate-qualified forms of the bare task id *target* when several candidates carry it, else none."""
    forms = tasks(root).get(target, [])
    return forms if len(forms) > 1 else []


def _archive_twice(archived: str, root: Path) -> tuple[dict[str, int], list[dict[str, Any]]]:
    """The first line of each plain archive id, and a finding for every later repeat."""
    plain: dict[str, int] = {}
    twice: list[dict[str, Any]] = []
    for number, record, legacy in archive_records(archived):
        if legacy:
            continue
        if (first := plain.setdefault(str(record["id"]), number)) != number:
            twice.append(_findings.finding(
                CODE, HISTO, number,
                f"duplicate record id {record['id']!r} (first archived at line {first})",
                _ledger.unwritten(root / HISTO, number, "`bugs.py archive`", _LAW),
            ))  # fmt: skip
    return plain, twice


def _record_lines(
    text: str, plain: dict[str, int], lines: dict[int, list[str]]
) -> tuple[dict[str, int], dict[str, object], set[str]]:
    """Walk the ledger *text* once: add each line's schema, invariant and duplicate messages to
    *lines*; return the first line of each id, each id's `caused_by`, and the legacy ids."""
    schema = load_schema()
    seen: dict[str, int] = {}
    links: dict[str, object] = {}
    legacy_ids: set[str] = set()

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
    return seen, links, legacy_ids


def _lineage(
    seen: dict[str, int],
    links: dict[str, object],
    legacy_ids: set[str],
    archived: str,
    root: Path,
    lines: dict[int, list[str]],
    fixes: dict[int, str],
) -> None:
    """Add to *lines* and *fixes* a finding for each `caused_by` that names no record or task
    or closes a loop."""
    known = {
        None,
        "none",
        *links,
        *(str(r["id"]) for _, r, _ in archive_records(archived)),
        *(t for task, forms in tasks(root).items() for t in (task, *forms)),
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
            lines.setdefault(seen[bug_id], []).append(f"{bug_id!r} caused_by {why}")
            bugs = script(Path(__file__).with_name("bugs.py"))
            fixes[seen[bug_id]] = (  # a cycle's wrong link is a judgement; a dangling one is not
                act("agent", f"decide which of {', '.join(chain)} names the wrong cause and "
                    f"set its caused_by to the real cause's id, or none, through `{bugs.inline('update', specs=root)}` ({_LAW})") if at == bug_id
                else bugs("update", bug_id, "--set", "caused_by=none", specs=root)
            )  # fmt: skip


def findings_for(
    text: str, rel: str = LEDGER, archived: str = "", root: Path = _ledger.SPECS
) -> list[dict[str, Any]]:
    """Every finding the ledger *text* carries — the ONE validation path, run both by
    ``check`` over the committed file and by every write over its own candidate bytes.
    Lineage: a `caused_by` names a record of *text* or of the archive text *archived*, or a release
    task `tasks` finds under *root*, and never loops. An id holds at most one plain
    record across *text* and *archived*; a pre-v6 event line is not a record."""
    lines: dict[int, list[str]] = {}
    fixes: dict[int, str] = {}  # a line a governance verb clears
    plain, twice = _archive_twice(archived, root)
    seen, links, legacy_ids = _record_lines(text, plain, lines)
    _lineage(seen, links, legacy_ids, archived, root, lines, fixes)
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


def archive_records(text: str) -> list[tuple[int, dict[str, Any], bool]]:
    """The `(line, record, legacy)` of each archive line of *text* that names an id: a line
    holding `event` and a `data` object is a legacy event line and yields its `data`; any other
    line is a record. A line with no `id` or an unreadable one is `histo_findings`' to name."""
    found = []
    for number, record, why in _jsonl.walk(text):
        if why or not isinstance(record, dict):
            continue
        legacy = "event" in record and isinstance(record.get("data"), dict)
        if "id" in (kept := record["data"] if legacy else record):
            found.append((number, kept, legacy))
    return found


def _uncited(specs: Path, text: str) -> list[dict[str, Any]]:
    """The live resolved records that carry a `fix_sha` and whose id line no commit of the main repo or a repo beside it reaches from its HEAD, one finding each, every one fixed by the one archive of all the misses; where a repo is a shallow clone a miss cannot be judged, so the misses are one finding for the cut. The sha is a hint, never judged."""
    held = {str(r["id"]): (n, r["fix_sha"]) for n, r, why in _jsonl.walk(text) if not why and isinstance(r, dict) and r.get("status") == "resolved" and r.get("fix_sha")}  # fmt: skip
    found = _git.fix_commit(context_repos(specs.parent), held)
    missed = [i for i in held if i not in found]
    repos = list(context_repos(specs.parent)) if missed else []
    if missed and (cut := next((p for p in repos if _git.shallow(p)), None)):
        return [_findings.finding(CODE, LEDGER, held[missed[0]][0], "the clone is shallow: its misses cannot be judged", git_line(cut, "fetch", "--unshallow"))]  # fmt: skip
    return [
        _findings.finding(
            CODE, LEDGER, held[i][0], f"{i!r} fix_sha {held[i][1]} has no commit in HEAD of {', '.join(p.name for p in repos)} holding the line `fix(bugs): {i} — …` or `refactor(bugs): {i} — …`",
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
