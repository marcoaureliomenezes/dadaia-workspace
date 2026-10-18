#!/usr/bin/env python3
"""The bug ledger's write path: :func:`commit` binds the one write loop (`_commit`) to the
ledger's own check, so every write is validated by the SAME `check` its bytes will meet."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import _commit
import _jsonl
from _bugs_check import HISTO, LEDGER, archived_records, findings_for, plain_ids
from _ledger import private_refusal, replace
from _platform import read_text
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
            f"sed -n '{exc.number}p' {path}",
        ) from exc


def history(specs: Path) -> Records:
    """The live ledger's records and the archive's."""
    return read_records(specs / LEDGER) + (
        archived_records(read_text(specs / HISTO)) if (specs / HISTO).is_file() else []
    )


def archived_plain_ids(specs: Path) -> frozenset[str]:
    """The ids of the archive's plain records."""
    return plain_ids(read_text(specs / HISTO)) if (specs / HISTO).is_file() else frozenset()


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
