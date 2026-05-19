"""Resilience tests for JsonServerRegistryStore (v0.1.1 / Bug B).

The store MUST never raise on malformed input. One bad entry must not blank
the entire registry.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import pytest

from dadaia_workspace.core.models.server_registry import PortEntry
from dadaia_workspace.infrastructure.json_server_registry_store import (
    JsonServerRegistryStore,
)


def _states_dir(tmp_path: Path) -> Path:
    states = tmp_path / "states"
    states.mkdir()
    return states


def _good_entry(port: int = 3000, project: str = "demo") -> dict:
    return {
        "port": port,
        "project": project,
        "reserved_at": "2026-05-17T20:00:00Z",
        "expires_at": "2026-05-18T04:00:00Z",
        "url": f"http://localhost:{port}",
        "status": "active",
        "pid": 1234,
        "description": "test",
    }


def test_invalid_json_returns_empty_registry_and_logs_warning(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    states = _states_dir(tmp_path)
    (states / "server_registry.json").write_text("{not valid json")

    store = JsonServerRegistryStore(states)
    with caplog.at_level(logging.WARNING):
        entries = store.list_all()

    assert entries == []
    assert any("registry_file_malformed" in rec.message for rec in caplog.records)


def test_missing_required_key_skips_entry_keeps_valid_ones(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    states = _states_dir(tmp_path)
    bad = _good_entry(port=3001)
    del bad["expires_at"]
    raw = {
        "version": "1",
        "range": {"min_port": 3000, "max_port": 3999},
        "entries": [_good_entry(port=3000), bad, _good_entry(port=3002)],
    }
    (states / "server_registry.json").write_text(json.dumps(raw))

    store = JsonServerRegistryStore(states)
    with caplog.at_level(logging.WARNING):
        entries = store.list_all()

    assert [e.port for e in entries] == [3000, 3002]
    assert any("registry_entry_malformed" in rec.message for rec in caplog.records)


def test_wrong_type_for_port_skips_entry(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    states = _states_dir(tmp_path)
    bad = _good_entry()
    bad["port"] = "3000"  # string instead of int
    raw = {
        "version": "1",
        "range": {"min_port": 3000, "max_port": 3999},
        "entries": [bad, _good_entry(port=3500)],
    }
    (states / "server_registry.json").write_text(json.dumps(raw))

    store = JsonServerRegistryStore(states)
    with caplog.at_level(logging.WARNING):
        entries = store.list_all()

    assert [e.port for e in entries] == [3500]
    assert any("port_not_int" in rec.message for rec in caplog.records)


def test_extra_unknown_key_is_accepted_forward_compat(tmp_path: Path) -> None:
    states = _states_dir(tmp_path)
    entry = _good_entry(port=3000)
    entry["future_field_we_dont_know_about"] = {"nested": True}
    raw = {
        "version": "1",
        "range": {"min_port": 3000, "max_port": 3999},
        "entries": [entry],
    }
    (states / "server_registry.json").write_text(json.dumps(raw))

    store = JsonServerRegistryStore(states)
    entries = store.list_all()

    assert len(entries) == 1
    assert entries[0].port == 3000


def test_root_not_dict_returns_empty(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    states = _states_dir(tmp_path)
    (states / "server_registry.json").write_text("[1, 2, 3]")  # JSON array, not object

    store = JsonServerRegistryStore(states)
    with caplog.at_level(logging.WARNING):
        entries = store.list_all()

    assert entries == []
    assert any("wrong_root_type" in rec.message for rec in caplog.records)


def test_missing_entries_list_returns_empty(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    states = _states_dir(tmp_path)
    (states / "server_registry.json").write_text('{"version": "1"}')

    store = JsonServerRegistryStore(states)
    with caplog.at_level(logging.WARNING):
        entries = store.list_all()

    assert entries == []
    assert any("missing_entries_list" in rec.message for rec in caplog.records)


def test_entry_is_not_a_dict_is_skipped(tmp_path: Path) -> None:
    states = _states_dir(tmp_path)
    raw = {
        "version": "1",
        "range": {"min_port": 3000, "max_port": 3999},
        "entries": ["not a dict", 42, _good_entry(port=3000)],
    }
    (states / "server_registry.json").write_text(json.dumps(raw))

    store = JsonServerRegistryStore(states)
    entries = store.list_all()

    assert [e.port for e in entries] == [3000]


def test_save_after_recovery_from_corrupt_file(tmp_path: Path) -> None:
    """After an empty-from-corrupt load, save() must still work and write a clean file."""
    states = _states_dir(tmp_path)
    (states / "server_registry.json").write_text("garbage")

    store = JsonServerRegistryStore(states)
    new_entry = PortEntry(
        port=3500,
        project="newproject",
        reserved_at="2026-05-17T20:00:00Z",
        expires_at="2026-05-18T04:00:00Z",
        url="http://localhost:3500",
        pid=9999,
        description="post-recovery",
    )
    store.save(new_entry)

    # Re-read; the saved entry should be there and the file should be valid JSON.
    entries = store.list_all()
    assert len(entries) == 1
    assert entries[0].port == 3500
    # Verify file is valid JSON now
    json.loads((states / "server_registry.json").read_text())
