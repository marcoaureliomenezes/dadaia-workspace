"""T-62-20 / FR3+ADR-5 — Layer-2 emitters at handoff-v1.2 with honest v1.1 fallback.

The two lifecycle emitters (``LifecyclePreflightService.blocked_push_preflight`` and
``LifecycleReportWorkflow.run``) must emit ``handoff-v1.2`` with ``self_pull.refs``
populated from the run's recorded ``InjectedContext`` refs (deduplicated, order kept).
When zero refs are available the role→atom map is the fallback; when THAT is also
empty the emitter falls back to an HONEST ``handoff-v1.1`` (ADR-5 — the only
sanctioned v1.1 emission; never a v1.2 with empty or fabricated refs). ADR-5
never-fabricate-self_pull must survive as named cases.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.core.protocols.runtime_files import RuntimeFileKind, RuntimeFileRef
from dadaia_workspace.features.lifecycle.gates import HandoffGateValidator
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


# --- ① honest-v1.1 fallback matrix: zero-refs / role-map-atom-present / atom-absent / -----
#     unmapped / blank-refs-never-fabricated


def test_honest_v11_fallback_matrix(tmp_path: Path) -> None:
    # zero-refs (unmapped agent 'lifecycle' via the service) -> honest v1.1, no self_pull.
    payload = _emit_blocked_push(_FakeRuntimeFiles())
    assert payload["schema_version"] == "handoff-v1.1"
    assert "self_pull" not in payload

    # role-map-atom-present: mapped role + atom on disk -> v1.2 via the role map.
    specs_dir = tmp_path / "specs"
    (specs_dir / "memory").mkdir(parents=True)
    (specs_dir / "memory" / "architecture.md").write_text("# arch", encoding="utf-8")
    version, self_pull = resolve_emitted_handoff_version(
        agent="software-architect", injected_refs=(), specs_dir=specs_dir
    )
    assert version == "handoff-v1.2"
    assert self_pull == {"refs": ["specs/memory/architecture.md"]}

    # atom-absent: mapped role but atom absent on disk -> never fabricate; honest v1.1.
    missing_version, missing_self_pull = resolve_emitted_handoff_version(
        agent="software-architect", injected_refs=(), specs_dir=tmp_path
    )
    assert missing_version == "handoff-v1.1"
    assert missing_self_pull is None

    # unmapped agent, no specs_dir -> honest v1.1.
    unmapped_version, unmapped_self_pull = resolve_emitted_handoff_version(
        agent="lifecycle", injected_refs=(), specs_dir=None
    )
    assert unmapped_version == "handoff-v1.1"
    assert unmapped_self_pull is None

    # blank-refs-never-fabricated: empty/whitespace injected refs never produce a
    # fabricated v1.2 self_pull.
    blank_version, blank_self_pull = resolve_emitted_handoff_version(
        agent="lifecycle", injected_refs=("", "  "), specs_dir=None
    )
    assert blank_version == "handoff-v1.1"
    assert blank_self_pull is None


# --- ② gate accept-set widened param + reject-unknown-token --------------------------


@pytest.mark.parametrize("token", ["handoff-v1", "handoff-v1.1", "handoff-v1.2"])
def test_gates_accept_set_widened(token: str) -> None:
    """FR3 accept-set widening: gates accept {v1, v1.1, v1.2}; an unknown token outside
    that set is still rejected."""
    reasons: list[str] = []
    HandoffGateValidator()._schema_version({"schema_version": token}, reasons)
    assert reasons == []

    unknown_reasons: list[str] = []
    HandoffGateValidator()._schema_version({"schema_version": "handoff-v1.3"}, unknown_reasons)
    assert unknown_reasons == ["malformed schema_version"]
