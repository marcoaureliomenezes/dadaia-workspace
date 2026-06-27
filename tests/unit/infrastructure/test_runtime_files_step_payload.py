"""Unit tests for the immutable workflow-step payload writer (v0.1.30 / T-30-D-04).

Pins A18's storage half: ``write_step_payload`` writes under the WORKSPACE-ROOT
``.dadaia/runs/lifecycle/<run_id>/steps/`` canonical zone, is immutable (re-write of an
existing key raises), returns a content hash, and never escapes the run zone via a
run-id-derived path. ``read_step_payload`` confines reads to the same zone.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.core.protocols.runtime_files import RuntimeFilePort, StepPayloadRef
from dadaia_workspace.infrastructure.runtime_files import (
    FilesystemRuntimeFileAdapter,
    RuntimeFilePathError,
)


def test_adapter_still_satisfies_runtime_file_port() -> None:
    adapter = FilesystemRuntimeFileAdapter(workspace_root=Path("/tmp/ws"))
    assert isinstance(adapter, RuntimeFilePort)


def test_write_step_payload_lands_under_workspace_root_runs_zone(tmp_path: Path) -> None:
    adapter = FilesystemRuntimeFileAdapter(tmp_path)
    ref = adapter.write_step_payload(
        run_id="run-1",
        producer_step="release_scope",
        attempt=0,
        content='{"k": 1}\n',
    )
    assert isinstance(ref, StepPayloadRef)
    assert ref.payload_ref == (
        ".dadaia/runs/lifecycle/run-1/steps/release_scope-attempt-0.step-payload.json"
    )
    # The file lands at the WORKSPACE-ROOT .dadaia, never a repo-relative one.
    written = tmp_path / ref.payload_ref
    assert written.is_file()
    assert written.read_text(encoding="utf-8") == '{"k": 1}\n'
    assert len(ref.content_hash) == 64


def test_write_step_payload_is_immutable(tmp_path: Path) -> None:
    adapter = FilesystemRuntimeFileAdapter(tmp_path)
    adapter.write_step_payload(run_id="run-1", producer_step="qa", attempt=1, content='{"a": 1}\n')
    with pytest.raises(RuntimeFilePathError):
        adapter.write_step_payload(
            run_id="run-1", producer_step="qa", attempt=1, content='{"a": 2}\n'
        )


def test_write_step_payload_distinguishes_attempts(tmp_path: Path) -> None:
    adapter = FilesystemRuntimeFileAdapter(tmp_path)
    a0 = adapter.write_step_payload(run_id="r", producer_step="qa", attempt=0, content="0")
    a1 = adapter.write_step_payload(run_id="r", producer_step="qa", attempt=1, content="1")
    assert a0.payload_ref != a1.payload_ref
    assert "attempt-0" in a0.payload_ref
    assert "attempt-1" in a1.payload_ref


def test_write_step_payload_rejects_negative_attempt(tmp_path: Path) -> None:
    adapter = FilesystemRuntimeFileAdapter(tmp_path)
    with pytest.raises(RuntimeFilePathError):
        adapter.write_step_payload(run_id="r", producer_step="qa", attempt=-1, content="x")


def test_write_step_payload_rejects_traversal_in_run_id(tmp_path: Path) -> None:
    adapter = FilesystemRuntimeFileAdapter(tmp_path)
    with pytest.raises(RuntimeFilePathError):
        adapter.write_step_payload(run_id="../escape", producer_step="qa", attempt=0, content="x")


def test_write_step_payload_rejects_traversal_in_producer_step(tmp_path: Path) -> None:
    adapter = FilesystemRuntimeFileAdapter(tmp_path)
    with pytest.raises(RuntimeFilePathError):
        adapter.write_step_payload(
            run_id="run-1", producer_step="../../etc/passwd", attempt=0, content="x"
        )


def test_read_step_payload_round_trips(tmp_path: Path) -> None:
    adapter = FilesystemRuntimeFileAdapter(tmp_path)
    ref = adapter.write_step_payload(
        run_id="run-1", producer_step="qa", attempt=0, content='{"x": 1}\n'
    )
    assert adapter.read_step_payload(ref.payload_ref) == '{"x": 1}\n'


def test_read_step_payload_missing_returns_none(tmp_path: Path) -> None:
    adapter = FilesystemRuntimeFileAdapter(tmp_path)
    assert (
        adapter.read_step_payload(".dadaia/runs/lifecycle/run-1/steps/ghost.step-payload.json")
        is None
    )


def test_read_step_payload_outside_zone_returns_none(tmp_path: Path) -> None:
    adapter = FilesystemRuntimeFileAdapter(tmp_path)
    (tmp_path / ".dadaia" / "handoff").mkdir(parents=True, exist_ok=True)
    sneaky = tmp_path / ".dadaia" / "handoff" / "x.json"
    sneaky.write_text("secret", encoding="utf-8")
    assert adapter.read_step_payload(".dadaia/handoff/x.json") is None
    assert adapter.read_step_payload("/etc/passwd") is None
    assert adapter.read_step_payload("../../../etc/passwd") is None
