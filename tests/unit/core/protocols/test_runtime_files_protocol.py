"""Unit tests for the runtime file protocol contract.

Slimmed to a conformance-only assert: mypy checks structural typing (Protocol), but does
not register ``isinstance`` — this is the only runtime-checkable conformance coverage for
RuntimeFilePort, so it is kept even though it is otherwise a thin structural check. One
write per kind proves every protocol method is present and callable; per-ref field-echo
assertions (mock-echo of the fake's own return values) are dropped.
"""

from dadaia_workspace.core.models.hygiene import HygieneCounters, HygieneSnapshot, SlopPolicy
from dadaia_workspace.core.protocols.runtime_files import (
    RuntimeFileKind,
    RuntimeFilePort,
    RuntimeFileRef,
    StepPayloadRef,
)


class FakeRuntimeFiles:
    def __init__(self) -> None:
        self.writes: list[RuntimeFileRef] = []
        self.step_payloads: dict[str, str] = {}

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

    def write_step_payload(
        self,
        *,
        run_id: str,
        producer_step: str,
        attempt: int,
        content: str,
    ) -> StepPayloadRef:
        ref = StepPayloadRef(
            payload_ref=(
                f".dadaia/runs/lifecycle/{run_id}/steps/"
                f"{producer_step}-attempt-{attempt}.step-payload.json"
            ),
            content_hash=str(len(content)),
        )
        self.step_payloads[ref.payload_ref] = content
        return ref

    def read_step_payload(self, payload_ref: str) -> str | None:
        return self.step_payloads.get(payload_ref)


def test_fake_runtime_files_satisfies_runtime_file_port_one_write_per_kind() -> None:
    files = FakeRuntimeFiles()

    assert isinstance(files, RuntimeFilePort)

    files.write_report(
        context="dadaia-workspace",
        agent="software-engineer",
        filename="report.html",
        html="<html></html>",
    )
    files.write_handoff(
        context="dadaia-workspace",
        filename="review.handoff.json",
        payload={"schema_version": "handoff-v1.1"},
    )
    files.write_tmp(
        workflow="lifecycle-report",
        date_slug="20260618",
        filename="scratch.txt",
        content="tmp",
        ttl_seconds=86400,
    )
    files.write_run_artifact(run_id="run-1", filename="preflight.json", content="{}")
    files.write_hygiene_snapshot(
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
    files.write_step_payload(run_id="run-1", producer_step="s1", attempt=1, content="{}")

    assert len(files.writes) == 5
