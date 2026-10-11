#!/usr/bin/env python3
"""The one JSON-lines and JSON-object reader and writer of the skill scripts."""

from __future__ import annotations

import argparse
import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from _refusal import Refusal


class LineError(ValueError):
    """Line *number* of a JSONL text is not a JSON object."""

    def __init__(self, number: int, message: str) -> None:
        super().__init__(message)
        self.number = number


class Unreadable(Refusal):
    """A document that is not one JSON object; ``.fix`` is the act its caller names."""


def load(text: str) -> list[dict[str, Any]]:
    """Every JSON object of JSONL *text*, split on ``\\n`` alone — ``splitlines()``
    breaks a record holding U+2028."""
    out: list[dict[str, Any]] = []
    for number, line in enumerate(text.split("\n"), start=1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise LineError(number, f"is not valid JSON ({exc.msg})") from exc
        if not isinstance(record, dict):
            raise LineError(number, "is not a JSON object")
        out.append(record)
    return out


def read(path: Path) -> list[dict[str, Any]]:
    """Every JSON object of the JSONL file *path*, in file order; absent reads empty."""
    return load(path.read_text(encoding="utf-8")) if path.is_file() else []


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
