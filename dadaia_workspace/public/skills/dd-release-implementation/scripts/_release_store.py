#!/usr/bin/env python3
"""The ONE write path onto the release files: read -> apply -> validate -> replace.

Every write goes through :func:`commit`: build the candidate bytes, run the SAME `check`
they will be validated by, then `os.replace` atomically. A concurrent write is detected
by the file's own (size, mtime) and re-applied once — a race surfaces and retries.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from _grammar import STATE
from _jsonl import parse_object
from _ledger import records, replace, stamp
from _refusal import Refusal as Refusal
from _release_check import state_findings
from _release_schema import Unreadable, current_candidate, live_id
from _specs import choice, script

State = dict[str, Any]
SCRIPT = script(Path(__file__).parent / "release.py")


@dataclass(frozen=True)
class Live:
    """The one live release, already proven readable, and its live candidate folder."""

    release_id: str
    release_dir: Path
    state: State
    candidate: Path | None


def read_state(path: Path) -> State:
    """One state document, refusing anything this script cannot read in full."""
    fix = f"Operator action: repair {path} until `{SCRIPT} check` passes"
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise Refusal(f"{path.name} cannot be read ({exc})", fix) from exc
    return parse_object(text, fix)


def live_release(specs: Path) -> Live:
    """Resolve the ONE live release and read its state, or refuse naming the reason."""
    try:
        live = live_id(specs)
    except Unreadable as exc:
        vars(refusal := Refusal(*exc.args)).update(vars(exc))  # the act's choice, if any
        raise refusal from None
    release_dir = specs / "releases" / live
    state = read_state(release_dir / STATE)
    return Live(live, release_dir, state, current_candidate(release_dir, state))


def window_start(state: State) -> str:
    """The memory window's start: the last memory entry's `until`, else `defined.sha`."""
    ends = [e["until"] for e in state.get("log") or []
            if isinstance(e, dict) and e.get("kind") == "memory" and e.get("until")]  # fmt: skip
    if not (start := ends[-1] if ends else (state.get("defined") or {}).get("sha")):
        raise choice(Refusal("the live release has no defined.sha to open the memory window at",
                     f"{SCRIPT} phase IMPLEMENTATION --sha"),
                     "with the sha of the commit that approved the definition")  # fmt: skip
    return str(start)


def open_bug_ids(specs: Path) -> list[str]:
    """Every persisted open bug id, sorted for deterministic refusals."""
    return sorted(
        str(record["id"])
        for record in records(specs / "bugs" / "BUGS.jsonl")
        if record.get("status") == "open" and record.get("id")
    )


def serialize(state: State) -> str:
    """The canonical bytes: 2-space indent, non-ASCII kept, one trailing newline."""
    return json.dumps(state, indent=2, ensure_ascii=False) + "\n"


def validated(state: State, rel: str) -> str:
    text = serialize(state)
    findings = state_findings(text, rel)
    if findings:
        detail = "; ".join(str(f["message"]) for f in findings[:5])
        raise Refusal(
            f"the resulting {rel} would not pass check — nothing was written ({detail})",
            f"{SCRIPT} check",
        )
    return text


def commit(path: Path, rel: str, apply: Callable[[State], State]) -> State:
    """Apply *apply* to *path*'s state and replace the document atomically.

    Validated BEFORE the replace, so a refused write leaves the file byte-identical; a file
    changed under the computation is re-applied ONCE, a second race refuses.
    """
    before = stamp(path)
    written = apply(read_state(path))
    text = validated(written, rel)
    if stamp(path) != before:
        before = stamp(path)
        written = apply(read_state(path))
        text = validated(written, rel)
        if stamp(path) != before:
            raise Refusal(
                f"{path.name} changed twice under this write — nothing was written",
                "Operator action: re-run the same command, unchanged",
            )
    replace(path, text)
    return written
