"""T-016-07: TOCTOU interleave test (sequential, no real threads).

Proves the O_EXCL sentinel CAS closes the read→stale-check→write window: while the
first acquirer holds the sentinel, a concurrent ``open(sentinel, 'x')`` fails, so
exactly one record is written per ``acquire()`` and no double-acquire occurs.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.features.spec_context import lease


def test_concurrent_cas_fails_exactly_one_record(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ctx = "toctou"
    sentinel = lease._sentinel_path(tmp_path, ctx)
    fired: dict[str, bool] = {}

    def before() -> None:
        # First acquirer holds the sentinel here. A concurrent acquirer's CAS must fail.
        with pytest.raises(FileExistsError), open(sentinel, "x", encoding="utf-8"):
            pass
        fired["ok"] = True

    monkeypatch.setattr(lease, "_before_write", before)
    status, rec = lease.acquire(tmp_path, ctx, "sessA", "v1", "IMPLEMENTATION")

    assert fired.get("ok") is True, "_before_write must have observed the held sentinel"
    assert status == "ACQUIRED"
    assert rec["session_id"] == "sessA"
    # Exactly one record; sentinel released after the critical section.
    assert lease.read_record(tmp_path, ctx)["session_id"] == "sessA"
    assert not sentinel.exists()

    # Retry path: the same session re-acquiring renews (still exactly one record).
    monkeypatch.setattr(lease, "_before_write", None)
    status2, _ = lease.acquire(tmp_path, ctx, "sessA", "v1", "IMPLEMENTATION")
    assert status2 == "RENEWED"

    # D1 soul-fold: a different session without a matching .ptr sees a live foreign
    # lease and is blocked with yield-iff-live-foreign (FR-P1-15). The record stays
    # owned by sessA; the sentinel is released even on the LockHeldError path.
    from dadaia_workspace.core.exceptions import LockHeldError

    with pytest.raises(LockHeldError) as exc_info:
        lease.acquire(tmp_path, ctx, "sessB", "v1", "IMPLEMENTATION")
    assert "dadaia lock steal" in str(exc_info.value) or "actively mutating" in str(
        exc_info.value
    ), "Yield message must be informative (mention lock steal or 'actively mutating')"
    assert lease.read_record(tmp_path, ctx)["session_id"] == "sessA"  # record unchanged
    assert not sentinel.exists()  # sentinel always cleaned up
