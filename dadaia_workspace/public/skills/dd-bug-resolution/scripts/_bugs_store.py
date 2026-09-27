#!/usr/bin/env python3
"""The ONE write path onto a bug ledger file: read -> apply -> validate -> replace.

Every write goes through :func:`commit`: build the candidate bytes, run the SAME `check`
they will be validated by, then `os.replace` atomically. A concurrent write is detected
by the file's own (size, mtime) and re-applied once — a race surfaces and retries.
"""

from __future__ import annotations

import json
import os
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _bugs_check import LEDGER, findings_for  # noqa: E402

Records = list[dict[str, Any]]


class Refusal(Exception):
    """A write this script refuses, carrying the one `fix:` line that unblocks it."""

    def __init__(self, message: str, fix: str = "") -> None:
        super().__init__(message)
        self.fix = fix


def _stamp(path: Path) -> tuple[int, int] | None:
    try:
        info = path.stat()
    except FileNotFoundError:
        return None
    return (info.st_size, info.st_mtime_ns)


def read_records(path: Path) -> Records:
    """Every record of *path*, in file order. A line that is not a JSON object refuses
    the read rather than being silently dropped from the rewrite that follows."""
    if not path.is_file():
        return []
    out: Records = []
    for number, line in enumerate(path.read_text(encoding="utf-8").split("\n"), start=1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise Refusal(
                f"{path.name}:{number} is not valid JSON ({exc.msg}) — refusing to "
                "rewrite a ledger this script cannot read in full",
                f"sed -n '{number}p' {path}",
            ) from exc
        if not isinstance(record, dict):
            raise Refusal(
                f"{path.name}:{number} is not a JSON object", f"sed -n '{number}p' {path}"
            )
        out.append(record)
    return out


def serialize(records: Records) -> str:
    return "".join(json.dumps(r, sort_keys=True, ensure_ascii=False) + "\n" for r in records)


def _validated(records: Records, rel: str) -> str:
    text = serialize(records)
    findings = findings_for(text, rel)
    if findings:
        detail = "; ".join(f"line {f['line']}: {f['message']}" for f in findings[:5])
        raise Refusal(
            f"the resulting {rel} would not pass check — nothing was written ({detail})",
            f"{Path(__file__).parent / 'bugs.py'} check --specs <specs>",
        )
    return text


def _replace(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def commit(
    path: Path, apply: Callable[[Records], Records], rel: str = LEDGER, archive: Path | None = None
) -> Records:
    """Apply *apply* to *path*'s records and replace the file atomically; with *archive*,
    the records *apply* dropped are appended there first.

    The candidate bytes are validated BEFORE either write, so a refused write leaves both
    files byte-identical. When the file changed under the computation, the change is
    re-read and re-applied ONCE; a second concurrent write refuses with a retry `fix:`.
    """
    before = _stamp(path)
    records = read_records(path)
    written = apply(records)
    text = _validated(written, rel)
    if _stamp(path) != before:
        before = _stamp(path)
        records = read_records(path)
        written = apply(records)
        text = _validated(written, rel)
        if _stamp(path) != before:
            raise Refusal(
                f"{path.name} changed twice under this write — nothing was written",
                "re-run this command",
            )
    if archive is not None:  # pre-v6 lines live there: only the moved records are new
        existing = archive.read_text(encoding="utf-8") if archive.is_file() else ""
        _replace(archive, existing + serialize([r for r in records if r not in written]))
    _replace(path, text)
    return written


def by_id(records: Records, bug_id: str) -> dict[str, Any]:
    for record in records:
        if record.get("id") == bug_id:
            return record
    raise Refusal(
        f"no bug record with id {bug_id!r} in this ledger",
        f"{Path(__file__).parent / 'bugs.py'} status --all --specs <specs>",
    )
