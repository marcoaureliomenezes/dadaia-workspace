"""Unit tests — install-ledger model + JSON store (mirrors json_plugin_store tests)."""

from __future__ import annotations

import json
from pathlib import Path

from dadaia_workspace.core.models.install_ledger import InstallLedger, LedgerEntry
from dadaia_workspace.infrastructure.json_install_ledger_store import JsonInstallLedgerStore


def _entry(rel: str = ".claude/rules/DADAIA.md") -> LedgerEntry:
    return LedgerEntry(relpath=rel, sha256="a" * 64, family="law")


def test_read_absent_returns_none(tmp_path: Path) -> None:
    assert JsonInstallLedgerStore().read(tmp_path) is None


def test_write_read_roundtrip(tmp_path: Path) -> None:
    store = JsonInstallLedgerStore()
    ledger = InstallLedger.of([_entry(), _entry(".codex/DADAIA.md")])
    store.write(tmp_path, ledger)
    assert store.read(tmp_path) == ledger
    assert (tmp_path / "install_ledger.json").is_file()


def test_write_is_idempotent(tmp_path: Path) -> None:
    store = JsonInstallLedgerStore()
    ledger = InstallLedger.of([_entry()])
    store.write(tmp_path, ledger)
    mtime = (tmp_path / "install_ledger.json").stat().st_mtime_ns
    store.write(tmp_path, ledger)
    assert (tmp_path / "install_ledger.json").stat().st_mtime_ns == mtime


def test_corrupt_ledger_reads_as_none_never_raises(tmp_path: Path) -> None:
    """A corrupt record degrades to bootstrap (prune nothing) — never to deletion."""
    (tmp_path / "install_ledger.json").write_text("{not json", encoding="utf-8")
    assert JsonInstallLedgerStore().read(tmp_path) is None
    (tmp_path / "install_ledger.json").write_text('{"schema_version": 3}', encoding="utf-8")
    assert JsonInstallLedgerStore().read(tmp_path) is None


def test_malicious_persisted_relpath_reads_as_none_never_raises(tmp_path: Path) -> None:
    """FR3 item 1: a persisted ledger carrying a traversal/absolute relpath must fail
    the SAME way any other malformed ledger does — ``LedgerEntry.__post_init__``
    raises ``ValueError`` while ``from_dict`` parses it, and ``read`` absorbs that into
    bootstrap semantics (record everything, prune nothing), never a crash or a write
    outside the workspace root."""
    for bad_relpath in ("../x", "/etc/passwd"):
        payload = json.dumps(
            {
                "schema_version": "1",
                "entries": [{"relpath": bad_relpath, "sha256": "a" * 64, "family": "law"}],
            }
        )
        (tmp_path / "install_ledger.json").write_text(payload, encoding="utf-8")
        assert JsonInstallLedgerStore().read(tmp_path) is None


def test_by_relpath_indexes_entries() -> None:
    ledger = InstallLedger.of([_entry("a"), _entry("b")])
    assert set(ledger.by_relpath()) == {"a", "b"}
