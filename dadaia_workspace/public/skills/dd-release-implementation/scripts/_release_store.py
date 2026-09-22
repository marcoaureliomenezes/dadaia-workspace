#!/usr/bin/env python3
"""The ONE write path onto the release files: read -> apply -> validate -> replace.

Every write goes through :func:`commit`: build the candidate bytes, run the SAME `check`
they will be validated by, then `os.replace` atomically. A concurrent write is detected
by the file's own (size, mtime) and re-applied once — a race surfaces and retries.
"""

from __future__ import annotations

import json
import os
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _release_check import state_findings  # noqa: E402
from _release_schema import SEMVER_RE, STATE  # noqa: E402

State = dict[str, Any]
SCRIPT = Path(__file__).parent / "release.py"


class Refusal(Exception):
    """A write this script refuses, carrying the one `fix:` line that unblocks it."""

    def __init__(self, message: str, fix: str = "") -> None:
        super().__init__(message)
        self.fix = fix


@dataclass(frozen=True)
class Live:
    """The one live release, already proven readable."""

    release_id: str
    release_dir: Path
    state: State


def live_ids(specs: Path) -> list[str]:
    """Every SemVer-named release directory directly under ``releases/`` carrying a state
    document — `_archive` is not live."""
    releases = specs / "releases"
    if not releases.is_dir():
        return []
    return sorted(
        d.name
        for d in releases.iterdir()
        if d.is_dir() and SEMVER_RE.match(d.name) and (d / STATE).is_file()
    )


def read_state(path: Path) -> State:
    """One state document, refusing anything this script cannot read in full."""
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise Refusal(
            f"{path.name} is not a readable release-state-v1 document ({exc})",
            f"{SCRIPT} check --specs <specs>",
        ) from exc
    if not isinstance(document, dict):
        raise Refusal(f"{path.name} is not a JSON object", f"{SCRIPT} check --specs <specs>")
    return document


def live_release(specs: Path) -> Live:
    """Resolve the ONE live release and read its state, or refuse naming the reason."""
    ids = live_ids(specs)
    if not ids:
        raise Refusal(
            "no live release under specs/releases/ — nothing to operate on",
            f"{SCRIPT} new <M.m.p> --specs {specs}",
        )
    if len(ids) > 1:
        raise Refusal(
            f"multiple live release directories carry {STATE}: {', '.join(ids)} — the "
            "release-candidates model allows exactly one",
            f"{SCRIPT} check --specs {specs}",
        )
    release_dir = specs / "releases" / ids[0]
    return Live(ids[0], release_dir, read_state(release_dir / STATE))


def window_start(state: State) -> str:
    """The memory window's start: the last memory entry's `until`, else `defined.sha`."""
    ends = [e.get("until") for e in state.get("log") or [] if e.get("kind") == "memory"]
    start = next((u for u in reversed(ends) if u), (state.get("defined") or {}).get("sha"))
    if not start:
        raise Refusal("the live release has no defined.sha to open the memory window at",
                      f"{SCRIPT} phase IMPLEMENTATION --sha <sha>")  # fmt: skip
    return str(start)


def serialize(state: State) -> str:
    """The canonical bytes: 2-space indent, non-ASCII kept, one trailing newline."""
    return json.dumps(state, indent=2, ensure_ascii=False) + "\n"


def validated(state: State, rel: str, *, archived: bool = False) -> str:
    text = serialize(state)
    findings = state_findings(text, rel, archived=archived)
    if findings:
        detail = "; ".join(str(f["message"]) for f in findings[:5])
        raise Refusal(
            f"the resulting {rel} would not pass check — nothing was written ({detail})",
            f"{SCRIPT} check --specs <specs>",
        )
    return text


def replace(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def _stamp(path: Path) -> tuple[int, int] | None:
    info = path.stat() if path.is_file() else None
    return (info.st_size, info.st_mtime_ns) if info else None


def commit(
    path: Path, rel: str, apply: Callable[[State], State], *, archived: bool = False
) -> State:
    """Apply *apply* to *path*'s state and replace the document atomically.

    Validated BEFORE the replace, so a refused write leaves the file byte-identical; a file
    changed under the computation is re-applied ONCE, a second race refuses.
    """
    before = _stamp(path)
    written = apply(read_state(path))
    text = validated(written, rel, archived=archived)
    if _stamp(path) != before:
        before = _stamp(path)
        written = apply(read_state(path))
        text = validated(written, rel, archived=archived)
        if _stamp(path) != before:
            raise Refusal(
                f"{path.name} changed twice under this write — nothing was written",
                "re-run this command",
            )
    replace(path, text)
    return written
