"""Unit tests for JsonHarnessProfileStore — the A1 infra adapter (v0.1.58 FR2).

The stateless JSON adapter for the ``HarnessProfileStore`` port: round-trip write→read,
absent-file → ``None`` (all-four convention), idempotent write (no rewrite when the bytes
match), and the exact on-disk shape ``{"schema_version": "1", "harnesses": [...]}`` the
W3 ``public_assets`` read side and the inline ``WorkspaceService.init`` write depend on.
"""

from __future__ import annotations

import json
from pathlib import Path

from dadaia_workspace.core.models.harness_profile import HarnessProfile
from dadaia_workspace.infrastructure.json_harness_profile_store import JsonHarnessProfileStore


def _states(tmp_path: Path) -> Path:
    states = tmp_path / ".dadaia" / "states"
    states.mkdir(parents=True, exist_ok=True)
    return states


def test_read_absent_returns_none(tmp_path: Path) -> None:
    assert JsonHarnessProfileStore().read(_states(tmp_path)) is None


def test_write_then_read_round_trips(tmp_path: Path) -> None:
    states = _states(tmp_path)
    store = JsonHarnessProfileStore()
    store.write(states, HarnessProfile(schema_version="1", harnesses=("claude", "codex")))
    assert store.read(states) == HarnessProfile(schema_version="1", harnesses=("claude", "codex"))


def test_write_produces_canonical_shape(tmp_path: Path) -> None:
    states = _states(tmp_path)
    JsonHarnessProfileStore().write(states, HarnessProfile.of(("pi",)))
    data = json.loads((states / "harness_profile.json").read_text(encoding="utf-8"))
    assert data == {"schema_version": "1", "harnesses": ["pi"]}


def test_write_is_idempotent_no_rewrite_when_bytes_match(tmp_path: Path) -> None:
    states = _states(tmp_path)
    store = JsonHarnessProfileStore()
    store.write(states, HarnessProfile.of(("codex",)))
    path = states / "harness_profile.json"
    first_mtime = path.stat().st_mtime_ns

    store.write(states, HarnessProfile.of(("codex",)))

    assert path.stat().st_mtime_ns == first_mtime


def test_write_overwrites_on_changed_set(tmp_path: Path) -> None:
    states = _states(tmp_path)
    store = JsonHarnessProfileStore()
    store.write(states, HarnessProfile.of(("claude",)))
    store.write(states, HarnessProfile.of(("claude", "codex", "pi")))
    assert store.read(states) == HarnessProfile(
        schema_version="1", harnesses=("claude", "codex", "pi")
    )
