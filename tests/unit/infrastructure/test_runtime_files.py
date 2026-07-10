"""Unit tests for filesystem runtime-file adapter path guarantees."""

import json
from pathlib import Path

import pytest

from dadaia_workspace.core.protocols.runtime_files import RuntimeFileKind
from dadaia_workspace.infrastructure.runtime_files import (
    FilesystemRuntimeFileAdapter,
    RuntimeFilePathError,
)


def test_writes_handoff_as_canonical_json_with_hash_and_rejects_hash_mismatch(
    tmp_path,
) -> None:  # type: ignore[no-untyped-def]
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

    report = adapter.write_report(
        context="dadaia-workspace",
        agent="software-engineer",
        filename="report.html",
        html="<html></html>",
    )
    with pytest.raises(RuntimeFilePathError):
        adapter.write_handoff(
            context="dadaia-workspace",
            filename="review2.handoff.json",
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


def test_rejects_handoff_artifact_refs_outside_runtime_zones(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """Handoff integrity feeds the pre-push security-verdict chokepoint — keep the
    full hostile-artifact-path param list verbatim."""
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


@pytest.mark.parametrize(
    "case",
    [
        "rejects-tmp-traversal-segment",
        "rejects-absolute-context",
        "rejects-malformed-report-suffix",
        "rejects-malformed-handoff-suffix",
        "rejects-handoff-missing-schema-version",
        "rejects-repo-root-destination",
        "allows-self-hosting-workspace-root",
        "rejects-non-html-report-content",
        "rejects-handoff-context-mismatch",
    ],
)
def test_path_rejection_and_self_hosting_matrix(tmp_path: Path, case: str) -> None:
    """One shared parametrized sweep over the path-safety contract: absolute /
    traversal segments, malformed artifact names, non-HTML report content,
    handoff context mismatch, a repo-root destination refusal, and the
    self-hosting workspace-root allow-case (has both .git and .dadaia)."""
    if case == "rejects-tmp-traversal-segment":
        adapter = FilesystemRuntimeFileAdapter(tmp_path)
        with pytest.raises(RuntimeFilePathError):
            adapter.write_tmp(
                workflow="workflow",
                date_slug="20260618",
                filename="../escape.txt",
                content="x",
                ttl_seconds=1,
            )

    elif case == "rejects-absolute-context":
        adapter = FilesystemRuntimeFileAdapter(tmp_path)
        with pytest.raises(RuntimeFilePathError):
            adapter.write_report(
                context="/absolute",
                agent="software-engineer",
                filename="report.html",
                html="<html></html>",
            )

    elif case == "rejects-malformed-report-suffix":
        adapter = FilesystemRuntimeFileAdapter(tmp_path)
        with pytest.raises(RuntimeFilePathError):
            adapter.write_report(
                context="dadaia-workspace",
                agent="software-engineer",
                filename="report.txt",
                html="<html></html>",
            )

    elif case == "rejects-malformed-handoff-suffix":
        adapter = FilesystemRuntimeFileAdapter(tmp_path)
        with pytest.raises(RuntimeFilePathError):
            adapter.write_handoff(
                context="dadaia-workspace",
                filename="review.json",
                payload={"schema_version": "handoff-v1.1"},
            )

    elif case == "rejects-handoff-missing-schema-version":
        adapter = FilesystemRuntimeFileAdapter(tmp_path)
        with pytest.raises(RuntimeFilePathError):
            adapter.write_handoff(
                context="dadaia-workspace",
                filename="review.handoff.json",
                payload={"agent": "qa-engineer"},
            )

    elif case == "rejects-repo-root-destination":
        repo_root = tmp_path / "repos" / "dadaia-workspace"
        repo_root.mkdir(parents=True)
        with pytest.raises(RuntimeFilePathError):
            FilesystemRuntimeFileAdapter(repo_root)

    elif case == "allows-self-hosting-workspace-root":
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

    elif case == "rejects-non-html-report-content":
        adapter = FilesystemRuntimeFileAdapter(tmp_path)
        with pytest.raises(RuntimeFilePathError):
            adapter.write_report(
                context="dadaia-workspace",
                agent="software-engineer",
                filename="report.html",
                html="plain text",
            )

    else:  # rejects-handoff-context-mismatch
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
