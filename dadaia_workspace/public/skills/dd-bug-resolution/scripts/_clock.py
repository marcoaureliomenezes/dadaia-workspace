#!/usr/bin/env python3
"""The one UTC clock of the skill scripts."""

from __future__ import annotations

import datetime as _dt


def now_iso() -> str:
    return _dt.datetime.now(tz=_dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def today() -> str:
    return now_iso()[:10]
