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


@pytest.mark.parametrize(
    ("case", "expected_ports", "expected_log_token"),
    [
        pytest.param(
            "invalid-json", [], "registry_file_malformed", id="invalid-json-returns-empty-registry"
        ),
        pytest.param(
            "missing-required-key",
            [3000, 3002],
            "registry_entry_malformed",
            id="missing-required-key-skips-entry-keeps-valid-ones",
        ),
        pytest.param(
            "wrong-type-for-port", [3500], "port_not_int", id="wrong-type-for-port-skips-entry"
        ),
        pytest.param("root-not-dict", [], "wrong_root_type", id="root-not-dict-returns-empty"),
        pytest.param(
            "missing-entries-list",
            [],
            "missing_entries_list",
            id="missing-entries-list-returns-empty",
        ),
        pytest.param("entry-not-a-dict", [3000], None, id="entry-not-a-dict-is-skipped"),
    ],
)
def test_malformed_registry_input_matrix(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
    case: str,
    expected_ports: list[int],
    expected_log_token: str | None,
) -> None:
    """The store never raises on malformed input; one bad entry never blanks the
    whole registry (skip-one-keep-rest), and every skip is logged."""
    states = _states_dir(tmp_path)

    if case == "invalid-json":
        text = "{not valid json"
    elif case == "missing-required-key":
        bad = _good_entry(port=3001)
        del bad["expires_at"]
        raw = {
            "version": "1",
            "range": {"min_port": 3000, "max_port": 3999},
            "entries": [_good_entry(port=3000), bad, _good_entry(port=3002)],
        }
        text = json.dumps(raw)
    elif case == "wrong-type-for-port":
        bad = _good_entry()
        bad["port"] = "3000"  # string instead of int
        raw = {
            "version": "1",
            "range": {"min_port": 3000, "max_port": 3999},
            "entries": [bad, _good_entry(port=3500)],
        }
        text = json.dumps(raw)
    elif case == "root-not-dict":
        text = "[1, 2, 3]"
    elif case == "missing-entries-list":
        text = '{"version": "1"}'
    else:  # entry-not-a-dict
        raw = {
            "version": "1",
            "range": {"min_port": 3000, "max_port": 3999},
            "entries": ["not a dict", 42, _good_entry(port=3000)],
        }
        text = json.dumps(raw)

    (states / "server_registry.json").write_text(text)

    store = JsonServerRegistryStore(states)
    with caplog.at_level(logging.WARNING):
        entries = store.list_all()

    assert [e.port for e in entries] == expected_ports
    if expected_log_token is not None:
        assert any(expected_log_token in rec.message for rec in caplog.records)


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


def test_save_after_recovery_from_corrupt_file(tmp_path: Path) -> None:
    """After an empty-from-corrupt load, save() must still work and write a clean
    file — the write path heals a corrupt registry rather than compounding it."""
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
