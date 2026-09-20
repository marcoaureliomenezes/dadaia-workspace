#!/usr/bin/env python3
"""The BACKLOG.json + backlog_histo.jsonl validator — the read half of `backlog.py`.

Every write in `backlog.py` runs these findings over the bytes it is about to commit,
so a writer/validator disagreement about what a valid backlog is unrepresentable.

Anchor RESOLUTION (does a bound subject name a live code/doc/cli anchor?) is NOT here:
it needs the whole source tree and stays the doctor's `BL-SCHEMA` reader. This file
validates only what the two ledger files themselves carry.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _backlog_schema import (  # noqa: E402
    CODE,
    DISPOSITIONS,
    HISTO,
    IDEA,
    LEDGER,
    TERMINAL,
    load_schema,
    validate,
)


def finding(path: str, line: int, message: str) -> dict[str, Any]:
    return {"code": CODE, "verdict": "error", "path": path, "line": line, "message": message}


def _item_errors(item: dict[str, Any]) -> Iterator[str]:
    """The live entry's own law: a live item never carries a terminal status, and an
    item past ``idea`` binds at least one typed intent (whether each intent RESOLVES is
    the doctor's question, not this file's)."""
    status, slug = item.get("status"), item.get("id")
    if status in TERMINAL:
        yield (
            f"entry {slug!r} carries the terminal status {status!r} — a terminal verdict "
            f"belongs to a {HISTO} record, never to a live active[] entry"
        )
    elif status != IDEA and not item.get("intents"):
        yield f"entry {slug!r} is {status!r}, past 'idea', and binds no typed intents[]"


def document_findings(text: str) -> list[dict[str, Any]]:
    """Every finding ``BACKLOG.json``'s *text* carries. ``line`` is the 1-based position
    in ``active[]`` for an entry finding, 1 for a whole-document one."""
    try:
        document = json.loads(text)
    except json.JSONDecodeError as exc:
        return [finding(LEDGER, exc.lineno, f"document is not valid JSON: {exc.msg}")]
    schema = load_schema("backlog-v1")
    findings = [finding(LEDGER, 1, m) for m in validate(document, schema, schema, "document")]
    if findings:
        return findings
    seen: dict[str, int] = {}
    for index, item in enumerate(document["active"], start=1):
        for message in _item_errors(item):
            findings.append(finding(LEDGER, index, message))
        first = seen.setdefault(str(item["id"]), index)
        if first != index:
            findings.append(
                finding(LEDGER, index, f"duplicate active[] id {item['id']!r} (first at #{first})")
            )
    return findings


def histo_findings(text: str) -> list[dict[str, Any]]:
    """Every finding the append-only exit ledger carries: the one histo-record-v1 shape,
    this ledger's terminal subset, and one line per id, ever."""
    schema = load_schema("histo-record-v1")
    findings: list[dict[str, Any]] = []
    seen: dict[str, int] = {}
    for number, raw in enumerate(text.split("\n"), start=1):
        if not raw.strip():
            continue
        try:
            record = json.loads(raw)
        except json.JSONDecodeError as exc:
            findings.append(finding(HISTO, number, f"line is not valid JSON: {exc.msg}"))
            continue
        messages = list(validate(record, schema, schema, "record"))
        findings.extend(finding(HISTO, number, message) for message in messages)
        if messages:
            continue
        if record["disposition"] not in DISPOSITIONS:
            findings.append(
                finding(
                    HISTO,
                    number,
                    f"disposition {record['disposition']!r} is not one of this ledger's "
                    f"terminal words {list(DISPOSITIONS)}",
                )
            )
        first = seen.setdefault(str(record["id"]), number)
        if first != number:
            findings.append(
                finding(HISTO, number, f"{record['id']!r} exits twice (first at line {first})")
            )
    return findings


def check(specs: Path) -> list[dict[str, Any]]:
    """Validate both committed files; a young specs tree with neither is not a finding.

    The cross-file invariant is the point of running them together: a slug that already
    exited is not also live, and a live slug has not already exited.
    """
    findings: list[dict[str, Any]] = []
    document, histo = specs / LEDGER, specs / HISTO
    live: dict[str, int] = {}
    if document.is_file():
        text = document.read_text(encoding="utf-8")
        findings += document_findings(text)
        if not findings:
            live = {str(i["id"]): n for n, i in enumerate(json.loads(text)["active"], start=1)}
    if histo.is_file():
        histo_text = histo.read_text(encoding="utf-8")
        broken = histo_findings(histo_text)
        findings += broken
        for number, raw in enumerate([] if broken else histo_text.split("\n"), start=1):
            exited = json.loads(raw).get("id") if raw.strip() else None
            if isinstance(exited, str) and exited in live:
                findings.append(
                    finding(
                        HISTO,
                        number,
                        f"{exited!r} exited at this line but is still live in active[] "
                        f"(#{live[exited]}) — an exit is once-only and terminal",
                    )
                )
    return findings
