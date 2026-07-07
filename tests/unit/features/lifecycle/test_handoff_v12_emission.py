"""T-62-20 / FR3+ADR-5 — Layer-2 emitters at handoff-v1.2 with honest v1.1 fallback.

The two lifecycle emitters (``LifecyclePreflightService.blocked_push_preflight`` and
``LifecycleReportWorkflow.run``) must emit ``handoff-v1.2`` with ``self_pull.refs``
populated from the run's recorded ``InjectedContext`` refs (deduplicated, order kept).
When zero refs are available the role→atom map is the fallback; when THAT is also
empty the emitter falls back to an HONEST ``handoff-v1.1`` (ADR-5 — the only
sanctioned v1.1 emission; never a v1.2 with empty or fabricated refs).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.core.protocols.runtime_files import RuntimeFileKind, RuntimeFileRef
from dadaia_workspace.features.lifecycle.service import (
    LifecyclePreflightService,
    resolve_emitted_handoff_version,
)


class _FakeRuntimeFiles:
    """Capture the handoff payload the service emits (no real filesystem writes)."""

    def __init__(self) -> None:
        self.payload: dict[str, object] | None = None

    def write_handoff(
        self, *, context: str, filename: str, payload: dict[str, object]
    ) -> RuntimeFileRef:
        self.payload = payload
        return RuntimeFileRef(
            kind=RuntimeFileKind.HANDOFF,
            path=f".dadaia/handoff/{context}/{filename}",
            content_hash="0" * 64,
        )


def _emit_blocked_push(
    runtime_files: _FakeRuntimeFiles,
    *,
    injected_refs: tuple[str, ...] = (),
    specs_dir: Path | None = None,
) -> dict[str, object]:
    LifecyclePreflightService().blocked_push_preflight(
        context="dadaia-workspace",
        release_id="v0.1.62",
        commit_sha="abc123",
        runtime_files=runtime_files,
        run_id="run-1",
        injected_refs=injected_refs,
        specs_dir=specs_dir,
    )
    assert runtime_files.payload is not None
    return runtime_files.payload


def test_blocked_push_emits_v12_with_deduped_injected_refs() -> None:
    """RED-first anchor: v1.2 + self_pull from InjectedContext refs, deduplicated."""
    payload = _emit_blocked_push(
        _FakeRuntimeFiles(),
        injected_refs=(
            "specs/memory/architecture.md",
            "specs/memory/quality-assurance.md",
            "specs/memory/architecture.md",
        ),
    )
    assert payload["schema_version"] == "handoff-v1.2"
    assert payload["self_pull"] == {
        "refs": [
            "specs/memory/architecture.md",
            "specs/memory/quality-assurance.md",
        ]
    }


def test_blocked_push_zero_refs_falls_back_to_honest_v11() -> None:
    """ADR-5: agent 'lifecycle' is unmapped — zero refs must yield honest v1.1."""
    payload = _emit_blocked_push(_FakeRuntimeFiles())
    assert payload["schema_version"] == "handoff-v1.1"
    assert "self_pull" not in payload


def test_resolver_role_map_fallback_requires_existing_atom(tmp_path: Path) -> None:
    """Zero injected refs + mapped role + atom on disk → v1.2 via the role map."""
    specs_dir = tmp_path / "specs"
    (specs_dir / "memory").mkdir(parents=True)
    (specs_dir / "memory" / "architecture.md").write_text("# arch", encoding="utf-8")
    version, self_pull = resolve_emitted_handoff_version(
        agent="software-architect", injected_refs=(), specs_dir=specs_dir
    )
    assert version == "handoff-v1.2"
    assert self_pull == {"refs": ["specs/memory/architecture.md"]}


def test_resolver_role_map_fallback_missing_atom_is_honest_v11(tmp_path: Path) -> None:
    """Mapped role but atom absent on disk → never fabricate; honest v1.1."""
    version, self_pull = resolve_emitted_handoff_version(
        agent="software-architect", injected_refs=(), specs_dir=tmp_path
    )
    assert version == "handoff-v1.1"
    assert self_pull is None


def test_resolver_unmapped_agent_no_specs_dir_is_honest_v11() -> None:
    version, self_pull = resolve_emitted_handoff_version(
        agent="lifecycle", injected_refs=(), specs_dir=None
    )
    assert version == "handoff-v1.1"
    assert self_pull is None


def test_resolver_never_emits_v12_with_empty_refs() -> None:
    """Empty/blank injected refs never produce a fabricated v1.2 self_pull."""
    version, self_pull = resolve_emitted_handoff_version(
        agent="lifecycle", injected_refs=("", "  "), specs_dir=None
    )
    assert version == "handoff-v1.1"
    assert self_pull is None


@pytest.mark.parametrize("token", ["handoff-v1", "handoff-v1.1", "handoff-v1.2"])
def test_gates_accept_set_widened(token: str) -> None:
    """FR3 accept-set widening: gates accept {v1, v1.1, v1.2}."""
    from dadaia_workspace.features.lifecycle.gates import HandoffGateValidator

    reasons: list[str] = []
    HandoffGateValidator()._schema_version({"schema_version": token}, reasons)
    assert reasons == []


def test_gates_reject_unknown_token() -> None:
    from dadaia_workspace.features.lifecycle.gates import HandoffGateValidator

    reasons: list[str] = []
    HandoffGateValidator()._schema_version({"schema_version": "handoff-v1.3"}, reasons)
    assert reasons == ["malformed schema_version"]
