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
import sys
from graphlib import CycleError, TopologicalSorter
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.append(str(Path(__file__).resolve().parents[2] / "dd-bug-resolution" / "scripts"))

import _ledger  # noqa: E402
from _ledger import SPECS, load_schema, validate  # noqa: E402
from _release_schema import (  # noqa: E402
    CODE,
    DELIVERED,
    HISTO,
    current_plan_jobs,
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
    """The PLAN's `## DAG` table (job | waits on | why) read once: Job 1 exists, at most 8
    jobs (Reconciliation uncounted), no cycle."""
    lines = plan.splitlines()
    dag_at = next((n for n, line in enumerate(lines) if re.match(r"^## DAG", line)), None)
    end = len(lines)
    current_table = False
    if dag_at is not None:
        saw_table = False
        for index, line in enumerate(lines[dag_at + 1 :], start=dag_at + 1):
            if line.lstrip().startswith("|"):
                if not saw_table:
                    lowered = line.lower()
                    current_table = "wave" in lowered and "w:" in lowered
                saw_table = True
            elif saw_table and line.strip():
                end = index
                break
    current, current_errors = current_plan_jobs("\n".join(lines[:end]) if current_table else plan)
    if current is not None:
        by_wave: dict[int, list[str]] = {}
        for wave, paths in current.values():
            by_wave.setdefault(wave, []).extend(paths)
        return current_errors + [
            f"PLAN.md DAG wave {wave}: two jobs write {path} — `W:` sets overlap"
            for wave, paths in by_wave.items()
            for path in sorted({path for path in paths if paths.count(path) > 1})
        ]
    section = re.split(r"^## DAG.*$", plan, maxsplit=1, flags=re.MULTILINE)[1:]
    rows = re.findall(r"^\|\s*Job (\d+)\s*\|([^|]*)\|", re.split(r"^#", section[0], flags=re.MULTILINE)[0],
                      re.MULTILINE) if section else []  # fmt: skip
    graph = {int(job): {int(n) for n in re.findall(r"\d+", waits)} for job, waits in rows}
    errors = current_errors + (["the DAG has no Job 1"] if section and 1 not in graph else [])
    errors += [f"the DAG holds {len(graph)} jobs — at most 8 jobs"] if len(graph) > 8 else []
    try:
        tuple(TopologicalSorter(graph).static_order())
    except CycleError as exc:
        errors.append(f"the DAG is cyclic: {' -> '.join(f'Job {n}' for n in exc.args[1])}")
    return errors
