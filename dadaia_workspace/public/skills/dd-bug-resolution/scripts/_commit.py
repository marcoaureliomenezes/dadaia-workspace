#!/usr/bin/env python3
"""The one write loop onto a ledger file: read -> apply -> validate -> replace.

A concurrent write is detected by the file's own (size, mtime) and re-applied once, so a
race surfaces and retries. The ledger decides what a record is: it hands in `load`,
`validate`, `replace` and, for an archive, `archive`.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any

from _jsonl import serialize
from _refusal import Refusal

Records = list[dict[str, Any]]


def stamp(path: Path) -> tuple[int, int] | None:
    """(size, mtime) — how a write detects a concurrent one; ``None`` when absent."""
    try:
        info = path.stat()
    except FileNotFoundError:
        return None
    return (info.st_size, info.st_mtime_ns)


def validated(
    records: Records,
    before: Records,
    rel: str,
    private: Callable[[Iterable[dict[str, Any]]], tuple[str, str] | None],
    findings: Callable[[str], list[dict[str, Any]]],
    fix: str,
) -> str:
    """The bytes of *records*, or a refusal: the new ones carry no private term and the
    bytes pass *findings*, the check the committed file is judged by."""
    why = private(r for r in records if r not in before)
    if why is not None:
        raise Refusal(*why)
    text = serialize(records)
    if found := findings(text):
        detail = "; ".join(f"line {f['line']}: {f['message']}" for f in found[:5])
        raise Refusal(
            f"the resulting {rel} would not pass check — nothing was written ({detail})", fix
        )
    return text


def commit(
    path: Path,
    load: Callable[[Path], Records],
    apply: Callable[[Records], Records],
    validate: Callable[[Records, Records, str, Records], str],
    replace: Callable[[Path, str], None],
    histo: Path | None = None,
    archive: Callable[[str, Records], str] | None = None,
) -> Records:
    """Apply *apply* to *path*'s records and replace the file with the bytes *validate*
    approves, BEFORE either write, so a refused write leaves both files byte-identical.

    *validate*(written, records, archive text, moved) returns those bytes. With *archive*,
    the records *apply* dropped are *moved*: *archive*(archive text, moved) is the new text
    of *histo*. The archive is read once per attempt, the base of the append, so a concurrent
    archive is never overwritten. A change under the computation is re-read and re-applied
    ONCE; a second concurrent write refuses with a retry `fix:`.
    """

    def attempt() -> tuple[tuple[int, int] | None, str, Records, Records, str]:
        before = stamp(path)
        old = histo.read_text(encoding="utf-8") if histo is not None and histo.is_file() else ""
        records = load(path)
        written = apply(records)
        moved = [r for r in records if r not in written] if archive else []
        return before, old, moved, written, validate(written, records, old, moved)

    before, old, moved, written, text = attempt()
    if stamp(path) != before:
        before, old, moved, written, text = attempt()
        if stamp(path) != before:
            raise Refusal(
                f"{path.name} changed twice under this write — nothing was written",
                "Operator action: re-run the same command, unchanged",
            )
    if archive and histo is not None:
        replace(histo, archive(old, moved))
    replace(path, text)
    return written
