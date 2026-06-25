"""Unit tests for the runtime file protocol contract."""

from dadaia_workspace.core.models.hygiene import HygieneCounters, HygieneSnapshot, SlopPolicy
from dadaia_workspace.core.protocols.runtime_files import (
    RuntimeFileKind,
    RuntimeFilePort,
    RuntimeFileRef,
)


class FakeRuntimeFiles:
    def __init__(self) -> None:
        self.writes: list[RuntimeFileRef] = []

    def write_report(
        self,
        *,
        context: str,
        agent: str,
        filename: str,
        html: str,
    ) -> RuntimeFileRef:
        ref = RuntimeFileRef(
            kind=RuntimeFileKind.REPORT,
            path=f".dadaia/reports/{context}/{agent}/{filename}",
            content_hash=str(len(html)),
        )
        self.writes.append(ref)
        return ref

    def write_handoff(
        self,
        *,
        context: str,
        filename: str,
        payload: dict[str, object],
    ) -> RuntimeFileRef:
        ref = RuntimeFileRef(
            kind=RuntimeFileKind.HANDOFF,
            path=f".dadaia/handoff/{context}/{filename}",
            content_hash=str(len(payload)),
        )
        self.writes.append(ref)
        return ref

    def write_tmp(
        self,
        *,
        workflow: str,
        date_slug: str,
        filename: str,
        content: str,
        ttl_seconds: int,
    ) -> RuntimeFileRef:
        ref = RuntimeFileRef(
            kind=RuntimeFileKind.TMP,
            path=f".dadaia/tmp/{workflow}/{date_slug}/{filename}",
            content_hash=str(len(content)),
            ttl_seconds=ttl_seconds,
        )
        self.writes.append(ref)
        return ref

    def write_run_artifact(
        self,
        *,
        run_id: str,
        filename: str,
        content: str,
    ) -> RuntimeFileRef:
        ref = RuntimeFileRef(
            kind=RuntimeFileKind.RUN_ARTIFACT,
            path=f".dadaia/runs/lifecycle/{run_id}/{filename}",
            content_hash=str(len(content)),
        )
        self.writes.append(ref)
        return ref

    def write_hygiene_snapshot(self, snapshot: HygieneSnapshot) -> RuntimeFileRef:
        ref = RuntimeFileRef(
            kind=RuntimeFileKind.HYGIENE_SNAPSHOT,
            path=f".dadaia/runs/lifecycle/{snapshot.run_id}/hygiene-snapshot.json",
            content_hash=snapshot.schema_version,
        )
        self.writes.append(ref)
        return ref


def test_fake_runtime_files_satisfies_runtime_file_port() -> None:
    files = FakeRuntimeFiles()

    assert isinstance(files, RuntimeFilePort)

    report = files.write_report(
        context="dadaia-workspace",
        agent="software-engineer",
        filename="report.html",
        html="<html></html>",
    )
    handoff = files.write_handoff(
        context="dadaia-workspace",
        filename="review.handoff.json",
        payload={"schema_version": "handoff-v1.1"},
    )
    tmp = files.write_tmp(
        workflow="lifecycle-report",
        date_slug="20260618",
        filename="scratch.txt",
        content="tmp",
        ttl_seconds=86400,
    )
    run_artifact = files.write_run_artifact(
        run_id="run-1",
        filename="preflight.json",
        content="{}",
    )
    snapshot = files.write_hygiene_snapshot(
        HygieneSnapshot(
            schema_version="hygiene-snapshot-v1",
            timestamp="2026-06-18T04:45:00Z",
            context="dadaia-workspace",
            release_id="v0.1.15",
            run_id="run-1",
            policy=SlopPolicy(),
            counters=HygieneCounters(),
        )
    )

    assert report.kind == RuntimeFileKind.REPORT
    assert handoff.path == ".dadaia/handoff/dadaia-workspace/review.handoff.json"
    assert tmp.ttl_seconds == 86400
    assert run_artifact.path == ".dadaia/runs/lifecycle/run-1/preflight.json"
    assert snapshot.kind == RuntimeFileKind.HYGIENE_SNAPSHOT
    assert len(files.writes) == 5
