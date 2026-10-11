"""core.clock is the package's view of the kernel's one UTC clock (AC11.4)."""

import datetime as dt
import importlib
import re
from types import ModuleType, SimpleNamespace

import pytest

from dadaia_workspace.core.skill_owner import load_owner


def _clock() -> ModuleType:
    # by name: the shim is created by J9.T5, so this file collects (and fails) before it exists
    return importlib.import_module("dadaia_workspace.core.clock")


class _Frozen(dt.datetime):
    @classmethod
    def now(cls, tz: dt.tzinfo | None = None) -> "_Frozen":
        return cls(2026, 10, 11, 3, 4, 5, tzinfo=tz)


@pytest.fixture
def frozen(monkeypatch: pytest.MonkeyPatch) -> None:
    owner = load_owner("dd-bug-resolution", "_clock")
    monkeypatch.setattr(owner, "_dt", SimpleNamespace(datetime=_Frozen, UTC=dt.UTC))


def test_now_iso_is_a_second_precision_utc_instant() -> None:
    assert re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ", _clock().now_iso())


def test_now_iso_and_today_follow_the_kernel_clock(frozen: None) -> None:
    kernel = load_owner("dd-bug-resolution", "_clock")
    assert kernel.now_iso() == "2026-10-11T03:04:05Z"
    assert _clock().now_iso() == "2026-10-11T03:04:05Z"
    assert _clock().today() == "2026-10-11"
