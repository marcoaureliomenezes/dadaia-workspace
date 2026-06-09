"""Spec-context doctor audit log invariant tests (LOCK-4, LOCK-5).

Lock-3 (per-release implementation lock) reclaim/heartbeat tests were removed
in v0.1.6 — replaced by ``test_doctor_gc.py`` and ``test_lock_steal.py``.

Acceptance criteria covered here:
    - LOCK-4: production-write audit event missing task_id is reported (NOT fixed).
    - LOCK-5: BLOCKED_ATTEMPT audit event surfaces as a signal (NOT fixed).
"""

from __future__ import annotations

# Guard: skip this entire module on platforms where fcntl is not available (e.g. Windows).
import pytest

pytest.importorskip("fcntl")

import json  # noqa: E402
import os  # noqa: E402
from datetime import UTC, datetime  # noqa: E402
from pathlib import Path  # noqa: E402

from dadaia_workspace.features.spec_context.doctor import DoctorService  # noqa: E402
from dadaia_workspace.features.spec_context.locking import (  # noqa: E402
    _audit_log_path,
    audit_blocked,
)
from tests.fakes import FakeContextStore, FakeGitClient  # noqa: E402

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_doctor(
    ws: Path,
    store: FakeContextStore | None = None,
) -> DoctorService:
    if store is None:
        store = FakeContextStore()
    return DoctorService(
        context_store=store,
        git_client=FakeGitClient(),
        workspace_root=ws,
    )


# ---------------------------------------------------------------------------
# LOCK-4: production-write event missing task_id — reported, not fixed
# ---------------------------------------------------------------------------


def test_lock4_production_write_missing_task_id_reported(tmp_path: Path) -> None:
    """LOCK-4: a PRODUCTION_WRITE event without task_id is reported; not fixed."""
    ws = tmp_path
    audit_path = _audit_log_path(ws)
    audit_path.parent.mkdir(parents=True, exist_ok=True)

    record_with_task = json.dumps(
        {
            "ts": datetime.now(tz=UTC).isoformat(),
            "event": "PRODUCTION_WRITE",
            "context": "proj",
            "release": "v1",
            "session_id": "sess_ok",
            "runtime": "test",
            "pid": os.getpid(),
            "task_id": "T-12",
        }
    )
    record_missing_task = json.dumps(
        {
            "ts": datetime.now(tz=UTC).isoformat(),
            "event": "PRODUCTION_WRITE",
            "context": "proj",
            "release": "v1",
            "session_id": "sess_bad",
            "runtime": "test",
            "pid": os.getpid(),
            # task_id deliberately absent
        }
    )

    audit_path.write_text(record_with_task + "\n" + record_missing_task + "\n")

    doctor = _make_doctor(ws)
    issues = doctor.check()

    lock4_issues = [i for i in issues if i.code == "LOCK-4"]
    assert len(lock4_issues) == 1, f"Expected 1 LOCK-4 issue, got: {lock4_issues}"
    assert "sess_bad" in lock4_issues[0].description
    assert lock4_issues[0].fixable is False

    # fix() must NOT remove the event
    doctor.fix()
    lines = [ln for ln in audit_path.read_text().splitlines() if ln.strip()]
    assert len(lines) == 2, "fix() must not delete audit log entries for LOCK-4"


# ---------------------------------------------------------------------------
# LOCK-5: BLOCKED_ATTEMPT event surfaces as signal
# ---------------------------------------------------------------------------


def test_lock5_blocked_attempt_surfaces_as_signal(tmp_path: Path) -> None:
    """LOCK-5: BLOCKED_ATTEMPT in audit log is surfaced; not fixed."""
    ws = tmp_path
    audit_path = _audit_log_path(ws)
    audit_path.parent.mkdir(parents=True, exist_ok=True)

    audit_blocked(
        ws,
        context="proj",
        release="v1",
        session_id="sess_blocked",
        runtime="test",
        pid=os.getpid(),
        reason="lock already held",
    )

    doctor = _make_doctor(ws)
    issues = doctor.check()

    lock5_issues = [i for i in issues if i.code == "LOCK-5"]
    assert len(lock5_issues) == 1, f"Expected 1 LOCK-5 issue, got: {lock5_issues}"
    assert lock5_issues[0].fixable is False
    assert "sess_blocked" in lock5_issues[0].description

    # fix() must NOT delete the audit event
    doctor.fix()
    lines = [ln for ln in audit_path.read_text().splitlines() if ln.strip()]
    assert len(lines) >= 1, "fix() must not delete audit log entries for LOCK-5"
