"""The package's door to the one UTC clock, ``dd-bug-resolution/scripts/_clock.py``."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from dadaia_workspace.core.skill_owner import load_owner

__all__ = ["compact_day", "compact_instant", "instant", "now_iso", "today"]

_owner = load_owner("dd-bug-resolution", "_clock")
now_iso: Callable[[], str] = _owner.now_iso
today: Callable[[], str] = _owner.today
compact_day: Callable[[], str] = _owner.compact_day
compact_instant: Callable[[], str] = _owner.compact_instant
instant: Callable[[], datetime] = _owner.instant
