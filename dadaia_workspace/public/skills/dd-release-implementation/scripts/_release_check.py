#!/usr/bin/env python3
"""The `_RELEASE.json` + releases_histo.jsonl validator — the read half of `release.py`.

Every write in `release.py` runs :func:`state_findings` over the bytes it is about to
commit, so a writer/validator disagreement about what a valid release state is cannot
be represented.

The tree walk (`_release_tree.check`) is the one release validator the doctor delegates
to; this file validates the documents a write touches.
"""

from __future__ import annotations

import json
import re
from graphlib import CycleError, TopologicalSorter
from pathlib import Path
from typing import Any

import _ledger
from _ledger import SPECS, load_schema, validate
from _release_schema import (
    CODE,
    DELIVERED,
    HISTO,
    current_job_writes,
    current_plan_jobs,
    job_errors,
    plan_errors,
)

_LAW = "specs/releases/AGENTS.md: release.py is this ledger's ONE writer"
#: A merged job's measurement, one `kind: merge` entry per job (RELEASE-EVENTS.md §log).
_JOB_MERGE = re.compile(
    r"job: [a-z0-9-]+; start: \S+; end: \S+; wall: \d+; ritual_wait: \d+; dispatches: \d+; job_gate_runs: \d+"
)
_CURRENT_LOG_KINDS = frozenset({"milestone", "note", "summary", "memory"})
_SUMMARY = re.compile(r"delivered: .+; carried: .+; backlog exits: .+")
_BIRTH = re.compile(r"^(?:Candidate|Release \d+\.\d+\.\d+) born\b")


def finding(path: str, line: int, message: str, fix: str) -> dict[str, Any]:
    """One `check --json` record of this ledger."""
    record: dict[str, Any] = _ledger.finding(CODE, path, line, message, fix)
    return record


def _unwritten(
    path: str, line: int, message: str, root: Path, at: int | str | None = None
) -> dict[str, Any]:
    """Content of this ledger no `release.py` verb wrote: a histo line, or *at* a state key."""
    fix = _ledger.unwritten(root / path, line if at is None else at, "`release.py`", _LAW)
    return finding(path, line, message, fix)


def _log_errors(document: dict[str, Any]) -> list[str]:
    """Validate ordering and the lean current-candidate log while retaining history."""
    entries = [entry for entry in document.get("log", []) if isinstance(entry, dict)]
    stamps = [entry.get("ts") for entry in entries]
    born = max(
        (index for index, entry in enumerate(entries) if _BIRTH.match(str(entry.get("text", "")))),
        default=len(entries),
    )
    current = entries[born:]
    return (
        [
            f"log[{born + index}] kind {entry.get('kind')!r} is legacy; current candidates "
            f"write only {', '.join(sorted(_CURRENT_LOG_KINDS))}"
            for index, entry in enumerate(current)
            if entry.get("kind") not in _CURRENT_LOG_KINDS
        ]
        + [
            f"log[{born + index}] kind memory is closure-only"
            for index, entry in enumerate(current)
            if entry.get("kind") == "memory" and document.get("phase") != "CLOSURE"
        ]
        + [
            f"log[{born + index}] kind summary must contain delivered, carried and backlog exits"
            for index, entry in enumerate(current)
            if entry.get("kind") == "summary" and not _SUMMARY.fullmatch(str(entry.get("text", "")))
        ]
        + [
            f"log[{index}] kind merge text {entry.get('text')!r} is not '{_JOB_MERGE.pattern}'"
            for index, entry in enumerate(entries)
            if entry.get("kind") == "merge"
            and str(entry.get("text")).startswith("job:")
            and not _JOB_MERGE.fullmatch(str(entry.get("text")))
        ]
        + [
            f"log[{index + 1}].ts {later!r} precedes log[{index}].ts {earlier!r}"
            for index, (earlier, later) in enumerate(zip(stamps, stamps[1:], strict=False))
            if isinstance(earlier, str) and isinstance(later, str) and later < earlier
        ]
    )


def state_findings(text: str, rel: str, root: Path = SPECS) -> list[dict[str, Any]]:
    """Every finding one live release-state document's *text* carries, at *rel*."""
    try:
        document = json.loads(text)
    except json.JSONDecodeError as exc:
        message, at = (
            f"document is not valid JSON: {exc.msg}",
            f"its JSON syntax (line {exc.lineno})",
        )
        return [_unwritten(rel, exc.lineno, message, root, at)]
    schema = load_schema("release-state-v1")
    messages = list(validate(document, schema, schema, "state")) or _log_errors(document)
    return [_unwritten(rel, 1, "; ".join(messages), root, _ledger.NAMED)] if messages else []


def histo_findings(text: str, root: Path = SPECS) -> list[dict[str, Any]]:
    """The append-only ship ledger: the histo-record-v1 shape, `delivered`, one line per
    release, ever."""
    schema = load_schema("histo-record-v1")
    findings: list[dict[str, Any]] = []
    seen: dict[str, int] = {}
    for number, raw in enumerate(text.split("\n"), start=1):
        if not raw.strip():
            continue
        try:
            record = json.loads(raw)
        except json.JSONDecodeError as exc:
            findings.append(_unwritten(HISTO, number, f"line is not valid JSON: {exc.msg}", root))
            continue
        messages = list(validate(record, schema, schema, "record"))
        if not messages and record["disposition"] != DELIVERED:
            messages.append(
                f"disposition {record['disposition']!r} — a release ships {DELIVERED!r}"
            )
        if not messages and (first := seen.setdefault(str(record["id"]), number)) != number:
            messages.append(f"{record['id']!r} ships twice (first at line {first})")
        if messages:
            findings.append(_unwritten(HISTO, number, "; ".join(messages), root))
    return findings


def dag_errors(plan: str) -> list[str]:
    """A historical PLAN's `## DAG` table (job | waits on | why): Job 1 exists, at most 8
    jobs (Reconciliation uncounted), no cycle."""
    section = re.split(r"^## DAG.*$", plan, maxsplit=1, flags=re.MULTILINE)[1:]
    rows = re.findall(r"^\|\s*Job (\d+)\s*\|([^|]*)\|", re.split(r"^#", section[0], flags=re.MULTILINE)[0],
                      re.MULTILINE) if section else []  # fmt: skip
    graph = {int(job): {int(n) for n in re.findall(r"\d+", waits)} for job, waits in rows}
    errors = ["the DAG has no Job 1"] if section and 1 not in graph else []
    errors += [f"the DAG holds {len(graph)} jobs — at most 8 jobs"] if len(graph) > 8 else []
    try:
        tuple(TopologicalSorter(graph).static_order())
    except CycleError as exc:
        errors.append(f"the DAG is cyclic: {' -> '.join(f'Job {n}' for n in exc.args[1])}")
    return errors


def candidate_errors(candidate: Path) -> list[tuple[Path, str, str]]:
    """The ONE judge of a candidate's PLAN DAG and `tasks/job<n>.md` files, as
    ``(file, message, fix)``: the PLAN's own errors, each job file's, then the DAG's jobs
    and their `W:` against the job files' exact unions. `check` and `phase` both read it."""
    plan, found = candidate / "PLAN.md", []
    planned = None
    if plan.is_file():
        text = plan.read_text(encoding="utf-8")
        planned = current_plan_jobs(text)[0]
        redo = f"Operator action: correct the as-is review and DAG in {plan.resolve()}"
        found += [(plan, e, redo) for e in plan_errors(text) + (dag_errors(text) if planned is None else [])]  # fmt: skip
    authorities: dict[str, set[str]] = {}
    for job in sorted(candidate.glob("tasks/*.md")):
        rel, fix = f"tasks/{job.name}", f"Operator action: correct {job.resolve()} (dd-release-definition §5)"  # fmt: skip
        body = job.read_text(encoding="utf-8")
        found += [(job, e, fix) for e in job_errors(body, rel)]
        if (writes := current_job_writes(body, rel)[0]) is None:
            continue
        number = job.stem.removeprefix("job")
        if not number.isdigit() or number.startswith("0"):
            found.append((job, f"current task authority {job.name} has no positive-numbered job filename",
                          f"Operator action: rename {job.resolve()} to its canonical positive-numbered job filename"))  # fmt: skip
        else:
            authorities[f"Job {int(number)}"] = writes
    if planned:
        jobs = {name: row for name, row in planned.items() if name != "Reconciliation"}
        if set(jobs) != set(authorities):
            found.append((plan, "PLAN.md DAG jobs do not equal the current tasks/job<n>.md authorities",
                          f"Operator action: make every current job appear exactly once in {plan.resolve()}"))  # fmt: skip
        found += [(plan, f"PLAN.md DAG {name} `W:` is not its exact task-file union",
                   f"Operator action: set {name}'s exact `W:` in {plan.resolve()} from tasks/job{name.split()[-1]}.md")  # fmt: skip
                  for name, (_, owned) in jobs.items() if name in authorities and owned != authorities[name]]  # fmt: skip
    return found
