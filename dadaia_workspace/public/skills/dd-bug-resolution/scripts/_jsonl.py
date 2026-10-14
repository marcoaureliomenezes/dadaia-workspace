#!/usr/bin/env python3
"""The one JSON-lines and JSON-object reader and writer of the skill scripts."""

from __future__ import annotations

import argparse
import json
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any

from _platform import quote
from _refusal import Refusal
from _root import workspace_of


class LineError(ValueError):
    """Line *number* of a JSONL text is not a JSON object."""

    def __init__(self, number: int, message: str) -> None:
        super().__init__(message)
        self.number = number


class Undecodable(Refusal):
    """The file *path* is not UTF-8: a verb refuses with the act that re-encodes its first bad
    line in place, a check reports a finding."""

    def __init__(self, path: Path, fix: str = "") -> None:
        raw = path.read_bytes().split(b"\n")
        bad = next((n for n, line in enumerate(raw, start=1) if not _utf8(line)), 1)
        super().__init__(
            f"{path} is not valid UTF-8",
            fix
            or f"Agent action: re-encode line {bad} of {path.resolve()} as UTF-8 in place; every other line stays",
        )
        self.path = path


def _utf8(raw: bytes) -> bool:
    try:
        raw.decode("utf-8")
    except UnicodeDecodeError:
        return False
    return True


class Unreadable(Refusal):
    """A document that is not one JSON object; ``.fix`` is the act its caller names."""


def reinstall_fix(start: Path) -> str:
    """The command that repairs a shipped file under *start*: `init` of the workspace holding
    it, which answers its harness from its own profile; outside every workspace, the act."""
    root = workspace_of(start)
    if root is None:
        return "Agent action: run `uvx dadaia-workspace init` with the workspace's directory as its first argument"
    return f"uvx dadaia-workspace init {quote(str(root))}"


def read_text(path: Path, fix: str = "") -> str:
    """The text of *path*; bytes that are not UTF-8 raise :class:`Undecodable` naming it, with
    *fix* in place of the git restore a tracked file gets."""
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise Undecodable(path, fix) from exc


def walk(text: str) -> Iterator[tuple[int, Any, str]]:
    """Each non-blank line of JSONL *text* as ``(number, value, why)``, split on ``\\n`` alone —
    ``splitlines()`` breaks a record holding U+2028. *why* is the parser's message, else ``""``."""
    for number, line in enumerate(text.split("\n"), start=1):
        if not line.strip():
            continue
        try:
            yield number, json.loads(line), ""
        except json.JSONDecodeError as exc:
            yield number, None, exc.msg


def load(text: str) -> list[dict[str, Any]]:
    """Every JSON object of JSONL *text*; the first line that is not one raises :class:`LineError`."""
    out: list[dict[str, Any]] = []
    for number, record, why in walk(text):
        if why:
            raise LineError(number, f"is not valid JSON ({why})")
        if not isinstance(record, dict):
            raise LineError(number, "is not a JSON object")
        out.append(record)
    return out


def read(path: Path) -> list[dict[str, Any]]:
    """Every JSON object of the JSONL file *path*, in file order; absent reads empty."""
    return load(read_text(path)) if path.is_file() else []


def serialize(records: Iterable[dict[str, Any]]) -> str:
    return "".join(json.dumps(r, sort_keys=True, ensure_ascii=False) + "\n" for r in records)


def values(args: argparse.Namespace, names: Iterable[str]) -> dict[str, Any]:
    """The parsed value of each option flag in *names*, keyed by its dest."""
    keys = [name.lstrip("-").replace("-", "_") for name in names]
    return {key: getattr(args, key) for key in keys}


def parse_object(text: str, fix: str) -> dict[str, Any]:
    """The JSON object *text* holds; anything else raises :class:`Unreadable` carrying *fix*."""
    try:
        document = json.loads(text)
    except json.JSONDecodeError as exc:
        raise Unreadable(f"the document is not valid JSON ({exc.msg})", fix) from exc
    if not isinstance(document, dict):
        raise Unreadable("the document is not a JSON object", fix)
    return document
