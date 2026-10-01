#!/usr/bin/env python3
"""The ONE write path onto a bug ledger file: read -> apply -> validate -> replace.

Every write goes through :func:`commit`: build the candidate bytes, run the SAME `check`
they will be validated by, then `os.replace` atomically. A concurrent write is detected
by the file's own (size, mtime) and re-applied once — a race surfaces and retries.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _bugs_check import LEDGER, findings_for  # noqa: E402
from _ledger import LineError, private_refusal, records, replace, stamp  # noqa: E402
from _specs import script  # noqa: E402

Records = list[dict[str, Any]]


class Refusal(Exception):
    """A write this script refuses, carrying the one `fix:` line that unblocks it."""

    def __init__(self, message: str, fix: str = "") -> None:
        super().__init__(message)
        self.fix = fix


def read_records(path: Path) -> Records:
    """Every record of *path*, in file order. A line that is not a JSON object refuses
    the read rather than being silently dropped from the rewrite that follows."""
    try:
        return records(path)
    except LineError as exc:
        raise Refusal(
            f"{path.name}:{exc.number} {exc} — refusing to rewrite a ledger this script "
            "cannot read in full",
            f"sed -n '{exc.number}p' {path}",
        ) from exc


def serialize(records: Records) -> str:
    return "".join(json.dumps(r, sort_keys=True, ensure_ascii=False) + "\n" for r in records)


def _validated(records: Records, rel: str, before: Records) -> str:
    for record in records:
        why = None if record in before else private_refusal(record)
        if why is not None:
            raise Refusal(*why)
    text = serialize(records)
    findings = findings_for(text, rel)
    if findings:
        detail = "; ".join(f"line {f['line']}: {f['message']}" for f in findings[:5])
        raise Refusal(
            f"the resulting {rel} would not pass check — nothing was written ({detail})",
            f"{script(Path(__file__).parent / 'bugs.py')} check",
        )
    return text


def commit(
    path: Path, apply: Callable[[Records], Records], rel: str = LEDGER, archive: Path | None = None
) -> Records:
    """Apply *apply* to *path*'s records and replace the file atomically; with *archive*,
    the records *apply* dropped are appended there first.

    The candidate bytes are validated BEFORE either write, so a refused write leaves both
    files byte-identical. When the file changed under the computation, the change is
    re-read and re-applied ONCE; a second concurrent write refuses with a retry `fix:`.
    """
    before = stamp(path)
    records = read_records(path)
    written = apply(records)
    text = _validated(written, rel, records)
    if stamp(path) != before:
        before = stamp(path)
        records = read_records(path)
        written = apply(records)
        text = _validated(written, rel, records)
        if stamp(path) != before:
            raise Refusal(
                f"{path.name} changed twice under this write — nothing was written",
                "re-run this command",
            )
    if archive is not None:  # pre-v6 lines live there: only the moved records are new
        existing = archive.read_text(encoding="utf-8") if archive.is_file() else ""
        replace(archive, existing + serialize([r for r in records if r not in written]))
    replace(path, text)
    return written


def by_id(records: Records, bug_id: str) -> dict[str, Any]:
    for record in records:
        if record.get("id") == bug_id:
            return record
    raise Refusal(
        f"no bug record with id {bug_id!r} in this ledger",
        f"{script(Path(__file__).parent / 'bugs.py')} status --all",
    )
