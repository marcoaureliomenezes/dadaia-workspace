#!/usr/bin/env python3
"""The ship ledger's one record: the append, and the summary it carries.

`releases_histo.jsonl` is the append-only history of PUBLISHED versions. `archive`
appends exactly one record per ship, LAST, after every filesystem step already
succeeded; `fold` rewrites one in place when ADR 0014 repairs a wrong archive.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _release_check import histo_findings  # noqa: E402
from _release_schema import HISTO  # noqa: E402
from _release_store import Refusal, State, replace  # noqa: E402

SCRIPT = Path(__file__).parent / "release.py"


def append_histo(path: Path, record: dict[str, Any]) -> None:
    """Append one validated terminal record to the append-only ship ledger. The record is
    validated ALONE — a pre-canon line already in the file is history, not this write's
    business, and re-validating the whole file would refuse every ship on a repo with one."""
    line = json.dumps(record, sort_keys=True, ensure_ascii=False) + "\n"
    findings = histo_findings(line)
    if findings:
        raise Refusal(
            f"the {HISTO} record this ship would write does not pass check — nothing was "
            f"written ({findings[0]['message']})",
            f"{SCRIPT} check --specs <specs>",
        )
    replace(path, (path.read_text(encoding="utf-8") if path.is_file() else "") + line)


def summary(release_id: str, sha: str, pr: int, state: State) -> str:
    """``shipped <sha> PR #<n>; rc=<rc>; <the last `summary` log entry>`` — the release's
    whole exit, in the one free-text field the histo record has for it."""
    parts = [f"shipped {sha} PR #{pr}", f"rc={state.get('rc')}"]
    texts = [
        entry.get("text")
        for entry in state.get("log", [])
        if isinstance(entry, dict) and entry.get("kind") == "summary" and entry.get("text")
    ]
    return "; ".join(parts + ([str(texts[-1])] if texts else [])) + f" ({release_id})"


def rewrite_histo(specs: Path, folded_id: str, into: str, placement: str) -> list[str]:
    """Rewrite every ship record naming *folded_id* in place: `release` becomes *into* and
    the summary names the placement. A pre-canon release may have none — that is not a
    refusal, the fold already happened."""
    path = specs / HISTO
    if not path.is_file():
        return []
    ids = {folded_id, f"v{folded_id}"}
    suffix = f" | folded into {into}/{placement} (operator ruling 2026-09-14, ADR 0014)"
    rewritten: list[str] = []
    lines: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        record = json.loads(raw)
        if record.get("id") in ids:
            record["release"] = into
            record["summary"] = (record.get("summary") or "") + suffix
            rewritten.append(str(record["id"]))
        lines.append(json.dumps(record, sort_keys=True, ensure_ascii=False))
    if rewritten:
        replace(path, "\n".join(lines) + "\n")
    return rewritten
