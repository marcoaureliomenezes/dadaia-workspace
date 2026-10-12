"""The package's door to the one UTC clock, ``dd-bug-resolution/scripts/_clock.py``."""

from __future__ import annotations

from collections.abc import Callable

from dadaia_workspace.core.skill_owner import load_owner

__all__ = ["now_iso", "today"]

_owner = load_owner("dd-bug-resolution", "_clock")
now_iso: Callable[[], str] = _owner.now_iso
today: Callable[[], str] = _owner.today
