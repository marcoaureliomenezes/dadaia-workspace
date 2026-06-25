"""Unit tests for filesystem runtime-file adapter path guarantees."""

import json
from pathlib import Path

import pytest

from dadaia_workspace.core.protocols.runtime_files import RuntimeFileKind, RuntimeFilePort
from dadaia_workspace.infrastructure.runtime_files import (
    FilesystemRuntimeFileAdapter,
    RuntimeFilePathError,
)


def test_runtime_file_adapter_satisfies_port() -> None:
    adapter = FilesystemRuntimeFileAdapter(workspace_root=Path("/tmp/ws"))

    assert isinstance(adapter, RuntimeFilePort)


def test_rejects_absolute_and_traversal_segments(tmp_path) -> None:  # type: ignore[no-untyped-def]
    adapter = FilesystemRuntimeFileAdapter(tmp_path)

    with pytest.raises(RuntimeFilePathError):
        adapter.write_tmp(
            workflow="workflow",
            date_slug="20260618",
            filename="../escape.txt",
            content="x",
            ttl_seconds=1,
        )

    with pytest.raises(RuntimeFilePathError):
        adapter.write_report(
            context="/absolute",
            agent="software-engineer",
            filename="report.html",
            html="<html></html>",
        )


def test_writes_handoff_as_canonical_json_with_hash(tmp_path) -> None:  # type: ignore[no-untyped-def]
    adapter = FilesystemRuntimeFileAdapter(tmp_path)
    ref = adapter.write_handoff(
        context="dadaia-workspace",
        filename="review.handoff.json",
        payload={
            "schema_version": "handoff-v1.1",
            "agent": "qa-engineer",
            "context": "dadaia-workspace",
            "produced_at": "2026-06-18T05:00:00Z",
            "artifact": {"type": "other"},
            "scope": "T-015-04",
            "metrics": {"tests": 5},
        },
    )

    assert ref.kind == RuntimeFileKind.HANDOFF
    assert ref.path == ".dadaia/handoff/dadaia-workspace/review.handoff.json"
    assert ref.content_hash is not None
    written = json.loads((tmp_path / ref.path).read_text(encoding="utf-8"))
    assert written["schema_version"] == "handoff-v1.1"


def test_rejects_malformed_artifact_names(tmp_path) -> None:  # type: ignore[no-untyped-def]
    adapter = FilesystemRuntimeFileAdapter(tmp_path)

    with pytest.raises(RuntimeFilePathError):
        adapter.write_report(
            context="dadaia-workspace",
            agent="software-engineer",
            filename="report.txt",
            html="<html></html>",
        )

    with pytest.raises(RuntimeFilePathError):
        adapter.write_handoff(
            context="dadaia-workspace",
            filename="review.json",
            payload={"schema_version": "handoff-v1.1"},
        )

    with pytest.raises(RuntimeFilePathError):
        adapter.write_handoff(
            context="dadaia-workspace",
            filename="review.handoff.json",
            payload={"agent": "qa-engineer"},
        )


def test_rejects_repo_root_destinations(tmp_path) -> None:  # type: ignore[no-untyped-def]
    repo_root = tmp_path / "repos" / "dadaia-workspace"
    repo_root.mkdir(parents=True)

    with pytest.raises(RuntimeFilePathError):
        FilesystemRuntimeFileAdapter(repo_root)


def test_allows_self_hosting_workspace_root_with_git_and_dadaia(tmp_path) -> None:  # type: ignore[no-untyped-def]
    (tmp_path / ".git").mkdir()
    (tmp_path / ".dadaia").mkdir()

    adapter = FilesystemRuntimeFileAdapter(tmp_path)

    ref = adapter.write_tmp(
        workflow="workflow",
        date_slug="20260618",
        filename="scratch.txt",
        content="tmp",
        ttl_seconds=86400,
    )
    assert ref.path == ".dadaia/tmp/workflow/20260618/scratch.txt"


def test_rejects_non_html_report_content(tmp_path) -> None:  # type: ignore[no-untyped-def]
    adapter = FilesystemRuntimeFileAdapter(tmp_path)

    with pytest.raises(RuntimeFilePathError):
        adapter.write_report(
            context="dadaia-workspace",
            agent="software-engineer",
            filename="report.html",
            html="plain text",
        )


def test_rejects_handoff_context_mismatch(tmp_path) -> None:  # type: ignore[no-untyped-def]
    adapter = FilesystemRuntimeFileAdapter(tmp_path)
    payload: dict[str, object] = {
        "schema_version": "handoff-v1.1",
        "agent": "qa-engineer",
        "context": "other-context",
        "produced_at": "2026-06-18T05:00:00Z",
        "artifact": {"type": "other"},
        "scope": "T-015-04",
        "metrics": {},
    }

    with pytest.raises(RuntimeFilePathError):
        adapter.write_handoff(
            context="dadaia-workspace",
            filename="review.handoff.json",
            payload=payload,
        )


def test_rejects_handoff_artifact_refs_outside_runtime_zones(tmp_path) -> None:  # type: ignore[no-untyped-def]
    adapter = FilesystemRuntimeFileAdapter(tmp_path)
    base_payload: dict[str, object] = {
        "schema_version": "handoff-v1.1",
        "agent": "qa-engineer",
        "context": "dadaia-workspace",
        "produced_at": "2026-06-18T05:00:00Z",
        "scope": "T-015-04",
        "metrics": {},
    }

    for artifact_path in (
        "/tmp/report.html",
        "../report.html",
        "repos/dadaia-workspace/report.html",
        ".dadaia/handoff/dadaia-workspace/review.handoff.json",
    ):
        with pytest.raises(RuntimeFilePathError):
            adapter.write_handoff(
                context="dadaia-workspace",
                filename="review.handoff.json",
                payload={
                    **base_payload,
                    "artifact": {
                        "type": "report",
                        "path": artifact_path,
                        "content_hash": "0" * 64,
                    },
                },
            )


def test_rejects_handoff_artifact_hash_mismatch(tmp_path) -> None:  # type: ignore[no-untyped-def]
    adapter = FilesystemRuntimeFileAdapter(tmp_path)
    report = adapter.write_report(
        context="dadaia-workspace",
        agent="software-engineer",
        filename="report.html",
        html="<html></html>",
    )

    with pytest.raises(RuntimeFilePathError):
        adapter.write_handoff(
            context="dadaia-workspace",
            filename="review.handoff.json",
            payload={
                "schema_version": "handoff-v1.1",
                "agent": "qa-engineer",
                "context": "dadaia-workspace",
                "produced_at": "2026-06-18T05:00:00Z",
                "artifact": {"type": "report", "path": report.path, "content_hash": "0" * 64},
                "scope": "T-015-04",
                "metrics": {},
            },
        )
