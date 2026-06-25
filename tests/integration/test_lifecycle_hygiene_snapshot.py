"""Integration coverage for lifecycle hygiene snapshot payloads."""

from __future__ import annotations

import datetime as dt
import json
import os
from pathlib import Path

from dadaia_workspace.core.models.hygiene import HygieneSnapshot, HygieneZone
from dadaia_workspace.features.lifecycle.hygiene import LifecycleHygieneService

NOW = dt.datetime(2026, 6, 18, 12, 0, tzinfo=dt.UTC)


def _write(path: Path, *, age: dt.timedelta, content: str = "content") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    timestamp = (NOW - age).timestamp()
    os.utime(path, (timestamp, timestamp))
    return path


def test_hygiene_snapshot_json_schema_round_trips_with_candidates(
    tmp_path: Path,
) -> None:
    report_ref = ".dadaia/reports/dadaia-workspace/qa/old.html"
    _write(
        tmp_path / report_ref,
        age=dt.timedelta(hours=72),
        content="<html><body>old review</body></html>",
    )
    _write(
        tmp_path / ".dadaia" / "handoff" / "dadaia-workspace" / "qa-review.handoff.json",
        age=dt.timedelta(hours=72),
        content=json.dumps(
            {
                "context": "dadaia-workspace",
                "release_id": "v0.1.15",
                "run_id": "run-015",
                "agent": "qa-engineer",
                "verdict": "APPROVED",
                "artifact": {"path": report_ref},
            }
        ),
    )
    _write(
        tmp_path / ".dadaia" / "tmp" / "workflow" / "old.txt",
        age=dt.timedelta(hours=72),
    )

    service = LifecycleHygieneService(
        tmp_path,
        now=NOW,
        active_release_id="v0.1.15",
    )
    cleanup = service.cleanup(dry_run=True)
    snapshot = HygieneSnapshot(
        schema_version="hygiene-snapshot-v1",
        timestamp=NOW.isoformat().replace("+00:00", "Z"),
        context="dadaia-workspace",
        release_id="v0.1.15",
        run_id="run-015",
        policy=service.policy,
        counters=service.status(),
        candidates=cleanup.candidates,
    )

    payload = snapshot.to_dict()
    restored = HygieneSnapshot.from_dict(payload)

    assert set(payload) == {
        "schema_version",
        "timestamp",
        "context",
        "release_id",
        "run_id",
        "policy",
        "counters",
        "candidates",
    }
    assert payload["schema_version"] == "hygiene-snapshot-v1"
    assert payload["context"] == "dadaia-workspace"
    assert payload["release_id"] == "v0.1.15"
    assert payload["run_id"] == "run-015"
    assert payload["policy"] == service.policy.to_dict()
    assert payload["counters"]["zone_totals"] == {
        "reports": 1,
        "handoff": 1,
        "tmp": 1,
    }
    assert payload["counters"]["expired_totals"] == {
        "reports": 1,
        "handoff": 1,
        "tmp": 1,
    }
    assert payload["counters"]["cleanup_candidate_count"] == 3
    assert payload["counters"]["protected_residual_count"] == 2
    assert isinstance(payload["counters"]["scan_elapsed_ms"], int)
    assert payload["counters"]["scan_elapsed_ms"] >= 0
    assert len(payload["candidates"]) == 3
    assert any(candidate["protected"] is True for candidate in payload["candidates"])
    assert any(candidate["zone"] == HygieneZone.TMP.value for candidate in payload["candidates"])
    assert restored == snapshot
