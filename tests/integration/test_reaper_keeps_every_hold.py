"""Two reaps of one origin inside one frozen second leave two byte-intact holds.

Intent: CONTRACT — sa-reaper-destroys-its-own-hold-before-ttl#B1..#B3 (AC1.2, ADR 0074).
Size: MEDIUM (integration: the full ``DoctorService.fix`` lane over a tmp_path workspace).

Structural cause pinned: ``sweep.move`` removed the existing hold at its destination
before storing the new one, so the second same-day reap destroyed the first hold
before its 7-day TTL — a deletion outside the TTL lane.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from dadaia_workspace.features.spec_context import doctor
from dadaia_workspace.features.spec_context.doctor import DoctorService
from tests.fakes import FakeContextStore, FakeGitClient


class _FrozenClock(datetime):
    @classmethod
    def now(cls, tz: object = None) -> _FrozenClock:  # type: ignore[override]
        return cls(2026, 9, 27, 12, 0, 0, tzinfo=UTC)


def test_two_same_second_reaps_of_one_origin_leave_two_intact_holds(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(doctor, "datetime", _FrozenClock)
    for zone in ("tmp", "states", "sessions", "reaped"):
        (tmp_path / ".dadaia" / zone).mkdir(parents=True, exist_ok=True)
    stray = tmp_path / "stray"

    stray.mkdir()
    (stray / "SKILL.md").write_bytes(b"v1\n")
    (stray / "refs.md").write_bytes(b"refs\n")
    DoctorService(FakeContextStore(), FakeGitClient(), tmp_path).fix()

    stray.mkdir()
    (stray / "SKILL.md").write_bytes(b"v2\n")
    DoctorService(FakeContextStore(), FakeGitClient(), tmp_path).fix()

    day = tmp_path / ".dadaia" / "reaped" / "20260927"
    holds = sorted(day.iterdir())
    assert [h.name for h in holds] == ["stray", "stray-1"]
    assert (day / "stray" / "SKILL.md").read_bytes() == b"v1\n"
    assert (day / "stray" / "refs.md").read_bytes() == b"refs\n"
    assert (day / "stray-1" / "SKILL.md").read_bytes() == b"v2\n"
    assert not stray.exists()
