"""Integration tests for canonical filesystem runtime-file writes."""

import json

from dadaia_workspace.core.models.hygiene import HygieneCounters, HygieneSnapshot, SlopPolicy
from dadaia_workspace.core.protocols.runtime_files import RuntimeFileKind
from dadaia_workspace.infrastructure.runtime_files import FilesystemRuntimeFileAdapter


def test_runtime_file_adapter_writes_only_canonical_dadaia_paths(tmp_path) -> None:  # type: ignore[no-untyped-def]
    adapter = FilesystemRuntimeFileAdapter(tmp_path)

    report = adapter.write_report(
        context="dadaia-workspace",
        agent="software-engineer",
        filename="report.html",
        html="<html></html>",
    )
    handoff = adapter.write_handoff(
        context="dadaia-workspace",
        filename="review.handoff.json",
        payload={
            "schema_version": "handoff-v1.1",
            "agent": "qa-engineer",
            "context": "dadaia-workspace",
            "produced_at": "2026-06-18T05:00:00Z",
            "artifact": {
                "type": "report",
                "path": report.path,
                "content_hash": report.content_hash,
            },
            "scope": "T-015-04",
            "metrics": {"tests": 5},
        },
    )
    tmp = adapter.write_tmp(
        workflow="lifecycle-report",
        date_slug="20260618",
        filename="scratch.txt",
        content="scratch",
        ttl_seconds=86400,
    )
    run = adapter.write_run_artifact(
        run_id="run-1",
        filename="preflight.json",
        content='{"status":"blocked"}',
    )
    snapshot = adapter.write_hygiene_snapshot(
        HygieneSnapshot(
            schema_version="hygiene-snapshot-v1",
            timestamp="2026-06-18T05:00:00Z",
            context="dadaia-workspace",
            release_id="v0.1.15",
            run_id="run-1",
            policy=SlopPolicy(),
            counters=HygieneCounters(cleanup_candidate_count=1),
        )
    )

    refs = (report, handoff, tmp, run, snapshot)
    assert all(ref.path.startswith(".dadaia/") for ref in refs)
    assert all((tmp_path / ref.path).is_file() for ref in refs)
    assert not (tmp_path / "repos").exists()
    assert tmp.kind == RuntimeFileKind.TMP
    assert tmp.ttl_seconds == 86400

    snapshot_data = json.loads((tmp_path / snapshot.path).read_text(encoding="utf-8"))
    assert snapshot_data["policy"]["reports_ttl_seconds"] == 172800
    assert snapshot_data["counters"]["cleanup_candidate_count"] == 1
