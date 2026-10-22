#!/usr/bin/env python3
"""The one UTC clock of the skill scripts, and the stamps it spells."""

from __future__ import annotations

import datetime as _dt


def instant() -> _dt.datetime:
    return _dt.datetime.now(tz=_dt.UTC)


def now_iso() -> str:
    return instant().strftime("%Y-%m-%dT%H:%M:%SZ")


def today() -> str:
    return now_iso()[:10]


def compact_day() -> str:
    return instant().strftime("%Y%m%d")


def compact_instant() -> str:
    return instant().strftime("%Y%m%dT%H%M%SZ")
