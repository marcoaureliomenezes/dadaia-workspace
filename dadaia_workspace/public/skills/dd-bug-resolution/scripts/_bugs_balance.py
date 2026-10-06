#!/usr/bin/env python3
"""The bug-balance block of `QUALITY.md`'s `## Bugs`: the ledger's records in, text out.

Three readouts over the records alone, no git and no I/O: the per-surface table, the
Laplace trend (Kanoun & Laprie, *Handbook of Software Reliability Engineering* ch. 10) with
days as the axis, and the defective-fix rate per rc (Kan, *Metrics and Models in Software
Quality Engineering* ch. 4). `bugs.py balance` feeds it; `release.py check` regenerates it.
"""

from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from datetime import datetime
from typing import Any, NamedTuple

Records = list[dict[str, Any]]
UNKNOWN = "unknown"
TREND = 4  # the trend window: the live release and the 3 published before it
_BUG = 2  # the bug window: the live release and the last published
_Z = 1.96
_HEAD = (
    *("surface", "records", "recurrences", "fix-induced"),
    *("archived", "rcs", "correlates", "settled"),
)
_APART = ("release unknown", "no found_in", "outside the window")
_HEADING = re.compile(r"^## Bugs\n", re.M)
_BLOCK = re.compile(
    r"(?P<head>^## Bugs\n(?:(?!## ).*\n)*?```text\n)(?P<body>(?:.*\n)*?)(?P<tail>^```$)", re.M
)


class Window(NamedTuple):
    order: list[str]  # every release id, oldest first, the live one last
    start: datetime  # the opening day of the oldest trend release
    end: datetime  # the live release's closure day


def _found(record: dict[str, Any]) -> tuple[str | None, str | None]:
    found = record.get("found_in")
    return (found.get("release"), found.get("rc")) if isinstance(found, dict) else (None, None)


def _surface(record: dict[str, Any]) -> str:
    return str(record.get("surface") or UNKNOWN)


def _induced(record: dict[str, Any]) -> bool:
    return record.get("caused_by") not in (None, "none")


def _row(surface: str, records: Records, archived: int, bug: set[str]) -> tuple[str, ...]:
    seen = {f for f in map(_found, records) if f[0] in bug}
    real = surface != UNKNOWN
    correlates = sum(len(r["correlates"]) for r in records if isinstance(r.get("correlates"), list))
    return (
        surface,
        str(len(records)),
        str(len(records) - 1) if real else "-",
        str(sum(map(_induced, records))),
        str(archived),
        str(sum(rc not in (None, UNKNOWN) for _, rc in seen)),
        str(correlates),
        ("no" if seen else "yes") if real else "-",
    )


def _table(main: list[tuple[str, ...]], apart: list[tuple[str, ...]]) -> list[str]:
    widths = [max(len(c[i]) for c in (_HEAD, *main, *apart)) for i in range(len(_HEAD))]

    def line(row: tuple[str, ...]) -> str:
        return "  ".join(c.ljust(w) for c, w in zip(row, widths, strict=True)).rstrip()

    return [line(_HEAD), *map(line, main), *(["dev-tooling:", *map(line, apart)] if apart else [])]


def laplace(days: list[float], span: float) -> float:
    """The Laplace factor u of *days* (each record's offset in the window) over *span* days."""
    return (sum(days) / len(days) - span / 2) / (span * math.sqrt(1 / (12 * len(days))))


def _reading(days: list[float], span: float) -> str:
    if not days or span <= 0:  # a window that opens and closes on one day has no axis
        return "u = n/a, no data"
    u = laplace(days, span)
    return f"u = {u:.2f}, {'converging' if u <= -_Z else 'diverging' if u >= _Z else 'no trend'}"


def _bucket(release: str | None, trend: set[str]) -> str:
    if release is None:
        return "no found_in"
    if release == UNKNOWN:
        return "release unknown"
    return "counted" if release in trend else "outside the window"


def _gaps(records: Records, window: Window) -> int:
    """Records of the trend window whose surface's previous record left the bug window."""
    rank = {release: i for i, release in enumerate(window.order)}
    ranks: defaultdict[str, list[int]] = defaultdict(list)
    for r in sorted(records, key=lambda r: str(r.get("ts"))):
        if _surface(r) != UNKNOWN and (release := _found(r)[0]) in rank:
            ranks[_surface(r)].append(rank[str(release)])
    first = len(window.order) - TREND
    return sum(
        later >= first and later - earlier >= _BUG
        for each in ranks.values()
        for earlier, later in zip(each, each[1:], strict=False)
    )


def _trend(records: Records, window: Window) -> list[str]:
    trend = set(window.order[-TREND:])
    span = (window.end - window.start).total_seconds() / 86400
    kinds = [_bucket(_found(r)[0], trend) for r in records]
    days = [
        (datetime.fromisoformat(str(r["ts"])) - window.start).total_seconds() / 86400
        for r, kind in zip(records, kinds, strict=True)
        if kind == "counted"
    ]
    apart = ", ".join(f"{kinds.count(k)} {k}" for k in _APART)
    shown = window.order[-TREND:]
    return [
        f"Laplace trend (days), window {shown[0]}..{shown[-1]}, T = {span:g} days: "
        f"{_reading(days, span)}",
        f"  counted {len(days)} of {len(records)} records; apart: {apart}",
        f"  records found on an already settled surface: {_gaps(records, window)}",
    ]


def _rates(records: Records) -> list[str]:
    keyed = [(_found(r), _induced(r)) for r in records]
    known = [(k, bad) for k, bad in keyed if UNKNOWN not in k and None not in k]
    total = Counter(k for k, _ in known)
    defective = Counter(k for k, bad in known if bad)

    def order(key: tuple[str | None, str | None]) -> list[int]:
        return [int(n) for n in re.findall(r"\d+", f"{key[0]}.{key[1]}")]

    return [
        f"{k[0]}/{k[1]}  {defective[k]}/{total[k]}  {100 * defective[k] // total[k]}%"
        for k in sorted(total, key=order)
    ]


def render(live: Records, archived: Records, window: Window, dev: frozenset[str]) -> str:
    """The block's text for the live and archived *records*; *dev* names the dev-tooling
    surfaces, printed apart. Ends with a newline; the same input renders the same bytes."""
    records = [*live, *archived]
    by: defaultdict[str, Records] = defaultdict(list)
    for r in records:
        by[_surface(r)].append(r)
    gone = Counter(map(_surface, archived))
    rows = {s: _row(s, rs, gone[s], set(window.order[-_BUG:])) for s, rs in sorted(by.items())}
    lines = [
        f"Bug balance from BUGS.jsonl: {len(records)} records "
        f"({len(live)} live, {len(archived)} archived).",
        *_table(
            [v for s, v in rows.items() if s not in dev], [v for s, v in rows.items() if s in dev]
        ),
        *_trend(records, window),
        "Defective-fix rate per rc (caused_by set over found in the rc):",
        *_rates(records),
    ]
    return "\n".join(lines) + "\n"


def stored(document: str) -> str | None:
    """The generated block's body under *document*'s `## Bugs`, None without one."""
    found = _BLOCK.search(document)
    return found["body"] if found else None


def replaced(document: str, body: str) -> str:
    """*document* with its `## Bugs` block set to *body*: in place, else right under an existing
    heading, else a section appended."""
    fenced = f"```text\n{body}```\n"
    if _BLOCK.search(document):
        return _BLOCK.sub(lambda m: m["head"] + body + m["tail"], document, count=1)
    if heading := _HEADING.search(document):
        rest = document[heading.end() :]
        gap = "" if rest[:1] in ("", "\n") else "\n"
        return f"{document[: heading.end()]}\n{fenced}{gap}{rest}"
    return f"{document.rstrip()}\n\n## Bugs\n\n{fenced}".lstrip()
