"""Tests for UTF-8 encoding correctness in JSON store I/O.

Non-ASCII round-trip and cleanup-on-success coverage for the package's one atomic-write
primitive itself (``core.atomic_write.atomic_write``) lives in
``tests/unit/core/test_atomic_write.py`` (v0.4.5 FR2/T-045-14: the eleven named/inline
writers this file used to exercise via ``_atomic_write_text`` are gone — every call site
now delegates directly to the primitive, so this file's remaining job is proving the
higher-level JSON store abstraction round-trips non-ASCII data end to end, not the
primitive's own byte-level contract).

Ensures that JSON stores (JsonContextStore, JsonServerRegistryStore) round-trip
non-ASCII data (paths, project names) correctly and the files on disk are valid UTF-8.
"""

from __future__ import annotations

import json
from pathlib import Path

# ---------------------------------------------------------------------------
# JSON store round-trip with non-ASCII data
# ---------------------------------------------------------------------------


def _make_ctx(name: str, repo_slug: str = "test-repo") -> object:
    from dadaia_workspace.core.models.spec_context import ContextState, SpecContextProject

    return SpecContextProject(
        name=name,
        state=ContextState.ALIVE,
        repo_slug=repo_slug,
        repo_url="https://github.com/example/test-repo",
        created_at="2026-06-09T00:00:00Z",
    )


def test_json_stores_roundtrip_non_ascii_and_valid_utf8(tmp_path: Path) -> None:
    """JsonContextStore and JsonServerRegistryStore both round-trip non-ASCII data
    (names/paths) correctly and the on-disk file is valid UTF-8."""
    from dadaia_workspace.infrastructure.json_context_store import JsonContextStore

    ctx_states_dir = tmp_path / "ctx-states"
    ctx_states_dir.mkdir()
    ctx_store = JsonContextStore(ctx_states_dir)

    name = "projet-café"
    ctx_store.save(_make_ctx(name))
    ctx_store.save(_make_ctx("日本語テスト", repo_slug="jp-repo"))

    contexts = ctx_store.list_all()
    assert any(c.name == name for c in contexts), "Context name should survive round-trip"
    assert any(c.name == "日本語テスト" for c in contexts)

    ctx_state_file = ctx_states_dir / "spec_contexts.json"
    ctx_raw = ctx_state_file.read_bytes()
    ctx_decoded = ctx_raw.decode("utf-8")  # must not raise
    ctx_data = json.loads(ctx_decoded)
    assert "contexts" in ctx_data

    from dadaia_workspace.core.models.server_registry import PortEntry
    from dadaia_workspace.infrastructure.json_server_registry_store import (
        JsonServerRegistryStore,
    )

    registry_states_dir = tmp_path / "registry-states"
    registry_states_dir.mkdir()
    registry_store = JsonServerRegistryStore(registry_states_dir)

    registry_store.save(
        PortEntry(
            port=3100,
            project="café-résumé-テスト",
            reserved_at="2026-06-09T00:00:00Z",
            expires_at="2026-06-09T08:00:00Z",
            url="http://localhost:3100",
        )
    )
    registry_store.save(
        PortEntry(
            port=3200,
            project="日本語プロジェクト",
            reserved_at="2026-06-09T00:00:00Z",
            expires_at="2026-06-09T08:00:00Z",
            url="http://localhost:3200",
        )
    )

    all_entries = registry_store.list_all()
    assert any(e.project == "café-résumé-テスト" for e in all_entries)
    assert any(e.project == "日本語プロジェクト" for e in all_entries)

    registry_state_file = registry_states_dir / "server_registry.json"
    registry_raw = registry_state_file.read_bytes()
    registry_raw.decode("utf-8")  # must not raise — verifies UTF-8 encoding on disk
