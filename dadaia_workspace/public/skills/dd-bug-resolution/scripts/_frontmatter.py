#!/usr/bin/env python3
"""The one frontmatter grammar of the workspace (ADR 0246): a stdlib strict subset of YAML
that equals ``yaml.safe_load`` or refuses, never a silent difference.

``split(text)`` returns ``(block, body)`` or ``None``, with a BOM and CRLF normalised away.
``parse(block)`` returns the mapping or raises ``ValueError`` whose message starts
``line N``. Accepted: top-level ``key: value``; plain scalars typed null/bool/int/str;
double-quoted (JSON rules) and single-quoted scalars; one-level flow maps and sequences
of scalars; block lists of scalars or mappings; nested block maps; folded ``>`` and
``>-``; a ``#`` comment after a plain or quoted value. Everything else raises: tabs,
duplicate keys, full-line comments, anchors, aliases, tags, ``|`` and ``>+``, multi-line plain or quoted
scalars, nested flow collections, and every YAML 1.1 ambiguity (``yes``, ``0755``,
``1_000``, a date, ``~``, ``<<``).
"""

from __future__ import annotations

import json
import re
from typing import Any, NamedTuple

__all__ = ["NotAMapping", "parse", "split"]

_SPLIT = re.compile(r"\A---[ \t]*\n(.*?)\n---[ \t]*\n?", re.DOTALL)
_KEY = re.compile(r"([A-Za-z_][A-Za-z0-9_.-]*):(?: +(.*))?$")
_BAD_CHAR = re.compile("[^\x20-\x7e\xa0-‧‪-﻾＀-�\U00010000-\U0010ffff]")
_DQ = re.compile(r'"(?:[^"\\]|\\.)*"')
_SQ = re.compile(r"'(?:[^']|'')*'")
_FLOW_PLAIN = re.compile(r"[^\s,\[\]{}\"'#:?][^,\[\]{}\"'#:?]*")
_TAIL = re.compile(r" *| +#.*")
_COMMENT = re.compile(r" +#.*")
_INT = re.compile(r"-?(?:0|[1-9][0-9]*)")
_VERSION = re.compile(r"[0-9]+(?:\.[0-9]+){2,}")
_TYPED: dict[str, Any] = {"null": None, "true": True, "false": False}
_KEYWORDS = frozenset({"yes", "no", "on", "off", "true", "false", "null"})
_NOT_FIRST = frozenset("&*!|>'\"%@`#,]}?:[{")
_NUMBER_LIKE = re.compile(r"[-+.](?:[0-9.iInN]|$| )")


class NotAMapping(ValueError):
    """The block is empty or its first line is not ``key: value`` (a list, a bare scalar)."""


def split(text: str) -> tuple[str, str] | None:
    """``(block, body)`` of the leading ``---`` block of *text*, or ``None``."""
    text = text.removeprefix("﻿").replace("\r\n", "\n")
    match = _SPLIT.match(text)
    return (match.group(1), text[match.end() :]) if match else None


def _fail(number: int, why: str) -> ValueError:
    return ValueError(f"line {number}: {why}")


def _plain(s: str, number: int) -> Any:
    if s in _TYPED:
        return _TYPED[s]
    if _INT.fullmatch(s):
        return int(s)
    if _VERSION.fullmatch(s):
        return s
    if (
        s[0] in _NOT_FIRST
        or s[0].isdigit()
        or _NUMBER_LIKE.match(s)
        or s in {"~", "<<", "="}
        or s.lower() in _KEYWORDS | {"y", "n"}
    ):
        raise _fail(number, f"plain scalar {s!r} is ambiguous or outside the subset; quote it")
    if ": " in s or s.endswith(":"):
        raise _fail(number, f"plain scalar {s!r} holds ': '; quote it")
    return s


def _quoted(s: str, pos: int, number: int) -> tuple[str, int]:
    """The quoted scalar of *s* at *pos* and the position after it."""
    if s[pos] == '"':
        match = _DQ.match(s, pos)
        if match is None:
            raise _fail(number, "unterminated double-quoted scalar")
        try:
            value: str = json.loads(match[0])
        except ValueError:
            raise _fail(number, f"escape of {match[0]!r} is outside the JSON subset") from None
        if any("\ud800" <= ch <= "\udfff" for ch in value):
            raise _fail(number, "surrogate escape")
        return value, match.end()
    match = _SQ.match(s, pos)
    if match is None:
        raise _fail(number, "unterminated single-quoted scalar")
    return match[0][1:-1].replace("''", "'"), match.end()


def _atom(s: str, pos: int, number: int) -> tuple[Any, int]:
    if pos < len(s) and s[pos] in "\"'":
        return _quoted(s, pos, number)
    match = _FLOW_PLAIN.match(s, pos)
    if match is None:
        raise _fail(number, "empty, nested or unsupported item in a flow collection")
    return _plain(match[0].rstrip(), number), match.end()


def _flow(s: str, number: int) -> list[Any] | dict[str, Any]:
    close = "]" if s[0] == "[" else "}"
    if s[-1] != close:
        raise _fail(number, "unterminated flow collection")
    inner, pos = s[1:-1], 0
    seq: list[Any] = []
    mapping: dict[str, Any] = {}
    while inner[pos:].strip():
        pos += len(inner[pos:]) - len(inner[pos:].lstrip(" "))
        item, pos = _atom(inner, pos, number)
        if close == "}":
            if not isinstance(item, str) or not inner.startswith(": ", pos):
                raise _fail(number, "flow map entry must be 'key: value' with a string key")
            if item in mapping:
                raise _fail(number, f"duplicate key {item!r}")
            pos += 2
            pos += len(inner[pos:]) - len(inner[pos:].lstrip(" "))
            mapping[item], pos = _atom(inner, pos, number)
        else:
            seq.append(item)
        rest = inner[pos:].lstrip(" ")
        pos = len(inner) - len(rest)
        if rest and not rest.startswith(","):
            raise _fail(number, "expected ',' in a flow collection")
        pos += 1 if rest else 0
        if rest and not inner[pos:].strip():
            raise _fail(number, "empty item in a flow collection")
    return mapping if close == "}" else seq


class _Line(NamedTuple):
    number: int
    indent: int
    text: str


class _Reader:
    def __init__(self, block: str) -> None:
        self.lines: list[_Line] = []
        self.i = 0
        for number, raw in enumerate(block.split("\n"), start=1):
            if _BAD_CHAR.search(raw):
                raise _fail(number, "tab, control or unsupported character")
            text = raw.lstrip(" ")
            self.lines.append(_Line(number, len(raw) - len(text), text))

    def peek(self) -> _Line | None:
        """The next structural line (blank lines skipped), or ``None``."""
        while self.i < len(self.lines):
            line = self.lines[self.i]
            if line.text:
                return line
            self.i += 1
        return None

    def mapping(self, indent: int) -> dict[str, Any]:
        out: dict[str, Any] = {}
        while (line := self.peek()) is not None and line.indent >= indent:
            if line.indent > indent:
                raise _fail(line.number, "unexpected indentation (multi-line scalar?)")
            match = _KEY.match(line.text)
            if match is None or match[1].lower() in _KEYWORDS:
                raise _fail(line.number, "expected a plain 'key: value' line")
            if match[1] in out:
                raise _fail(line.number, f"duplicate key {match[1]!r}")
            self.i += 1
            out[match[1]] = self.value((match[2] or "").strip(" "), indent, line.number)
        return out

    def sequence(self, indent: int) -> list[Any]:
        out: list[Any] = []
        while (line := self.peek()) is not None and line.indent >= indent:
            if line.indent > indent or not line.text.startswith("- "):
                raise _fail(line.number, "expected a '- item' line")
            item = line.text[1:].lstrip(" ")
            if not item:
                raise _fail(line.number, "empty list item")
            offset = indent + len(line.text) - len(item)
            if item[0] not in "\"'[{" and _KEY.match(item):
                self.lines[self.i] = _Line(line.number, offset, item)
                out.append(self.mapping(offset))
            else:
                self.i += 1
                out.append(self.scalar(item.rstrip(" "), line.number))
        return out

    def scalar(self, s: str, number: int) -> Any:
        if s[0] in "\"'":
            value, end = _quoted(s, 0, number)
            if not _TAIL.fullmatch(s[end:]):
                raise _fail(number, "text after a quoted scalar")
            return value
        if s[0] in "[{":
            return _flow(s, number)
        return _plain(_COMMENT.sub("", s), number)

    def value(self, rest: str, indent: int, number: int) -> Any:
        if rest.startswith(">"):
            return self.folded(rest, indent, number)
        if rest:
            return self.scalar(rest, number)
        nxt = self.peek()
        if nxt is None or nxt.indent <= indent:
            return None
        return self.sequence(nxt.indent) if nxt.text.startswith("- ") else self.mapping(nxt.indent)

    def folded(self, header: str, indent: int, number: int) -> str:
        if header not in {">", ">-"}:
            raise _fail(number, f"block scalar header {header!r} is outside the subset")
        content: list[str | None] = []
        start, width, last = self.i, -1, -1
        while self.i < len(self.lines):
            line = self.lines[self.i]
            if line.text == "" and line.indent:
                raise _fail(line.number, "whitespace-only line in a block scalar")
            if line.text and line.indent <= indent:
                break
            if line.text:
                width = width if width >= 0 else line.indent
                if line.indent != width:
                    raise _fail(line.number, "block scalar indentation differs or is more-indented")
                last = len(content)
                content.append(line.text)
            else:
                content.append(None)
            self.i += 1
        if last < 0:
            return ""
        if content[0] is None:
            raise _fail(number + 1, "block scalar starts with a blank line")
        out = content[0] or ""
        gap = 0
        for part in content[1 : last + 1]:
            if part is None:
                gap += 1
                continue
            out += "\n" * gap if gap else " "
            out += part
            gap = 0
        followed = start + last + 1 < len(self.lines)
        return out + "\n" if header == ">" and followed else out


def parse(block: str) -> dict[str, Any]:
    """The mapping of a frontmatter *block*; ``ValueError`` (``line N: …``) on any refusal."""
    reader = _Reader(block)
    first = reader.peek()
    if first is None:
        raise NotAMapping("line 1: no content")
    if first.text.startswith("- ") or first.text == "-" or not re.search(r":(?: |$)", first.text):
        raise NotAMapping(f"line {first.number}: not a mapping")
    try:
        out = reader.mapping(first.indent)
    except RecursionError:
        raise _fail(reader.lines[min(reader.i, len(reader.lines) - 1)].number, "too deep") from None
    if (extra := reader.peek()) is not None:
        raise _fail(extra.number, "unexpected content")
    return out
