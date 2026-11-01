#!/usr/bin/env python3
"""The bug ledger's write path: :func:`commit` binds the one write loop (`_commit`) to the
ledger's own check, so every write is validated by the SAME `check` its bytes will meet."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import _commit
import _jsonl
from _bugs_check import HISTO, LEDGER, OPEN, archive_records, findings_for
from _ledger import private_refusal, replace
from _platform import command, read_text
from _refusal import Refusal as Refusal
from _specs import script

Records = list[dict[str, Any]]


def read_records(path: Path) -> Records:
    """Every record of *path*, in file order. A line that is not a JSON object refuses
    the read rather than being silently dropped from the rewrite that follows."""
    try:
        return _jsonl.read(path)
    except _jsonl.LineError as exc:
        raise Refusal(
            f"{path.name}:{exc.number} {exc} — refusing to rewrite a ledger this script "
            "cannot read in full",
            command("sed", "-n", f"{exc.number}p", str(path)),
        ) from exc


def _archive(specs: Path) -> list[tuple[int, dict[str, Any], bool]]:
    return archive_records(read_text(specs / HISTO)) if (specs / HISTO).is_file() else []


def history(specs: Path) -> Records:
    """The live ledger's records and the archive's, a legacy event line as its `data`."""
    return read_records(specs / LEDGER) + [record for _, record, _ in _archive(specs)]


def archived_plain_ids(specs: Path) -> frozenset[str]:
    """The ids of the archive's plain records."""
    return frozenset(str(record["id"]) for _, record, legacy in _archive(specs) if not legacy)


def open_ids(specs: Path) -> list[str]:
    """The ids of the live ledger's open records, sorted."""
    return sorted(str(r["id"]) for r in read_records(specs / LEDGER) if r.get("status") == OPEN)


def standing(specs: Path, bug_id: str, release: str) -> str:
    """`traced` when the record of *bug_id* was resolved in *release* (a legacy `resolved_release`),
    is rejected, or is superseded by a bug that stands so; `untraced` while not; else why it is wrong."""
    records = {str(r["id"]): r for r in history(specs)}
    seen: set[str] = set()
    while bug_id not in seen:
        seen.add(bug_id)
        if (record := records.get(bug_id)) is None:
            return f"names no record under bugs/ ({bug_id})"
        if not (by := record.get("superseded_by")):
            declined = record.get("status") == "rejected"
            return "traced" if declined or record.get("resolved_release") == release else "untraced"
        bug_id = str(by)
    return "untraced"


def _validator(path: Path, rel: str) -> Callable[[Records, Records, str, Records], str]:
    def validate(written: Records, records: Records, old: str, moved: Records) -> str:
        archived = old + _jsonl.serialize(moved)
        why = private_refusal((r for r in written if r not in records), path)
        if why is not None:
            raise Refusal(*why)
        return _commit.validated(
            _jsonl.serialize(written),
            rel,
            lambda text: findings_for(text, rel, archived, path.parents[1]),
            script(Path(__file__).parent / "bugs.py")("check"),
        )

    return validate


def commit(
    path: Path, apply: Callable[[Records], Records], rel: str = LEDGER, archive: bool = False
) -> Records:
    """Apply *apply* to *path*'s records and replace the file atomically; with *archive*,
    the records *apply* dropped are appended to the ledger's archive first, and only those
    stay known ids — a drop without it leaves a dangling `caused_by` refused here."""
    return _commit.commit(
        path,
        read_records,
        apply,
        _validator(path, rel),
        replace,
        path.parents[1] / HISTO,
        (lambda old, moved: old + _jsonl.serialize(moved)) if archive else None,
    )


def by_id(records: Records, bug_id: str) -> dict[str, Any]:
    for record in records:
        if record.get("id") == bug_id:
            return record
    raise Refusal(
        f"no bug record with id {bug_id!r} in this ledger",
        script(Path(__file__).parent / "bugs.py")("status", "--all"),
    )
